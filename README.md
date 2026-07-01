# 💊 Drug-Excipient Compatibility Prediction System (DECPS)

[English Version](#english-version) | [中文版](#中文版)

---

# English Version

## 💊 Drug-Excipient Compatibility Prediction System (DECPS)

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

1. **Dual-Excipient Co-compatibility Prediction**
   - API + Excipient 1
   - API + Excipient 2
   - Excipient 1 + Excipient 2 (Cross-interaction)
2. **Quantitative Impurity Regression**
   - Predicts total impurity percentage, max single impurity percentage, and impurity count.
   - Enforces physical constraints: $\text{Total Impurities} \geq \text{Max Single Impurity}$.
3. **Interpretability with SHAP**
   - Explains predictions using SHAP (SHapley Additive exPlanations) values to identify which molecular structures (e.g. ECFP fingerprints, MACCS keys, Delta properties) contributed to the risk.
4. **Pharmaceutical AI Assistant**
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

## 📂 Data Sources & Datasets

### 🎁 Shared Dataset File (`data.csv`)

> ⚠️ **IMPORTANT NOTE**: The `data.csv` shared in this repository is **NOT** the final high-dimensional feature file directly used for training (the model inputs are processed and converted into 13,060-dimensional representation via the pipeline). Instead, it is a **curated base dataset of drug-excipient relationships**. Although named `.csv`, **its actual file format is an Excel workbook** (we recommend reading it directly with Pandas/Excel, or renaming it to `.xlsx` first).
>
> In addition, this dataset is not only for drug-excipient compatibility prediction. Because it contains rich molecular physical-chemical properties and pairwise mapping, **it can be directly used in other drug discovery and molecular property prediction projects**.

#### 📊 Dataset Structure (Excel Sheets)

The `data.csv` (actually Excel) contains the following three sheets:

1. **`核心数据` (Core Data)**
   * **Purpose**: Records original compatibility labels and sources.
   * **Columns**: `API_Name`, `API_SMILES`, `Excipient_Name`, `Excipient_SMILES`, `Compatibility` (1 = compatible, 0 = incompatible/high risk), `Source`.
2. **`分子特征` (Molecular Features)**
   * **Purpose**: Pre-computed 2D molecular descriptors, useful for feature analysis and chemistry-related modeling.
   * **Columns**: MW, logP, HBD, HBA, TPSA, MR, pKa, atom count, ring count, etc. for both API and excipient, along with property delta terms (e.g. `ΔlogP`, `ΔTPSA`) and `Compatibility` labels.
3. **`统计信息` (Statistical Summary)**
   * **Purpose**: Dataset statistics.
   * **Metrics**: Total rows: `61,411`, Unique APIs: `3,382`.

### 📚 Raw Data Sources
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

---

# 中文版

## 💊 原辅料相容性预测系统 (DECPS)

> **“从实验台到 Vibe Coding 的跨界之旅。”**
> 本项目由一位**生物制药专业大三学生**，借助 AI 辅助的 **Vibe Coding**（氛围代码）技术构建而成。它架起了传统药物制剂开发与现代机器学习/RAG（检索增强生成）技术之间的桥梁。

---

## 🌟 Vibe Coding 的故事与起源
作为一名生物制药专业的本科生，在面对复杂的制剂筛选时，意味着需要翻阅无数的指导原则（例如《化学药物制剂研究基本技术指导原则 2005》），并进行繁琐的试错实验。

为了解决这一痛点，我使用 **Vibe Coding** 构建了 **DECPS** —— 利用 AI 快速进行原型设计，并将复杂的机器学习模型、RAG 知识库以及药物化学规则深度融合。

本仓库实现了一个基于机器学习的原辅料相容性预测框架，集成了高维分子特征映射以及基于规则与模型的混合风险评估系统。

---

## 🧬 系统架构
系统采用双引擎架构：**机器学习引擎**（用于高维相容性预测）和 **RAG + 化学规则引擎**（用于确定性安全边界和科学原理解释）。

```
用户 (Vue 3 界面) ◄──► Flask 后端 (Web App)
                       │
                       ├─► [ML 引擎]: 13,060 维分子指纹特征向量 ──► XGBoost 模型
                       ├─► [规则引擎]: RDKit SMARTS 子结构矩阵 ──► 145 条配对化学规则
                       └─► [RAG 助手]: 本地知识库 (PDF/DOCX) + Deepseek API ──► 上下文限定问答与实验方案设计
```

---

## 🛠️ 核心功能

1. **双辅料协同相容性预测（双辅料三组预测模式）**
   - 主药 (API) + 辅料 1
   - 主药 (API) + 辅料 2
   - 辅料 1 + 辅料 2（交叉反应预测）
2. **定量杂质回归预测**
   - 预测总杂质含量百分比、最大单杂含量百分比以及杂质个数。
   - 强制物理约束：$\text{总杂质} \geq \text{最大单杂}$。
3. **基于 SHAP 的可解释性**
   - 使用 SHAP 归因方法解释预测结果，帮助识别具体是哪些分子结构（如 ECFP 环状指纹、MACCS 结构键、Delta 差值属性）贡献了相容性风险。
4. **制剂 AI 助手**
   - 引导式多步骤实验设计（基于法规和本地知识库 RAG 的严谨回答）。
   - 关联前沿文献与临床试验数据支持。

---

## 📊 特征工程与模型表现

### 分子特征矩阵 (13,060 维度)
本系统不依赖简单的药物名称，而是通过 Pipeline 将主药（API）和辅料的结构式（SMILES）翻译成统一的 **13,060 维** 向量表示：

| 特征组 (Feature Group) | 维度 (Dimensions) | 描述 (Description) |
|--------------|-----------|-------------|
| Morgan ECFP (API & 辅料) | $3 \times 2048$ | 环状分子指纹（半径为 2） |
| MACCS 结构键 (API & 辅料) | $3 \times 166$ | 166 个用于官能团定义的结构键 |
| RDKit FP (API & 辅料) | $3 \times 2048$ | 基于路径的分子连通性指纹 |
| 基础与扩展物理化学描述符 | $3 \times (7 + 17)$ | 分子量 (MW)、油水分配系数 (logP)、氢键供体/受体数 (HBD/HBA)、极性表面积 (TPSA)、摩尔折射率 (MR) 等 |
| 自定义官能团及反应活性 | $3 \times (20 + 28)$ | 磺酸酯、磷酸酯等敏感基团，以及水解/氧化活性指标 |
| 环境与相互作用项 | $5 + 15$ | 温度、湿度、光照、放置天数及交互乘积项 |
| SMARTS 配对化学规则 | 17 | 核心反应性基团匹配（如美拉德反应、酯化反应等） |

### 模型表现
* **准确率 (Accuracy):** 90.0%
* **精确率 (Precision):** 88.0%
* **召回率 (Recall):** 77.1%
* **AUC 值:** 0.954
* **5 折交叉验证 (按 API 拆分):** 84.4%

---

## 📂 数据源与数据集

### 🎁 共享数据集文件说明 (`data.csv`)

> ⚠️ **重要提示**：本仓库中共享的 `data.csv` 并非最终训练模型所直接使用的完整高维特征文件（最终模型输入需要经过 Pipeline 转化为 13,060 维的特征向量），而是**自己整理的一份原辅料相关基础数据文件**。该文件虽然以 `.csv` 命名，但**其实际格式为 Excel 工作簿**（建议使用 Excel/Pandas 直接读取，或重命名为 `.xlsx` 后打开）。
>
> 此外，该数据集不仅可以用于原辅料相容性预测，由于其中包含了丰富的分子理化性质特征与配对关系，**在药物研发、分子性质预测等其他相关项目中也可以直接使用**。

#### 📊 数据集结构总结 (Excel 工作表)

`data.csv` (实际为 Excel) 包含以下三个工作表（Sheets）：

1. **`核心数据` (Core Data)**
   * **作用**：记录了原辅料配对的原始兼容性状态与来源。
   * **包含字段**：
     * `API_Name`: 活性药物成分（API）名称
     * `API_SMILES`: API 的 SMILES 结构式
     * `Excipient_Name`: 辅料名称
     * `Excipient_SMILES`: 辅料的 SMILES 结构式
     * `Compatibility`: 兼容性标签（`1` 为相容，`0` 为不相容）
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

### 📚 原始数据来源 (Data Sources)
本数据集由以下公开数据和研究编译、整理而成：
* 抓取 EMA / Swissmedic 公开注册文件中的处方记录
* FDA 批准的制剂处方数据库
* **DE_Interact (2023)** 公开基准数据集
* 从科学文献中提取的不兼容配对

共享文件包括：
* `data.csv`（重命名为 `.csv` 的 Excel 数据集，具体用法见上方说明）
* `public_compatibility_database.csv`（原始基准数据库）

---

## ⚡ 快速开始

### 1. 前提条件
- **Python 3.11+**
- **Node.js 18+** (用于前端开发)
- **RDKit** (通过 `pip` 或 `conda` 安装)

### 2. 安装步骤
```bash
# 克隆仓库
git clone <your-repo-url>
cd github

# 安装 Python 依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件并将 DEEPSEEK_API_KEY 替换为您自己的 Key
```

### 3. 运行后端服务 (生产模式)
```bash
# 在 8080 端口同时托管后端 API 和已编译的 Vue3 前端
python3 ml/webapp/app.py
```

### 4. 运行前端服务 (开发模式)
```bash
cd ml/frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173 (自动代理到 :8080 后端接口)
```

---

## 🎓 免责声明与开源协议
本项目仅开发用于生物制药领域的**学术研究、教育目的和课程设计**。关键的处方相容性请务必在物理实验室中进行实验验证。

本项目基于 **MIT License** 开源。
