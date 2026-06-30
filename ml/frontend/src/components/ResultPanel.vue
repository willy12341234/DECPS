<template>
  <div v-if="store.result && !store.result.error">
    <div class="loading" v-if="store.loading">
      <div class="spinner"></div>
      <p>{{ t('predicting') }}</p>
    </div>

    <div v-if="store.result" id="results">
      <div v-if="!store.result.two_excipient_mode" class="card" id="single-result-card">
        <h2>{{ t('results_title') }}</h2>
        <div class="mode-badge" style="text-align:center;font-size:11px;color:#86868b;margin-bottom:12px">
          <span style="background:#e3f2fd;color:#1565c0;padding:2px 10px;border-radius:10px;font-weight:500">{{ t('model_mode_single') }}</span>
        </div>
        <ResultCard :data="store.result" />
        <div v-if="store.result.model_votes && store.result.model_votes.fingerprint_xgb !== undefined" class="model-votes">
          <div style="font-size:12px;font-weight:600;color:#6b6b70;margin-bottom:8px">{{ t('votes_lbl') }}</div>
          <div class="vote-bar">
            <span style="flex:0 0 70px;font-size:13px;font-weight:500;color:#1d1d1f">FP-XGB</span>
            <div class="vote-bar-track">
              <div class="vote-bar-fill" :style="{ width: (store.result.model_votes.fingerprint_xgb * 100).toFixed(1) + '%' }"></div>
            </div>
            <span style="flex:0 0 52px;text-align:right;font-family:monospace;font-size:13px;color:#6b6b70">{{ (store.result.model_votes.fingerprint_xgb * 100).toFixed(1) }}%</span>
          </div>
        </div>
        <div class="risk-interpretation" v-if="store.result.prob !== undefined">
          <div :style="riskStyle" v-html="riskText"></div>
        </div>
      </div>

      <div v-if="store.result.two_excipient_mode" class="card">
        <h2>{{ t('results_title') }}</h2>
        <div class="mode-badge" style="text-align:center;font-size:11px;color:#86868b;margin-bottom:12px">
          <span style="background:#e3f2cd;color:#1565c0;padding:2px 10px;border-radius:10px;font-weight:500">{{ t('model_mode_dual') }}</span>
        </div>
        <div v-if="dualSummary" class="dual-summary" :style="dualSummary.style" v-html="dualSummary.html"></div>
        <div class="sub-labels" style="margin-top:20px;font-size:14px;font-weight:600;color:#1d1d1f">{{ t('detail_analysis') }}</div>
        <ResultCard v-for="(sr, i) in store.result.sub_results" :key="i" :data="sr" :title="subLabels[i]" />
      </div>

      <div class="card" v-if="!store.result.two_excipient_mode" id="shap-card">
        <h2>
          <span>{{ t('shap_title') }}</span>
          <span class="shap-help" @click="showShapHelp = true">?</span>
        </h2>
        <p style="font-size:12px;color:#86868b;margin-bottom:14px" v-html="t('shap_desc')"></p>
        <div v-if="store.result.top && store.result.top.length" class="features">
          <div v-for="(f, i) in store.result.top" :key="i" class="feat-item">
            <span class="feat-name">{{ f.feature }}</span>
            <span class="feat-help" @click.stop="showFeatDesc($event, f.feature)">?</span>
            <div class="feat-bar">
              <div class="feat-fill" :style="featBarStyle(f, store.result.top)"></div>
            </div>
            <span class="feat-val" :class="f.dir === '↑' ? 'dir-up' : 'dir-down'">
              {{ f.dir === '↑' ? '+' : '-' }}{{ (Math.abs(f.shap) * 100).toFixed(1) }}%
            </span>
          </div>
        </div>
        <div v-if="activeTooltip" class="feat-tooltip" :style="tooltipStyle" @click="activeTooltip=''" @mouseleave="activeTooltip=''">
          <div class="feat-tooltip-content">{{ activeTooltip }}</div>
        </div>
        <div v-else></div>

        <div v-if="showShapHelp" class="shap-help-overlay" @click="showShapHelp = false">
          <div class="shap-help-modal" @click.stop>
            <div class="shap-help-header">
              <span>{{ t('shap_help_title') }}</span>
              <span class="shap-help-close" @click="showShapHelp = false">✕</span>
            </div>
            <div class="shap-help-body" v-html="t('shap_help_body')"></div>
          </div>
        </div>
      </div>

      <GroupAnalysis />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { usePredictionStore } from '../stores/prediction'
