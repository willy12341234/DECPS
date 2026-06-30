"""
Evidence Chain RAG — rerank, citation binding, consistency verification, refusal.
Evidence chain principle: no retrieval = no answer, no evidence = refuse.

Flow:
  user_query → retrieve → rerank (denoise + threshold) →
  citation_bind → llm_generate → consistency_check →
    [OK] passed → return answer with citations
    [FAIL] failed → refuse / escalate
"""
import os, re, json, sys, numpy as np
from typing import Optional
from knowledge_base import get_kb

# ── Configurable thresholds ──
MIN_SIMILARITY_SCORE = 0.13       # Rerank minimum similarity threshold (insufficient evidence below this)
MIN_CITATION_SCORE = 0.30         # Minimum citation relevance (unreliable below this)
MAX_UNCITED_CLAIM_RATIO = 0.30    # Maximum ratio of uncited content in answer (inconsistent above this)

_SYS_PATH_SET = False

def _ensure_paths():
    global _SYS_PATH_SET
    if _SYS_PATH_SET: return
    _prj = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(_prj, 'training'))
    _SYS_PATH_SET = True

# ══════════════════════════════════════════════════
#  1. RETRIEVE
# ══════════════════════════════════════════════════

def retrieve_evidence(query: str, top_k: int = 10) -> list:
    """Retrieve raw chunks from knowledge base."""
    kb = get_kb()
    results = kb.retrieve(query, top_k=top_k)
    return results  # list of (chunk_dict, score)


# ══════════════════════════════════════════════════
#  2. RERANK — denoise + threshold filter
# ══════════════════════════════════════════════════

def _cross_encoder_score(query: str, chunk_text: str) -> float:
    """
    Lightweight cross-encoder rerank using keyword overlap + length penalty.
    比纯 embedding cosine 更精准地判断 query-chunk 相关性。
    """
    q_words = set(re.findall(r'[a-zA-Z0-9一-鿿]+', query.lower()))
    c_words = set(re.findall(r'[a-zA-Z0-9一-鿿]+', chunk_text.lower()))
    if not q_words or not c_words:
        return 0.0
    overlap = len(q_words & c_words)
    # Penalize very short or very long chunks
    len_penalty = min(1.0, len(chunk_text) / 200.0) if len(chunk_text) < 200 else min(1.0, 600.0 / len(chunk_text))
    jaccard = overlap / (len(q_words | c_words) + 1e-10)
    # Boost exact phrase matches
    phrase_boost = 1.2 if any(q in chunk_text for q in query.split() if len(q) > 2) else 1.0
    return float(jaccard * len_penalty * phrase_boost)


def rerank(query: str, results: list) -> dict:
    """
    Rerank retrieved chunks, filter by threshold.
    Returns:
    {
        'passed': bool,           # True if sufficient evidence
        'chunks': list,           # [(chunk, score), ...] filtered & sorted
        'max_score': float,
        'mean_score': float,
        'verdict': str,           # 'sufficient' | 'insufficient' | 'empty'
        'reason': str,            # Human-readable explanation
    }
    """
    if not results:
        return {
            'passed': False,
            'chunks': [],
            'max_score': 0.0,
            'mean_score': 0.0,
            'verdict': 'empty',
            'reason': '[FAIL] 知识库中未检索到任何相关信息',
        }

    # Rerank with cross-encoder style scoring
    scored = []
    for chunk, orig_score in results:
        rerank_score = _cross_encoder_score(query, chunk.get('text', ''))
        # Combine original embedding score + rerank score
        combined = 0.3 * orig_score + 0.7 * rerank_score
        scored.append((chunk, combined))

    # Sort by combined score descending
    scored.sort(key=lambda x: -x[1])
    max_score = scored[0][1] if scored else 0.0
    mean_score = float(np.mean([s for _, s in scored])) if scored else 0.0

    # Filter: keep only chunks above threshold
    filtered = [(c, s) for c, s in scored if s >= MIN_SIMILARITY_SCORE]

    if not filtered:
        top_text = scored[0][0].get('text', '')[:100] if scored else ''
        return {
            'passed': False,
            'chunks': [],
            'max_score': max_score,
            'mean_score': mean_score,
            'verdict': 'insufficient',
            'reason': f'[FAIL] 检索到的内容与问题相关度不足（最高分: {max_score:.2f}，阈值: {MIN_SIMILARITY_SCORE})。'
                      f'{" 最相关片段: " + top_text if top_text else ""}',
        }

    return {
        'passed': True,
        'chunks': filtered,
        'max_score': max_score,
        'mean_score': mean_score,
        'verdict': 'sufficient',
        'reason': f'[OK] 检索到 {len(filtered)} 条相关证据（最高分: {max_score:.2f}）',
    }


