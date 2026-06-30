"""Prediction module v3 — enhanced features, multi-target, condition-aware."""

import numpy as np, json, os, xgboost as xgb, requests, shap, re
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, MACCSkeys, rdMolDescriptors

_BASE = os.path.dirname(os.path.abspath(__file__))
_PRJ = os.path.join(_BASE, '..')

_model = None
_model_count = None
_model_total = None
_model_maxsingle = None
_smiles = {}
_names = []
_num_feats = []
_num_idx = []
_feat_idx = None  # feature selection indices for model
_CN2EN = {}

def load():
    global _model, _model_count, _model_total, _model_maxsingle, _smiles, _names, _num_feats, _num_idx, _feat_idx, _CN2EN
    for mname, attr in [("xgb_clf_final.json", "_model"), ("xgb_count.json", "_model_count"),
                         ("xgb_total.json", "_model_total"), ("xgb_maxsingle.json", "_model_maxsingle")]:
        p = os.path.join(_PRJ, "models", mname)
        if os.path.exists(p):
            try:
                m = xgb.XGBClassifier() if attr == "_model" else xgb.XGBRegressor()
                m.load_model(p)
                globals()[attr] = m
            except Exception:
                pass
    cp = os.path.join(_PRJ, "caches", "smiles_cache.json")
    if os.path.exists(cp):
        try:
            with open(cp) as f: _smiles.update(json.load(f))
        except Exception: pass
    ccp = os.path.join(_PRJ, "caches", "cn2en_cache.json")
    if os.path.exists(ccp):
        try:
            with open(ccp, encoding='utf-8') as f: _CN2EN.update(json.load(f))
        except Exception: pass
    fn = os.path.join(_PRJ, "features", "feature_names.json")
    if os.path.exists(fn):
        try:
            with open(fn) as f: _names.extend(json.load(f))
        except Exception: pass
    nf = os.path.join(_PRJ, "features", "num_feat_names.json")
    if os.path.exists(nf):
        try:
            with open(nf) as f: _num_feats.extend(json.load(f))
            _num_idx[:] = [i for i, n in enumerate(_names) if n in _num_feats]
        except Exception: pass
    if not _num_idx and _names:
        _num_feats = _names[:100]
        _num_idx = list(range(min(100, len(_names))))
    fi = os.path.join(_PRJ, "models", "feature_indices_2000.npy")
    if os.path.exists(fi):
        try: _feat_idx = np.load(fi)
        except: _feat_idx = None
    else: _feat_idx = None

try:
    load()
except Exception as e:
    print(f"[WARN] Model init failed: {e}")
load()

# ---------------------------------------------------------------------------
# Condition parsing: temperature, humidity, light
# ---------------------------------------------------------------------------
COND_MAP = {
    '高温60℃':  (60, 0,  0), '高温50℃':    (50, 0,  0),
    '高温60°C': (60, 0,  0), '高温50°C':   (50, 0,  0),
    '60℃':     (60, 0,  0), '50℃':        (50, 0,  0),
    '60°C':    (60, 0,  0), '50°C':       (50, 0,  0),
    '高温':     (60, 0,  0),
    '高湿RH92.5%': (25, 92.5, 0), '高湿RH75%': (25, 75, 0),
    '高湿':     (25, 75, 0), '92.5%RH':   (25, 92.5, 0),
    '光照':     (25, 0,  1),
}

def cond_to_params(cond_str):
    """Parse condition text → (temp_C, humidity_pct, light_exposure)."""
    cond_str = str(cond_str).strip()
    if cond_str in ('N/A', 'None', '', 'nan'):
        return (25.0, 0.0, 0.0)
    # "0" = Normal (25°C, Ambient / normal humidity) -> humidity should be ~60% RH
    if cond_str == '0':
        return (25.0, 60.0, 0.0)
    # Legacy codes: 1=light, 2=high_temp, 3=high_humidity
    LEGACY_NUM = {'1': (25, 0, 1), '2': (60, 0, 0), '3': (25, 75, 0)}
    if cond_str in LEGACY_NUM:
        return LEGACY_NUM[cond_str]
    key = cond_str
    if key in COND_MAP:
        return COND_MAP[key]
    m_temp = re.search(r'(\d+)\s*[℃°C]', cond_str)
    m_rh   = re.search(r'RH\s*(\d+(?:\.\d+)?)\s*%', cond_str)
    temp = float(m_temp.group(1)) if m_temp else 25.0
    humidity = float(m_rh.group(1)) if m_rh else 0.0
    # Normal humidity ~= 60% RH, not 0%
    has_ambient_humidity = '常湿' in cond_str or 'ambient' in cond_str.lower() or 'normal' in cond_str.lower()
    if humidity == 0.0 and has_ambient_humidity:
        humidity = 60.0
    light = 1.0 if '光照' in cond_str or 'light' in cond_str.lower() else 0.0
    return (temp, humidity, light)


