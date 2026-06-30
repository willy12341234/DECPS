"""
Experiment Design Pipeline — phased search + ML prediction + AI synthesis.
Yields {'type': 'phase', 'phase': N, 'status': 'running'|'done', 'text': ..., 'data': ...}
and {'type': 'content', 'text': ...} for DeepSeek stream.
"""
import os, sys, json, re, time, requests, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

_PRJ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(_PRJ, 'src'))
sys.path.insert(0, os.path.join(_PRJ, 'webapp'))

from knowledge_base import get_kb

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"

_search_pool = ThreadPoolExecutor(max_workers=4)
_api_names_cache = {}



_API_HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
_SEARCH_TIMEOUT = 5

def _to_english_name(name):
    """Resolve Chinese drug/excipient name to English. Uses CN2EN dict first,
    then DeepSeek AI for unknown/typo names with full timeout (user OK with slow)."""
    try:
        sys.path.insert(0, os.path.join(_PRJ, 'webapp'))
        from predictor import _CN2EN
        en = _CN2EN.get(name)
        if en:
            return en
    except:
        pass
    # AI fallback — user wants this even if slow
    try:
        sys.path.insert(0, os.path.join(_PRJ, 'webapp'))
        from predictor import _ai_translate_name
        en_name, _ = _ai_translate_name(name)
        if en_name:
            return en_name
    except:
        pass
    # AI also failed — return original name, frontend will show search URL with it
    return name

def _expand_api_names(en_api):
    """Use DeepSeek AI to get ALL related names/synonyms for an API (brand names, IUPAC, etc.).
    Returns a list of search terms."""
    key = en_api.lower().strip()
    if key in _api_names_cache:
        return _api_names_cache[key]
    terms = [en_api]
    try:
        sys.path.insert(0, os.path.join(_PRJ, 'webapp'))
        from predictor import _CN2EN
        for k, v in _CN2EN.items():
            if v.lower() == en_api.lower() and k.lower() != en_api.lower():
                terms.append(k)
    except:
        pass
    # Validate: skip DeepSeek expansion for names that won't benefit from it
    should_expand = True
    if en_api and en_api.isascii():
        # Skip for gibberish (no vowels, repeated chars)
        vowels = set('aeiouAEIOU')
        if not any(c in vowels for c in en_api) and len(set(en_api.lower())) <= 2:
            should_expand = False
    else:
        # Chinese names: already covered by _CN2EN, skip DeepSeek
        should_expand = False
    if not should_expand:
        _api_names_cache[key] = terms
        return terms
    try:
        resp = requests.post(
            DEEPSEEK_URL,
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a pharmaceutical API synonym expert. Given an API name, list ALL known synonyms including: brand names, IUPAC names, chemical names, research codes, and common trade names. Return ONLY a JSON array of strings, no thinking, no explanation. Example: [\"ibuprofen\", \"motrin\", \"advil\", \"2-(4-isobutylphenyl)propionic acid\", \"brufen\", \"nurofen\", \"p-uprofen\"]"},
                    {"role": "user", "content": en_api}
                ],
                "temperature": 0.1,
                "max_tokens": 1024,
            },
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            timeout=5
        )
        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content'].strip()
            content = content.replace('```json', '').replace('```', '').strip()
            ai_names = json.loads(content)
            if isinstance(ai_names, list):
                for n in ai_names:
                    n = n.strip()
                    if n and n.lower() not in [t.lower() for t in terms]:
                        terms.append(n)
    except:
        pass
    # Also add base name variants without special chars
    base_added = set(t.lower() for t in terms)
    for t in terms[:]:
        clean = re.sub(r'[^a-zA-Z0-9 ]', '', t).strip()
        if clean and clean.lower() not in base_added and len(clean) > 2:
            terms.append(clean)
            base_added.add(clean.lower())
        # Add base forms: "cortexolone 17α-propionate" → "cortexolone"
        parts = re.split(r'[\s\-]', clean)
        if len(parts) > 1:
            for p in parts:
                p = p.strip()
                if p and p.lower() not in base_added and len(p) > 4:
                    terms.append(p)
                    base_added.add(p.lower())
    # If the name has a numeric suffix like "CB-03-01", also try without
    for t in terms[:]:
        clean = re.sub(r'[\s\-]', ' ', t).strip()
        parts = clean.split()
        for p in parts:
            if p and p.lower() not in base_added and len(p) > 4 and not p.isdigit():
                terms.append(p)
                base_added.add(p.lower())
    # If still only the original name, try AI again with a more specific prompt for base names
    if len(terms) <= 2:
        try:
            resp2 = requests.post(
                DEEPSEEK_URL,
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": "Return ONLY a JSON array of base chemical names that this drug is derived from or related to. No thinking. Example: for \"clascoterone\" → [\"cortexolone\", \"17α-hydroxyprogesterone\"]"},
                        {"role": "user", "content": f"What base chemicals is {en_api} derived from?"}
                    ],
                    "temperature": 0.05,
                    "max_tokens": 512,
                },
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                timeout=5
            )
            if resp2.status_code == 200:
                c2 = resp2.json()['choices'][0]['message']['content'].strip()
                c2 = c2.replace('```json', '').replace('```', '').strip()
                extra = json.loads(c2)
                for n in extra:
                    n = n.strip()
                    if n and n.lower() not in base_added:
                        terms.append(n)
                        base_added.add(n.lower())
        except:
            pass
    _api_names_cache[key] = terms
    return terms

# ── Patent search ──────────────────────────────────────────────
_title_trans_cache = {}

def _batch_translate_titles(items, src='en', dst='zh-cn'):
    """Translate patent/literature titles in batch using DeepSeek."""
    if not items:
        return items
    need = [r for r in items if r.get('title') and r.get('title') not in _title_trans_cache]
    if need:
        pairs = [(r['title'], i) for i, r in enumerate(need)]
        titles = [p[0] for p in pairs]
        try:
            resp = requests.post(
                DEEPSEEK_URL,
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": "Translate the following English patent/literature titles to Chinese. Return ONLY a JSON array of strings, same order as input. No thinking, no explanations."},
                        {"role": "user", "content": json.dumps(titles, ensure_ascii=False)}
                    ],
                    "temperature": 0.05,
                    "max_tokens": 2048,
                },
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                timeout=15
            )
            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content'].strip()
                content = content.replace('```json', '').replace('```', '').strip()
                translated = json.loads(content)
                for r, cn_title in zip(need, translated):
                    cn = (cn_title or '').strip()
                    if cn:
                        _title_trans_cache[r['title']] = cn
                        r['title_cn'] = cn
        except Exception:
            pass
    for r in items:
        if r.get('title') and r['title'] in _title_trans_cache and 'title_cn' not in r:
            r['title_cn'] = _title_trans_cache[r['title']]
    return items