# ══════════════════════════════════════════════════
#  3. CITATION BINDING
# ══════════════════════════════════════════════════

def build_citation_context(rerank_result: dict) -> str:
    """Build a citation-tagged context string for the LLM prompt."""
    if not rerank_result['passed']:
        return ''

    lines = ['【检索到的证据（按相关度排序）】']
    for i, (chunk, score) in enumerate(rerank_result['chunks']):
        source = chunk.get('source', 'unknown')
        section = chunk.get('section', '')
        text = chunk.get('text', '')[:500]
        tag = f'[citation:{i+1}]'
        lines.append(f'\n{tag} 来源: {source} | 章节: {section} | 相关度: {score:.2f}')
    return '\n'.join(lines)

# ══════════════════════════════════════════════════
#  4. CONSISTENCY CHECK
# ══════════════════════════════════════════════════

def check_consistency(answer: str, rerank_result: dict) -> dict:
    """
    Verify that the LLM answer is supported by retrieved evidence.
    Returns:
    {
        'passed': bool,
        'uncited_claims': list,
        'unsupported_claims': list,
        'verdict': str,
        'reason': str,
    }
    """
    if not rerank_result['passed']:
        return {
            'passed': False,
            'uncited_claims': [],
            'unsupported_claims': [],
            'verdict': 'no_evidence',
            'reason': '[FAIL] 无可用证据，无法验证答案一致性',
        }

    # Check 1: Does the answer reference any citations at all?
    citation_refs = re.findall(r'【来源:\s*citation:(\d+)】', answer)
    source_tags = re.findall(r'\[citation:(\d+)\]', answer)
    all_refs = set(citation_refs + source_tags)

    if not all_refs:
        # No citations at all — check if answer is generic (refuse) or knowledge-based
        if len(answer) < 100:
            return {
                'passed': False,
                'uncited_claims': [answer[:100]],
                'unsupported_claims': [],
                'verdict': 'no_citations',
                'reason': '[WARN] 答案未引用任何证据来源，无法验证',
            }
        return {
            'passed': False,
            'uncited_claims': [answer[:200]],
            'unsupported_claims': [],
            'verdict': 'no_citations',
            'reason': '[WARN] 答案包含未引用证据的陈述，可能包含幻觉',
        }

    # Check 2: Do the referenced citations actually exist?
    valid_indices = set(range(1, len(rerank_result['chunks']) + 1))
    invalid_refs = [r for r in all_refs if int(r) not in valid_indices]
    if invalid_refs:
        return {
            'passed': False,
            'uncited_claims': [],
            'unsupported_claims': [f'引用编号不存在: citation:{", ".join(invalid_refs)}'],
            'verdict': 'hallucinated_citations',
            'reason': f'[FAIL] 答案引用了不存在的证据编号: citation:{", ".join(invalid_refs)} — 典型幻觉',
        }

    # Check 3: Estimate ratio of cited vs uncited content
    cited_sections = re.split(r'【来源:\s*citation:\d+】', answer)
    # If answer has long sections without citations after filtering, flag it
    uncited_segments = []
    for seg in cited_sections:
        clean = seg.strip()
        if len(clean) > 100 and not re.search(r'\(基于化学知识\)|基于我的知识|一般来说', clean):
            uncited_segments.append(clean)

    uncited_ratio = sum(len(s) for s in uncited_segments) / max(len(answer), 1)

    if uncited_ratio > MAX_UNCITED_CLAIM_RATIO and len(answer) > 200:
        return {
            'passed': False,
            'uncited_claims': uncited_segments[:3],
            'unsupported_claims': [],
            'verdict': 'high_uncited_ratio',
            'reason': f'[WARN] 答案中 {uncited_ratio:.0%} 的内容没有引用来源（阈值: {MAX_UNCITED_CLAIM_RATIO:.0%}）',
        }

    return {
        'passed': True,
        'uncited_claims': [],
        'unsupported_claims': [],
        'verdict': 'consistent',
        'reason': '[OK] 答案与引用证据一致',
    }


