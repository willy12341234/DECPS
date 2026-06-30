import { ref } from 'vue'

export const LOCALE = {
  zh: {
    title: '药物-辅料相容性预测系统',
    subtitle: 'Fingerprint XGBoost',
    input_title: '输入原辅料',
    api_label: 'API 名称或 SMILES',
    exc1_label: '辅料 1 名称或 SMILES',
    exc2_label: '辅料 2 名称或 SMILES',
    days_label: '储存天数',
    cond_label: '条件',
    predict_btn: '预测相容性',
    results_title: '预测结果 (FP-XGB)',
    risk_lbl: '杂质风险',
    prob_lbl: '杂质概率',
    pred_lbl: '预测结论',
    std_lbl: '模型标准差 (σ)',
    smarts_lbl: '化学反应规则匹配',
    count_lbl: '预测杂质个数',
    total_lbl: '预测总杂质 %',
    max_lbl: '预测最大单杂质 %',
    votes_lbl: '模型投票',
    groups_title: '化学基团分析',
    groups_api: 'API 化学基团',
    groups_exc: '辅料化学基团',
    groups_exc2: '辅料2 化学基团',
    groups_hydrolysis: '💧 水解敏感基团',
    groups_oxidation: '🔥 氧化敏感基团',
    groups_photolysis: '☀️ 光解敏感基团',
    groups_chelation: '🧪 螯合相关基团',
    groups_hydrolysis_risk: '在水分和加热条件下易水解，产生降解杂质',
    groups_oxidation_risk: '易被氧化，尤其在有金属离子或过氧化物存在时',
    groups_photolysis_risk: '对紫外/可见光敏感，暴露在光照下易降解',
    groups_chelation_risk: '可与金属离子螯合，影响颜色和稳定性',
    groups_other: '其他官能团',
    groups_risks: '交叉反应风险（API × 辅料1）',
    groups_risks2: '交叉反应风险（API × 辅料2）',
    groups_safe: 'API × 辅料1 未检测到已知化学反应规则匹配',
    groups_safe2: 'API × 辅料2 未检测到已知化学反应规则匹配',
    groups_none: '未检测到已知反应活性基团',
    groups_sub: '基于SMARTS子结构匹配',
    groups_help: '该模块基于SMARTS子结构匹配，识别API和辅料中存在的化学基团及其潜在降解风险途径。可帮助理解杂质产生的化学本质。',
    groups_help_body: '',
    shap_title: 'SHAP 解释 — 关键驱动特征',
    shap_desc: '<span style="color:#c62828">↑ 正值 = 增加杂质风险</span> &nbsp; <span style="color:#2e7d32">↓ 负值 = 降低杂质风险</span>',
    shap_help_title: 'SHAP 特征说明',
    shap_help_body: '<p><strong>↑ / ↓</strong> — 对杂质风险的影响方向（↑ 增加风险，↓ 降低风险）。</p><p><strong>柱状条长度</strong> — 相对重要性，越长表示该特征对模型预测影响越大。</p><p><strong>所有可能出现的指标说明：</strong></p><table style="width:100%;border-collapse:collapse;font-size:12px;margin:6px 0"><thead><tr style="background:rgba(0,0,0,0.04)"><th style="padding:5px 8px;text-align:left;font-weight:600;border-bottom:1px solid rgba(0,0,0,0.08)">特征名前缀</th><th style="padding:5px 8px;text-align:left;font-weight:600;border-bottom:1px solid rgba(0,0,0,0.08)">含义</th></tr></thead><tbody>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>api_d / hbd / hba / tpsa / logp / mr / mw</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API 的分子描述符：密度、氢键供体/受体数、极性表面积、脂溶性、摩尔折射率、分子量</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>api_ecfp_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API 的 ECFP 分子指纹（2048 位子结构特征）</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>api_maccs_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API 的 MACCS 结构钥匙（166 位化学基团特征）</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>api_react_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API 反应活性预测（水解/氧化/光解/螯合等 42 项）</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>api_extra_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API 扩展描述符（17 项额外理化参数）</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>api_cg_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API 的化学基团特征（20 项自定义官能团指纹）</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>exc1_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">辅料 1 的全部特征，与 api_* 包含完全相同的类型（描述符、指纹、MACCS、反应性、扩展描述符、化学基团）</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>exc2_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">辅料 2 的全部特征，与 api_* / exc1_* 包含完全相同的类型</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>Δ_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API 与辅料 1 对应特征的差值</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>temp / humidity / light / days</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">实验条件：温度、湿度、光照、储存天数</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>interact_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">条件×反应活性交互项：温湿度时间分别与水解/氧化/光解/螯合/稳定性的乘积（共15项）</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>pair_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API-辅料对交互特征：18项 RAG 知识库化学反应规则，API和辅料各含特定官能团时值为1</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>rdk_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">RDKit 分子指纹位（2048位），与 ECFP 类似但不同哈希算法</td></tr>'
    + '</tbody></table><p style="margin-top:6px">SHAP 值绝对值越大，该特征对预测结果的影响越显著。<br>悬停 <b>?</b> 图标查看详细说明。</p>',
    sidebar_title: 'AI 制剂助手',
    parsed_title: '解析结果',
    clear_btn: '清空对话',
    chat_hint: 'Shift+Enter 换行',
    send_btn: '发送',
    save_btn: '保存设置',
    chat_placeholder: '例：原料是布洛芬，辅料1是乳糖，辅料2是甘露醇，在高温60摄氏度和常湿的情况下',
    cond_opts: ['正常 (25°C, 常湿)', '高温 50°C', '高温 60°C', '高湿 75%RH', '高湿 92.5%RH', '光照', '自定义'],
    welcome_msg:
      '## 👋 欢迎使用 AI 制剂助手\n\n'
      + '我可以帮你完成以下药物研发相关任务：\n\n'
      + '### 🔬 原辅料相容性预测（默认）\n'
      + '输入 API + 辅料名称，自动预测杂质风险、生成 SHAP 解释和化学机制分析。\n\n'
      + '### 🧪 实验方案设计\n'
      + '自动设计原辅料相容性实验方案，包含配比、条件、时间点、检测方法。\n\n'
      + '### 💊 剂型调研\n'
      + '查询药品已批/在研剂型。例：`查一下克拉考特酮有没有除乳膏外的剂型`\n\n'
      + '### 📄 专利深度分析\n'
      + '提取专利中的适应症、药理、处方、临床效果、用法用量。\n\n'
      + '### 🔍 竞品调研\n'
      + '对比多个品种的开发状态。例：`对比芦可替尼、巴瑞替尼、乌帕替尼的外用制剂`\n\n'
      + '### 📦 包材研究\n'
      + '检索包材变更历史和优劣势对比。\n\n'
      + '### 📋 立项报告\n'
      + '自动生成结构化立项调研报告。\n\n'
      + '---\n'
      + '💡 **直接输入问题**，AI 会自动判断任务类型并执行；\n'
      + '也可以在上方 **切换 Skill** 手动指定任务类型。',
    placeholder_auto: '',
    placeholder_compatibility: '例：API：布洛芬，辅料：乳糖，条件：60°C',
    placeholder_experiment: '例：帮我设计布洛芬和乳糖的原辅料相容性实验',
    placeholder_formulation: '例：查一下克拉考特酮有没有除乳膏外的剂型',
    placeholder_patent: '例：分析克拉考特酮的专利，找出适应症和处方信息',
    placeholder_competitive: '例：对比芦可替尼、巴瑞替尼、乌帕替尼的外用制剂',
    placeholder_packaging: '例：克林霉素阿达帕林过氧苯甲酰的铝管包装为何取消',
    placeholder_project: '例：生成克拉考特酮外用溶液的立项报告',
    skill_intro_compatibility: '🔄 已切换至 **相容性预测**\n\n输入 API 和辅料名称，我会自动预测杂质风险。\n\n示例：`API：布洛芬，辅料：乳糖，条件：60°C`',
    skill_intro_experiment: '🔄 已切换至 **实验设计**\n\n描述你想做的实验，我会自动生成完整方案。\n\n示例：`帮我设计布洛芬和乳糖的原辅料相容性实验方案`',
    skill_intro_formulation: '🔄 已切换至 **剂型调研**\n\n输入药品名，我会检索已批和临床在研的剂型信息。\n\n示例：`查一下克拉考特酮有没有除乳膏外的剂型`',
    skill_intro_patent: '🔄 已切换至 **专利分析**\n\n输入药品名，我会从专利中提取适应症、药理、处方、临床效果、用法用量。\n\n示例：`分析克拉考特酮的专利`',
    skill_intro_competitive: '🔄 已切换至 **竞品调研**\n\n输入多个品种名称，我会对比它们的开发状态和立项机会。\n\n示例：`对比芦可替尼、巴瑞替尼、乌帕替尼的外用制剂`',
    skill_intro_packaging: '🔄 已切换至 **包材研究**\n\n输入药品名，我检索包材变更历史和优劣势对比。\n\n示例：`克林霉素阿达帕林过氧苯甲酰的铝管包装为何取消`',
    skill_intro_project: '🔄 已切换至 **立项报告**\n\n输入目标品种，我会自动生成结构化立项调研报告。\n\n示例：`生成克拉考特酮外用溶液的立项报告`',
    login_title: '原辅料相容性预测系统',
    login_sub: 'Drug-Excipient Compatibility Predictor',
    login_btn: '登录',
    login_user: '用户名',
    login_pass: '密码',
    login_error: '用户名或密码错误',
    compatible: '相容',
    incompatible: '不相容',
    low_risk: '低风险',
    medium_risk: '中风险',
    high_risk: '高风险',
    overall: '综合判定',
    model_mode_single: '🔷 FP-XGB 单模型预测',
    model_mode_dual: '🔷 双辅料模式 — 三组独立预测',
    search_title: '联网搜索',
    patent_results: '专利检索结果',
    literature_results: '文献检索结果',
    clinical_results: '临床试验',
    patent_id: '专利号',
    country_label: '国家',
    inventor: '发明人',
    source_article: '来源',
    pmid_label: '文献ID',
    nct_label: '试验编号',
    phase_label: '阶段',
    status_label: '状态',
    year_label: '年份',
    date_label: '日期',
    skill_auto: '自动判断',
    skill_compatibility: '相容性预测',
    skill_experiment: '实验设计',
    skill_formulation: '剂型调研',
    skill_patent: '专利分析',
    skill_competitive: '竞品调研',
    skill_packaging: '包材研究',
    skill_project: '立项报告',
    patent_step: '专利检索',
    literature_step: '文献检索',
    clinical_step: '临床检索',
    ml_step: 'ML预测',
    plan_step: '方案生成',
    count_suffix: '条',
    history_title: '对话历史',
    history_none: '暂无记录',
    export_all: '导出全部',
    source_patent: '📄',
    source_pubmed: '📚',
    source_clinical: '🏥',
    source_web: '🔗',
    wv_addr_placeholder: '输入或点击链接开始浏览...',
    wv_empty_title: '点击链接开始浏览',
    wv_empty_desc: '在右侧 AI 回复中点击任意链接，即可在左侧查看网页详情。\n也可在上方地址栏手动输入 URL。',
    wv_loading: '正在加载页面...',
    wv_blocked: '该网站不允许嵌入，已自动提取页面内容',
    wv_word_count: '共 {n} 字',
    wv_expand_all: '展开全文',
    wv_collapse: '收起',
    wv_open_new: '在新标签页打开',
    export_title: '实验设计方案',
    export_unknown_api: '未知API',
    export_unknown_exc: '未知辅料',
    export_error: '导出失败',
    api_saved: '✅ API 设置已保存。',
    new_chat_btn: '新建对话',
    history_btn: '历史',
    logout_btn: '退出',
    sources_title: '📎 参考来源',
    download_btn: '📄 下载为Word文档',
    feedback_btn: '反馈建议',
    feedback_title: '💬 反馈与建议',
    feedback_placeholder: '请描述你的问题、建议或想法...',
    feedback_submit: '提交反馈',
    predicting: '预测中...',
    waiting_pred: '等待预测...',
    detail_analysis: '🔍 各组详细分析',
    empty_reply: '(空回复)',
    overall_verdict: '📊 综合判定',
    impurity_count: '🧪 杂质个数',
    total_pct: '📈 总杂质%',
    max_single: '🔬 最大单杂%',
    risk_low: '<strong>低风险判断</strong>：杂质概率 {p}%（阈值 < 30%），结论为〈相容〉。API与辅料在该条件下化学稳定性良好，杂质生成风险低。',
    risk_medium_low: '<strong>中低风险判断</strong>：杂质概率 {p}%（阈值 30-50%），结论为〈相容〉但需关注。建议进行长期稳定性考察，尤其关注高温高湿条件。',
    risk_medium_high: '<strong>中高风险判断</strong>：杂质概率 {p}%（阈值 50-70%），结论为〈不相容〉。建议考虑更换辅料或添加稳定剂。',
    risk_high: '<strong>高风险判断</strong>：杂质概率 {p}%（阈值 > 70%），结论为〈不相容〉。强烈建议更换该辅料。',
  },
  en: {
    title: 'Drug–Excipient Compatibility Prediction',
    subtitle: 'Fingerprint XGBoost',
    input_title: 'Input Formulation',
    api_label: 'API Name or SMILES',
    exc1_label: 'Excipient 1 Name or SMILES',
    exc2_label: 'Excipient 2 Name or SMILES',
    days_label: 'Storage Days',
    cond_label: 'Condition',
    predict_btn: 'Predict Compatibility',
    results_title: 'Prediction Results (FP-XGB)',
    risk_lbl: 'Impurity Risk',
    prob_lbl: 'Prob(Impurity)',
    pred_lbl: 'Prediction',
    std_lbl: 'Model Std (σ)',
    smarts_lbl: 'SMARTS Rule Matches',
    count_lbl: 'Predicted Impurity Count',
    total_lbl: 'Predicted Total Impurity %',
    max_lbl: 'Predicted Max Single Impurity %',
    votes_lbl: 'Model Votes',
    groups_title: 'Chemical Group Analysis',
    groups_api: 'API Chemical Groups',
    groups_exc: 'Excipient Chemical Groups',
    groups_exc2: 'Excipient 2 Chemical Groups',
    groups_hydrolysis: '💧 Hydrolysis-Prone Groups',
    groups_oxidation: '🔥 Oxidation-Prone Groups',
    groups_photolysis: '☀️ Photolysis-Prone Groups',
    groups_chelation: '🧪 Chelation-Related Groups',
    groups_hydrolysis_risk: 'Prone to hydrolytic cleavage under heat and moisture',
    groups_oxidation_risk: 'Prone to oxidation, especially with metal ions or peroxides',
    groups_photolysis_risk: 'Light-sensitive, degrades under UV/visible exposure',
    groups_chelation_risk: 'Can chelate metal ions, affecting color and stability',
    groups_other: 'Other Functional Groups',
    groups_risks: 'Cross-Reaction Risks (API × Excipient 1)',
    groups_risks2: 'Cross-Reaction Risks (API × Excipient 2)',
    groups_safe: 'No known reaction rules matched for API × Excipient 1',
    groups_safe2: 'No known reaction rules matched for API × Excipient 2',
    groups_none: 'No reactive groups detected',
    groups_sub: 'SMARTS substructure matching',
    groups_help: 'This module uses SMARTS substructure matching to detect chemical groups in API and excipient, and their potential degradation pathways.',
    groups_help_body: '',
    shap_title: 'SHAP Explanation — Top Driving Features',
    shap_desc: '<span style="color:#c62828">↑ Positive = increases impurity risk</span> &nbsp; <span style="color:#2e7d32">↓ Negative = decreases impurity risk</span>',
    shap_help_title: 'SHAP Feature Guide',
    shap_help_body: '<p><strong>↑ / ↓</strong> — Direction of impact on impurity risk (↑ increases risk, ↓ decreases risk).</p><p><strong>Bar length</strong> — Relative importance; longer bars indicate greater influence on the prediction.</p><p><strong>All possible features explained:</strong></p><table style="width:100%;border-collapse:collapse;font-size:12px;margin:6px 0"><thead><tr style="background:rgba(0,0,0,0.04)"><th style="padding:5px 8px;text-align:left;font-weight:600;border-bottom:1px solid rgba(0,0,0,0.08)">Feature Prefix</th><th style="padding:5px 8px;text-align:left;font-weight:600;border-bottom:1px solid rgba(0,0,0,0.08)">Description</th></tr></thead><tbody>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>api_d / hbd / hba / tpsa / logp / mr / mw</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API molecular descriptors: density, H-bond donor/acceptor count, polar surface area, lipophilicity, molar refractivity, molecular weight</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>api_ecfp_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API ECFP molecular fingerprint (2048-bit substructure features)</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>api_maccs_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API MACCS structural keys (166-bit chemical group features)</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>api_react_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API reactivity predictions (hydrolysis/oxidation/photolysis/chelation, 42 items)</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>api_extra_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API extended descriptors (17 additional physicochemical parameters)</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>api_cg_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API custom chemical group features (20 custom functional group fingerprints)</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>exc1_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">All feature types for Excipient 1, identical to api_* (descriptors, fingerprints, MACCS, reactivity, extra descriptors, custom groups)</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>exc2_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">All feature types for Excipient 2, identical to api_* / exc1_*</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>Δ_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">Difference between API and Excipient 1 for the corresponding feature</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>temp / humidity / light / days</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">Experimental conditions: temperature, humidity, light exposure, storage days</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>interact_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">Condition × reactivity interaction: temperature/humidity/time multiplied by hydrolysis/oxidation/photolysis/chelation/stability scores (15 items)</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>pair_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">API–excipient pairwise interaction features: 18 RAG knowledge-base rules, value=1 when both API and excipient carry specific reactive groups</td></tr>'
    + '<tr><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)"><code>rdk_*</code></td><td style="padding:4px 8px;border-bottom:1px solid rgba(0,0,0,0.04)">RDKit fingerprint bits (2048-bit), similar to ECFP but with different hashing</td></tr>'
    + '</tbody></table><p style="margin-top:6px">The larger the absolute SHAP value, the more that feature influences the prediction.<br>Hover <b>?</b> for detailed per-feature description.</p>',
    sidebar_title: 'AI Assistant',
    parsed_title: 'Parsed Input',
    clear_btn: 'Clear Chat',
    chat_hint: 'Shift+Enter for new line',
    send_btn: 'Send',
    save_btn: 'Save Settings',
    chat_placeholder: 'e.g. API: Ibuprofen, Excipient 1: Lactose, Excipient 2: Mannitol, 60°C, ambient humidity',
    cond_opts: ['Normal (25°C, Ambient)', 'High Temperature 50°C', 'High Temperature 60°C', 'High Humidity 75%RH', 'High Humidity 92.5%RH', 'Light Exposure', 'Custom'],
    welcome_msg:
      '## 👋 Welcome to AI Formulation Assistant\n\n'
      + 'I can help with the following pharmaceutical R&D tasks:\n\n'
      + '### 🔬 Drug-Excipient Compatibility (Default)\n'
      + 'Input API + excipient names to predict impurity risk, SHAP explanations, and chemical mechanism analysis.\n\n'
      + '### 🧪 Experiment Design\n'
      + 'Design API-excipient compatibility experiment protocols including ratios, conditions, time points, and test methods.\n\n'
      + '### 💊 Formulation Research\n'
      + 'Search approved and investigational dosage forms. Example: `Check clascoterone dosage forms beyond cream`\n\n'
      + '### 📄 Patent Analysis\n'
      + 'Extract indications, pharmacology, formulation, clinical efficacy, and dosage from patents.\n\n'
      + '### 🔍 Competitive Intelligence\n'
      + 'Compare development status of multiple drugs. Example: `Compare ruxolitinib, baricitinib, upadacitinib topical`\n\n'
      + '### 📦 Packaging Research\n'
      + 'Research packaging change history and compare packaging material pros/cons.\n\n'
      + '### 📋 Project Initiation Report\n'
      + 'Generate structured project initiation reports.\n\n'
      + '---\n'
      + '💡 **Just type your question** — AI will auto-detect task type;\n'
      + 'or **switch Skill** above to specify manually.',
    placeholder_auto: '',
    placeholder_compatibility: 'e.g. API: Ibuprofen, Excipient: Lactose, Condition: 60°C',
    placeholder_experiment: 'e.g. Design a compatibility experiment for Ibuprofen and Lactose',
    placeholder_formulation: 'e.g. Check clascoterone dosage forms beyond cream',
    placeholder_patent: 'e.g. Analyze clascoterone patents for formulation details',
    placeholder_competitive: 'e.g. Compare ruxolitinib, baricitinib, upadacitinib topical',
    placeholder_packaging: 'e.g. Why was aluminum tube packaging discontinued for clindamycin gel',
    placeholder_project: 'e.g. Generate project report for clascoterone topical solution',
    skill_intro_compatibility: '🔄 Switched to **Compatibility Prediction**\n\nInput API and excipient names for impurity risk prediction.\n\nExample: `API: Ibuprofen, Excipient: Lactose, Condition: 60°C`',
    skill_intro_experiment: '🔄 Switched to **Experiment Design**\n\nDescribe your experiment for an automatic protocol.\n\nExample: `Design a compatibility experiment for Ibuprofen and Lactose`',
    skill_intro_formulation: '🔄 Switched to **Formulation Research**\n\nSearch approved and investigational dosage forms.\n\nExample: `Check clascoterone dosage forms beyond cream`',
    skill_intro_patent: '🔄 Switched to **Patent Analysis**\n\nExtract indications, pharmacology, formulation, and dosage from patents.\n\nExample: `Analyze clascoterone patents`',
    skill_intro_competitive: '🔄 Switched to **Competitive Intelligence**\n\nCompare development status of multiple drugs.\n\nExample: `Compare ruxolitinib, baricitinib, upadacitinib topical`',
    skill_intro_packaging: '🔄 Switched to **Packaging Research**\n\nResearch packaging changes and compare materials.\n\nExample: `Why was aluminum tube packaging discontinued`',
    skill_intro_project: '🔄 Switched to **Project Report**\n\nGenerate structured project initiation reports.\n\nExample: `Generate project report for clascoterone topical solution`',
    login_title: 'Drug-Excipient Compatibility',
    login_sub: 'Drug-Excipient Compatibility Predictor',
    login_btn: 'Log In',
    login_user: 'Username',
    login_pass: 'Password',
    login_error: 'Invalid credentials',
    compatible: 'Compatible',
    incompatible: 'Incompatible',
    low_risk: 'Low Risk',
    medium_risk: 'Medium Risk',
    high_risk: 'High Risk',
    overall: 'Overall',
    model_mode_single: '🔷 FP-XGB Single Model',
    model_mode_dual: '🔷 2-Excipient Mode — 3 paired predictions',
    search_title: 'Web Search',
    patent_results: 'Patent Results',
    literature_results: 'Literature Results',
    clinical_results: 'Clinical Trials',
    patent_id: 'Patent ID',
    country_label: 'Country',
    inventor: 'Inventor',
    source_article: 'Source',
    pmid_label: 'PMID',
    nct_label: 'NCT ID',
    phase_label: 'Phase',
    status_label: 'Status',
    year_label: 'Year',
    date_label: 'Date',
    skill_auto: 'Auto',
    skill_compatibility: 'Compatibility',
    skill_experiment: 'Experiment',
    skill_formulation: 'Formulation',
    skill_patent: 'Patent',
    skill_competitive: 'Competitive',
    skill_packaging: 'Packaging',
    skill_project: 'Project',
    patent_step: 'Patent',
    literature_step: 'Literature',
    clinical_step: 'Clinical',
    ml_step: 'ML',
    plan_step: 'Generate',
    count_suffix: 'results',
    history_title: 'Chat History',
    history_none: 'No history',
    export_all: 'Export All',
    source_patent: '📄',
    source_pubmed: '📚',
    source_clinical: '🏥',
    source_web: '🔗',
    wv_addr_placeholder: 'Enter URL or click a link...',
    wv_empty_title: 'Click a link to start browsing',
    wv_empty_desc: 'Click any link in the AI chat on the right to view the page here.\nYou can also type a URL in the address bar above.',
    wv_loading: 'Loading page...',
    wv_blocked: 'This site does not allow embedding. Page content has been extracted.',
    wv_word_count: '{n} words',
    wv_expand_all: 'Expand All',
    wv_collapse: 'Collapse',
    wv_open_new: 'Open in new tab',
    export_title: 'Experiment Design Plan',
    export_unknown_api: 'Unknown API',
    export_unknown_exc: 'Unknown Excipient',
    export_error: 'Export failed',
    api_saved: '✅ API settings saved.',
    new_chat_btn: 'New Chat',
    history_btn: 'History',
    logout_btn: 'Logout',
    sources_title: '📎 References',
    download_btn: '📄 Download as Word',
    feedback_btn: 'Feedback',
    feedback_title: '💬 Feedback & Suggestions',
    feedback_placeholder: 'Describe your issue, suggestion or idea...',
    feedback_submit: 'Submit',
    predicting: 'Running prediction...',
    waiting_pred: 'Waiting for prediction...',
    detail_analysis: '🔍 Detailed Analysis',
    empty_reply: '(empty response)',
    overall_verdict: '📊 Overall',
    impurity_count: '🧪 Count',
    total_pct: '📈 Total%',
    max_single: '🔬 Max Single%',
    risk_low: '<strong>Low Risk</strong>: Impurity probability {p}% (threshold < 30%), conclusion: Compatible. API and excipient are chemically stable under these conditions.',
    risk_medium_low: '<strong>Low-Medium Risk</strong>: Impurity probability {p}% (threshold 30-50%), conclusion: Compatible but monitor. Recommend long-term stability study, especially under high temperature and humidity.',
    risk_medium_high: '<strong>Medium-High Risk</strong>: Impurity probability {p}% (threshold 50-70%), conclusion: Incompatible. Consider replacing excipient or adding stabilizer.',
    risk_high: '<strong>High Risk</strong>: Impurity probability {p}% (threshold > 70%), conclusion: Incompatible. Strongly recommend replacing this excipient.',
  }
}

const lang = ref(localStorage.getItem('lang') || 'zh')
export const currentLang = lang

export function t(key, vars) {
  const l = LOCALE[lang.value] || LOCALE.zh
  let val = l[key] !== undefined ? l[key] : (LOCALE.zh[key] || key)
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      val = val.replace(new RegExp(`\\{${k}\\}`, 'g'), v)
    }
  }
  return val
}

export function setLang(l) {
  lang.value = l
  localStorage.setItem('lang', l)
}

export function toggleLang() {
  setLang(lang.value === 'zh' ? 'en' : 'zh')
}