def _search_europepmc_patents_simple(query_term, api_name, timeout=8):
    '''Simple Europe PMC patent search by query term. Returns list of patent dicts.'''
    results = []
    try:
        r = requests.get(
            'https://www.ebi.ac.uk/europepmc/webservices/rest/search',
            params={'query': f'({query_term}) AND (SRC:PAT)', 'pageSize': 10, 'format': 'json'},
            timeout=timeout, headers=_API_HEADERS,
        )
        if r.status_code == 200:
            for entry in r.json().get('resultList', {}).get('result', []):
                pid = entry.get('id', '') or ''
                title = (entry.get('title', '') or '').strip()
                if not title or not pid:
                    continue
                year = entry.get('pubYear', '') or ''
                country = pid[:2] if len(pid) >= 2 and pid[:2].isalpha() else ''
                author = (entry.get('authorString', '') or '').strip()
                results.append({
                    'title': title,
                    'patent_id': pid,
                    'country': country,
                    'year': year,
                    'inventor': author,
                    'link': f'https://patents.google.com/patent/{pid}/',
                    'snippet': f'{pid} | {country} | {year}',
                })
    except Exception:
        pass
    return results


def _search_patents_ddg(query_term, api_name, timeout=8):
    '''Search patents via DuckDuckGo. Returns list of patent dicts.'''
    results = []
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            ddg_results = list(ddgs.text(query_term, max_results=10))
        for r in ddg_results:
            title = (r.get('title', '') or '').strip()
            url = (r.get('href', '') or '').strip()
            if not title or not url:
                continue
            # Extract patent ID from URL if possible
            pid = ''
            import re as _re
            pm = _re.search(r'(US|WO|EP|CN|JP|KR|AU|CA)\d{4,12}[A-Z0-9]*', url)
            if pm:
                pid = pm.group(0)
            # Extract year
            year = ''
            ym = _re.search(r'20\d{2}', url)
            if ym:
                year = ym.group(0)
            results.append({
                'title': title,
                'patent_id': pid,
                'country': pid[:2] if pid else '',
                'year': year,
                'inventor': '',
                'link': url,
                'snippet': title[:100],
            })
    except Exception:
        pass
    return results


def _search_patents(api_name, exc1_name, exc2_name=None):
    """Multi-source patent search: 3 keyword groups × (DuckDuckGo + Europe PMC) in parallel."""
    en_api = _to_english_name(api_name)
    api_names = _expand_api_names(en_api)
    alt1 = api_names[1] if len(api_names) > 1 else en_api
    alt2 = api_names[2] if len(api_names) > 2 else en_api
    brand = api_names[-1] if len(api_names) > 3 and api_names[-1] != en_api else en_api

    # 3 keyword groups
    kw_groups = [
        [f'{en_api} patent', f'{en_api} pharmaceutical'],
        [f'{en_api} formulation', f'{en_api} composition', f'{en_api} dosage'],
        [f'{alt1} patent', f'{alt2}', f'{brand} {en_api}'],
    ]

    seen_pids = set()
    all_patents = []

    def _add(p):
        pid = p.get('patent_id', '') or p.get('title', '')
        if pid and pid not in seen_pids:
            seen_pids.add(pid)
            all_patents.append(p)

    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = []
        for group in kw_groups:
            for kw in group:
                futures.append(ex.submit(_search_europepmc_patents_simple, kw, api_name))
                futures.append(ex.submit(_search_patents_ddg, kw, api_name))

        for f in as_completed(futures, timeout=30):
            try:
                for p in f.result():
                    _add(p)
            except Exception:
                pass

    # Deduplicate by normalized title/patent_id
    deduped = []
    seen_norm = set()
    for p in all_patents:
        t = p.get('title', '').strip().lower()
        if not t or len(t) <= 10:
            t = p.get('patent_id', '').strip().lower() or t
        t_clean = re.sub(r'[^a-z0-9一-鿿\s]', '', t)
        t_clean = re.sub(r'\s+', ' ', t_clean).strip()
        if t_clean and len(t_clean) > 3 and t_clean not in seen_norm:
            seen_norm.add(t_clean)
            deduped.append(p)

    # Sort: real titles first (Europe PMC), then by year
    deduped.sort(key=lambda p: (
        0 if p.get('patent_id', '') else 1,
        0 if en_api.lower() in p.get('title', '').lower() else 1,
        -(int(p['year']) if p.get('year', '').isdigit() else 0),
    ))
    # Filter: only keep actual patent entries (must have patent_id or patent-like title)
    deduped = [p for p in deduped if p.get('patent_id', '') or
               any(kw in p.get('title', '').lower() for kw in
                   ['patent', '专利', 'composition', 'formulation', 'cortexolone', 'clascoterone',
                    'enzyme', 'ester', 'androgen', 'topical', 'cream', 'steroid'])]
    return {'core': deduped[:8], 'related': deduped[8:16]}


# ── Literature search ───────────────────────────────────────────
def _search_pubmed(api_name):
    """Search PubMed via NIH E-utilities — drug name + pharmaceutics filter + post-filter."""
    results = []
    _IRRELEVANT_PUBMED_KW = [
        'pain', 'analgesia', 'analgesic', 'surgery', 'surgical', 'anesthesia',
        'case report', 'poisoning', 'overdose', 'self-poisoning',
        'migraine', 'headache', 'back pain', 'dysmenorrhea', 'fever',
        'knee replacement', 'orthopedic', 'nerve block',
    ]
    try:
        search_name = _to_english_name(api_name)
        pharma_filter = (
            'formulation[Title/Abstract] OR pharmaceutical[Title/Abstract] OR '
            'composition[Title/Abstract] OR stability[Title/Abstract] OR '
            'compatibility[Title/Abstract] OR excipient[Title/Abstract] OR '
            'topical[Title/Abstract] OR cream[Title/Abstract] OR tablet[Title/Abstract] OR '
            'dosage[Title/Abstract] OR "drug delivery"[Title/Abstract] OR '
            'degradation[Title/Abstract] OR dissolution[Title/Abstract]'
        )
        r = requests.get(
            'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi',
            params={
                'db': 'pubmed', 'retmax': 40, 'retmode': 'json',
                'term': f'({search_name}[Title/Abstract]) AND ({pharma_filter})',
            },
            timeout=_SEARCH_TIMEOUT, headers=_API_HEADERS,
        )
        if r.status_code != 200:
            return results
        id_list = r.json().get('esearchresult', {}).get('idlist', [])
        if not id_list:
            return results
        fr = requests.get(
            'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi',
            params={'db': 'pubmed', 'id': ','.join(id_list), 'retmode': 'json'},
            timeout=_SEARCH_TIMEOUT, headers=_API_HEADERS,
        )
        if fr.status_code == 200:
            fdata = fr.json()
            for pid in id_list:
                info = fdata.get('result', {}).get(pid, {})
                title = (info.get('title', '') or '').strip()
                # Post-filter: skip irrelevant clinical/pain studies
                t = title.lower()
                if any(kw in t for kw in _IRRELEVANT_PUBMED_KW):
                    continue
                results.append({
                    'title': title,
                    'source': info.get('source', ''),
                    'date': info.get('pubdate', ''),
                    'link': f'https://pubmed.ncbi.nlm.nih.gov/{pid}/',
                    'pmid': pid,
                })
    except Exception:
        pass
    return results