import { currentLang, t, LOCALE } from '../i18n'
import ResultCard from './ResultCard.vue'
import GroupAnalysis from './GroupAnalysis.vue'

const store = usePredictionStore()
const showShapHelp = ref(false)
const activeTooltip = ref('')
const tooltipStyle = ref({})

const subLabels = computed(() => {
  if (!store.result?.sub_results) return []
  const apiVal = document.querySelector('#api')?.value || ''
  const exc1Val = document.querySelector('#exc1')?.value || ''
  const exc2Val = document.querySelector('#exc2')?.value || ''
  return store.result.sub_results.map(sr => {
    const map = {
      exc1: `${apiVal} + ${exc1Val}`,
      exc2: `${apiVal} + ${exc2Val}`,
      exc1_exc2: `${exc1Val} + ${exc2Val}`,
    }
    return map[sr.label] || sr.label
  })
})

const dualSummary = computed(() => {
  const d = store.result
  if (!d || !d.two_excipient_mode) return null
  const isHigh = d.prob >= 0.5
  const bgColor = isHigh ? 'rgba(239,83,80,0.08)' : 'rgba(129,199,132,0.08)'
  const bdColor = isHigh ? 'rgba(239,83,80,0.2)' : 'rgba(129,199,132,0.2)'
  const txtColor = isHigh ? '#c62828' : '#2e7d32'
  const verdict = isHigh ? t('incompatible') : t('compatible')
  const html = `<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
    <span style="font-size:15px;font-weight:700;color:${txtColor}">${t('overall_verdict')}</span>
    <span style="font-size:14px;font-weight:600;color:#1d1d1f">${verdict} · ${(d.prob * 100).toFixed(1)}%</span>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:#6b6b70">
    <span>${t('impurity_count')}: <strong style="color:#1d1d1f">${Math.round(d.impurity_count)}</strong></span>
    <span>${t('total_pct')}: <strong style="color:#1d1d1f">${fmtPct(d.total_impurity_pct)}</strong></span>
    <span>${t('max_single')}: <strong style="color:#1d1d1f">${fmtPct(d.max_single_impurity_pct)}</strong></span>
  </div>`
  return { html, style: { background: bgColor, border: `1px solid ${bdColor}`, borderRadius: '12px', padding: '14px 16px', marginBottom: '16px' } }
})

const riskText = computed(() => {
  const d = store.result
  if (!d) return ''
  const pct = (d.prob * 100).toFixed(1)
  const key = d.prob < 0.3 ? 'risk_low' : d.prob < 0.5 ? 'risk_medium_low' : d.prob < 0.7 ? 'risk_medium_high' : 'risk_high'
  return `📊 ${t(key, { p: pct })}`
})

const riskStyle = computed(() => {
  const d = store.result
  if (!d) return {}
  if (d.prob < 0.3) return { background: '#e8f5e9', color: '#2e7d32', borderRadius: '12px', padding: '12px 16px', fontSize: '13px', lineHeight: '1.7' }
  if (d.prob < 0.5) return { background: '#fff8e1', color: '#f57f17', borderRadius: '12px', padding: '12px 16px', fontSize: '13px', lineHeight: '1.7' }
  if (d.prob < 0.7) return { background: '#fff3e0', color: '#e65100', borderRadius: '12px', padding: '12px 16px', fontSize: '13px', lineHeight: '1.7' }
  return { background: '#ffebee', color: '#c62828', borderRadius: '12px', padding: '12px 16px', fontSize: '13px', lineHeight: '1.7' }
})

function fmtPct(v) {
  v = Number(v) || 0
  if (v === 0) return '0%'
  if (v >= 0.001) return v.toFixed(4) + '%'
  return v.toExponential(2) + '%'
}

function showFeatDesc(e, name) {
  const desc = featDesc(name)
  if (!desc) return
  const rect = e.target.getBoundingClientRect()
  tooltipStyle.value = {
    position: 'fixed',
    top: (rect.bottom + 6) + 'px',
    left: Math.max(10, Math.min(rect.left, window.innerWidth - 320)) + 'px',
    zIndex: 3000,
  }
  activeTooltip.value = desc
}

