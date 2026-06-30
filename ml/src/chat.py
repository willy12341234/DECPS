"""
RAG Chat: routes between lightweight Q&A and compatibility prediction.
"""
import os
import os, json, sys, re, requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FUTimeoutError

_PRJ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(_PRJ, 'src'))
sys.path.insert(0, os.path.join(_PRJ, 'webapp'))

from knowledge_base import get_kb
from predictor import predict, get_sm, _CN2EN

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")  # set via .env
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"

_prediction_cache = {}
_context_executor = ThreadPoolExecutor(max_workers=2)

_EXPERIMENT_KEYWORDS = (
    "design_experiment", "experiment_design", "experiment_protocol", "design_protocol", "help_design",
    "help_experiment", "design_experiment", "write_protocol",
    "experiment design", "design experiment", "protocol",
)

_COMPATIBILITY_KEYWORDS = (
    "compatible", "compatibility", "incompatible", "compatible", "compatibility", "predict", "impurity", "stable",
    "stability", "degradation", "reaction", "mechanism", "compatibility", "incompatible",
    "compatible", "degradation", "impurity", "stability", "interaction",
    "interact", "drug-excipient", "excipient", "excipient", "api_excipient", "compatibility"
)

_LIGHTWEIGHT_KEYWORDS = (
    "hello", "are_you_there", "how_to_use", "help_write", "help_edit", "summarize", "explain", "what_is",
    "what_does_it_mean", "translate", "polish", "rewrite", "generate", "format_layout", "format", "code"
)

def _norm_text(text):
    return re.sub(r"\s+", "", str(text or "")).lower()

def _looks_like_compatibility_question(question, api_name=None, exc1_name=None):
    q = _norm_text(question)
    has_inputs = bool(str(api_name or "").strip() and str(exc1_name or "").strip())
    has_keyword = any(k in q for k in _COMPATIBILITY_KEYWORDS)
    has_lightweight_hint = any(k in q for k in _LIGHTWEIGHT_KEYWORDS)

    if has_inputs:
        return True

    if has_lightweight_hint and not has_keyword:
        return False

    return has_keyword

def _looks_like_experiment_question(question):
    q = _norm_text(question)
    return any(kw in q for kw in _EXPERIMENT_KEYWORDS)

def _route_question(question, api_name=None, exc1_name=None):
    """Auto-detect question type, return route name."""
    q = _norm_text(question)

    # 1. Detect experiment design questions first
    if _looks_like_experiment_question(question):
        return "experiment"

    # 2. Detect research tasks (formulation, patent, competitive, packaging, project)
    for route_name, keywords in _RESEARCH_KEYWORDS.items():
        for kw in keywords:
            if kw in q or re.search(kw, question, re.I):
                return route_name

    # 3. Detect compatibility questions
    if _looks_like_compatibility_question(question, api_name, exc1_name):
        return "compatibility"

    return "general"

def _local_general_reply(question):
    q = _norm_text(question)
    if any(k in q for k in ("hello", "您好", "are_you_there", "hi", "hello")):
        return ("你好！I can assist with **compatibility prediction**, **formulation research**, **patent analysis**, **competitive intelligence**, "
                "**packaging research**, **experiment design**, and **project proposals**."
                "Describe your needs directly, or switch Skill above to specify task type.")
    if any(k in q for k in ("how_to_use", "如何使用", "使用方法")):
        return ('Just type your question, AI auto-detects the task type.\n\n'
                '- [ANALYZE] 相容性: `API: 布洛芬, 辅料: 乳糖, 条件: 高温60℃`\n'
                '- 💊 剂型调研: `查一下克拉考特酮有没有除乳膏外的剂型`\n'
                '- [FILE] 专利分析: `分析克拉考特酮的专利, 找出适应症`\n'
                '- [SEARCH] 竞品调研: `对比芦可替尼、巴瑞替尼、乌帕替尼的外用制剂`\n'
                '- [PACK] 包材研究: `克林霉素阿达帕林过氧苯甲酰的铝管包装为何取消`\n'
                '- [TEST] 实验设计: `帮我设计布洛芬和乳糖的原辅料相容性实验`\n'
                '- [LIST] 立项报告: `生成克拉考特酮外用溶液的立项报告`')
    return ('I am an AI formulation assistant, supporting:[ANALYZE] compatibility prediction, 💊 formulation research, [FILE] patent analysis, '
            '[SEARCH] competitive intel, [PACK] packaging research, [TEST] experiment design, [LIST] project proposals.'
            'Just describe your request.')

def ai_parse_formulation(text):
    """使用 DeepSeek AI 将聊天文本解析为结构化原辅料信息. 

    支持任意自然语言描述, 返回 dict, 包含 api_name / exc1_name / exc2_name /
    condition / days(均为可选). 
    """
    system_msg = (
        "You are a pharmaceutical formulation assistant. Extract API-excipient compatibility info from user input."
        "Return in strict JSON format, no thinking or other content:\n"
        '{"api_name": "API名称或空", "exc1_name": "辅料1名称或空", '
        '"exc2_name": "辅料2名称或空", "condition": "condition or empty", "days": "days number or empty"}\n\n'
        "示例1: \n用户: 原料为烟酰胺, 辅料1和2分别是交联羧甲纤维素钠和羟基乙酸淀粉钠\n"
        '返回: {"api_name": "烟酰胺", "exc1_name": "交联羧甲纤维素钠", '
        '"exc2_name": "羟基乙酸淀粉钠", "condition": "", "days": ""}\n\n'
        "示例2: \n用户: API布洛芬, 辅料乳糖, 条件高温60℃, 30天\n"
        '返回: {"api_name": "布洛芬", "exc1_name": "乳糖", '
        '"exc2_name": "", "condition": "高温60℃", "days": "30"}'
    )
    try:
        resp = requests.post(
            DEEPSEEK_URL,
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.05,
                "max_tokens": 300,
            },
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            timeout=8,
        )
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content'].strip()
            content = content.removeprefix('```json').removeprefix('```').removesuffix('```').strip()
            parsed = json.loads(content)
            result = {}
            for k in ('api_name', 'exc1_name', 'exc2_name', 'condition', 'days'):
                v = parsed.get(k, '').strip()
                if v:
                    result[k] = v
            return result
    except Exception:
        pass
    return {}