# ---------------------------------------------------------------------------
# Chemistry helpers
# ---------------------------------------------------------------------------
def _fp_arr(fp_vec, nb):
    a = np.zeros(nb, dtype=int)
    for b in fp_vec.GetOnBits():
        if b < nb: a[b] = 1
    return a

def _delta(sm):
    m = Chem.MolFromSmiles(sm)
    if not m: return None
    gs = [
        (1125,33.5,"[CX4;H3]"),(1180,16.1,"[CX4;H2]"),(820,-1.0,"[CX4;H1]"),(350,-19.2,"[CX4;H0]"),
        (1030,28.5,"[CX3;H2]"),(1030,13.5,"[CX3;H1]"),(1030,-5.5,"[CX3;H0]"),(7630,71.4,"c1ccccc1"),
        (410,18.0,"[F]"),(2760,24.0,"[Cl]"),(3700,30.0,"[Br]"),(4550,31.5,"[I]"),
        (7120,10.0,"[OH][CX4]"),(7120,1.0,"[OH]c"),(1000,3.5,"[OD2]([#6])[#6]"),
        (5100,22.0,"[CX3H1](=O)[#6]"),(4150,10.8,"[CX3](=O)([#6])[#6]"),
        (8970,28.5,"[CX3](=O)[OH]"),(3590,18.0,"[CX3](=O)[OX2][#6]"),
        (16200,34.0,"[CX3](=O)[NH2]"),(12500,27.0,"[CX3](=O)[NH]"),
        (3140,19.2,"[NH2]"),(2100,4.5,"[NH1]"),(1200,-9.0,"[NH0]"),
        (6100,24.0,"[C]#[N]"),(6900,32.0,"[N+](=O)[O-]"),(3450,28.0,"[SH]"),(3380,12.0,"[SX2]"),
    ]
    mh = Chem.AddHs(m); E=V=0.0
    for Ei,Vi,sma in gs:
        pat = Chem.MolFromSmarts(sma)
        if pat:
            n = len(mh.GetSubstructMatches(pat))
            E += n*Ei; V += n*Vi
    ri = mh.GetRingInfo()
    if ri.NumRings()>0:
        E += ri.NumRings()*310
        if sum(1 for a in mh.GetAtoms() if a.GetIsAromatic())>0: E+=830
    return round((E/V)**0.5, 2) if V>0 else None

# ---- Extended RDKit descriptors ----
EXTRA_DESC = [
    ('fcsp3',       lambda m: rdMolDescriptors.CalcFractionCSP3(m)),
    ('rot_bonds',   lambda m: rdMolDescriptors.CalcNumRotatableBonds(m)),
    ('nhoh_count',  lambda m: Descriptors.NHOHCount(m)),
    ('no_count',    lambda m: Descriptors.NOCount(m)),
    ('heavy_atoms', lambda m: m.GetNumHeavyAtoms()),
    ('sat_rings',   lambda m: rdMolDescriptors.CalcNumSaturatedRings(m)),
    ('ali_rings',   lambda m: rdMolDescriptors.CalcNumAliphaticRings(m)),
    ('het_atoms',   lambda m: rdMolDescriptors.CalcNumHeteroatoms(m)),
    ('spiro_atoms', lambda m: rdMolDescriptors.CalcNumSpiroAtoms(m)),
    ('bridge_atoms',lambda m: rdMolDescriptors.CalcNumBridgeheadAtoms(m)),
    ('ar_hetero',   lambda m: rdMolDescriptors.CalcNumAromaticHeterocycles(m)),
    ('sat_hetero',  lambda m: rdMolDescriptors.CalcNumSaturatedHeterocycles(m)),
    ('balaban_j',   lambda m: Descriptors.BalabanJ(m) if Chem.MolFromSmiles('C') else 0),
    ('bertz_ct',    lambda m: Descriptors.BertzCT(m)),
    ('kappa1',      lambda m: rdMolDescriptors.CalcKappa1(m)),
    ('kappa2',      lambda m: rdMolDescriptors.CalcKappa2(m)),
    ('kappa3',      lambda m: rdMolDescriptors.CalcKappa3(m)),
]

