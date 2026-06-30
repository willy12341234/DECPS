"""
FDA Knowledge Layer — post-prediction validation & confidence adjustment.
Loads IID, Orange Book & NDC data to verify ML predictions against real-world approvals.
"""
import os, csv, re, json, sys, gzip
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

_PRJ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(_PRJ, 'webapp'))

_FDA_DIR = os.path.join(_PRJ, '..', 'fda_data')

# ── Lazy-loaded FDA data ──
_iid = None           # list[dict]
_ob_products = None   # dict: API → list[dict]
_ndc_products = None  # dict: API → list[dict]
_route_unii_cache = {} # (ingredient, route) → max_potency

_EXCIPIENT_NAME_ALIASES = {
    'lactose': ['lactose', 'lactose monohydrate', 'lactose anhydrous', ' milk sugar'],
    'magnesium stearate': ['magnesium stearate'],
    'povidone': ['povidone', 'polyvinylpyrrolidone', 'pvp', 'kollidon'],
    'croscarmellose sodium': ['croscarmellose sodium', 'crosscarmellose sodium'],
    'starch': ['starch', 'corn starch', 'maize starch', 'potato starch'],
    'silicon dioxide': ['silicon dioxide', 'colloidal silicon dioxide', 'silica'],
    'talc': ['talc', 'talcum'],
    'titanium dioxide': ['titanium dioxide', 'tio2'],
    'polyethylene glycol': ['polyethylene glycol', 'peg', 'macrogol'],
    'propylene glycol': ['propylene glycol'],
    'glycerin': ['glycerin', 'glycerol', 'glycerine'],
    'ethanol': ['ethanol', 'alcohol', 'ethyl alcohol'],
    'water': ['water', 'purified water', 'sterile water', 'water for injection'],
    'sodium chloride': ['sodium chloride', 'nacl', 'salt', 'common salt'],
    'sucrose': ['sucrose', 'sugar', 'cane sugar'],
    'mannitol': ['mannitol', 'mannite'],
    'sorbitol': ['sorbitol', 'sorbit'],
    'microcrystalline cellulose': ['microcrystalline cellulose', 'mcc', 'cellulose microcrystalline'],
    'hydroxypropyl methylcellulose': ['hydroxypropyl methylcellulose', 'hpmc', 'hypromellose'],
    'carboxymethylcellulose sodium': ['carboxymethylcellulose sodium', 'carmellose sodium', 'cmc sodium'],
    'polysorbate 80': ['polysorbate 80', 'tween 80', 'polyoxyethylene sorbitan monooleate'],
    'polysorbate 20': ['polysorbate 20', 'tween 20'],
    'sodium lauryl sulfate': ['sodium lauryl sulfate', 'sls', 'sodium dodecyl sulfate'],
    'citric acid': ['citric acid', 'citrate'],
    'benzyl alcohol': ['benzyl alcohol'],
    'methylparaben': ['methylparaben', 'methyl paraben', 'nipagin'],
    'propylparaben': ['propylparaben', 'propyl paraben', 'nipasol'],
    'edta': ['edta', 'disodium edta', 'edetate disodium', 'ethylenediaminetetraacetic acid'],
    'butylated hydroxytoluene': ['butylated hydroxytoluene', 'bht'],
    'butylated hydroxyanisole': ['butylated hydroxyanisole', 'bha'],
}

def _load_iid():
    global _iid
    if _iid is not None:
        return
    path = os.path.join(_FDA_DIR, 'fda_iid.csv')
    if not os.path.exists(path):
        _iid = []
        return
    _iid = []
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            row['_name'] = row['IngredientName'].lower().strip(' .').lstrip('.')
            _iid.append(row)

def _load_ob():
    global _ob_products
    if _ob_products is not None:
        return
    path = os.path.join(_FDA_DIR, 'fda_ob_products.csv')
    if not os.path.exists(path):
        _ob_products = {}
        return
    _ob_products = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            api = row['ActiveIngredient'].lower().strip()
            if api not in _ob_products:
                _ob_products[api] = []
            _ob_products[api].append(row)

def _load_ndc():
    global _ndc_products
    if _ndc_products is not None:
        return
    path = os.path.join(_FDA_DIR, 'fda_ndc_products.csv')
    if not os.path.exists(path):
        _ndc_products = {}
        return
    _ndc_products = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            api = row['Nonproprietaryname'].lower().strip()
            if api not in _ndc_products:
                _ndc_products[api] = []
            _ndc_products[api].append(row)

def load_all():
    _load_iid()
    _load_ob()
    _load_ndc()

# ── Exc ingredient name resolution ──
@lru_cache(maxsize=1024)
def _normalize_excipient_name(name: str) -> str:
    """Find the canonical IID ingredient name for a given excipient name."""
    n = name.lower().strip()
    # Resolve Chinese name to English first
    try:
        from predictor import _CN2EN
        en = _CN2EN.get(name, '')
        if en:
            n = en.lower().strip()
    except:
        pass

    _load_iid()
    # Direct match
    for r in _iid:
        if n == r['_name']:
            return r['_name']
    # Substring match
    for r in _iid:
        if n in r['_name'] or r['_name'] in n:
            return r['_name']
    # Alias match
    for canonical, aliases in _EXCIPIENT_NAME_ALIASES.items():
        if n in aliases or any(a in n for a in aliases):
            return canonical
    return n