# ══════════════════════════════════════════════════
#  5. EVIDENCE CHAIN — full pipeline
# ══════════════════════════════════════════════════

class EvidenceChainResult:
    """Result of the full evidence chain pipeline."""
    def __init__(self, query: str):
        self.query = query
        self.retrieval = []
        self.rerank_result = None
        self.citation_context = ''
        self.answer = ''
        self.consistency = None
        self.should_refuse = False
        self.refuse_reason = ''

    @property
    def passed(self) -> bool:
        return (
            self.rerank_result is not None
            and self.rerank_result['passed']
            and self.consistency is not None
            and self.consistency['passed']
        )

    def to_dict(self) -> dict:
        return {
            'query': self.query,
            'passed': self.passed,
            'should_refuse': self.should_refuse,
            'refuse_reason': self.refuse_reason,
            'n_chunks': len(self.retrieval),
            'n_filtered': len(self.rerank_result['chunks']) if self.rerank_result else 0,
            'max_score': self.rerank_result['max_score'] if self.rerank_result else 0,
            'retrieval_verdict': self.rerank_result['verdict'] if self.rerank_result else 'empty',
            'consistency_verdict': self.consistency['verdict'] if self.consistency else 'unchecked',
            'rerank_reason': self.rerank_result['reason'] if self.rerank_result else '',
            'consistency_reason': self.consistency['reason'] if self.consistency else '',
        }


def run_evidence_chain(
    query: str,
    top_k: int = 10,
    skip_consistency: bool = False,
) -> EvidenceChainResult:
    """
    Full evidence-chain pipeline:
      retrieve → rerank → check_sufficiency → (optional) consistency_check

    If evidence is insufficient, sets should_refuse=True with reason.
    """
    result = EvidenceChainResult(query)

    # Step 1: Retrieve
    result.retrieval = retrieve_evidence(query, top_k=top_k)

    # Step 2: Rerank
    result.rerank_result = rerank(query, result.retrieval)

    # Step 2b: Check if we should refuse
    if not result.rerank_result['passed']:
        result.should_refuse = True
        result.refuse_reason = result.rerank_result['reason']
        return result

    # Step 3: Build citation context
    result.citation_context = build_citation_context(result.rerank_result)

    return result