function featBarStyle(f, all) {
  const absV = Math.abs(f.shap)
  const maxAbs = Math.max(...all.map(x => Math.abs(x.shap)))
  const pct = Math.min((absV / maxAbs) * 100, 100)
  const color = f.dir === '↑' ? '#e57373' : '#81c784'
  return { width: pct + '%', background: color }
}

function featDesc(name) {
  const isZh = currentLang.value === 'zh'
  const n = (name || '').toLowerCase()
  const nn = n.replace(/\s+/g, ' ')

  // ── Interaction / stability ──
  if (nn.includes('interact stability temp')) return isZh
    ? '🔬 温度交互效应\n反应条件(温度)与API-辅料组合的协同影响\n例：高温(60℃)下API+乳糖的降解速率是单独API的3倍'
    : '🔬 Temperature interaction effect\nSynergistic effect of temperature on API-excipient pair\nE.g., degradation rate of API+lactose at 60°C is 3× that of API alone'
  if (nn.includes('interact stability humidity')) return isZh
    ? '💧 湿度交互效应\n反应条件(湿度)与API-辅料组合的协同影响\n例：高湿(75%RH)下API+PVP的吸湿增重是单独API的5倍'
    : '💧 Humidity interaction effect\nSynergistic effect of humidity on API-excipient pair\nE.g., moisture uptake of API+PVP at 75%RH is 5× that of API alone'
  if (nn.includes('interact')) return isZh
    ? '⚡ 环境条件交互效应\n温度/湿度与API-辅料组合的协同影响\n正值=该条件增加不相容风险'
    : '⚡ Environmental interaction effect\nSynergistic effect of temperature/humidity on API-excipient pair\nPositive = condition increases incompatibility risk'

  // ── logP / lipophilicity ──
  if (nn.includes('api logp') || nn.includes('api_logp')) return isZh
    ? '🧪 API 脂水分配系数 (logP)\n衡量分子亲脂性的关键参数，logP越大越亲脂\n例：布洛芬 logP≈3.5（中等亲脂），二甲双胍 logP≈-1.3（亲水）\n影响：亲脂性API更易与辅料的疏水区域相互作用'
    : '🧪 API lipophilicity (logP)\nKey measure of molecular fat/water partitioning; higher = more lipophilic\nE.g., ibuprofen logP≈3.5 (moderately lipophilic), metformin logP≈-1.3 (hydrophilic)\nImpact: lipophilic APIs interact more with excipient hydrophobic regions'
  if (n.includes('辅料1 logp') || n.includes('exc1 logp') || n.includes('exc1_logp')) return isZh
    ? '🧪 辅料1 脂水分配系数 (logP)\n该辅料的亲脂性参数，影响API在制剂中的分散和释放\n例：乳糖 logP≈-3.3（强亲水），硬脂酸镁 logP≈7.5（强亲脂）\n正值→辅料越亲脂越可能增加杂质风险'
    : '🧪 Excipient 1 lipophilicity (logP)\nExcipient fat/water partitioning; affects API dispersion and release\nE.g., lactose logP≈-3.3 (strongly hydrophilic), Mg stearate logP≈7.5 (strongly lipophilic)\nPositive→more lipophilic excipient increases impurity risk'

  // ── TPSA ──
  if (nn.includes('api tpsa') || nn.includes('api_tpsa')) return isZh
    ? '🧬 API 极性表面积 (TPSA)\n分子中极性原子(N,O)的表面积总和，衡量分子极性\n例：阿司匹林 TPSA≈63Å²，肝素 TPSA≈350Å²\n影响：TPSA低的API更易穿透生物膜，但也更可能与辅料非极性区域发生相互作用'
    : '🧬 API topological polar surface area (TPSA)\nSum of polar atom (N,O) surface areas; measures molecular polarity\nE.g., aspirin TPSA≈63Å², heparin TPSA≈350Å²\nImpact: low-TPSA APIs penetrate membranes easily but may interact with excipient nonpolar regions'
  if (n.includes('辅料1 tpsa') || n.includes('exc1 tpsa')) return isZh
    ? '🧬 辅料1 极性表面积 (TPSA)\n辅料的极性特征，影响其与API的相互作用方式\n例：乳糖 TPSA≈190Å²（多羟基→强极性），微晶纤维素 TPSA≈0Å²（非极性）'
    : '🧬 Excipient 1 topological polar surface area (TPSA)\nExcipient polarity; affects how it interacts with API\nE.g., lactose TPSA≈190Å² (polyhydroxy→polar), MCC TPSA≈0Å² (nonpolar)'

  // ── molecular weight ──
  if (nn.includes('api mw') || nn.includes('api_mw') || nn.includes('api mw')) return isZh
    ? '⚖️ API 分子量 (MW)\n分子质量，反映分子大小\n例：布洛芬 MW≈206g/mol，紫杉醇 MW≈854g/mol\n影响：小分子API(＜300)扩散快，与辅料接触更充分，反应概率更高'
    : '⚖️ API molecular weight (MW)\nMolecular mass; reflects molecule size\nE.g., ibuprofen MW≈206g/mol, paclitaxel MW≈854g/mol\nImpact: small APIs (<300) diffuse faster, contact excipients more, higher reaction probability'

  // ── Balaban J ──
  if (nn.includes('balaban') || nn.includes('balaban j')) return isZh
    ? '📐 Balaban J 拓扑指数\n描述分子分支度和环状结构的拓扑不变量\n例：直链烷烃(正己烷) J≈1.6，苯环结构 J≈2.1，高度分支的API J值更大\n正值→API分支度越高杂质风险越大'
    : '📐 Balaban J topological index\nGraph-theoretic descriptor of molecular branching and ring structures\nE.g., linear hexane J≈1.6, benzene J≈2.1, highly branched APIs have larger J\nPositive→more branched API → higher impurity risk'

  // ── kappa descriptors ──
  if (nn.includes('kappa2') || nn.includes('kappa 2')) return isZh
    ? '📏 Kappa2 分子形状指数\n描述分子形状的刚性/柔性，基于原子连接路径计数\n例：柔性长链分子kappa2大，刚性环状分子kappa2小\n负值→Δkappa2降低→API与辅料形状相似度高→相容性好'
    : '📏 Kappa2 molecular shape index\nDescribes molecular rigidity/flexibility based on atom connectivity path count\nE.g., flexible long-chain molecules have larger kappa2, rigid rings have smaller\nNegative→Δkappa2 decrease→API and excipient shape similar→compatible'
  if (nn.includes('kappa1') || nn.includes('kappa 1')) return isZh
    ? '📏 Kappa1 分子形状指数\n一阶形状指数，基于分子中原子数的一维路径计数\n衡量分子的线性/分支程度\n例：直链比环状分子的kappa1值更高'
    : '📏 Kappa1 molecular shape index\nFirst-order shape index based on 1-atom path count\nMeasures linear vs branched molecular shape\nE.g., linear molecules have higher kappa1 than ring structures'

  // ── RDKit fingerprint ──
  if (nn.startsWith('api rdk') || nn.startsWith('api_rdk')) {
    const bit = n.replace(/\D/g, '')
    return isZh
      ? `🧩 API RDKit分子指纹位 ${bit}\nRDKit 2048位摩根指纹中的第${bit}位，标记特定子结构是否存在\n例：位1459可能对应"芳香环+羧基"子结构，位1060对应"羰基"结构\n值=1表示API含有该子结构，0表示不含\n正值→该子结构存在→增加杂质风险`
      : `🧩 API RDKit fingerprint bit ${bit}\nBit ${bit} of 2048-bit Morgan fingerprint; flags specific substructure\nE.g., bit 1459 may represent "aromatic ring+carboxyl" substructure\nValue=1 when substructure present, 0 when absent\nPositive→substructure present→increases impurity risk`
  }
  if (nn.startsWith('api maccs') || nn.startsWith('api_maccs')) {
    const bit = n.replace(/\D/g, '')
    return isZh
      ? `🔗 API MACCS结构键 ${bit}\nMACCS 166位化学结构键中的第${bit}位\n例：MACCS键39对应"CH2"，键114对应"≥4元环"\n值=1表示API含有该结构特征，0表示不含`
      : `🔗 API MACCS structural key ${bit}\nBit ${bit} of 166-bit MACCS chemical structure keys\nE.g., key 39="CH2 group", key 114="≥4-membered ring"\nValue=1 when structural feature present, 0 when absent`
  }

  // ── delta (difference) features ──
  if (nn.includes('delta') || nn.includes('Δ') || nn.startsWith('extra Δ') || nn.startsWith('extra ')) {
    const base = name.replace(/^extra\s+/i, '').replace(/^Δ/i, '').replace(/^delta\s+/i, '').trim() || name
    if (nn.includes('balaban')) return isZh
      ? `📐 ΔBalaban J（API与辅料1的Balaban J指数差值）\n正值→API比辅料分支度高→两分子拓扑结构差异大→机械混合时空间位阻失配\n例：API(分支状)+辅料(直链状)→ΔJ大→混合均匀性差→局部高浓度→反应风险↑`
      : `📐 ΔBalaban J (difference in Balaban J index)\nPositive→API more branched than excipient→topological mismatch→poor mixing→local concentration→reaction risk↑`
    if (nn.includes('kappa2')) return isZh
      ? `📏 ΔKappa2（API与辅料1的分子形状指数差值）\n负值→辅料比API更柔性(更长的链状结构)\n例：API(刚性环)+辅料(长链)→Δkappa2为负→柔性辅料包裹API可能改变其微环境`
      : `📏 ΔKappa2 (shape index difference)\nNegative→excipient more flexible (longer chain) than API\nE.g., rigid API + long-chain excipient→negative Δkappa2→flexible excipient may alter API microenvironment`
    if (nn.includes('kappa1')) return isZh
      ? `📏 ΔKappa1（一阶形状指数差值）\n衡量API与辅料在线性/分支程度上的差异\n正值→API比辅料更线性`
      : `📏 ΔKappa1 (first-order shape difference)\nMeasures linearity/branching mismatch between API and excipient\nPositive→API more linear than excipient`
    if (nn.includes('logp')) return isZh
      ? `💧 ΔlogP（脂水分配系数差值）\nAPI与辅料亲脂性差异\n绝对值越大→两者极性差异越大→混合时可能发生相分离\n例：API(亲脂)+辅料(亲水)→ΔlogP大→体系热力学不稳定→促进降解`
      : `💧 ΔlogP (lipophilicity difference)\nPolarity mismatch between API and excipient\nLarge absolute→phase separation risk→thermodynamic instability→promotes degradation`
    if (nn.includes('tpsa')) return isZh
      ? `🧬 ΔTPSA（极性表面积差值）\nAPI与辅料极性差异\n正值→API极性大于辅料→两者极性不匹配\n例：极性API+非极性辅料→吸附不均匀→局部过饱和→结晶或降解`
      : `🧬 ΔTPSA (polar surface area difference)\nPolarity mismatch between API and excipient\nPositive→API more polar than excipient→uneven adsorption→local supersaturation→crystallization/degradation`
    if (nn.includes('mw') || nn.includes('molecular weight')) return isZh
      ? `⚖️ ΔMW（分子量差值）\nAPI与辅料分子大小差异\n大差值→大小分子混合→小分子可能嵌入大分子间隙→改变固体分散体结构`
      : `⚖️ ΔMW (molecular weight difference)\nSize mismatch between API and excipient\nLarge diff→small molecules may embed in large molecule gaps→alter solid dispersion structure`
    return isZh
      ? `📊 ${base}的API-辅料差值\n正值→API的${base}大于辅料\n负值→辅料的${base}大于API\n绝对值越大→两者在该性质上差异越大→潜在不相容风险↑`
      : `📊 Δ${base} (API-excipient difference)\nPositive→API has higher ${base} than excipient\nNegative→excipient has higher ${base} than API\nLarger absolute→greater property mismatch→higher incompatibility risk`
  }

  // ── Extended descriptors ──
  if (nn.startsWith('extra')) return isZh
    ? `📊 扩展分子描述符\nRDKit计算的其他理化参数，包括：\n• Chi系列(分子连接性指数) → 衡量分子饱和度和分支度\n• Kappa系列(形状指数) → 描述分子拓扑形状\n• 氮氧原子计数 → 潜在氢键位点数量\n高绝对值→该参数对预测结果影响显著`
    : `📊 Extended molecular descriptor\nAdditional RDKit physicochemical parameters:\n• Chi indices (molecular connectivity)→saturation/branching\n• Kappa indices (shape)→topological shape\n• N/O counts→potential H-bond sites\nLarge absolute→significant impact on prediction`

  // ── Density ──
  if (nn.includes('api d ') || nn.includes('api_d') || nn.includes('api density')) return isZh
    ? '📦 API 密度\n单位体积质量，反映分子堆积效率\n例：大多数有机药物密度1.1-1.4 g/cm³\n高密度→分子堆积紧密→反应位点暴露少→可能降低反应性'
    : '📦 API density\nMass per unit volume; reflects packing efficiency\nE.g., most organic drugs 1.1-1.4 g/cm³\nHigh density→tight packing→fewer exposed reaction sites→lower reactivity'

  // ── Molar refractivity ──
  if (nn.includes('api mr') || nn.includes('api_mr ')) return isZh
    ? '🔍 API 摩尔折射度 (MR)\n衡量分子总体极化率，与分子体积和电子分布相关\n例：芳香环多的API MR值大\n正值→MR大→分子极化率高→易受亲电/亲核试剂攻击'
    : '🔍 API molar refractivity (MR)\nMeasures total molecular polarizability; related to volume and electron distribution\nE.g., APIs with many aromatic rings have large MR\nPositive→high MR→high polarizability→susceptible to electrophilic/nucleophilic attack'

  // ── HBD / HBA ──
  if (nn.includes('api hbd') || nn.includes('api_hbd')) return isZh
    ? '💫 API 氢键供体数 (HBD)\n分子中可提供氢键的-OH、-NH、-SH等基团数\n例：布洛芬 HBD=1(一个羧基-OH)，葡萄糖 HBD=5(五个-OH)\nHBD越多→API越易与辅料形成分子间氢键→可能促进或抑制反应'
    : '💫 API H-bond donor count (HBD)\nCount of -OH, -NH, -SH groups that can donate H-bonds\nE.g., ibuprofen HBD=1 (one carboxyl -OH), glucose HBD=5 (five -OH)\nMore HBD→more intermolecular H-bonds with excipient→may promote or inhibit reaction'
  if (nn.includes('api hba') || nn.includes('api_hba')) return isZh
    ? '💫 API 氢键受体数 (HBA)\n分子中可接受氢键的N、O、F等原子数\n例：阿司匹林 HBA=4(2个O+2个=O)，二甲双胍 HBA=5(5个N)\nHBA多→API易与含羟基的辅料(如乳糖、PEG)形成氢键网络'
    : '💫 API H-bond acceptor count (HBA)\nCount of N, O, F atoms that can accept H-bonds\nE.g., aspirin HBA=4, metformin HBA=5\nMore HBA→more H-bond network with hydroxyl-containing excipients (lactose, PEG)'

  // ── Exc1 / Exc2 ──
  if (n.includes('辅料1') || n.includes('exc1')) {
    const prop = name.replace(/辅料1\s*/i, '').replace(/exc1\s*/i, '').trim()
    return isZh
      ? `📋 辅料1 ${prop || ''}特征\n该辅料在${prop || '该性质'}上的特征值影响整体相容性\n正值→辅料该性质值越大→杂质风险↑\n例：辅料1 logP为正且↑→该辅料亲脂性强→与中等亲脂API相容性可能较差`
      : `📋 Excipient 1 ${prop || ''} feature\nThis excipient's ${prop || 'property'} value affects overall compatibility\nPositive→higher excipient value→increases impurity risk\nExample: exc1 logP positive→lipophilic excipient may be less compatible with moderately lipophilic API`
  }
  if (n.includes('辅料2') || n.includes('exc2')) {
    const prop = name.replace(/辅料2\s*/i, '').replace(/exc2\s*/i, '').trim()
    return isZh
      ? `📋 辅料2 ${prop || ''}特征\n正值→该辅料性质值越大→增加杂质风险`
      : `📋 Excipient 2 ${prop || ''} feature\nPositive→higher excipient property→increases impurity risk`
  }

  // ── Pair features ──
  if (n.startsWith('pair')) return isZh
    ? '🔗 API-辅料配对反应特征\n基于18条RAG知识库规则判断的API-辅料官能团配对\n例："pair ester_acid"=1表示API含酯基+辅料含羧基→可能发生酯交换反应\n值=1→该危险配对存在→相容性风险'
    : '🔗 API-excipient pair reaction feature\nBased on 18 RAG knowledge-base rules for functional group matching\nE.g., "pair ester_acid"=1→API has ester + excipient has carboxyl→transesterification risk\nValue=1→risky pair present→compatibility risk'

  // ── Fallback ──
  return isZh
    ? `📊 ${name}\n该特征用于衡量分子结构和理化性质\n正值→数值↑→增加杂质风险\n负值→数值↓→降低杂质风险`
    : `📊 ${name}\nMolecular structure/physicochemical descriptor\nPositive→higher value→increases impurity risk\nNegative→lower value→decreases impurity risk`
}
</script>