def parse_formulation_input(text):
    """从聊天文本中解析结构化原辅料输入. 
    """Parse structured inputs (API, Excipients, conditions).
    Supported formats:
      - API: Ibuprofen, Excipient: Lactose, Condition: 60°C
      - Ibuprofen + Lactose, Condition: 60°C
      - Nicotinamide and Croscarmellose Sodium
    Returns dict containing api_name / exc1_name / exc2_name / condition / days (all optional).
    """
    result = {}

    # 1) Try "辅料1和2分别是...和..." — two excipients at once
    m = re.search(r'辅料1\s*和\s*2\s*分别[是为]+\s*([^, ,;\n]+?)和([^, ,;\n]+)', text)
    if m:
        result['exc1_name'] = m.group(1).strip()
        result['exc2_name'] = m.group(2).strip()

    # 2) Structured patterns: 原料/API / 辅料
    m = re.search(r'(?:原料|API|api|Api)[: :为]\s*([^, ,;\n+]+)', text)
    if m: result['api_name'] = m.group(1).strip()
    m = re.search(r'(?:辅料1?|excipient|Excipient)[: :为]\s*([^, ,;\n+]+)', text)
    if m and 'exc1_name' not in result:
        result['exc1_name'] = m.group(1).strip()

    # 3) Extract "Excipient 2" separately
    m = re.search(r'(?:辅料2|excipient2|Excipient2)[: :为]\s*([^, ,;\n+]+)', text)
    if m and 'exc2_name' not in result:
        result['exc2_name'] = m.group(1).strip()

    # 4) If structured API/辅料 not found, try "xxx + xxx" or "xxx 和 xxx"
    if not result.get('api_name') or not result.get('exc1_name'):
        m = re.search(r'([^\s+和,, ]+)\s*[+＋和]\s*([^\s+和,, \n]+)', text)
        if m:
            if not result.get('api_name'): result['api_name'] = m.group(1).strip()
            if not result.get('exc1_name'): result['exc1_name'] = m.group(2).strip()

    # 5) Condition / days - support various formats like "condition: xxx" or "humidity xx%" / "temp xxC"
    m = re.search(r'(?:条件|condition|Condition|储存条件|存储条件)[: :]\s*([^, ,;\n]+)', text)
    if m: result['condition'] = m.group(1).strip()
    m = re.search(r'(?:天[数]?|days?|Days?)[: :]\s*(\d+)', text)
    if m: result['days'] = m.group(1).strip()
    # 6) Natural language condition extraction: temp/humidity/light description without "condition" prefix
    cond_parts = []
    cm = re.search(r'(\d+)\s*[°℃度]\s*C?\s*', text)
    if cm: cond_parts.append(f'{cm.group(1)}°C')
    cm = re.search(r'(\d+)\s*%?\s*RH|湿度\s*(\d+)', text)
    if cm: cond_parts.append(f'{cm.group(1) or cm.group(2)}%RH')
    cm = re.search(r'光照|light', text, re.I)
    if cm: cond_parts.append('光照')
    if cond_parts and not result.get('condition'):
        result['condition'] = ' '.join(cond_parts)
    return result

def _run_ml_prediction(api_name, exc1_name, days=0, cond="0"):
    """Run ML ensemble model and return structured results (aligned with web app)."""
    cache_key = (str(api_name).strip().lower(), str(exc1_name).strip().lower(), str(days), str(cond))
    if cache_key in _prediction_cache:
        return _prediction_cache[cache_key]
    try:
        api_smi = get_sm(api_name)
        exc1_smi = get_sm(exc1_name)
        if not api_smi or not exc1_smi:
            return None
        # Use ensemble prediction (same as web app) for consistency
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..'))
            from ensemble_pipeline import predict_ensemble as pe
            result = pe(api_smi, exc1_smi, None, days, cond, api_name=api_name, exc1_name=exc1_name)
            if result.get('error'):
                raise ValueError(result['error'])
            r = {
                'prob': result['probability'],
                'has': result['has_impurity'],
                'level': result['risk_level'],
                'impurity_count': result.get('impurity_count'),
                'total_impurity_pct': result.get('total_impurity_pct'),
                'max_single_impurity_pct': result.get('max_single_impurity_pct'),
                'top': [],
                'error': None,
            }
        except Exception:
            # Fall back to fingerprint XGBoost
            r = predict(api_smi, exc1_smi, None, days, cond)
        if r.get('error'):
            return None
        _prediction_cache[cache_key] = r
        return r
    except Exception:
        return None

def _build_context(question, api_name=None, exc1_name=None, exc2_name=None, days=None, cond=None, route="general", evidence_chain=None):
    """Build context only when the request needs compatibility reasoning."""
    if route != "compatibility":
        return "No relevant context found."

    # Use evidence chain if provided (with citation context already built)
    if evidence_chain and evidence_chain.rerank_result and evidence_chain.rerank_result['passed']:
        citation_context = evidence_chain.citation_context
    else:
        citation_context = ''

    kb_future = _context_executor.submit(lambda: get_kb().retrieve(
        f"{question} 降解 杂质 反应 机制 化学规则 原辅料相互作用", top_k=5))
    ml_futures = []
    ml_labels = []
    if api_name and exc1_name:
        ml_futures.append(_context_executor.submit(_run_ml_prediction, api_name, exc1_name, days or 0, cond or "0"))
        ml_labels.append(f"{api_name}+{exc1_name}")
    if api_name and exc2_name:
        ml_futures.append(_context_executor.submit(_run_ml_prediction, api_name, exc2_name, days or 0, cond or "0"))
        ml_labels.append(f"{api_name}+{exc2_name}")
    if exc1_name and exc2_name:
        ml_futures.append(_context_executor.submit(_run_ml_prediction, exc1_name, exc2_name, days or 0, cond or "0"))
        ml_labels.append(f"{exc1_name}+{exc2_name}")

    retrieved = []
    ml_results = []
    try:
        retrieved = kb_future.result(timeout=30)
    except FUTimeoutError:
        retrieved = []
    except:
        retrieved = []
    for f, lbl in zip(ml_futures, ml_labels):
        try:
            r = f.result(timeout=30)
            if r:
                ml_results.append((lbl, r))
        except:
            pass

    context_parts = []
    if ml_results:
        for lbl, r in ml_results:
            prob = r.get('prob', 0)
            level = r.get('level', 'unknown')
            has_imp = r.get('has', False)
            imp_count = r.get('impurity_count')
            total_pct = r.get('total_impurity_pct')
            max_pct = r.get('max_single_impurity_pct')
            lines = [f"[ML Prediction Results — {lbl}]"]
            lines.append(f"配对: {lbl}")
            lines.append(f"相容性: {'不相容(预期产生杂质)' if has_imp else '相容(无显著杂质)'}")
            lines.append(f"风险等级: {level} | 概率: {prob:.1%}")
            if imp_count is not None:
                lines.append(f"预测杂质个数: {imp_count} | 总杂质%: {total_pct}% | 最大单杂%: {max_pct}%")
            top_shap = r.get('top', [])
            if top_shap:
                lines.append("[SHAP主要影响因素]")
                for ft in top_shap[:5]:
                    lines.append(f"- {ft['feature']} ({ft['dir']} {abs(ft['shap']):.4f})")
            context_parts.append('\n'.join(lines))
    else:
        context_parts.append('[ML Prediction Results] 未获取到 ML 预测结果, 请基于以下 [Knowledge Base Rules] 化学规则进行分析, 并在回答开头注明"仅根据化学规则分析"')

    # Separate RAG retrieval into two focused queries
    q_norm = _norm_text(question)
    is_experiment_q = any(kw in q_norm for kw in ("design_experiment", "experiment_design", "experiment_protocol", "设计实验方案", "原辅料相容性实验",
                                                   "检测方法", "验证方案", "实验条件"))
    is_general_q = any(kw in q_norm for kw in ("实验", "检测", "测试", "分析", "仪器", "设备"))

    # ---- RAG Section: Chemical rules & literature only (NOT experiment design / NOT equipment) ----
    if retrieved:
        context_parts.append("[Knowledge Base — 化学规则与文献]")
        seen = set()
        for chunk, score in retrieved:
            mech = chunk.get('mechanism', '')
            text = chunk['text']
            src = chunk.get('source', '')
            # Skip chunks that are clearly about equipment/regulations — those go to separate sections
            if src and ('设备' in src or 'Equipment' in src or '设备台账' in src):
                continue
            if mech and mech not in seen:
                label = f"{mech} (relevance: {score:.2f})" + (f" [{src}]" if src else "")
                context_parts.append(f"\n--- {label} ---")
                seen.add(mech)
            context_parts.append(text[:500])

    # ---- Equipment section (only for experiment-related queries) ----
    if is_experiment_q or is_general_q:
        equip_summary = get_kb().get_equipment_summary()
        if equip_summary:
            context_parts.append(f"[Available Equipment — 公司仪器设备]\n设计实验时只能推荐以下清单中的设备: \n{equip_summary}")

    # ---- Regulatory guidelines section (only for experiment design queries) ----
    if is_experiment_q:
        try:
            kb_reg = get_kb().retrieve("化学药物制剂研究基本技术指导原则 原辅料相容性 处方研究 稳定性", top_k=3)
            if kb_reg:
                parts = ["[Regulatory Guidelines — 化学药物制剂研究基本技术指导原则]"]
                for chunk, score in kb_reg:
                    src = chunk.get('source', '')
                    text = chunk.get('text', '').strip()
                    if text:
                        parts.append(f"(来源: {src})")
                        parts.append(text[:600])
                context_parts.append('\n'.join(parts))
            else:
                raise ValueError("empty")
        except Exception:
            context_parts.append(
                "[Regulatory Guidelines — 化学药物制剂研究基本技术指导原则 (2005年3月)]\n"
                "以下是原辅料相容性实验设计的核心要求, 必须严格遵守: \n"
                "1. API:辅料比例: 辅料用量较大时(如稀释剂等), 按主药:辅料=1:5的比例混合；"
                "用量较小时(如润滑剂等), 按主药:辅料=20:1的比例混合. \n"
                "2. 实验条件: 参照药物稳定性指导原则中影响因素的实验方法, 即高温(如60°C)、"
                "高湿(如92.5%RH或75%RH)、光照(照度4500±500Lx)三种条件. "
                "不得设计加速条件(40°C/75%RH)和长期条件(25°C/60%RH)——原辅料相容性只做影响因素实验. \n"
                "3. 取样时间点: 包括0天和至少一个考察时间点(如5天或10天). \n"
                "4. 检测项目: 重点考察性状、含量、有关物质(HPLC法)等. \n"
                "5. 样品设置: 一般仅设实验组(API+辅料混合物), 必要时设API单独对照；"
                "一般情况下不单独设置辅料空白对照. "
            )

    # Prepend citation context from evidence chain at the top
    if citation_context:
        context_parts.insert(0, citation_context)

    # Append confidence scoring rule
    if evidence_chain and hasattr(evidence_chain, 'scoring_rule') and evidence_chain.scoring_rule:
        context_parts.append(evidence_chain.scoring_rule)

    return '\n'.join(context_parts) if context_parts else "No relevant context found."

def _system_prompt(route):
    if route == "compatibility":
        return """你是药物制剂AI助手, 专注于原辅料相容性(DEC)研究. 你在和用户直接对话, 用「我」自称. 