def _search_clinicaltrials(api_name):
    """Search ClinicalTrials.gov via API v2 — drug name + pharmaceutics filter + post-filter."""
    results = []
    _IRRELEVANT_CLIN_KW = [
        'pain', 'analgesia', 'migraine', 'headache', 'back pain', 'fever',
        'dysmenorrhea', 'knee replacement', 'orthopedic', 'nerve block',
        'surgery', 'anesthesia', 'cancer pain', 'neuropathic pain',
    ]
    try:
        en_api = _to_english_name(api_name)
        r = requests.get(
            'https://clinicaltrials.gov/api/v2/studies',
            params={
                'query.term': f'{en_api} AND (formulation OR cream OR tablet OR pharmaceutical OR compatibility OR stability OR topical OR gel OR solution OR "dosage form")',
                'pageSize': 20, 'format': 'json',
                'fields': 'NCTId,BriefTitle,OverallStatus,Phase',
            },
            timeout=_SEARCH_TIMEOUT, headers=_API_HEADERS,
        )
        if r.status_code == 200:
            for study in r.json().get('studies', []):
                pm = study.get('protocolSection', {})
                im = pm.get('identificationModule', {})
                sm = pm.get('statusModule', {})
                dm = pm.get('designModule', {})
                nct = im.get('nctId', '')
                title = (im.get('briefTitle', '') or '').strip()
                if nct and title:
                    # Post-filter: skip irrelevant pain/surgery studies
                    t = title.lower()
                    if any(kw in t for kw in _IRRELEVANT_CLIN_KW):
                        continue
                    results.append({
                        'title': title,
                        'nct': nct,
                        'phase': ', '.join(dm.get('phases', [])) if dm.get('phases') else '',
                        'status': sm.get('overallStatus', ''),
                        'link': f'https://clinicaltrials.gov/study/{nct}',
                    })
    except Exception:
        pass
    return results

def _reconstruct_abstract(inv_index):
    """Reconstruct abstract text from OpenAlex inverted index."""
    if not inv_index:
        return ''
    word_positions = []
    for word, positions in inv_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return ' '.join(w for _, w in word_positions)

def _search_openalex(api_name, exc1_name):
    """Search OpenAlex for broad academic literature (includes abstract)."""
    results = []
    try:
        en_api = _to_english_name(api_name)
        en_exc = _to_english_name(exc1_name)
        r = requests.get(
            'https://api.openalex.org/works',
            params={
                'search': f'{en_api} {en_exc} formulation',
                'per_page': 8,
                'select': 'id,title,doi,publication_date,primary_location,cited_by_count,abstract_inverted_index',
            },
            timeout=_SEARCH_TIMEOUT, headers=_API_HEADERS,
        )
        if r.status_code == 200:
            for work in r.json().get('results', []):
                doi = work.get('doi', '') or ''
                venue = ''
                pl = work.get('primary_location')
                if pl and pl.get('source'):
                    venue = pl['source'].get('display_name', '')
                abstract = _reconstruct_abstract(work.get('abstract_inverted_index'))
                results.append({
                    'title': work.get('title', ''),
                    'link': doi.replace('https://doi.org/', 'https://doi.org/'),
                    'snippet': f'Cited: {work.get("cited_by_count", 0)} | Venue: {venue} | Date: {work.get("publication_date", "")}',
                    'doi': doi,
                    'abstract': abstract,
                })
    except Exception:
        pass
    return results

def _search_crossref(api_name, exc1_name):
    """Search CrossRef for DOIs and publication metadata."""
    results = []
    try:
        en_api = _to_english_name(api_name)
        en_exc = _to_english_name(exc1_name)
        r = requests.get(
            'https://api.crossref.org/works',
            params={
                'query.title': f'{en_api} {en_exc} formulation',
                'rows': 8, 'order': 'desc', 'sort': 'published',
            },
            timeout=_SEARCH_TIMEOUT,
            headers=_API_HEADERS,
        )
        if r.status_code == 200:
            for item in r.json().get('message', {}).get('items', []):
                doi = item.get('DOI', '')
                title = (item.get('title', [''])[0] if item.get('title') else '')
                container = (item.get('container-title', [''])[0] if item.get('container-title') else '')
                pub_date = (item.get('published-print', {}).get('date-parts', [[None]])[0] or
                           item.get('created', {}).get('date-parts', [[None]])[0])
                pub_str = '-'.join(str(p) for p in pub_date if p) if pub_date else ''
                results.append({
                    'title': title,
                    'link': f'https://doi.org/{doi}' if doi else '',
                    'doi': doi,
                    'snippet': f'CrossRef | {container} | {pub_str}',
                    'source': container,
                    'date': pub_str,
                })
    except Exception:
        pass
    return results

def _fetch_pubmed_abstracts(pmids):
    """Fetch full abstract text for a list of PubMed IDs via EFetch (XML)."""
    if not pmids:
        return {}
    try:
        r = requests.get(
            'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi',
            params={'db': 'pubmed', 'id': ','.join(pmids), 'retmode': 'xml', 'rettype': 'abstract'},
            timeout=10, headers=_API_HEADERS,
        )
        if r.status_code != 200:
            return {}
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.text)
        result = {}
        for article in root.iter('PubmedArticle'):
            pmid_e = article.find('.//PMID')
            pmid = pmid_e.text if pmid_e is not None else ''
            abs_parts = []
            for at in article.iter('AbstractText'):
                label = at.get('Label', '')
                text = ''.join(at.itertext())
                if label:
                    abs_parts.append(f'{label}: {text}')
                else:
                    abs_parts.append(text)
            if abs_parts:
                result[pmid] = '\n'.join(abs_parts)
        return result
    except Exception:
        return {}