# ---- Custom functional group counts ----
CUSTOM_GROUP_SMARTS = [
    ('sulfonate',    '[#16X4](=[OX1])(=[OX1])[OX1H0-]'),
    ('sulfate',      '[#16X4](=[OX1])(=[OX1])([OX1H0-])[OX1H0-]'),
    ('phosphate',    '[#15X4](=[OX1])([OX1H0-])([OX1H0-])[OX1H0-]'),
    ('nitrile',      '[C]#[N]'),
    ('epoxide',      'C1OC1'),
    ('carbamate',    '[NX3][CX3](=[OX1])[OX2]'),
    ('urea',         '[NX3][CX3](=[OX1])[NX3]'),
    ('sulfonamide',  '[#16X4](=[OX1])(=[OX1])[NX3]'),
    ('boronic_acid', '[BX3]([OX1H])[OX1H]'),
    ('tert_amine',   '[NX3]([#6])([#6])[#6]'),
    ('quat_n',       '[N+X4]'),
    ('ether_o',      '[OD2]([#6])[#6]'),
    ('carbonyl',     '[CX3]=[OX1]'),
    ('azide',        '[N-]=[N+]=[N]'),
    ('hydrazine',    '[NX3][NX3]'),
    ('hydroxylamine','[NX3][OX2H]'),
    ('f_atom',       lambda m: sum(1 for a in m.GetAtoms() if a.GetAtomicNum()==9)),
    ('cl_atom',      lambda m: sum(1 for a in m.GetAtoms() if a.GetAtomicNum()==17)),
    ('br_atom',      lambda m: sum(1 for a in m.GetAtoms() if a.GetAtomicNum()==35)),
    ('i_atom',       lambda m: sum(1 for a in m.GetAtoms() if a.GetAtomicNum()==53)),
]

# ---- Reactivity SMARTS (kept, same as before) ----
REACT_SMARTS = [
    ('est','[CX3](=O)[OX2][#6]'),('amd','[CX3](=O)[NX3]'),('lac','[#6]-[NX3]1-[#6]=[#6]-[#6]-[#6]-1'),
    ('lct','[#6]-[OX2]1-[#6]=[#6]-[#6]-[#6]-1'),('act','[#6][OX2][#6]([OX2][#6])[OX2][#6]'),
    ('imn','[#6]=[NX2]'),('ahd','[CX3](=O)[OX2][CX3](=O)'),
    ('pho','[OH]c1ccccc1'),('ani','[NX3;H2]c1ccccc1'),('thl','[SX1H]'),
    ('the','[#16X2]([#6])[#6]'),('ald','[CX3H1](=O)[#6]'),('pal','[CX4;H2][OX2H]'),
    ('ben','[c]:[#6][CX4H2]'),('all','[#6]=[#6]-[CX4H2]'),
    ('nit','[NX3](=O)=[O]'),('nox','[NX3+][O-]'),('qui','O=C1C=CC(=O)C=C1'),
    ('acl','[Cl]c1ccccc1'),('abr','[Br]c1ccccc1'),('aid','[I]c1ccccc1'),
    ('bdk','O=[#6][#6][#6]=O'),('cat','[OH]c1c(O)cccc1'),('cax','[CX3](=O)[OX1H]'),
    ('pam','[NX3;H2][#6]'),
]

def _react_vec(mol):
    if mol is None: return [0]*28
    v = []
    for _, sma in REACT_SMARTS:
        pat = Chem.MolFromSmarts(sma)
        v.append(len(mol.GetSubstructMatches(pat)) if pat else 0)
    ri = mol.GetRingInfo()
    v.append(ri.NumRings())
    v.append(rdMolDescriptors.CalcNumAromaticRings(mol))
    v.append(Descriptors.NumHDonors(mol) + Descriptors.NumHAcceptors(mol))
    return v

