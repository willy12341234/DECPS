# 💊 Drug-Excipient Compatibility Prediction System (DECPS)

> **"From lab tables to vibe coding."** 
> This is a project built by a **Junior (Year 3) Biopharmaceutics (生物制药) student** using the power of AI-assisted **Vibe Coding**. It bridges the gap between classic pharmaceutical formulation development and modern machine learning/RAG technology.

---

## 🌟 The Vibe Coding Story & Origin
As a junior biopharmaceutics student, navigating the complex world of formulation screening meant looking at endless guidance documents (like the *Technical Guidelines for Research of Chemical Drug Formulations 2005*) and doing tedious trial-and-error experiments. 

To solve this, I built **DECPS** using **Vibe Coding**—leveraging AI to rapidly prototype and integrate complex machine learning models, RAG (Retrieval-Augmented Generation) knowledge bases, and pharmaceutical chemistry rules.

This repository implements the concepts of an ML-driven compatibility prediction framework, integrating high-dimensional molecular feature mapping with hybrid rule-and-model-based risk evaluation.

---

## 🧬 System Architecture
The system employs a dual-engine architecture: a **Machine Learning Engine** (for high-dimensional prediction) and a **RAG + Chemical Rule Engine** (for deterministic safety limits and scientific explanation).

```
User (Vue 3 UI) ◄──► Flask Backend (Web App)
                       │
                       ├─► [ML Engine]: 13,060-dim Molecular Fingerprint Vector ──► XGBoost Models
                       ├─► [Rule Engine]: RDKit SMARTS Substructure Matrix ──────► 145 Pairwise Rules
                       └─► [RAG Assistant]: Local KB (PDFs/DOCX) + DeepSeek API ──► Context-Bound Chat & Protocol Design
```

---

## 🛠️ Key Features

1. **Dual-Excipient Co-compatibility Prediction (双辅料三组预测模式)**
   - API + Excipient 1
   - API + Excipient 2
   - Excipient 1 + Excipient 2 (Cross-interaction)
2. **Quantitative Impurity Regression (定量杂质预测)**
   - Predicts total impurity percentage, max single impurity percentage, and impurity count.
   - Enforces physical constraints: $\text{Total Impurities} \geq \text{Max Single Impurity}$.
3. **Interpretability with SHAP (模型可解释性)**
   - Explains predictions using SHAP (SHapley Additive exPlanations) values to identify which molecular structures (e.g. ECFP fingerprints, MACCS keys, Delta properties) contributed to the risk.
4. **Pharmaceutical AI Assistant (AI 制剂助手)**
   - Guided multi-step experiment design (RAG-backed, adhering to regulatory guidelines).
   - Literature & clinical trial evidence binding.

---

## 📊 Feature Engineering & Model Performance

### Molecular Feature Matrix (13,060 Dimensions)
Instead of relying on simple drug names, the pipeline translates API and excipient structures (SMILES) into a unified **13,060-dimensional** representation:

| Feature Group | Dimensions | Description |
|--------------|-----------|-------------|
| Morgan ECFP (API & Exc) | $2 \times 2048$ | Circular fingerprints (radius 2) |
| MACCS Keys (API & Exc) | $2 \times 166$ | 166 structural keys for functional groups |
| RDKit FP (API & Exc) | $2 \times 2048$ | Path-based molecular connectivity |
| Basic & Extended Descriptors | $2 \times (7 + 17)$ | MW, logP, HBD, HBA, TPSA, MR, fcsp3, etc. |
| Custom Group & Reactivity | $2 \times (20 + 28)$ | Sulfonate, phosphate, hydrolysis/oxidation reactivity |
| Environment & Interaction Terms | $5 + 15$ | Temperature, Humidity, Light, Storage Days & cross-products |
| SMARTS Pairwise Rules | 17 | Core reactive group matches (e.g. Maillard reaction, esterification) |

### Performance
* **Accuracy:** 90.0%
* **Precision:** 88.0%
* **Recall:** 77.1%
* **AUC:** 0.954
* **5-Fold Cross-Validation (API-Level Split):** 84.4%

---

## 📂 Data Sources & Datasets

### 🎁 Free Shared Dataset (`data.csv`)
To support open science, I have **scraped, cleaned, and compiled a large-scale drug-excipient compatibility dataset** containing **66,654** pairs (covering 3,582 APIs and 387 excipients), shared here completely for free. 

The dataset is compiled and curated from various public records and studies:
* Scraped EMA / Swissmedic public registry formulation logs
* FDA Approved Formulations databases
* **DE_Interact (2023)** public benchmarks
* Literature-extracted incompatible pairings

The dataset is shared as:
* `data.csv` (curated CSV dataset)
* `public_compatibility_database.csv` (raw baseline database)

---

## ⚡ Quick Start

### 1. Prerequisites
- **Python 3.11+**
- **Node.js 18+** (for frontend development)
- **RDKit** (installed via `pip` or `conda`)

### 2. Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd github

# Install python dependencies
pip install -r requirements.txt

# Configure your environment
cp .env.example .env
# Edit .env and replace DEEPSEEK_API_KEY with your key
```

### 3. Running the Server (Production Mode)
```bash
# Serves both backend API and pre-compiled Vue3 frontend on port 8080
python3 ml/webapp/app.py
```

### 4. Running the Frontend (Development Mode)
```bash
cd ml/frontend
npm install
npm run dev
# Frontend runs on http://localhost:5173 (proxies to backend :8080)
```

---

## 🎓 Disclaimer & License
This project was developed for **academic research, educational purposes, and course projects** in Biopharmaceutics. Always verify critical formulation compatibilities in a physical laboratory.

Licensed under the **MIT License**.