def _score_relevance(title, abstract_text, api_name, exc1_name):
    """Score a paper's relevance to the given API+excipient+experiment design."""
    if not title and not abstract_text:
        return 0
    text = f'{title or ""} {abstract_text or ""}'.lower()
    en_api = _to_english_name(api_name).lower()
    en_exc = _to_english_name(exc1_name).lower()
    score = 0
    if en_api in text:
        score += 8
    if en_exc in text:
        score += 8
    for kw in ['compatibility', 'stability', 'degradation', 'impurity', 'excipient',
               'formulation', 'reaction', 'interaction', 'incompatible',
               '相容性', '降解', '杂质', '反应', '相互作用']:
        score += text.count(kw) * 2
    if 'experiment' in text or 'design' in text or 'design' in text:
        score += 3
    return score

def _fetch_abstracts_and_filter(api_name, exc1_name, clinical):
    """Fetch full abstracts for search results, score relevance, enrich results dict.

    Returns clinical dict with added 'abstracts' and 'highly_relevant' entries.
    """
    clinical['abstracts'] = {}
    clinical['highly_relevant'] = []

    # 1. Fetch PubMed abstracts
    pmids = [p.get('pmid', '') for p in clinical.get('pubmed', []) if p.get('pmid')]
    if pmids:
        abstracts = _fetch_pubmed_abstracts(pmids)
        clinical['abstracts'].update(abstracts)
        for p in clinical['pubmed']:
            pmid = p.get('pmid', '')
            abstract_text = abstracts.get(pmid, '')
            score = _score_relevance(p.get('title', ''), abstract_text, api_name, exc1_name)
            p['abstract'] = abstract_text
            p['relevance_score'] = score
            if score >= 10:
                clinical['highly_relevant'].append(p)

    # 2. OpenAlex results already have abstract_text
    for g in clinical.get('general', []):
        abstract_text = g.get('abstract', '')
        score = _score_relevance(g.get('title', ''), abstract_text, api_name, exc1_name)
        g['relevance_score'] = score
        if score >= 10:
            clinical['highly_relevant'].append(g)

    # 3. Sort highly_relevant by score
    clinical['highly_relevant'].sort(key=lambda x: -x.get('relevance_score', 0))
    return clinical

def _search_europepmc_literature(api_name, exc1_name):
    """Search Europe PMC for formulation/stability literature."""
    results = []
    try:
        en_api = _to_english_name(api_name)
        en_exc = _to_english_name(exc1_name)
        r = requests.get(
            'https://www.ebi.ac.uk/europepmc/webservices/rest/search',
            params={
                'query': f'({en_api}) AND ({en_exc}) AND (formulation OR stability OR excipient OR compatibility)',
                'pageSize': 10, 'format': 'json',
            },
            timeout=_SEARCH_TIMEOUT, headers=_API_HEADERS,
        )
        if r.status_code == 200:
            for entry in r.json().get('resultList', {}).get('result', []):
                title = entry.get('title', '') or ''
                pmid = entry.get('id', '') or ''
                src = entry.get('source', '')
                results.append({
                    'title': title.strip(),
                    'link': f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/' if pmid else '',
                    'snippet': f'Source: {src} | {entry.get("journalTitle", "")[:60]}',
                    'pmid': pmid,
                })
    except Exception:
        pass
    return results

def _search_clinical_data(api_name, exc1_name):
    """Phase 2: Search literature + clinical data via stable APIs (parallel)."""
    results = {'pubmed': [], 'clinicaltrials': [], 'general': []}
    with ThreadPoolExecutor(max_workers=3) as ex:
        f1 = ex.submit(_search_pubmed, api_name)
        f2 = ex.submit(_search_clinicaltrials, api_name)
        f3 = ex.submit(_search_openalex, api_name, exc1_name)
        f4 = ex.submit(_search_europepmc_literature, api_name, exc1_name)
        results['pubmed'] = f1.result() or []
        results['clinicaltrials'] = f2.result() or []
        general = (f3.result() or []) + (f4.result() or [])
        results['general'] = general
    return results

def _run_ml_prediction(api_name, exc1_name, days=0, cond="0"):
    """Phase 3: Run ML compatibility prediction."""
    try:
        # Use webapp predictor (known working version)
        webapp_dir = os.path.join(_PRJ, 'webapp')
        sys.path.insert(0, webapp_dir)
        from predictor import get_sm as web_get_sm, predict as web_predict

        api_smi = web_get_sm(api_name)
        exc1_smi = web_get_sm(exc1_name)
        if not api_smi or not exc1_smi:
            return None

        fp_result = web_predict(api_smi, exc1_smi, None, days, cond)
        if fp_result.get('error'):
            return None

        return {
            'probability': fp_result.get('prob', 0),
            'risk_level': fp_result.get('level', 'unknown'),
            'has_impurity': fp_result.get('has', False),
            'impurity_count': fp_result.get('impurity_count'),
            'total_impurity_pct': fp_result.get('total_impurity_pct'),
            'max_single_impurity_pct': fp_result.get('max_single_impurity_pct'),
            'smarts_matches': None,
        }
    except Exception as e:
        print(f'  ML prediction error: {e}')
        return None