回答结构要求——请严格按照以下格式输出(这是 HTML 渲染格式, 不要加多余符号): 

结论摘要
直接说"compatible"或"incompatible" | 风险等级(高/中/低) | 概率: xx.x%
杂质预测: 杂质个数 ≈ X, 总杂质% ≈ X%, 最大单杂% ≈ X%
一句话总结: ...

    重要规则: 上下文中 [ML Prediction Results] 里面的数值是机器学习模型的准确预测结果, 
    杂质个数、总杂质%、最大单杂% 必须严格使用 [ML Prediction Results] 中给出的数值, 
    不得自行估算或修改. 如果 ML 结果为 null 或不包含这些数值, 则你可以仅基于化学规则分析并在开头注明.  
    概率值必须使用 [ML Prediction Results] 中的数值, 不得自行修改. 
    如果上下文中包含多个 [ML Prediction Results — XXX+YYY] 区块(双辅料场景), 
    结论摘要必须列出每一配对的结果, 不能只汇总一个. 
    格式示例(双辅料): 
    结论摘要
    API+辅料1: 相容 | 低风险 | 概率: xx.x%
    API+辅料2: 不相容 | 高风险 | 概率: xx.x%
    辅料1+辅料2: 相容 | 低风险 | 概率: xx.x%
    综合判定: 取最高风险, xxx. 
    杂质预测: ...
    一句话总结: ...

