"""
Shared SMARTS reaction rules for drug-excipient pairwise compatibility matching.
Used by predictor.py (ML feature engineering) and experiment_design.py (LLM context).
Centralized to avoid dual-maintenance.
"""
import os, json

_BASE = os.path.dirname(os.path.abspath(__file__))
_PRJ = os.path.join(_BASE, '..')

PAIRWISE_RULES = []

# Load from caches/pairwise_rules.json
p = os.path.join(_PRJ, "caches", "pairwise_rules.json")
if os.path.exists(p):
    try:
        with open(p, encoding='utf-8') as f:
            PAIRWISE_RULES = [tuple(r) for r in json.load(f)]
    except Exception:
        pass