def _build_prompt(question, api_name, exc1_name, exc2_name, patents, clinical, ml_result, equipment_summary, kb_regulatory=None, enriched_clinical=None):
    """Build the final prompt with all context."""
    lines = [f"## 用户问题\n{question}"]
    lines.append(f"\n## 原辅料信息\nAPI: {api_name}\n辅料1: {exc1_name}")
    if exc2_name:
        lines.append(f"辅料2: {exc2_name}")

    # Patent info — core (API+excipient specific) and related (broader API formulations)
    core_pats = patents.get('core', []) or patents.get('patents', [])
    rel_pats = patents.get('related', [])
    if core_pats:
        lines.append("\n## 【相关专利 — API+辅料组合匹配】")
        for p in core_pats:
            title = p.get('title', '')
            pid = p.get('patent_id', '') or p.get('patentId', '')
            country = p.get('country', '')
            year = p.get('year', '')
            link = p.get('link', '')
            snippet = f'{p.get("snippet", "")}' if not year else f'{pid} [{country}] {year}'
            lines.append(f"- **{title}**")
            if link:
                lines.append(f"  {link}")
            if snippet:
                lines.append(f"  {snippet[:200]}")
    elif rel_pats:
        lines.append("\n## 【相关专利 — API相关（未找到API+辅料组合专利）】")
        for p in rel_pats[:6]:
            title = p.get('title', '')
            pid = p.get('patent_id', '') or p.get('patentId', '')
            year = p.get('year', '')
            link = p.get('link', '')
            snippet = f'{pid} | {year}' if year else pid
            lines.append(f"- **{title}**")
            if link:
                lines.append(f"  {link}")
            if snippet:
                lines.append(f"  {snippet[:200]}")
    else:
        lines.append("\n## 【相关专利】\n未检索到相关专利。方案将基于法规指南和化学规则制定。")
    if rel_pats and core_pats:
        lines.append("\n## 【扩展专利】API其他相关专利")
        for p in rel_pats[:6]:
            title = p.get('title', '')
            pid = p.get('patent_id', '') or p.get('patentId', '')
            year = p.get('year', '')
            link = p.get('link', '')
            snippet = f'{pid} | {year}' if year else pid
            lines.append(f"- **{title}**")
            if link:
                lines.append(f"  {link}")
            if snippet:
                lines.append(f"  {snippet[:200]}")

    # Clinical/literature — try external search first, then RAG KB fallback
    has_external = bool(clinical.get('pubmed') or clinical.get('clinicaltrials') or clinical.get('highly_relevant'))
    if clinical.get('pubmed'):
        lines.append("\n## PubMed 相关文献")
        for p in clinical['pubmed']:
            lines.append(f"- [{p['title']}]({p['link']}) ({p.get('source','')})")

    if clinical.get('clinicaltrials'):
        lines.append("\n## 临床试验数据")
        for c in clinical['clinicaltrials']:
            lines.append(f"- [{c['title']}]({c['link']}) | Phase: {c.get('phase','')} | Status: {c.get('status','')}")
    elif not has_external:
        lines.append("\n## 文献与临床试验\n未检索到直接相关文献和临床试验（搜索无结果或结果与当前API不相关）。方案将基于法规指南和化学规则制定。")

    # Fallback: retrieve related literature from local RAG KB when external search fails
    if not has_external and api_name and exc1_name:
        try:
            from knowledge_base import get_kb
            kb_query = f"{api_name} {exc1_name} compatibility literature study"
            kb_retrieved = get_kb().retrieve(kb_query, top_k=4)
            if kb_retrieved:
                lines.append("\n## 知识库检索 — 相关文献与研究")
                for chunk, score in kb_retrieved:
                    src = chunk.get('source', '')
                    text = chunk.get('text', '').strip()[:400]
                    if text:
                        lines.append(f"- （{src}）{text}")
            else:
                lines.append("\n## 文献与临床数据\n未检索到直接相关文献。方案基于法规指南、ML预测和化学规则制定。")
        except Exception:
            lines.append("\n## 文献与临床数据\n未检索到直接相关文献。方案基于法规指南、ML预测和化学规则制定。")

    # Highly relevant literature with full abstracts (from abstract fetching + scoring)
    enriched = enriched_clinical or clinical
    if enriched.get('highly_relevant'):
        lines.append("\n## 【高相关度文献摘要】（AI已阅读以下文献，用于指导实验设计）")
        for item in enriched['highly_relevant'][:4]:
            title = item.get('title', '')
            link = item.get('link', '') or item.get('doi', '')
            abstract = item.get('abstract', '') or enriched.get('abstracts', {}).get(item.get('pmid', ''), '')
            score = item.get('relevance_score', 0)
            lines.append(f"\n**{title}** (相关度: {score})")
            if link:
                lines.append(f"  链接: {link}")
            if abstract:
                # Truncate very long abstracts
                ab = abstract[:600] + '...' if len(abstract) > 600 else abstract
                lines.append(f"  摘要: {ab}")

    if clinical.get('general'):
        lines.append("\n## 其他相关文献/数据")
        for r in clinical['general']:
            lines.append(f"- [{r['title']}]({r.get('link','')})")

    # ML result
    if ml_result:
        lines.append("\n## ML 相容性预测结果")
        imp_status = "不相容（预期产生杂质）" if ml_result.get('has_impurity') else "相容（无显著杂质）"
        lines.append(f"- 相容性判断: {imp_status}")
        lines.append(f"- 风险等级: {ml_result.get('risk_level', 'unknown')}")
        lines.append(f"- 概率: {ml_result.get('probability', 0):.1%}")
        if ml_result.get('impurity_count') is not None:
            lines.append(f"- 预测杂质个数: {ml_result['impurity_count']}")
            lines.append(f"- 总杂质%: {ml_result['total_impurity_pct']}%")
            lines.append(f"- 最大单杂%: {ml_result['max_single_impurity_pct']}%")

    # Chemical reaction rule matching (SMARTS pairwise)
    try:
        from rdkit import Chem
        prj_smiles = os.path.join(_PRJ, 'caches', 'smiles_cache.json')
        if os.path.exists(prj_smiles) and api_name and exc1_name:
            with open(prj_smiles) as _sf:
                _sc = json.load(_sf)
            _a_sm = next((v for k, v in _sc.items() if api_name.lower() in k.lower()), None)
            _e_sm = next((v for k, v in _sc.items() if exc1_name.lower() in k.lower()), None)
            if _a_sm and _e_sm:
                _m_api = Chem.MolFromSmiles(_a_sm)
                _m_exc = Chem.MolFromSmiles(_e_sm)
                if _m_api and _m_exc:
                    # Import shared SMARTS rules (single source of truth)
                    try:
                        sys.path.insert(0, os.path.join(_PRJ, 'src'))
                        from smarts_rules import PAIRWISE_RULES as _PW
                        _pair_rules = [(desc, api_sma, exc_sma) for _, api_sma, exc_sma, desc in _PW]
                    except Exception:
                        _pair_rules = []
                    matched = []
                    for _desc, _api_sma, _exc_sma in _pair_rules:
                        _ap = Chem.MolFromSmarts(_api_sma)
                        _ep = Chem.MolFromSmarts(_exc_sma)
                        if not _ap or not _ep: continue
                        _ha = len(_m_api.GetSubstructMatches(_ap)) > 0
                        _he = len(_m_exc.GetSubstructMatches(_ep)) > 0
                        if _ha and _he:
                            matched.append(f"- [OK] {_desc}（API和辅料均含匹配基团）")
                        elif _ha:
                            matched.append(f"- [WARN] {_desc}（仅API含匹配基团）")
                        elif _he:
                            matched.append(f"- [WARN] {_desc}（仅辅料含匹配基团）")
                    if matched:
                        lines.append("\n## 化学反应规则匹配结果")
                        lines.extend(matched)
    except Exception:
        pass

    # KB-retrieved regulatory guidelines (from PDFs in ml/rag_kb/)
    if kb_regulatory:
        lines.append(f"\n## 【知识库检索】相关法规指南与技术文献")
        for chunk, score in kb_regulatory:
            src = chunk.get('source', '')
            text = chunk.get('text', '').strip()
            if text:
                lines.append(f"（来源: {src}）")
                lines.append(text[:800])
    else:
        # Fallback hardcoded guidelines
        lines.append("\n## 原辅料相容性实验设计关键原则（来自《化学药物制剂研究基本技术指导原则》2005年3月）")
        lines.append("- API:辅料比例：辅料用量较大时（如稀释剂等），按主药:辅料=1:5的比例混合；用量较小时（如润滑剂等），按主药:辅料=20:1的比例混合")
        lines.append("- 实验条件：参照药物稳定性指导原则中影响因素的实验方法，即高温（如60°C）、高湿（如92.5%RH或75%RH）、光照（照度4500±500Lx）三种条件")
        lines.append("- 实验设计中不得出现加速条件(40°C/75%RH)和长期条件(25°C/60%RH)——原辅料相容性只做影响因素实验")
        lines.append("- 取样时间点：包括0天和至少一个考察时间点（如5天或10天）")
        lines.append("- 检测项目：重点考察性状、含量、有关物质（HPLC法）等")
        lines.append("- 样品设置：一般仅设实验组（API+辅料混合物），必要时设API单独对照；一般情况下不单独设置辅料空白对照")

    # Equipment
    if equipment_summary:
        lines.append(f"\n## 公司可用仪器设备（设计实验时只能使用以下设备）")
        lines.append(equipment_summary)

    return '\n'.join(lines)