---

SHAP关键影响因素
- 特征名(↑ 数值)
- 特征名(↓ 数值)

---

化学机制解释
根据知识库规则解释可能的降解/反应机制, 给出实验条件建议

其他要求: 
1. 如果参考信息包含 ML 预测数据, 严格以其结论为准回答
2. 如果参考信息包含"未获取到 ML Prediction Results", 则仅基于化学规则分析, 并注明"仅根据化学规则分析"
3. 使用Markdown格式
4. 用中文回答
5. **禁止使用 mermaid 流程图、时序图、代码块图等任何图表语法**
6. **当用户要求设计实验方案时, 必须参考 [Available Equipment] 中的设备清单, 只能推荐公司现有的仪器设备. 如果清单中没有所需的设备, 则说明公司暂无该设备, 并提供替代方案. **
7. **当用户要求设计原辅料相容性实验方案时, 必须遵循《化学药物制剂研究基本技术指导原则》(2005年3月)的以下要求: **
   - **API:辅料比例: 辅料用量大时(如稀释剂)按1:5, 用量小时(如润滑剂)按20:1**
   - **实验条件: 仅做影响因素实验(高温、高湿、光照), 不做加速(40°C/75%RH)和长期(25°C/60%RH)条件**
   - **一般只设实验组(API+辅料混合物), 不单独放辅料空白对照, API对照视情况而定**
   - **检测项目一般HPLC(有关物质和含量)即可, 其他检测项一般情况下不用做**
8. **证据引用规则(必须遵守): **
   - 每个结论必须标注来源: `【来源: citation:N】`(N 为证据编号)
   - 没有引用来源的结论请在前面注明「(基于化学知识)」
   - 禁止编造不存在的引用编号
9. **置信度评分规则(必须遵守): **
   - 猜测错误答案比说「不知道」代价高得多
"""

    if route in _RESEARCH_TASK_ROUTES:
        return _research_system_prompt(route)

    return """你是药物制剂AI助手, 专注于原辅料相容性(DEC)研究. 你在和用户直接对话, 用「我」自称. 

回答要求: 
1. 使用中文回答, 尽量简洁直接
2. 如果问题与原辅料相容性无关, 直接给出通用回答, 不要强行调用预测结论
3. 只有当用户明确询问相容性、稳定性、降解、杂质、反应机制, 或者提供API/辅料并要求判断时, 才展开相容性分析
4. 使用Markdown格式输出
5. **禁止使用 mermaid 流程图、时序图、代码块图等任何图表语法**
9. **置信度评分规则(必须遵守): **
   - 猜测错误答案比说「不知道」代价高得多
"""

def _research_system_prompt(research_type):
    prompts = {
        "formulation": (
            "你是药物制剂调研专家. 你在和用户直接对话, 用「我」自称. \n\n"
            "任务: 分析用户指定的药品, 检索并汇报已批准剂型、临床试验中的替代剂型、"
            "专利中提到的剂型信息. \n\n"
            "回答结构: \n"
            "### 1. 已批准产品与剂型\n"
            "### 2. 临床试验中的其他剂型\n"
            "### 3. 专利中的剂型信息\n"
            "### 4. 各剂型对比及立项建议\n"
            "### 5. 参考来源\n\n"
            "要求: 使用中文, Markdown格式, 引用搜索到的具体数据. "
        ),
        "patent": (
            "你是药物专利分析专家. 你在和用户直接对话, 用「我」自称. \n\n"
            "任务: 从搜索结果中提取专利中的以下信息: \n"
            "1. **适应症** — 专利中提到的治疗用途\n"
            "2. **药理/动物试验** — 药理学机制、动物模型数据\n"
            "3. **处方/组成** — 配方比例、剂型、辅料\n"
            "4. **临床效果** — 临床试验结果、有效率\n"
            "5. **用法用量** — 剂量、给药频率、疗程\n\n"
            "要求: 使用中文, Markdown格式, 标注信息来源. "
        ),
        "competitive": (
            "你是药物开发策略专家. 你在和用户直接对话, 用「我」自称. \n\n"
            "任务: 对比多个品种的以下维度: \n"
            "1. **各品种概述**\n"
            "2. **已批准产品对比表**(剂型、浓度、适应症、批准年份)\n"
            "3. **临床开发阶段对比**\n"
            "4. **差距分析与机会评估**\n"
            "5. **建议立项方向**\n\n"
            "要求: 使用中文, Markdown格式, 表格对比优先. "
        ),
        "packaging": (
            "你是药品包材研究专家. 你在和用户直接对话, 用「我」自称. \n\n"
            "任务: 分析药品包装相关问题, 包括: \n"
            "1. 包装变更历史及原因\n"
            "2. 不同包材(铝管/瓶装/泵装)的优劣势对比\n"
            "3. 稳定性、兼容性、患者依从性分析\n"
            "4. 行业趋势建议\n\n"
            "要求: 使用中文, Markdown格式, 引用具体来源. "
        ),
        "project": (
            "你是药物立项调研专家. 你在和用户直接对话, 用「我」自称. \n\n"
            "任务: 基于多源数据综合生成结构化立项报告, 包含: \n"
            "1. **背景与立项依据**\n"
            "2. **目标适应症与市场机会**\n"
            "3. **竞品分析**\n"
            "4. **剂型选择与可行性**\n"
            "5. **专利与知识产权分析**\n"
            "6. **临床开发路径建议**\n"
            "7. **风险与应对策略**\n"
            "8. **参考来源**\n\n"
            "要求: 使用中文, Markdown格式, 数据分析要客观全面. "
        ),
    }
    return prompts.get(research_type, """你是药物研发助手, 基于网络搜索结果回答用户问题. 