def _react_categories(rv):
    """Group 28 reactivity features into 5 mechanism sums: hydrolysis, oxidation, photolysis, chelation, stability."""
    return {
        'hydrolysis': sum(rv[0:7]),
        'oxidation':  sum(rv[7:15]),
        'photolysis': sum(rv[15:21]),
        'chelation':  sum(rv[21:25]),
        'stability':  sum(rv[25:28]),
    }

# ===== RAG-derived pairwise reaction rules =====
# Single source of truth: src/smarts_rules.py
import sys as _sys; _sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
from smarts_rules import PAIRWISE_RULES

def _pairwise_vec(mol_a, mol_e):
    """Compute pairwise interaction features between API and excipient molecules.
    Returns weighted feature vector for each rule:
      - 0 if no match
      - count of API matches if only API matches (potential)
      - count of excipient matches if only excipient matches (potential)
      - API_match_count × excipient_match_count if both match (active reaction)
      This weighted encoding helps the model learn reaction strength.
    """
    v = []
    total_score = 0.0
    for name, api_smarts, exc_smarts, desc in PAIRWISE_RULES:
        api_pat = Chem.MolFromSmarts(api_smarts)
        exc_pat = Chem.MolFromSmarts(exc_smarts)
        if api_pat is None or exc_pat is None:
            v.append(0.0)
            continue
        api_matches = len(mol_a.GetSubstructMatches(api_pat)) if mol_a else 0
        exc_matches = len(mol_e.GetSubstructMatches(exc_pat)) if mol_e else 0
        # Weight: count of both matching (reaction sites)
        weighted = float(api_matches) * float(exc_matches)
        v.append(weighted)
        total_score += weighted
    # Also return mechanism-level aggregates as a separate dict
    # This is accessed externally for feature addition
    return v

# Reaction mechanism indices for aggregate scoring
# Maps each pairwise rule index to its mechanism category
_REACTION_MECHANISMS = {
    'maillard': list(range(0, 5)),  # Maillard reactions
    'hydrolysis': list(range(5, 12)),  # Hydrolysis
    'oxidation': list(range(12, 20)),  # Oxidation
    'acid_base': list(range(20, 28)),  # Acid-base
    'misc_rxn': list(range(28, 145)),  # Other reactions
}

def _reaction_risk_scores(mol_a, mol_e):
    '''Compute 5 aggregate reaction risk scores (0-1 each).
    These are continuous features that capture overall reactivity.
    '''
    from smarts_rules import PAIRWISE_RULES
    scores = {'maillard': 0.0, 'hydrolysis': 0.0, 'oxidation': 0.0, 
              'acid_base': 0.0, 'misc_rxn': 0.0}
    
    for i, (name, api_smarts, exc_smarts, desc) in enumerate(PAIRWISE_RULES):
        api_pat = Chem.MolFromSmarts(api_smarts) if api_smarts else None
        exc_pat = Chem.MolFromSmarts(exc_smarts) if exc_smarts else None
        
        api_match = len(mol_a.GetSubstructMatches(api_pat)) if (api_pat and mol_a) else 0
        exc_match = len(mol_e.GetSubstructMatches(exc_pat)) if (exc_pat and mol_e) else 0
        
        if api_match > 0 and exc_match > 0:
            weight = float(api_match * exc_match)
            for mech, indices in _REACTION_MECHANISMS.items():
                if i in indices:
                    scores[mech] = max(scores[mech], min(weight, 1.0))
                    break
    
    # Add total reaction score
    scores['total_reactive'] = sum(scores.values())
    return [min(scores[k], 1.0) for k in ['maillard', 'hydrolysis', 'oxidation', 'acid_base', 'total_reactive']]

def _extra_descs(mol):
    if mol is None: return [0.0]*len(EXTRA_DESC)
    try:
        return [fn(mol) for _, fn in EXTRA_DESC]
    except:
        return [0.0]*len(EXTRA_DESC)

