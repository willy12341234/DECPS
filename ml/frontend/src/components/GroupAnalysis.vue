<template>
  <div v-if="hasData" class="card" id="group-analysis-card">
    <h2>
      <span>{{ t('groups_title') }}</span>
      <span class="shap-help" @click="showGroupHelp = true">?</span>
    </h2>
    <div class="group-content" v-html="groupHtml"></div>

    <div v-if="showGroupHelp" class="shap-help-overlay" @click="showGroupHelp = false">
      <div class="shap-help-modal" @click.stop>
        <div class="shap-help-header">
          <span>{{ t('groups_title') }}</span>
          <span class="shap-help-close" @click="showGroupHelp = false">✕</span>
        </div>
        <div class="shap-help-body" v-html="groupHelpBody"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { usePredictionStore } from '../stores/prediction'
import { currentLang, t, LOCALE } from '../i18n'

const store = usePredictionStore()
const showGroupHelp = ref(false)
const groupData = ref(null)

watch(() => store.result, async (res) => {
  if (!res || res.error) {
    groupData.value = null
    return
  }
  const apiVal = document.querySelector('#api')?.value || store.pendingForm.api || ''
  const exc1Val = document.querySelector('#exc1')?.value || store.pendingForm.exc1 || ''
  const exc2Val = document.querySelector('#exc2')?.value || store.pendingForm.exc2 || ''
  if (!apiVal || !exc1Val) {
    groupData.value = null
    return
  }
  try {
    const body = { api: apiVal, excipient1: exc1Val }
    if (exc2Val) body.excipient2 = exc2Val
    const r = await fetch('/api/analyze_groups', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    const d = await r.json()
    if (!d.error) groupData.value = d
  } catch (e) {}
}, { immediate: true })

const hasData = computed(() => groupData.value !== null)

const GROUP_ZH = {
  'Ester': '酯键', 'Amide': '酰胺键', 'Lactam': '内酰胺', 'Lactone': '内酯',
  'Acetal': '缩醛', 'Imine': '亚胺', 'Anhydride': '酸酐',
  'Phenol': '酚羟基', 'Aniline': '苯胺基', 'Thiol': '巯基', 'Thioether': '硫醚',
  'Aldehyde': '醛基', '1° Alcohol': '伯醇', 'Benzylic': '苄基', 'Allyl': '烯丙基',
  'Nitro': '硝基', 'N-oxide': 'N-氧化物', 'Quinone': '醌类',
  'Ar-Cl': '芳基氯', 'Ar-Br': '芳基溴', 'Ar-I': '芳基碘',
  'β-diketone': 'β-二酮', 'Catechol': '邻苯二酚', 'Carboxylic acid': '羧酸', '1° Amine': '伯胺',
}
const PAIR_ZH = {
  'Maillard (amine+ester)': '美拉德反应(胺+酯)',
  'Maillard (amine+aldehyde)': '美拉德反应(胺+醛)',
  'Esterification (acid+alcohol)': '酯化反应(酸+醇)',
  'Transesterification (ester+alcohol)': '转酯反应(酯+醇)',
  'Amidation (ester+amine)': '酰胺化反应(酯+胺)',
  'Hydrolysis (ester+acid)': '水解反应(酯+酸)',
  'Hydrolysis (amide+acid)': '水解反应(酰胺+酸)',
  'Hydrolysis (ester+base)': '水解反应(酯+碱)',
  'Hydrolysis (amide+base)': '水解反应(酰胺+碱)',
  'Oxidation (phenol+thioether)': '氧化反应(酚+硫醚)',
  'Oxidation (thiol+thioether)': '氧化反应(巯基+硫醚)',
  'Oxidation (aniline+thioether)': '氧化反应(苯胺+硫醚)',
  'Oxidation (aldehyde+thioether)': '氧化反应(醛+硫醚)',
  'Oxidation (benzylic+thioether)': '氧化反应(苄基+硫醚)',
  'Chelation (diketone+acid)': '螯合反应(二酮+酸)',
  'Chelation (catechol+acid)': '螯合反应(邻苯二酚+酸)',
  'Schiff base (aldehyde+amine)': '席夫碱反应(醛+胺)',
  'Acid-base (acid+base)': '酸碱反应(酸+碱)',
}

function xlate(s) {
  if (currentLang.value !== 'zh') return s.replace(/\((\d+)\)/g, '×$1')
  const keys = Object.keys(GROUP_ZH).sort((a, b) => b.length - a.length)
  for (const en of keys) {
    s = s.split(en).join(GROUP_ZH[en])
  }
  return s.replace(/\((\d+)\)/g, '×$1')
}

function xlatePair(name) {
  if (currentLang.value !== 'zh') return name
  return PAIR_ZH[name] || name
}

const groupHtml = computed(() => {
  const d = groupData.value
  if (!d) return ''
  const isZh = currentLang.value === 'zh'
  let html = '<div style="max-width:720px;margin:0 auto">'

  const catLabels = {
    hydrolysis: t('groups_hydrolysis'),
    oxidation: t('groups_oxidation'),
    photolysis: t('groups_photolysis'),
    chelation: t('groups_chelation'),
  }

  html += `<div style="margin-bottom:16px;text-align:center"><span style="font-weight:600;color:#1d1d1f">${t('groups_api')}</span><span style="font-size:12px;color:#86868b;margin-left:8px">(${t('groups_sub')})</span></div>`
  const ag = d.api_groups
  let hasApi = false
  for (const cat of ['hydrolysis', 'oxidation', 'photolysis', 'chelation']) {
    const items = ag[cat] || []
    if (!items.length) continue
    hasApi = true
    html += `<div style="margin:6px 0;font-size:12px;text-align:center"><span style="color:#555">${catLabels[cat]}</span><span style="margin-left:6px;color:#777">${items.map(xlate).join(', ')}</span></div>`
  }
  if (ag.custom_groups && Object.keys(ag.custom_groups).length) {
    hasApi = true
    const items = Object.entries(ag.custom_groups).map(([k, v]) => `${xlate(k)}×${v}`).join(', ')
    html += `<div style="margin:6px 0;font-size:12px;text-align:center"><span style="color:#555">${t('groups_other')}</span><span style="margin-left:6px;color:#777">${items}</span></div>`
  }
  if (!hasApi) html += `<div style="margin:6px 0;font-size:12px;text-align:center;color:#86868b">${t('groups_none')}</div>`

  html += `<div style="margin:20px auto 16px;border-top:1px solid #eee;padding-top:16px;text-align:center"><span style="font-weight:600;color:#1d1d1f">${t('groups_exc')}</span></div>`
  const eg = d.exc1_groups
  let hasExc = false
  for (const cat of ['hydrolysis', 'oxidation', 'photolysis', 'chelation']) {
    const items = eg[cat] || []
    if (!items.length) continue
    hasExc = true
    html += `<div style="margin:6px 0;font-size:12px;text-align:center"><span style="color:#555">${catLabels[cat]}</span><span style="margin-left:6px;color:#777">${items.map(xlate).join(', ')}</span></div>`
  }
  if (eg.custom_groups && Object.keys(eg.custom_groups).length) {
    hasExc = true
    const items = Object.entries(eg.custom_groups).map(([k, v]) => `${xlate(k)}×${v}`).join(', ')
    html += `<div style="margin:6px 0;font-size:12px;text-align:center"><span style="color:#555">${t('groups_other')}</span><span style="margin-left:6px;color:#777">${items}</span></div>`
  }
  if (!hasExc) html += `<div style="margin:6px 0;font-size:12px;text-align:center;color:#86868b">${t('groups_none')}</div>`

  if (d.exc2_groups) {
    html += `<div style="margin:20px auto 16px;border-top:1px solid #eee;padding-top:16px;text-align:center"><span style="font-weight:600;color:#1d1d1f">🟠 ${t('groups_exc2')}</span></div>`
    const eg2 = d.exc2_groups
    let hasE2 = false
    for (const cat of ['hydrolysis', 'oxidation', 'photolysis', 'chelation']) {
      const items = eg2[cat] || []
      if (!items.length) continue
      hasE2 = true
      html += `<div style="margin:6px 0;font-size:12px;text-align:center"><span style="color:#555">${catLabels[cat]}</span><span style="margin-left:6px;color:#777">${items.map(xlate).join(', ')}</span></div>`
    }
    if (eg2.custom_groups && Object.keys(eg2.custom_groups).length) {
      hasE2 = true
      const items = Object.entries(eg2.custom_groups).map(([k, v]) => `${xlate(k)}×${v}`).join(', ')
      html += `<div style="margin:6px 0;font-size:12px;text-align:center"><span style="color:#555">${t('groups_other')}</span><span style="margin-left:6px;color:#777">${items}</span></div>`
    }
    if (!hasE2) html += `<div style="margin:6px 0;font-size:12px;text-align:center;color:#86868b">${t('groups_none')}</div>`
  }

  const activeRisks = (d.pairwise_risks || []).filter(r => r.active)
  if (activeRisks.length) {
    html += `<div style="margin:20px auto 16px;border-top:1px solid #eee;padding-top:16px;text-align:center"><span style="font-weight:600;color:#c62828">⚠ ${t('groups_risks')}</span></div>`
    for (const risk of activeRisks) {
      html += `<div style="margin:6px 0;font-size:12px;text-align:center"><span style="color:#c62828">${xlatePair(risk.name)}</span><br><span style="color:#777;font-size:11px">${risk.description}</span></div>`
    }
  } else {
    html += `<div style="margin:20px auto 16px;border-top:1px solid #eee;padding-top:16px;text-align:center"><span style="font-weight:600;color:#2e7d32">${t('groups_safe')}</span></div>`
  }

  if (d.exc2_pairwise_risks) {
    const activeRisks2 = d.exc2_pairwise_risks.filter(r => r.active)
    if (activeRisks2.length) {
      html += `<div style="margin:20px auto 16px;border-top:1px solid #eee;padding-top:16px;text-align:center"><span style="font-weight:600;color:#c62828">⚠ ${t('groups_risks2')}</span></div>`
      for (const risk of activeRisks2) {
        html += `<div style="margin:6px 0;font-size:12px;text-align:center"><span style="color:#c62828">${xlatePair(risk.name)}</span><br><span style="color:#777;font-size:11px">${risk.description}</span></div>`
      }
    } else {
      html += `<div style="margin:20px auto 16px;border-top:1px solid #eee;padding-top:16px;text-align:center"><span style="font-weight:600;color:#2e7d32">${t('groups_safe2')}</span></div>`
    }
  }

  html += '</div>'
  return html
})

const groupHelpBody = computed(() => {
  const isZh = currentLang.value === 'zh'
  return isZh
    ? '<p>该模块基于 <strong>SMARTS 子结构匹配</strong>，分析 API 和辅料分子中存在的化学基团及其对杂质生成的影响。</p>'
    + '<p style="margin-top:8px"><strong>基团分类：</strong></p><ul>'
    + '<li><strong>水解敏感基团</strong> — 酯键、酰胺键、内酯环、缩醛等在水分和加热条件下易断裂</li>'
    + '<li><strong>氧化敏感基团</strong> — 酚羟基、巯基、硫醚、苯胺等在金属离子或过氧化物存在下易氧化</li>'
    + '<li><strong>光解敏感基团</strong> — 硝基、N-氧化物、芳基卤化物等在光照下易降解</li>'
    + '<li><strong>螯合相关基团</strong> — β-二酮、邻苯二酚、羧酸等可与金属离子形成络合物</li>'
    + '</ul><p style="margin-top:8px"><strong>交叉反应风险</strong> 列出 API 和辅料之间已匹配的已知化学反应规则（如美拉德反应、酯化反应等），帮助理解杂质产生的化学本质。</p>'
    : '<p>This module uses <strong>SMARTS substructure matching</strong> to analyze chemical groups in API and excipient molecules and their impact on impurity formation.</p>'
    + '<p style="margin-top:8px"><strong>Group Categories:</strong></p><ul>'
    + '<li><strong>Hydrolysis-Prone</strong> — Esters, amides, lactones, acetals cleave under heat and moisture</li>'
    + '<li><strong>Oxidation-Prone</strong> — Phenols, thiols, thioethers, anilines oxidize with metal ions or peroxides</li>'
    + '<li><strong>Photolysis-Prone</strong> — Nitro, N-oxide, aryl halides degrade under light exposure</li>'
    + '<li><strong>Chelation-Related</strong> — β-diketones, catechols, carboxylic acids form metal complexes</li>'
    + '</ul><p style="margin-top:8px"><strong>Cross-Reaction Risks</strong> lists matched chemical reaction rules between API and excipient (e.g. Maillard reaction, esterification) to help understand the chemical basis of impurity formation.</p>'
})
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
  align-items: center;
  justify-content: center;
}
.shap-help-modal {
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255,255,255,0.6);
  border-radius: 18px;
  max-width: 480px;
  width: 90%;
  box-shadow: 0 16px 48px rgba(0,0,0,0.15);
  overflow: hidden;
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
}
.group-content {
  font-size: 13px;
  line-height: 1.6;
}
</style>
