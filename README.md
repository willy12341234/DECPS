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
| Morgan ECFP (API & Exc) | $3 \times 2048$ | Circular fingerprints (radius 2) |
| MACCS Keys (API & Exc) | $3 \times 166$ | 166 structural keys for functional groups |
| RDKit FP (API & Exc) | $3 \times 2048$ | Path-based molecular connectivity |
| Basic & Extended Descriptors | $3 \times (7 + 17)$ | MW, logP, HBD, HBA, TPSA, MR, fcsp3, etc. |
| Custom Group & Reactivity | $3 \times (20 + 28)$ | Sulfonate, phosphate, hydrolysis/oxidation reactivity |
| Environment & Interaction Terms | $5 + 15$ | Temperature, Humidity, Light, Storage Days & cross-products |
| SMARTS Pairwise Rules | 17 | Core reactive group matches (e.g. Maillard reaction, esterification) |

### Performance
* **Accuracy:** 90.0%
* **Precision:** 88.0%
* **Recall:** 77.1%
* **AUC:** 0.954
* **5-Fold Cross-Validation (API-Level Split):** 84.4%

---

## 📂 Data Sources & Datasets / 数据集与数据源

### 🎁 共享数据集文件说明 (`data.csv`)

> ⚠️ **重要提示**：本仓库中共享的 `data.csv` 并非最终训练模型所直接使用的完整高维特征文件（最终模型输入需要经过 Pipeline 转化为 13,060 维的特征向量），而是**自己整理的一份原辅料相关基础数据文件**。该文件虽然以 `.csv` 命名，但**其实际格式为 Excel 工作簿**（建议使用 Excel/Pandas 直接读取，或重命名为 `.xlsx` 后打开）。
>
> 此外，该数据集不仅可以用于原辅料相容性预测，由于其中包含了丰富的分子理化性质特征与配对关系，**在药物研发、分子性质预测等其他相关项目中也可以直接使用**。

#### 📊 数据集结构总结 (Excel Sheets)

`data.csv` (实际为 Excel) 包含以下三个工作表（Sheets）：

1. **`核心数据` (Core Data)**
   * **作用**：记录了原辅料配对的原始兼容性状态与来源。
   * **包含字段**：
     * `API_Name`: 活性药物成分（API）名称
     * `API_SMILES`: API 的 SMILES 结构式
     * `Excipient_Name`: 辅料名称
     * `Excipient_SMILES`: 辅料的 SMILES 结构式
     * `Compatibility`: 兼容性标签（`1` 为不兼容/有风险，`0` 为兼容）
     * `Source`: 数据来源（如：文献扩充数据集等）

2. **`分子特征` (Molecular Features)**
   * **作用**：预计算的分子二维及物理化学描述符特征，可用于机器学习特征分析及其他化学性质预测项目。
   * **包含字段**：
     * API 与辅料的分子量 (`MW`)、油水分配系数 (`logP`)、氢键供体/受体数 (`HBD`/`HBA`)、拓扑极性表面积 (`TPSA`)、摩尔折射率 (`MR`)、酸碱解离常数 (`pKa_acid`/`pKa_base`)、原子数、重原子数、旋转键数、环数等。
     * API 与辅料之间的理化性质差异值，如 `ΔlogP`、`ΔTPSA` 等。
     * 目标分类标签 `Compatibility`。

3. **`统计信息` (Statistical Summary)**
   * **作用**：数据集的基础统计数据。
   * **核心指标**：总数据量 `61,411` 行，包含 `3,382` 个唯一的 API。

---

### 📚 数据来源 (Data Sources)
The dataset is compiled and curated from various public records and studies:
* Scraped EMA / Swissmedic public registry formulation logs
* FDA Approved Formulations databases
* **DE_Interact (2023)** public benchmarks
* Literature-extracted incompatible pairings

The dataset is shared as:
* `data.csv` (Curated Excel dataset renamed to .csv, see instructions above)
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