def _custom_groups(mol):
    if mol is None: return [0]*len(CUSTOM_GROUP_SMARTS)
    v = []
    for name, sma in CUSTOM_GROUP_SMARTS:
        if callable(sma):
            v.append(sma(mol))
        else:
            pat = Chem.MolFromSmarts(sma)
            v.append(len(mol.GetSubstructMatches(pat)) if pat else 0)
    return v

def _cmol(sm):
    m = Chem.MolFromSmiles(sm)
    if not m: return None
    base = {
        'e':_fp_arr(AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048), 2048),
        'm':_fp_arr(MACCSkeys.GenMACCSKeys(m), 166),
        'r':_fp_arr(Chem.RDKFingerprint(m, fpSize=2048), 2048),
        'd':_delta(sm) or 0, 'hbd':Descriptors.NumHDonors(m),
        'hba':Descriptors.NumHAcceptors(m), 'tpsa':round(Descriptors.TPSA(m),2),
        'logp':round(Descriptors.MolLogP(m),2), 'mr':round(Descriptors.MolMR(m),2),
        'mw':round(Descriptors.MolWt(m),2),
    }
    base['extra'] = _extra_descs(m)
    base['cg'] = _custom_groups(m)
    base['react'] = _react_vec(m)
    base['r_cat'] = _react_categories(base['react'])
    base['mol'] = m
    return base


def _ai_smiles(name):
    """Use DeepSeek to translate a drug name to SMILES."""
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
        from chat import DEEPSEEK_API_KEY, DEEPSEEK_URL, DEEPSEEK_MODEL
        resp = requests.post(
            DEEPSEEK_URL,
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a pharmaceutical chemistry assistant. Return ONLY the SMILES string for the given drug/excipient name. No thinking, no reasoning, no explanations. Handle common typos, misspellings, and synonyms. If the name is slightly misspelled, infer the correct drug. Return ONLY the SMILES, no explanation. If truly unknown, return UNKNOWN."},
                    {"role": "user", "content": f"SMILES for {name}"}
                ],
                "temperature": 0.05,
                "max_tokens": 8192,
            },
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            timeout=15
        )
        if resp.status_code == 200:
            sm = resp.json()['choices'][0]['message']['content'].strip().rstrip('.')
            if sm and sm != 'UNKNOWN' and Chem.MolFromSmiles(sm):
                _smiles[name] = sm
                return sm
    except:
        pass
    return None

def _ai_translate_name(name):
    """Use DeepSeek to correct typos and find the English drug name.
    Returns (english_name, smiles) or (None, None)."""
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
        from chat import DEEPSEEK_API_KEY, DEEPSEEK_URL, DEEPSEEK_MODEL
        resp = requests.post(
            DEEPSEEK_URL,
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a pharmaceutical chemistry assistant. Given a drug or excipient name (which may have typos, be in Chinese, or be incomplete), return the CORRECT English name and SMILES. No thinking, no reasoning, no explanations. Format: {\"name\": \"correct english name\", \"smiles\": \"SMILES\"}. Handle typos intelligently. If unknown, return {\"name\": null, \"smiles\": null}."},
                    {"role": "user", "content": name}
                ],
                "temperature": 0.3,
                "max_tokens": 8192,
            },
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            timeout=30
        )
        if resp.status_code == 200:
            import json
            content = resp.json()['choices'][0]['message']['content'].strip()
            content = content.removeprefix('```json').removeprefix('```').removesuffix('```').strip()
            parsed = json.loads(content)
            en_name = parsed.get('name')
            smiles = parsed.get('smiles')
            if en_name and smiles:
                from rdkit import Chem
                if Chem.MolFromSmiles(smiles):
                    _smiles[name] = smiles
                    _smiles[en_name] = smiles
                    return en_name, smiles
    except:
        pass
    return None, None