# ── API name resolution ──
@lru_cache(maxsize=1024)
def _normalize_api_name(name: str) -> str:
    """Resolve API name to FDA-compatible form."""
    try:
        from predictor import _CN2EN, get_sm
        en = _CN2EN.get(name, name)
    except:
        en = name
    return en.lower().strip()

# ── Public query functions ──

def route_compatibility_score(api_name: str, excipient_name: str, condition_str: str = '') -> dict:
    """Score how well an API-excipient pair matches FDA approved data.

    Returns:
    {
        'excipient_approved_routes': [...],
        'route_overlap': bool,          # Does excipient have approval for API's route?
        'excipient_max_potency': float,
        'api_approved_forms': [...],
        'confidence': 'high'|'medium'|'low'|'unknown',
        'evidence': str,                # Human-readable explanation
    }
    """
    _load_iid()
    _load_ob()

    canonical_exc = _normalize_excipient_name(excipient_name)
    canonical_api = _normalize_api_name(api_name)

    # 1. Exc ingredient routes
    exc_routes = set()
    for r in _iid:
        if canonical_exc in r['_name'] or r['_name'] in canonical_exc:
            if r['Route'].strip():
                exc_routes.add(r['Route'].strip())

    # 2. API routes from Orange Book
    api_routes = set()
    for api_key, products in _ob_products.items():
        if canonical_api in api_key or api_key in canonical_api:
            for p in products:
                if p['Route'].strip():
                    api_routes.add(p['Route'].strip())

    # 3. Detect route from condition string
    detected_route = _detect_route_from_condition(condition_str)
    if not detected_route and api_routes:
        detected_route = list(api_routes)[0]  # use API's first route

    # 4. Route overlap
    route_overlap = bool(exc_routes & api_routes) if api_routes else False

    # 5. Confidence
    if route_overlap and exc_routes:
        confidence = 'high'
        evidence = f'{excipient_name} has FDA approval in {len(exc_routes)} routes matching {api_name}'
    elif exc_routes and not api_routes:
        confidence = 'medium'
        evidence = f'{excipient_name} approved in {len(exc_routes)} routes; {api_name} has no Orange Book data'
    elif not exc_routes:
        confidence = 'low'
        evidence = f'{excipient_name} not found in FDA IID'
    else:
        confidence = 'unknown'
        evidence = 'Insufficient FDA data'

    return {
        'excipient_approved_routes': sorted(exc_routes),
        'api_approved_routes': sorted(api_routes),
        'route_overlap': route_overlap,
        'confidence': confidence,
        'evidence': evidence,
    }


def _detect_route_from_condition(cond: str) -> str:
    """Heuristic route detection from condition string."""
    if not cond:
        return ''
    c = cond.lower()
    if 'topical' in c or 'cream' in c or 'ointment' in c or 'gel' in c or '外用' in c:
        return 'TOPICAL'
    if 'oral' in c or 'tablet' in c or 'capsule' in c or '口服' in c:
        return 'ORAL'
    if 'inject' in c or 'iv' in c or '静脉' in c:
        return 'INJECTION'
    if 'ophthalmic' in c or 'eye' in c or '滴眼' in c:
        return 'OPHTHALMIC'
    if 'inhal' in c or '吸入' in c:
        return 'INHALATION'
    if 'nasal' in c or '鼻' in c:
        return 'NASAL'
    return ''


def fda_knowledge_adjustment(api_name: str, exc1_name: str,
                              ml_probability: float,
                              condition: str = '') -> dict:
    """Adjust ML prediction confidence based on FDA knowledge.

    Returns:
    {
        'adjusted_probability': float,       # ML prob ± FDA adjustment
        'confidence_delta': str,              # 'up'|'down'|'none'
        'fda_evidence': str,
        'fda_confidence': str,
    }
    """
    info = route_compatibility_score(api_name, exc1_name, condition)
    adjustment = 0.0

    # Route overlap → increase confidence in ML prediction
    if info['route_overlap']:
        if ml_probability > 0.5:
            adjustment = -0.03  # Slightly reduce alarm for FDA-approved combos
        else:
            adjustment = -0.05  # Reinforce compatible verdict
        confidence_delta = 'up'
    elif info['excipient_approved_routes'] and not info['route_overlap']:
        # Excipient approved for other routes but not this API's route
        if ml_probability > 0.5:
            adjustment = 0.05  # Incompatible more likely if route mismatch
        else:
            adjustment = 0.03  # Compatible less certain
        confidence_delta = 'down'
    elif not info['excipient_approved_routes']:
        # Exc ingredient not in FDA database at all
        confidence_delta = 'none'
    else:
        confidence_delta = 'none'

    adjusted = max(0.0, min(1.0, ml_probability + adjustment))

    return {
        'adjusted_probability': round(adjusted, 4),
        'confidence_delta': confidence_delta,
        'fda_evidence': info['evidence'],
        'fda_confidence': info['confidence'],
    }