def _call_deepseek_stream(messages):
    """Stream DeepSeek response."""
    resp = requests.post(
        DEEPSEEK_URL,
        json={"model": DEEPSEEK_MODEL, "messages": messages, "temperature": 0.3, "max_tokens": 8192, "stream": True},
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
        timeout=180,
        stream=True,
    )
    if resp.status_code != 200:
        yield f"**API请求失败** (HTTP {resp.status_code})"
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
                    yield content
            except Exception:
                pass

def _try_parse_api_excipient(question):
    """Try to extract API and excipient names from question."""
    result = {'api_name': '', 'exc1_name': '', 'exc2_name': '', 'days': None, 'cond': None}

    # Try regex patterns first
    m = re.search(r'(?:API|api|Api|原料)[：:为是]\s*([^，,;\n+]+)', question)
    if m: result['api_name'] = m.group(1).strip()
    m = re.search(r'(?:辅料1?|excipient|Excipient)[：:为是]\s*([^，,;\n+]+)', question)
    if m: result['exc1_name'] = m.group(1).strip()
    m = re.search(r'辅料2[：:为是]\s*([^，,;\n+]+)', question)
    if m: result['exc2_name'] = m.group(1).strip()

    # Try xxx+xxx format
    if not result['api_name'] or not result['exc1_name']:
        m = re.search(r'([^\s+和,，]+)\s*[+＋和]\s*([^\s+和,，\n]+)', question)
        if m:
            if not result['api_name']: result['api_name'] = m.group(1).strip()
            if not result['exc1_name']: result['exc1_name'] = m.group(2).strip()

    m = re.search(r'(?:条件|condition)[：:]\s*([^，,;\n]+)', question)
    if m: result['cond'] = m.group(1).strip()
    m = re.search(r'(?:天[数]?|days?)[：:]\s*(\d+)', question)
    if m: result['days'] = m.group(1).strip()

    # Try DeepSeek AI parsing as fallback
    if not result['api_name'] or not result['exc1_name']:
        try:
            system_msg = (
                "你是一个药物制剂信息提取助手。从用户的自然语言描述中提取原辅料相容性相关信息。"
                "请严格按 JSON 格式返回："
                '{"api_name": "...", "exc1_name": "...", "exc2_name": "...", "condition": "...", "days": "..."}'
            )
            resp = requests.post(
                DEEPSEEK_URL,
                json={"model": DEEPSEEK_MODEL, "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": question},
                ], "temperature": 0.05, "max_tokens": 300},
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                timeout=15,
            )
            if resp.status_code == 200:
                content = resp.json()['choices'][0]['message']['content'].strip()
                content = content.removeprefix('```json').removeprefix('```').removesuffix('```').strip()
                parsed = json.loads(content)
                if not result['api_name']: result['api_name'] = parsed.get('api_name', '')
                if not result['exc1_name']: result['exc1_name'] = parsed.get('exc1_name', '')
                if not result['exc2_name']: result['exc2_name'] = parsed.get('exc2_name', '')
                if not result['cond']: result['cond'] = parsed.get('condition', '')
                if not result['days']: result['days'] = parsed.get('days', '')
        except Exception:
            pass

    return result