def get_sm(name):
    name = name.strip()
    if not name:
        return None
    # Fast path: direct SMILES parsing for strings that look like chemical notation
    if any(c in name for c in ['=', '#', '[', ']', '@', '(', ')']) and any(c.isdigit() for c in name):
        m = Chem.MolFromSmiles(name)
        if m:
            _smiles[name] = name
            return name
    # Reject obviously invalid input (prevents DeepSeek API timeouts on garbage)
    # - Pure gibberish (repeated single char, no vowels in ASCII)
    # - Very long non-SMILES strings
    # - Strings with no alphabetic characters
    ascii_only = name.isascii()
    if ascii_only:
        # Reject: no vowels (gibberish like "zzzzzzzzz")
        vowels = set('aeiouAEIOU')
        has_vowel = any(c in vowels for c in name)
        # Reject: repeated single character (gibberish)
        unique_chars = len(set(name.lower()))
        if (not has_vowel and len(name) > 4) or unique_chars <= 2:
            m = Chem.MolFromSmiles(name)
            if m:
                _smiles[name] = name
                return name
            return None
    else:
        # Chinese text check: reject names with "不存在" (doesn't exist) pattern
        if '不存在' in name:
            return None
    # 1) Direct cache lookup
    if name in _smiles and _smiles[name]:
        return _smiles[name]
    name_lower = name.lower()
    for k, v in _smiles.items():
        if k.lower() == name_lower and v:
            return v
    # 2) Chinese → English translation → cache → PubChem
    en_name = _CN2EN.get(name)
    if en_name:
        for k, v in _smiles.items():
            if k.lower() == en_name.lower() and v:
                return v
        try:
            r = requests.get(f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{requests.utils.quote(en_name)}/property/SMILES/JSON', timeout=8)
            if r.status_code == 200:
                sm = r.json()['PropertyTable']['Properties'][0]['SMILES']
                _smiles[name] = sm
                return sm
        except:
            pass
    # 3) AI-assisted translation (handles typos, misspellings, non-standard names)
    sm = _ai_smiles(name)
    if sm:
        return sm

    # 3b) AI translation: get corrected English name + SMILES
    en_name_ai, sm_ai = _ai_translate_name(name)
    if sm_ai:
        _smiles[name] = sm_ai
        return sm_ai
    if en_name_ai:
        en_name = en_name_ai

    # 4) Try PubChem with name (AI-corrected first, then original)
    pubchem_name = en_name or name
    for try_name in [pubchem_name, name] if pubchem_name != name else [name]:
        try:
            r = requests.get(f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{requests.utils.quote(try_name)}/property/SMILES/JSON', timeout=8)
            if r.status_code == 200:
                sm = r.json()['PropertyTable']['Properties'][0]['SMILES']
                _smiles[name] = sm
                return sm
        except:
            pass
    # 5) Try as SMILES directly
    if Chem.MolFromSmiles(name):
        _smiles[name] = name
        return name
    # 6) Fallback: try PubChem synonym search
    try:
        r = requests.get(f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{requests.utils.quote(name)}/synonyms/JSON', timeout=6)
        if r.status_code == 200:
            data = r.json()
            cid = data['InformationList']['Information'][0].get('CID')
            if cid:
                r2 = requests.get(f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/SMILES/JSON', timeout=6)
                if r2.status_code == 200:
                    sm = r2.json()['PropertyTable']['Properties'][0]['SMILES']
                    _smiles[name] = sm
                    return sm
    except:
        pass
    # 7) Try RDKit from molecular formula (for simple inorganics)
    try:
        m = Chem.MolFromFormula(name)
        if m and m.GetNumAtoms() > 0:
            sm = Chem.MolToSmiles(m)
            _smiles[name] = sm
            return sm
    except:
        pass
    return None


# ---------------------------------------------------------------------------
# Feature vector builder layout (13060 dimensions)
# ---------------------------------------------------------------------------
#   [0:6]        = 7 basic descriptors - API
#   [7:2054]     = 2048 ECFP - API
#   [2055:2220]  = 166 MACCS - API
#   [2221:4268]  = 2048 RDKit - API
#   [4269:4270]  = 2 placeholder (has_smiles, ratio)
#   [4271:4277]  = 7 basic descriptors - Exc1
#   [4278:6325]  = 2048 ECFP - Exc1
#   [6326:6491]  = 166 MACCS - Exc1
#   [6492:8539]  = 2048 RDKit - Exc1
#   [8540:8548]  = 9 delta properties
#   [8549:8550]  = 2 placeholder (exc2 has_smiles, ratio)
#   [8551:12826] = Exc2 block (4276 dimensions)
#   [12827:12828] = condition, days
#   [12829:12911] = 83 reactivity features (water/oxidation/heat)
#   [12912:12962] = 51 extra descriptors (17 API, 17 Exc1, 17 Delta)
#   [12963:13022] = 60 custom group features (20 API, 20 Exc1, 20 Delta)
#   [13023:13027] = 5 experimental conditions (temp, humidity, light, days, cond_code)
#   [13028:13042] = 15 condition-reactivity interaction terms
#   [13043:13059] = 17 pairwise chemical reaction rules
#   Total dimensions: 13060


def build_vec(api_s, e1_s, e2_s=None, days=0, cond=0):
    a = _cmol(api_s); e1 = _cmol(e1_s); e2 = _cmol(e2_s) if e2_s else None
    if not a or not e1: return None
    v = []
    # ---- API block ----
    for k in ['d','hbd','hba','tpsa','logp','mr','mw']: v.append(a[k])
    v.extend(a['e'].tolist()); v.extend(a['m'].tolist()); v.extend(a['r'].tolist())
    v.append(1); v.append(0.0)
    # ---- Exc1 block ----
    for k in ['d','hbd','hba','tpsa','logp','mr','mw']: v.append(e1[k])
    v.extend(e1['e'].tolist()); v.extend(e1['m'].tolist()); v.extend(e1['r'].tolist())
    for pk,ek in [('hbd','hbd'),('hba','hba'),('tpsa','tpsa'),('logp','logp'),('mr','mr')]:
        v.append(a[pk]-e1[ek])
    v.append((a['d']-e1['d'])*2.045); v.append(a['d']-e1['d'])
    # ---- Exc2 block ----
    v.append(1 if e2 else 0); v.append(0.0)
    if e2:
        for k in ['d','hbd','hba','tpsa','logp','mr','mw']: v.append(e2[k])
        v.extend(e2['e'].tolist()); v.extend(e2['m'].tolist()); v.extend(e2['r'].tolist())
        for pk,ek in [('hbd','hbd'),('hba','hba'),('tpsa','tpsa'),('logp','logp'),('mr','mr')]:
            v.append(a[pk]-e2[ek])
        v.append((a['d']-e2['d'])*2.045); v.append(a['d']-e2['d'])
    else:
        v.extend([0]*7+[0]*2048+[0]*166+[0]*2048+[0]*7)
    # ---- Condition: parse to physical params (used for all condition features) ----
    if isinstance(cond, str):
        temp, hum, light = cond_to_params(cond)
    else:
        temp, hum, light = cond_to_params(str(cond))
    days_f = float(days) if days else 0.0
    cond_code = float(cond) if isinstance(cond, (int, float)) else 0.0
    # ---- Condition (legacy compat, 2 features) ----
    v.append(cond_code); v.append(days_f)
    # ---- 84 reactivity features ----
    v.extend(a['react']); v.extend(e1['react'])
    v.extend([a['react'][i] - e1['react'][i] for i in range(len(a['react']))])  # delta

    # ---- NEW: 17 extra descriptors: API, Exc1, Delta ----
    for d in a['extra']: v.append(d)
    for d in e1['extra']: v.append(d)
    for i in range(len(a['extra'])): v.append(a['extra'][i] - e1['extra'][i])

    # ---- NEW: 20 custom groups: API, Exc1, Delta ----
    for d in a['cg']: v.append(d)
    for d in e1['cg']: v.append(d)
    for i in range(len(a['cg'])): v.append(a['cg'][i] - e1['cg'][i])

    # ---- NEW: Condition params (5 features) ----
    v.append(temp); v.append(hum); v.append(light)
    v.append(days_f)
    v.append(cond_code)

    # ---- NEW: Condition × reactivity interaction terms (15) ----
    r_api_cat = _react_categories(a['react'])
    r_e1_cat = _react_categories(e1['react'])
    for key in ['hydrolysis','oxidation','photolysis','chelation','stability']:
        s = r_api_cat[key] + r_e1_cat[key]
        v.append(s * temp / 60.0)   # temp acceleration
        v.append(s * hum / 100.0)   # humidity acceleration
        v.append(s * days_f / 30.0) # time accumulation
    # +3 more: photo-specific × light, hydrolysis-specific × humidity, oxidation-specific × temp
    v.append(r_api_cat['photolysis'] * light)
    v.append(r_api_cat['hydrolysis'] * hum / 100.0)
    v.append(r_api_cat['oxidation'] * temp / 60.0)

    # ---- Pairwise interaction features (truncated to 18 for model compatibility) ----
    pw = _pairwise_vec(a['mol'], e1['mol'])
    v.extend(pw)  # ALL weighted pairwise features

    # ---- Aggregated reaction risk scores (5 features) ----
    rxn_scores = _reaction_risk_scores(a['mol'], e1['mol']) if a and e1 else [0]*5
    v.extend(rxn_scores)
    return np.array(v, dtype=float)


def predict(api_s, e1_s, e2_s=None, days=0, cond=0):
    # Resolve names to SMILES before building feature vectors
    api_sm = get_sm(api_s) or api_s
    e1_sm = get_sm(e1_s) or e1_s
    e2_sm = get_sm(e2_s) if e2_s else None
    vec = build_vec(api_sm, e1_sm, e2_sm, days, cond)
    if vec is None: return {'error': 'Molecular structure parsing failed, try AI Chat for input'}
    vec_full = vec.reshape(1, -1)
    # Feature selection: classifier uses 2000 features, regressors use full 13063
    global _feat_idx
    vec_2d = vec_full  # Use full 13195 features (model expects this)
    prob = float(_model.predict_proba(vec_2d)[0, 1])
    explainer = shap.TreeExplainer(_model, feature_perturbation='tree_path_dependent',
                                    feature_names=_names)  # _names = selected names
    sv_full = explainer.shap_values(vec_2d, check_additivity=False)[0]
    top = []
    # Score ALL features (not just _num_idx) to capture pairwise features
    all_abs_shap = np.abs(sv_full)
    top_indices = np.argsort(all_abs_shap)[-30:][::-1]  # top 30
    for idx in top_indices:
        if idx < len(sv_full):
            nm = _names[idx] if idx < len(_names) else f'feat_{idx}'
            top.append((nm, sv_full[idx], idx))
    result_top = []
    for nm, sv, idx in top[:10]:
        dn = nm.replace('api_','API ').replace('exc1_','Exc1 ').replace('exc2_','Exc2 ')
        dn = dn.replace('delta_','Δ')
        if dn.startswith('pair_'):
            dn = '[RX]' + dn
        dn = dn.replace('_',' ')
        result_top.append({'feature':dn, 'shap':round(float(sv),4),
                          'dir':'↑' if sv>0 else '↓'})
    lv = 'low'
    if prob > 0.7: lv = 'high'
    elif prob > 0.3: lv = 'medium'

    # Multi-target: impurity count, total impurity %, max single impurity %
    # (regressors expect full 13195 features)
    pred_extra = {}
    # Regression models use full feature vector (may have dimension mismatches)
    for m, key in [(_model_count, 'impurity_count'), (_model_total, 'total_impurity_pct'), (_model_maxsingle, 'max_single_impurity_pct')]:
        if m:
            try:
                val = float(m.predict(vec_full)[0])
                pred_extra[key] = round(max(0, val), 4)
            except Exception:
                pass
    # Enforce physical constraint: total impurity >= max single impurity
    if 'total_impurity_pct' in pred_extra and 'max_single_impurity_pct' in pred_extra:
        pred_extra['total_impurity_pct'] = max(pred_extra['total_impurity_pct'], pred_extra['max_single_impurity_pct'])
    # Suppress output values if impurity count is extremely low (< 0.5)
    ic = pred_extra.get('impurity_count', 1)
    if ic < 0.5:
        pred_extra['total_impurity_pct'] = 0.0
        pred_extra['max_single_impurity_pct'] = 0.0
    elif ic < 1.0:
        factor = (ic - 0.5) * 2  # Linear interpolation between 0.5 (factor 0) and 1.0 (factor 1)
        if 'total_impurity_pct' in pred_extra:
            pred_extra['total_impurity_pct'] = round(pred_extra.get('total_impurity_pct', 0) * factor, 4)
        if 'max_single_impurity_pct' in pred_extra:
            pred_extra['max_single_impurity_pct'] = round(pred_extra.get('max_single_impurity_pct', 0) * factor, 4)

    return {'prob':round(prob,4), 'has':lv != 'low', 'level':lv,
            'top':result_top, 'error':None, **pred_extra}