<style scoped>
.card {
  background: rgba(255,255,255,0.72);
  border: 1px solid rgba(255,255,255,0.5);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow: 0 4px 24px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.02);
}
.card h2 {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.loading {
  text-align: center;
  padding: 32px;
}
.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(0,0,0,0.08);
  border-top-color: #0071e3;
  border-radius: 50%;
  animation: spin .7s linear infinite;
  margin: 0 auto 10px;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.model-votes {
  margin-top: 16px;
}
.vote-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 4px 0;
}
.vote-bar-track {
  flex: 1;
  height: 22px;
  background: rgba(0,0,0,0.06);
  border-radius: 6px;
  overflow: hidden;
}
.vote-bar-fill {
  height: 100%;
  background: #0071e3;
  border-radius: 6px;
  transition: width .6s ease;
}
.shap-help {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0,0,0,0.06);
  color: #86868b;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all .2s;
  vertical-align: middle;
  margin-left: 6px;
  line-height: 1;
}
.shap-help:hover {
  background: #0071e3;
  color: #fff;
  box-shadow: 0 2px 8px rgba(0,113,227,0.25);
}
.shap-help-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.3);
  backdrop-filter: blur(4px);
  z-index: 2000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow-y: auto;
  padding: 40px 0;
}
.shap-help-modal {
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255,255,255,0.6);
  border-radius: 18px;
  max-width: 480px;
  width: 90%;
  box-shadow: 0 16px 48px rgba(0,0,0,0.15);
}
.shap-help-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
}
.shap-help-close {
  background: none;
  border: none;
  color: #86868b;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  transition: color .2s;
}
.shap-help-close:hover {
  color: #1d1d1f;
}
.shap-help-body {
  padding: 16px 20px 20px;
  font-size: 13px;
  line-height: 1.6;
  color: #6b6b70;
  max-height: 50vh;
  overflow-y: auto;
}
.features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.feat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255,255,255,0.5);
  border-radius: 10px;
  padding: 8px 12px;
  border: 1px solid rgba(255,255,255,0.5);
  backdrop-filter: blur(8px);
  transition: background .25s;
}
.feat-item:hover {
  background: rgba(255,255,255,0.85);
}
.feat-name {
  font-size: 11px;
  color: #6b6b70;
  max-width: 130px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.feat-help {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(0,0,0,0.05);
  color: #aeaeb2;
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: all .2s;
  flex-shrink: 0;
  line-height: 1;
}
.feat-help:hover {
  background: #0071e3;
  color: #fff;
}
.feat-tooltip {
  max-width: 320px;
  background: rgba(30,30,32,0.92);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 12px;
  line-height: 1.6;
  color: #f5f5f7;
  white-space: pre-line;
  pointer-events: auto;
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}
.feat-tooltip-content {
  font-size: 12px;
  line-height: 1.6;
}
.feat-bar {
  width: 50px;
  height: 5px;
  background: rgba(0,0,0,0.08);
  border-radius: 3px;
  overflow: hidden;
}
.feat-fill {
  height: 100%;
  border-radius: 3px;
}
.feat-val {
  font-size: 11px;
  min-width: 40px;
  text-align: right;
  font-family: monospace;
}
.dir-up {
  color: #c62828;
}
.dir-down {
  color: #2e7d32;
}
</style>