def search_experiment(question, api_name=None, exc1_name=None, days=None, cond=None, exc2_name=None):
    """
    Main experiment design pipeline — generator yielding phase/content events.

    Yields:
      {'type': 'phase', 'phase': N, 'status': 'running'|'done',
       'text': str, 'data': dict|None}
      {'type': 'content', 'text': str}
      {'type': 'sources', 'sources': [...]}
    """
    # Parse inputs
    parsed = _try_parse_api_excipient(question)
    api_name = api_name or parsed.get('api_name', '')
    exc1_name = exc1_name or parsed.get('exc1_name', '')
    exc2_name = exc2_name or parsed.get('exc2_name', '')
    days = days or parsed.get('days')
    cond = cond or parsed.get('cond')

    if not api_name or not exc1_name:
        yield {'type': 'phase', 'phase': 0, 'status': 'error',
               'text': '无法从问题中识别API和辅料名称，请明确指定。'}
        return

    # Start all searches in parallel immediately
    patent_future = _search_pool.submit(_search_patents, api_name, exc1_name, exc2_name)
    pubmed_future = _search_pool.submit(_search_pubmed, api_name)
    crossref_future = _search_pool.submit(_search_crossref, api_name, exc1_name)
    openalex_future = _search_pool.submit(_search_openalex, api_name, exc1_name)
    epmc_lit_future = _search_pool.submit(_search_europepmc_literature, api_name, exc1_name)
    clinical_future = _search_pool.submit(_search_clinicaltrials, api_name)
    ml_future = _search_pool.submit(_run_ml_prediction, api_name, exc1_name, days or 0, cond or "0")

    # Convert names to English for URL display
    en_api = _to_english_name(api_name) or api_name
    en_exc = _to_english_name(exc1_name) or exc1_name

    # Send name correction event if names differ from original
    if en_api != api_name:
        yield {'type': 'web_action', 'action': 'name_correction',
               'field': 'api', 'original': api_name, 'corrected': en_api,
               'label': f'名称已纠正: {api_name} → {en_api}'}
    if en_exc != exc1_name:
        yield {'type': 'web_action', 'action': 'name_correction',
               'field': 'exc1', 'original': exc1_name, 'corrected': en_exc,
               'label': f'名称已纠正: {exc1_name} → {en_exc}'}

    # Phase 1: Patent search
    yield {'type': 'phase', 'phase': 1, 'status': 'running',
           'text': '[SEARCH] 正在检索相关专利信息...'}
    # Web action: DDGS search (URL-encode names for safe URLs)
    en_api_url = urllib.parse.quote(en_api)
    en_exc_url = urllib.parse.quote(en_exc)
    search_queries = [
        f"https://duckduckgo.com/?q={en_api_url}+{en_exc_url}+pharmaceutical+formulation+patent",
        f"https://duckduckgo.com/?q={en_api_url}+pharmaceutical+composition+patent",
        f"https://patents.google.com/?q={en_api_url}+{en_exc_url}+formulation",
    ]
    for sq in search_queries:
        yield {'type': 'web_action', 'action': 'fetch', 'url': sq,
               'label': '搜索专利', 'source': 'DDGS/Google Patents', 'status': 'running'}
    patents = patent_future.result()
    n_core = len(patents.get('core', []) or patents.get('patents', []))
    n_related = len(patents.get('related', []))
    n_patents = n_core + n_related
    for sq in search_queries:
        yield {'type': 'web_action', 'action': 'fetch', 'url': sq,
               'label': '搜索专利', 'source': 'Europe PMC / Google Patents', 'status': 'done'}
    all_patents = patents.get('core', []) + patents.get('related', [])
    all_patents.sort(key=lambda p: (
        0 if en_api.lower() in p.get('title', '').lower() and en_exc and en_exc.lower() in p.get('title', '').lower()
        else 1 if en_api.lower() in p.get('title', '').lower()
        else 2,
        p.get('year', '9999') or '9999',
    ))
    _batch_translate_titles(all_patents)
    yield {'type': 'web_action', 'action': 'results', 'label': '专利检索结果',
           'results': all_patents[:20],
           'count': len(all_patents), 'source': 'patent'}
    yield {'type': 'phase', 'phase': 1, 'status': 'done',
           'text': f'[OK] 全球专利检索完成，{n_core} 篇直接相关 + {n_related} 篇后续相关',
           'data': patents}

    # Phase 2: Literature search (PubMed + CrossRef + Semantic Scholar)
    yield {'type': 'phase', 'phase': 2, 'status': 'running',
           'text': '[SEARCH] 正在检索全球学术文献...'}
    yield {'type': 'web_action', 'action': 'fetch',
           'url': f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=({urllib.parse.quote(en_api)}[Title/Abstract])+AND+(formulation+OR+stability+OR+excipient)&retmax=5&retmode=json',
           'label': '搜索PubMed文献', 'source': 'NCBI E-utilities', 'status': 'running'}
    pubmed_results = pubmed_future.result() if not pubmed_future.done() else pubmed_future.result()
    crossref_results = crossref_future.result() if not crossref_future.done() else crossref_future.result()
    openalex_results = openalex_future.result() if not openalex_future.done() else openalex_future.result()
    epmc_lit_results = epmc_lit_future.result() if not epmc_lit_future.done() else epmc_lit_future.result()
    yield {'type': 'web_action', 'action': 'fetch',
           'url': f'https://api.crossref.org/works?query={urllib.parse.quote(en_api)}+formulation',
           'label': '搜索学术文献', 'source': 'CrossRef/OpenAlex/EuroPMC', 'status': 'done'}
    n_pubmed = len(pubmed_results)
    n_crossref = len(crossref_results)
    n_openalex = len(openalex_results)
    n_epmc = len(epmc_lit_results)
    # Merge all literature sources, dedup by title
    seen_lit = set()
    all_lit = []
    for r in pubmed_results + crossref_results + openalex_results + epmc_lit_results:
        key = r.get('pmid', '') or r.get('doi', '') or r.get('title', '')[:80]
        if key and key not in seen_lit:
            seen_lit.add(key)
            score = 0
            t = (r.get('title', '') + ' ' + r.get('abstract', '') + ' ' + r.get('snippet', '')).lower()
            if en_api.lower() in t: score += 5
            if en_exc.lower() in t: score += 5
            for kw in ['compatibility', 'stability', 'degradation', 'impurity', 'excipient',
                       'formulation', 'reaction', 'incompatible', '相容', '降解', '杂质']:
                if kw in t: score += 2
            r['_score'] = score
            all_lit.append(r)
    all_lit.sort(key=lambda x: -x.get('_score', 0))
    all_lit = all_lit[:12]
    if all_lit:
        lit_results = [{'title': r['title'], 'link': r.get('link', ''),
                        'source': r.get('source', '') or r.get('snippet', ''),
                        'abstract': r.get('abstract', '')[:200] if r.get('abstract') else ''} for r in all_lit]
        _batch_translate_titles(lit_results)
        yield {'type': 'web_action', 'action': 'results', 'label': '文献检索结果',
               'results': lit_results,
               'count': len(lit_results), 'source': 'pubmed'}
    yield {'type': 'phase', 'phase': 2, 'status': 'done',
           'text': f'[OK] 文献检索完成 (PubMed {n_pubmed} + CrossRef {n_crossref} + OpenAlex {n_openalex} + EuroPMC {n_epmc})',
           'data': all_lit}

    # Phase 3: Clinical trials search (ClinicalTrials.gov + EU CTR)
    yield {'type': 'phase', 'phase': 3, 'status': 'running',
           'text': '[SEARCH] 正在检索全球临床试验数据...'}
    yield {'type': 'web_action', 'action': 'fetch',
           'url': f'https://clinicaltrials.gov/api/v2/studies?query.term={urllib.parse.quote(en_api)}+AND+formulation&pageSize=5&format=json',
           'label': '搜索ClinicalTrials', 'source': 'ClinicalTrials.gov', 'status': 'running'}
    clinical_results = clinical_future.result() if not clinical_future.done() else clinical_future.result()
    n_clinical = len(clinical_results)
    if clinical_results:
        clin_results = [{'title': r['title'], 'link': r.get('link', ''),
                         'nct': r.get('nct',''), 'phase': r.get('phase',''),
                         'status': r.get('status','')} for r in clinical_results[:8]]
        _batch_translate_titles(clin_results)
        yield {'type': 'web_action', 'action': 'results', 'label': '临床试验',
               'results': clin_results,
               'count': n_clinical, 'source': 'clinical'}
    yield {'type': 'phase', 'phase': 3, 'status': 'done',
           'text': f'[OK] 临床检索完成 (ClinicalTrials.gov {n_clinical})',
           'data': clinical_results}

    # Signal: all external searches done, switch left panel to ML view
    yield {'type': 'web_action', 'action': 'search_done', 'label': '所有搜索已完成'}

    # Phase 4: ML prediction
    yield {'type': 'phase', 'phase': 4, 'status': 'running',
           'text': '[TEST] 正在运行 ML 相容性预测模型...'}
    ml_result = ml_future.result() if not ml_future.done() else ml_future.result()
    if ml_result:
        level = ml_result.get('risk_level', 'unknown')
        prob = ml_result.get('probability', 0)
        yield {'type': 'phase', 'phase': 4, 'status': 'done',
               'text': f'[OK] ML 预测完成 — 风险等级: {level}，概率: {prob:.1%}',
               'data': ml_result}
    else:
        yield {'type': 'phase', 'phase': 4, 'status': 'done',
               'text': '[WARN] ML 预测未能运行（可能是SMILES解析失败），将仅基于文献和设备信息设计方案',
               'data': None}

    # Assemble combined clinical dict for _build_prompt
    clinical = {'pubmed': pubmed_results, 'clinicaltrials': clinical_results, 'general': []}

    # Fetch full abstracts & score relevance for all search results
    yield {'type': 'phase', 'phase': 3, 'status': 'running',
           'text': '[LOAD] 正在获取文献摘要并评估相关性...'}
    try:
        clinical = _fetch_abstracts_and_filter(api_name, exc1_name, clinical)
        n_relevant = len(clinical.get('highly_relevant', []))
        yield {'type': 'phase', 'phase': 3, 'status': 'running',
               'text': f'[OK] 摘要获取完成，{n_relevant} 篇高相关度文献已供AI参考'}
    except Exception as e:
        print(f'  Abstract fetch error: {e}')
        clinical.setdefault('abstracts', {})
        clinical.setdefault('highly_relevant', [])
    yield {'type': 'phase', 'phase': 3, 'status': 'done',
           'text': f'[FILE] 文献摘要检索完成',
           'data': clinical}

    # Collect all sources for reference
    all_sources = []
    for p in (patents.get('core', []) or patents.get('patents', [])):
        if p.get('link'):
            all_sources.append({'type': 'patent', 'title': p['title'], 'url': p['link']})
    for p in (patents.get('related', [])):
        if p.get('link'):
            all_sources.append({'type': 'patent', 'title': p['title'], 'url': p['link']})
    for p in pubmed_results:
        if p.get('link'):
            all_sources.append({'type': 'pubmed', 'title': p['title'], 'url': p['link']})
    for c in clinical_results:
        if c.get('link'):
            all_sources.append({'type': 'clinical', 'title': c['title'], 'url': c['link']})

    # Phase 5: Build full context and generate experiment design
    yield {'type': 'phase', 'phase': 5, 'status': 'running',
           'text': '[LIST] 正在从知识库检索法规指南与文献...'}

    kb_regulatory = None
    try:
        kb = get_kb()
        equipment_summary = kb.get_equipment_summary()
        kb_query = f"{api_name} {exc1_name} 原辅料相容性 实验设计 化学药物制剂研究 技术指导原则 处方研究 稳定性"
        if exc2_name:
            kb_query += f" {exc2_name}"
        kb_results = kb.retrieve(kb_query, top_k=6)
        if kb_results:
            kb_regulatory = kb_results
    except Exception as e:
        print(f'  KB retrieval error: {e}')
        equipment_summary = ''

    context = _build_prompt(question, api_name, exc1_name, exc2_name, patents, clinical, ml_result, equipment_summary, kb_regulatory, enriched_clinical=clinical)

    system_prompt = """你是药物制剂AI助手，专注于原辅料相容性（DEC）和实验方案设计。

**核心原则：你必须基于下面"用户提供的参考信息"中的实际搜索结果来设计方案，不能使用固定模板。**

请逐条阅读以下内容，并严格按照要求输出：

【如何参考搜索结果】
- 如果【相关专利信息】中有具体专利（有标题和链接），你必须：阅读专利标题，判断是否与当前API+辅料的相容性/制剂相关，如果相关则在实验方案中引用并说明依据；如果专利数量为0或未检索到，则在回答中明确说明"未检索到直接相关专利，方案基于通用科学知识设计"。
- 如果【PubMed相关文献】中有具体文献，你必须：阅读文献标题及摘要（如果提供），判断是否与当前API+辅料的相容性研究直接相关。仅当文献明确包含当前API或辅料时才能引用，不相关的不要强行引用。
- 如果【临床试验数据】不为空，参考文献的临床设计思路。
- 本方案应基于证据设计，而非固定的模板格式。实验条件、检测方法应参考检索到的现有研究，而不是机械套用指导原则。

**核心法规依据（仅当搜索无结果时作为兜底）：**
- 辅料用量较大的（如稀释剂等），按主药：辅料=1：5的比例混合
- 辅料用量较小的（如润滑剂等），按主药：辅料=20：1的比例混合
- 实验条件参照药物稳定性指导原则中影响因素的实验方法（即：高温、高湿、光照三种条件，**不做加速40°C/75%RH和长期25°C/60%RH条件**）
- 重点考察性状、含量、有关物质等
- 必要时可用原料药和辅料分别做平行对照实验
- 检测项目一般HPLC（有关物质和含量）即可

**回答结构要求：**

## 1. 结论摘要
相容/不相容判断 | 风险等级 | 概率

## 2. 参考信息
- 相关专利摘要（如有检索到，附标题和链接；如未检索到则注明无相关专利）
- 相关文献摘要（仅列出与当前API直接相关的文献）
- 临床试验数据（如有）
- ML模型预测结果

## 3. 实验方案设计（基于检索到的证据设计，不套模板）
### 3.1 实验目的
参考现有专利和文献中的实验设计思路
### 3.2 样品准备（配方比例）
严格按照指导原则：辅料用量大时按API:辅料=1:5，用量小时按API:辅料=20:1。
### 3.3 样品制备方法（使用公司现有设备）
### 3.4 实验条件
### 3.5 检测方法（参考相关文献中使用的检测方法）
### 3.6 取样时间点
### 3.7 数据记录与判定标准

## 4. 参考来源（列出所有引用的专利、文献和临床试验的完整链接）

其他要求：
1. 使用Markdown格式
2. 用中文回答
3. 设计方案时必须参考公司已有仪器设备，只能推荐公司现有的设备
4. **禁止使用 mermaid 流程图、时序图、代码块图等任何图表语法**
5. 引用来源必须标注链接
6. 如果专利/文献检索结果为0，必须明确说明，不能含糊其辞
7. 仅引用与当前API直接相关的文献，不相关的不要硬塞"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]

    # Stream sources reference first
    if all_sources:
        yield {'type': 'sources', 'sources': all_sources}

    # Stream DeepSeek response
    for text in _call_deepseek_stream(messages):
        yield {'type': 'content', 'text': text}

    yield {'type': 'phase', 'phase': 5, 'status': 'done', 'text': '[OK] 实验方案生成完成'}