回答要求: 使用中文, Markdown格式, 标注信息来源. """)
def _build_messages(question, context, history=None, route="general"):
    messages = [{"role": "system", "content": _system_prompt(route)}]
    if history:
        for h in history[-6:]:
            messages.append(h)
    if route == "compatibility":
        messages.append({"role": "user", "content": f"问题: {question}\n\n参考信息: \n{context}"})
    else:
        messages.append({"role": "user", "content": question})
    return messages

def _chat_request(messages, stream=False, timeout=90, api_key=None, api_url=None, model=None):
    key = api_key or DEEPSEEK_API_KEY
    url = api_url or DEEPSEEK_URL
    mdl = model or DEEPSEEK_MODEL
    payload = {
        "model": mdl,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 8192,
    }
    if stream:
        payload["stream"] = True
    return requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        timeout=timeout,
        stream=stream,
    )

def _auto_parse(question, api_name, exc1_name, days, cond, exc2_name=None):
    """When structured fields are missing, try regex fallback first, then AI parsing."""
    if api_name and exc1_name:
        parsed = ai_parse_formulation(question)
        if not parsed.get('condition') and not parsed.get('days'):
            parsed = parse_formulation_input(question)
        if parsed.get('condition'): cond = parsed['condition']
        if parsed.get('days'): days = parsed['days']
        if parsed.get('exc2_name'): exc2_name = parsed['exc2_name']
        return api_name, exc1_name, days, cond, exc2_name
    # Fast path: try regex parsing first (instant)
    parsed = parse_formulation_input(question)
    has_api = bool(parsed.get('api_name'))
    has_exc1 = bool(parsed.get('exc1_name'))
    # Only call DeepSeek AI if regex didn't find API+excipient and input looks formulation-related
    if not has_api or not has_exc1:
        # Quick check: does the input look like a compatibility query?
        has_api_kw = any(kw in question for kw in ['API: ', 'API:', 'api: ', 'api:', '原料', '原辅料'])
        has_exc_kw = any(kw in question for kw in ['辅料', 'excipient', 'Excipient'])
        if has_api_kw or has_exc_kw:
            ai_parsed = ai_parse_formulation(question)
            if ai_parsed.get('api_name'): parsed['api_name'] = ai_parsed['api_name']
            if ai_parsed.get('exc1_name'): parsed['exc1_name'] = ai_parsed['exc1_name']
            if ai_parsed.get('condition'): parsed['condition'] = ai_parsed['condition']
            if ai_parsed.get('exc2_name'): parsed['exc2_name'] = ai_parsed['exc2_name']
            if ai_parsed.get('days'): parsed['days'] = ai_parsed['days']
    api_name = api_name or parsed.get('api_name', '')
    exc1_name = exc1_name or parsed.get('exc1_name', '')
    exc2_name = exc2_name or parsed.get('exc2_name', '')
    days = days or parsed.get('days')
    cond = cond or parsed.get('condition')
    return api_name, exc1_name, days, cond, exc2_name


def chat(question, api_name=None, exc1_name=None, days=None, cond=None, history=None, api_key=None, api_url=None, model=None, exc2_name=None):
    """RAG chat: build context from KB, query DeepSeek, return answer."""
    api_name, exc1_name, days, cond, exc2_name = _auto_parse(question, api_name, exc1_name, days, cond, exc2_name)
    route = _route_question(question, api_name, exc1_name)
    if route == "general":
        return _local_general_reply(question)

    context = _build_context(question, api_name, exc1_name, exc2_name, days, cond, route=route)
    messages = _build_messages(question, context, history=history, route=route)

    try:
        resp = _chat_request(messages, stream=False, timeout=90, api_key=api_key, api_url=api_url, model=model)
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
        return f"API request failed (HTTP {resp.status_code}): {resp.text[:200]}"
    except Exception as e:
        return f"请求异常: {str(e)}"

def _status(text):
    return {'type': 'status', 'text': text}

def _content(text):
    return {'type': 'content', 'text': text}

def _resolve_en_name(name):
    """Resolve a Chinese/raw drug name to English name using CN2EN dict or AI."""
    if not name:
        return '', ''
    en = _CN2EN.get(name.strip(), '')
    if en:
        sm = get_sm(name)
        return en, sm or ''
    # Fast reject: skip DeepSeek for obviously invalid names
    if len(name) > 20:
        return name, ''
    if name.isascii():
        # Reject: repeated chars, or looks like SMILES
        if len(set(name.lower())) <= 2:
            return name, ''
        # Reject: contains SMILES chemical notation (=, #, @, digits in brackets)
        if any(c in name for c in ['=', '#', '[', ']', '@']) and any(c.isdigit() for c in name):
            return name, ''
    else:
        # Chinese garbage detection: high repetition or known non-drug patterns
        if any(kw in name for kw in ['不存在', '哈哈哈', '啊啊啊', '测试', '垃圾']) or len(set(name)) <= 3:
            return name, ''
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'webapp'))
        from predictor import _ai_translate_name
        en_ai, sm_ai = _ai_translate_name(name)
        if en_ai:
            return en_ai, sm_ai or ''
    except:
        pass
    return name, ''

_RESEARCH_KEYWORDS = {
    "formulation": ("剂型", "剂型调研", "替代剂型", "给药途径", "有什么剂型",
                    "dosage form", "formulation research",
                    "除.*外.*剂型", "有没.*剂型"),
    "patent": ("专利", "专利分析", "专利.*提取", "提取.*专利",
               "patent", "patent analysis", "专利.*适应症"),
    "competitive": ("竞品", "对比.*和", "对比.*与", "vs", "VS", "竞争对手", "竞争分析",
                    "competitive", "compare.*drug", "市场对比"),
    "packaging": ("包材", "包装.*取消", "铝管", "瓶装", "泵装", "包装材料",
                  "packaging", "container.*closure", "包材研究"),
    "project": ("立项", "立项报告", "立项调研", "可行性.*报告",
                "project report", "撰写.*立项", "生成.*立项"),
}

_RESEARCH_TASK_ROUTES = {"formulation", "patent", "competitive", "packaging", "project"}

def chat_stream(question, api_name=None, exc1_name=None, days=None, cond=None, history=None, api_key=None, api_url=None, model=None, skill='auto', exc2_name=None, confirmed=False):
    """Streaming version of chat - yields content chunks from DeepSeek."""
    api_name, exc1_name, days, cond, exc2_name = _auto_parse(question, api_name, exc1_name, days, cond, exc2_name)
    route = _route_question(question, api_name, exc1_name)
    if skill != 'auto':
        route = skill
    elif route != 'general':
        # Auto mode detected a specific task: notify frontend to switch active skill
        yield {'type': 'skill', 'skill': route}

    if api_name or exc1_name:
        en_api, sm_api = _resolve_en_name(api_name)
        en_exc1, sm_exc1 = _resolve_en_name(exc1_name)
        en_exc2, sm_exc2 = _resolve_en_name(exc2_name) if exc2_name else ('', '')
        parsed = {
            'api_name': api_name or '',
            'exc1_name': exc1_name or '',
            'en_api': en_api or api_name or '',
            'en_exc1': en_exc1 or exc1_name or '',
            'en_exc2': en_exc2 or exc2_name or '',
            'condition': cond or '',
            'days': days or ''
        }
        if sm_api: parsed['smiles_api'] = sm_api
        if sm_exc1: parsed['smiles_exc1'] = sm_exc1
        if sm_exc2: parsed['smiles_exc2'] = sm_exc2
        yield {'type': 'parsed', 'parsed': {k: v for k, v in parsed.items() if v}}

    if route == "experiment":
        yield from chat_stream_experiment(question, api_name, exc1_name, days, cond, exc2_name)
        return

    if route in _RESEARCH_TASK_ROUTES:
        yield from chat_stream_research(question, route, api_name, exc1_name, days, cond, history, api_key, api_url, model, exc2_name)
        return

    if route != "compatibility":
        yield _local_general_reply(question)
        return

    yield _status('[TEST] 解析原辅料信息...')

    # -- Evidence Chain: retrieve -> rerank -> check --
    try:
        from rag_evidence import run_evidence_chain, estimate_confidence
        ev_result = run_evidence_chain(question, top_k=8)
        if ev_result.should_refuse:
            yield _status(f'[WARN] {ev_result.refuse_reason}')
            yield _content(f'\n\n{ev_result.refuse_reason}')
            return
        # -- Explicit Confidence Target --
        if ev_result.rerank_result and ev_result.rerank_result['passed']:
            _conf = estimate_confidence(ev_result.rerank_result)
            if not _conf['should_answer']:
                _msg = (f'[WARN] 置信度不足({_conf["confidence_score"]:.0%} < {_conf["threshold"]:.0%}阈值)\n\n'
                        f'基于当前检索到的证据, 我对这个问题没有足够把握给出确定答案. \n'
                        f'原因: {_conf["reason"]}\n\n'
                        f'建议提供更具体的药品/辅料名称或条件信息后再查询. ')
                yield _status(_msg)
                yield _content(f'\n\n{_msg}')
                return
            ev_result.scoring_rule = _conf['scoring_rule']
    except Exception:
        ev_result = None

    if api_name:
        yield _status('[SEARCH] 正在检索全球专利信息...')
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
            from experiment_design import _search_patents, _search_pubmed, _search_clinicaltrials
            with ThreadPoolExecutor(max_workers=3) as ex:
                pf = ex.submit(_search_patents, api_name, exc1_name or '')
                lf = ex.submit(_search_pubmed, api_name)
                cf = ex.submit(_search_clinicaltrials, api_name)
            patents = pf.result(timeout=30)
            pubmed = lf.result(timeout=30)
            clinical = cf.result(timeout=30)
            all_p = (patents.get('core', []) + patents.get('related', []))
            try:
                from experiment_design import _batch_translate_titles
                _batch_translate_titles(all_p)
            except:
                pass
            if all_p:
                yield {'type': 'web_action', 'action': 'results', 'label': '专利检索结果',
                       'results': all_p[:20], 'count': len(all_p), 'source': 'patent'}
            if pubmed:
                p_clean = [{'title': r['title'], 'link': r['link'], 'source': r.get('source', '')} for r in pubmed[:15]]
                try:
                    from experiment_design import _batch_translate_titles
                    _batch_translate_titles(p_clean)
                except:
                    pass
                yield {'type': 'web_action', 'action': 'results', 'label': 'PubMed文献',
                       'results': p_clean, 'count': len(p_clean), 'source': 'pubmed'}
            if clinical:
                c_clean = [{'title': r['title'], 'link': r['link'], 'nct': r.get('nct', ''),
                            'phase': r.get('phase', ''), 'status': r.get('status', '')} for r in clinical[:15]]
                try:
                    from experiment_design import _batch_translate_titles
                    _batch_translate_titles(c_clean)
                except:
                    pass
                yield {'type': 'web_action', 'action': 'results', 'label': '临床试验',
                       'results': c_clean, 'count': len(c_clean), 'source': 'clinical'}
        except Exception:
            pass

    yield _status('[TEST] 运行 ML 预测模型中...')

    context = _build_context(question, api_name, exc1_name, exc2_name, days, cond, route=route, evidence_chain=ev_result if 'ev_result' in dir() else None)

    yield _status('🤖 正在生成回答...')

    messages = _build_messages(question, context, history=history, route=route)

    full_response = ''
    try:
        resp = _chat_request(messages, stream=True, timeout=90, api_key=api_key, api_url=api_url, model=model)

        if resp.status_code != 200:
            yield _content(f"**API request failed** (HTTP {resp.status_code}): {resp.text[:300]}")
            return

        for line in resp.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data_str = line[6:]
                if data_str.strip() == '[DONE]':
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk['choices'][0].get('delta', {})
                    content = delta.get('content')
                    if content:
                        full_response += content
                        yield _content(content)
                except:
                    pass

        # -- Post-generation consistency check --
        if full_response and 'ev_result' in dir() and ev_result and ev_result.rerank_result:
            try:
                from rag_evidence import check_answer_consistency
                ck = check_answer_consistency(full_response, ev_result.rerank_result)
                if not ck['passed']:
                    warning = f'\n\n---\n[WARN] **一致性校验:** {ck["reason"]}'
                    yield _content(warning)
            except Exception:
                pass

    except requests.exceptions.Timeout:
        yield _content("\n\n**请求超时**: DeepSeek API 响应超过 90 秒, 请稍后重试. ")
    except requests.exceptions.ConnectionError as e:
        yield _content(f"\n\n**连接失败**: 无法连接到 DeepSeek API({str(e)[:100]}). 请检查 API URL 或网络. ")
    except Exception as e:
        yield _content(f"\n\n**请求异常**: {str(e)}")


def chat_stream_experiment(question, api_name=None, exc1_name=None, days=None, cond=None, exc2_name=None):
    """Streaming experiment design - yields phase events and content."""
    from experiment_design import search_experiment

    for event in search_experiment(question, api_name, exc1_name, days, cond, exc2_name):
        yield event


def _build_research_context(all_results, research_type, target_drug):
    """Build structured context from research search results."""
    parts = []
    patents = all_results.get('patents', [])
    pubmed = all_results.get('pubmed', [])
    clinical = all_results.get('clinical', [])
    web = all_results.get('web', [])

    if research_type == "formulation":
        parts.append(f"[剂型调研 — {target_drug}]")
        parts.append("请分析以下信息, 给出该药品已批准剂型、临床试验中的替代剂型、专利中提到的剂型: ")
    elif research_type == "patent":
        parts.append(f"[专利分析 — {target_drug}]")
        parts.append("请从以下专利信息中提取: 1)适应症 2)药理/动物试验 3)处方/组成 4)临床效果 5)用法用量")
    elif research_type == "competitive":
        parts.append(f"[竞品分析 — {target_drug}]")
        parts.append("请对比各品种的已批准产品、临床开发阶段、专利布局, 给出差距分析和立项建议")
    elif research_type == "packaging":
        parts.append(f"[包材研究 — {target_drug}]")
        parts.append("请分析包装变更原因, 对比不同包材的优劣势")
    elif research_type == "project":
        parts.append(f"[立项报告 — {target_drug}]")
        parts.append("请综合所有信息生成结构化立项报告, 包含背景、剂型、临床、专利、建议")

    if patents:
        parts.append("\n【专利信息】")
        for p in patents[:8]:
            parts.append(f"- {p.get('title', '')} ({p.get('year', '')}) patent_id: {p.get('patent_id', '')}")
            if p.get('abstract'):
                parts.append(f"  摘要: {p['abstract'][:300]}")
    if clinical:
        parts.append("\n【临床试验】")
        for c in clinical[:8]:
            parts.append(f"- {c.get('title', '')} [{c.get('nct', '')}] phase: {c.get('phase', '')} status: {c.get('status', '')}")
    if pubmed:
        parts.append("\n【文献】")
        for p in pubmed[:15]:
            parts.append(f"- {p.get('title', '')} ({p.get('source', '')})")
    if web:
        parts.append("\n【网络信息】")
        for w in web[:5]:
            parts.append(f"- {w.get('title', '')}: {w.get('snippet', '')}")

    return '\n'.join(parts)


def _extract_drug_name(text):
    """Fallback: extract a potential drug name from Chinese/English research query."""
    if not text:
        return ''
    # Reject pure numbers and common non-drug patterns
    if text.strip().isdigit():
        return ''
    if re.match(r'^[\d\s\-\.\,]+$', text.strip()):
        return ''
    # 1) Try known drug names from CN->EN mapping (longest match first)
    try:
        from predictor import _CN2EN
        for cn_name in sorted(_CN2EN.keys(), key=len, reverse=True):
            if cn_name in text:
                return cn_name
    except Exception:
        pass
    # 2) Try Chinese drug name patterns (common pharmaceutical suffixes)
    m = re.search(
        r'([一-鿿]{2,}(?:酮|胺|素|辛|平|汀|唑|松|酸|醇|酚|醚|酯|苷|'
        r'林|沙星|洛尔|普利|沙坦|拉唑|替丁|格列|西汀|那非|雄胺|替尼|帕利|西普|'
        r'拉平|必利|格雷|奈德|米松|比星|硝唑))',
        text
    )
    if m:
        return m.group(1)
    # 3) Try English drug name (capitalized word ≥3 chars, not at line start)
    m = re.search(r'(?:^|[^A-Za-z])([A-Z][a-z]{3,}(?:[- ][a-z]+){0,2})', text)
    if m:
        return m.group(1).strip()
    # 4) Try extracting anything after "查一下|分析|查找|对比|研究" keywords
    m = re.search(r'(?:查一下|分析|查找|对比|研究|查查|检索|关于)\s*(.+?)(?:的|在|有|和|与|vs|VS|$)', text)
    if m:
        cand = m.group(1).strip()
        if cand and len(cand) >= 2:
            return cand
    return ''


def _is_valid_drug_name(name):
    """Check if a string looks like a plausible drug name (not numbers, SMILES, or junk)."""
    if not name or len(name) < 2:
        return False
    s = name.strip()
    # Reject pure numbers
    if s.isdigit():
        return False
    # Reject strings that look like SMILES (contain chemical notation)
    if any(c in s for c in ['=', '#', '@']) and any(c.isdigit() for c in s):
        return False
    # Reject single characters
    if len(s) <= 2:
        return False
    # Reject common English query verbs (not drug names)
    if s.lower() in ('analyze', 'analyse', 'compare', 'search', 'find', 'check',
                      'look', 'show', 'tell', 'what', 'which', 'list', 'give',
                      'make', 'help', 'need', 'want', 'know', 'test', 'patent'):
        return False
    return True


def chat_stream_research(question, research_type, api_name=None, exc1_name=None, days=None, cond=None, history=None, api_key=None, api_url=None, model=None, exc2_name=None):
    """Streaming research for drug formulation/patent/competitive/packaging/project tasks."""
    target_drug = api_name or exc1_name or ''
    if not target_drug:
        # Fast path: regex extraction first (instant)
        target_drug = _extract_drug_name(question)
    if not target_drug:
        # Slow path: DeepSeek AI parsing (may be slow)
        parsed = ai_parse_formulation(question)
        target_drug = parsed.get('api_name', '') or parsed.get('exc1_name', '')

    import sys as _sys
    print(f"[chat_stream_research] question={question[:50]!r} api_name={api_name!r} exc1_name={exc1_name!r} target_drug={target_drug!r}", file=_sys.stderr)

    # Validate drug name - skip search if it doesn't look like a real drug
    if not target_drug or not _is_valid_drug_name(target_drug):
        yield _status('[WARN] 无法识别有效的药物名称, 将基于AI知识回答...')
        all_results = {}
        yield _status('🤖 正在生成回答...')
        context = _build_research_context(all_results, research_type, target_drug or question)
        messages = _build_messages(question, context, history=history, route=research_type)
        try:
            resp = _chat_request(messages, stream=True, timeout=90, api_key=api_key, api_url=api_url, model=model)
            if resp.status_code != 200:
                yield _content(f"**API request failed** (HTTP {resp.status_code}): {resp.text[:300]}")
                return
            for line in resp.iter_lines():
                if not line: continue
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str.strip() == '[DONE]': break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk['choices'][0].get('delta', {})
                        content = delta.get('content')
                        if content: yield _content(content)
                    except: pass
        except Exception as e:
            yield _content(f"\n\n**请求异常**: {str(e)}")
        return

    all_results = {}

    yield _status('📚 正在检索文献和临床试验...')
    try:
        from experiment_design import _search_patents, _search_pubmed, _search_clinicaltrials
        with ThreadPoolExecutor(max_workers=3) as ex:
            pf = ex.submit(_search_patents, target_drug, '')
            lf = ex.submit(_search_pubmed, target_drug)
            cf = ex.submit(_search_clinicaltrials, target_drug)
        patents = pf.result(timeout=30)
        pubmed = lf.result(timeout=30)
        clinical = cf.result(timeout=30)

        all_p = patents.get('core', []) + patents.get('related', [])
        if all_p:
            all_results['patents'] = all_p[:20]
            try:
                from experiment_design import _batch_translate_titles
                _batch_translate_titles(all_p[:15])
            except:
                pass
            yield {'type': 'web_action', 'action': 'results', 'label': '专利检索结果',
                   'results': all_p[:15], 'count': len(all_p), 'source': 'patent'}
        if pubmed:
            p_clean = [{'title': r['title'], 'link': r['link'], 'source': r.get('source', '')} for r in pubmed[:15]]
            all_results['pubmed'] = pubmed[:15]
            try:
                from experiment_design import _batch_translate_titles
                _batch_translate_titles(p_clean)
            except:
                pass
            yield {'type': 'web_action', 'action': 'results', 'label': 'PubMed文献',
                   'results': p_clean, 'count': len(p_clean), 'source': 'pubmed'}
        if clinical:
            c_clean = [{'title': r['title'], 'link': r['link'], 'nct': r.get('nct', ''),
                        'phase': r.get('phase', ''), 'status': r.get('status', '')} for r in clinical[:15]]
            all_results['clinical'] = clinical[:15]
            try:
                from experiment_design import _batch_translate_titles
                _batch_translate_titles(c_clean)
            except:
                pass
            yield {'type': 'web_action', 'action': 'results', 'label': '临床试验',
                   'results': c_clean, 'count': len(c_clean), 'source': 'clinical'}
    except Exception:
        pass

    yield _status('🤖 正在综合生成调研报告...')

    context = _build_research_context(all_results, research_type, target_drug)
    messages = _build_messages(question, context, history=history, route=research_type)

    try:
        resp = _chat_request(messages, stream=True, timeout=90, api_key=api_key, api_url=api_url, model=model)
        if resp.status_code != 200:
            yield _content(f"**API request failed** (HTTP {resp.status_code}): {resp.text[:300]}")
            return
        for line in resp.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data_str = line[6:]
                if data_str.strip() == '[DONE]':
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk['choices'][0].get('delta', {})
                    content = delta.get('content')
                    if content:
                        yield _content(content)
                except:
                    pass
    except requests.exceptions.Timeout:
        yield _content("\n\n**请求超时**: DeepSeek API 响应超过 90 秒, 请稍后重试. ")
    except requests.exceptions.ConnectionError as e:
        yield _content(f"\n\n**连接失败**: 无法连接到 DeepSeek API({str(e)[:100]}). 请检查 API URL 或网络. ")
    except Exception as e:
        yield _content(f"\n\n**请求异常**: {str(e)}")