def estimate_confidence(rerank_result: dict, default_threshold: float = 0.30) -> dict:
    """
    Estimate confidence based on evidence quality (Explicit Confidence Targets).
    基于证据质量、数量、多样性估算置信度，支持动态阈值调整。

    Returns:
    {
        'confidence_score': float,  # 0~1
        'should_answer': bool,      # confidence >= threshold?
        'threshold': float,
        'reason': str,
        'scoring_rule': str,        # scoring rule injected into the prompt
    }
    """
    if not rerank_result or not rerank_result.get('chunks'):
        return {
            'confidence_score': 0.0, 'should_answer': False,
            'threshold': default_threshold,
            'reason': 'No available evidence',
            'scoring_rule': '',
        }

    chunks = rerank_result['chunks']
    max_score = rerank_result['max_score']
    mean_score = rerank_result['mean_score']

    # 1) Evidence quality (0~1): combined top + mean similarity
    quality = 0.3 * max_score + 0.3 * mean_score

    # 2) Evidence quantity (0~1): how many chunks pass a moderate bar
    good_chunks = sum(1 for _, s in chunks if s >= 0.15)
    quantity = min(1.0, good_chunks / 3.0)

    # 3) Source diversity (0~1): more independent sources -> higher confidence
    sources = set(c.get('source', '') for c, _ in chunks)
    diversity = min(1.0, len(sources) / 2.0)

    # Combined
    confidence = 0.50 * quality + 0.30 * quantity + 0.20 * diversity

    # Dynamic threshold - calibrated for typical cross-encoder score range (0.10~0.35)
    threshold = default_threshold
    if max_score < 0.12:
        threshold = 0.50   # very weak evidence
    elif max_score < 0.16:
        threshold = 0.40   # weak evidence
    elif max_score < 0.20:
        threshold = 0.35   # moderate evidence

    should_answer = confidence >= threshold
    t = threshold

    scoring_rule = (
        "\n\n## [WARN] 置信度评分规则（必须遵守）\n"
        "每条结论按以下规则计分：\n"
        f"- 正确：+1 分\n"
        f"- 错误：-{t/(1-t):.1f} 分（t={t}，即错误扣 {t/(1-t):.1f} 分）\n"
        '- "我不确定" / "我没有足够的信息"：0 分\n\n'
        f"**策略：只有当你对某个结论的正确性有 >{t*100:.0f}% 的把握时，才应该回答。**\n"
        "如果不确定，请明确说「我不确定」或「我没有足够的信息」。\n"
        "猜测一个错误答案会严重扣分，不符合你的最佳利益。"
    )

    return {
        'confidence_score': round(confidence, 3),
        'should_answer': should_answer,
        'threshold': round(threshold, 2),
        'reason': (
            f'证据质量={quality:.2f} (max={max_score:.2f}, mean={mean_score:.2f}), '
            f'数量={quantity:.2f} ({good_chunks}条≥0.20), '
            f'来源={diversity:.2f} ({len(sources)}个)'
        ),
        'scoring_rule': scoring_rule,
    }


def check_answer_consistency(answer: str, rerank_result: dict) -> dict:
    """Public API for post-generation consistency check."""
    return check_consistency(answer, rerank_result)


# ══════════════════════════════════════════════════
#  TEST
# ══════════════════════════════════════════════════

if __name__ == '__main__':
    print('=== 证据链 RAG 测试 ===\n')

    # Test 1: Compatible query (should have evidence)
    q1 = '乳糖和伯胺类API在高温下会发生什么反应？'
    r1 = run_evidence_chain(q1)
    print(f'Q: {q1}')
    print(f'  检索: {len(r1.retrieval)} 条, 过滤后: {r1.rerank_result["verdict"]}')
    print(f'  最高分: {r1.rerank_result["max_score"]:.2f}')
    print(f'  拒答: {r1.should_refuse} | 原因: {r1.refuse_reason[:80]}')
    print()

    # Test 2: Unrelated query (should trigger refusal)
    q2 = '明天天气怎么样？'
    r2 = run_evidence_chain(q2)
    print(f'Q: {q2}')
    print(f'  检索: {len(r2.retrieval)} 条, 过滤后: {r2.rerank_result["verdict"]}')
    print(f'  最高分: {r2.rerank_result["max_score"]:.2f}')
    print(f'  拒答: {r2.should_refuse} | 原因: {r2.refuse_reason[:80]}')
    print()

    # Test 3: Consistency check
    good_answer = '根据美拉德反应规则【来源: citation:1】，还原糖的羰基与伯胺在高温下生成席夫碱。'
    bad_answer = '乳糖和伯胺在高温下会产生剧毒氰化物，需要特别注意防护。'
    print('一致性校验:')
    print(f'  合理答案: {check_answer_consistency(good_answer, r1.rerank_result)["verdict"]}')
    print(f'  幻觉答案: {check_answer_consistency(bad_answer, r1.rerank_result)["verdict"]}')