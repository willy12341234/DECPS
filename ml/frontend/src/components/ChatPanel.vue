<template>
  <div class="chat-container" @click="onChatClick">
    <div class="sidebar-header">
      <div class="sidebar-header-top">
        <h3>{{ t('sidebar_title') }}</h3>
        <div style="display:flex;gap:4px;align-items:center">
          <button class="sidebar-close" @click="newChat" :title="t('new_chat_btn')">➕</button>
          <button class="sidebar-close" @click="showApiSettings = !showApiSettings" title="API Settings">⚙</button>
          <button class="sidebar-close" @click="showHistory = !showHistory" :title="t('history_btn')">📖</button>
        </div>
      </div>
    </div>

    <div class="api-settings" :class="{ open: showApiSettings }">
      <div class="api-settings-row">
        <label>Key</label>
        <input type="password" v-model="apiKey" placeholder="sk-...">
      </div>
      <div class="api-settings-row">
        <label>URL</label>
        <input type="text" v-model="apiUrl" placeholder="https://api.deepseek.com/v1/chat/completions">
      </div>
      <div class="api-settings-row">
        <label>Model</label>
        <input type="text" v-model="apiModel" placeholder="deepseek-chat">
      </div>
      <button class="api-settings-save" @click="saveApiSettings">{{ t('save_btn') }}</button>
    </div>

    <HistoryPanel v-if="showHistory" :histories="store.history" @load="loadHistory" @delete="store.deleteHistoryItem" />

    <div class="skill-bar">
      <button v-for="s in skills" :key="s.id"
        :class="['skill-pill', { active: currentSkill === s.id }]"
        @click="switchSkill(s.id)"
        :title="s.desc">
        {{ s.icon }} {{ currentLang === 'zh' ? s.label : s.labelEn }}
      </button>
    </div>

    <div class="exp-progress" :class="{ open: expOpen }">
      <div class="exp-steps">
        <div v-for="(step, i) in 5" :key="i" class="exp-step" :class="expSteps[i]">
          <div class="exp-step-dot">{{ expSteps[i] === 'done' ? '✓' : expSteps[i] === 'running' ? '◉' : i + 1 }}</div>
          <div class="exp-step-label">{{ labelText(i) }}</div>
          <div v-if="i < 4" class="exp-connector"></div>
        </div>
      </div>
      <div class="exp-status-text" :class="expStatusClass">{{ expStatusText }}</div>
    </div>

    <div class="exp-sources" :class="{ open: sourcesOpen }">
      <div class="exp-sources-title">{{ t('sources_title') }}</div>
      <div v-for="(s, i) in sources" :key="i" class="exp-source-item">
        <span class="exp-source-icon">{{ sourceIcon(s.type) }}</span>
        <a class="exp-source-link" :href="s.url" :data-wv-link="s.url">{{ s.title || s.url }}</a>
      </div>
    </div>

    <div class="chat-parsed" :class="{ open: parsedOpen }">
      <div class="chat-parsed-title">{{ t('parsed_title') }}</div>
      <div class="chat-parsed-content">
        <span v-for="(tag, i) in parsedTags" :key="i" :style="tag.style">{{ tag.label }}: {{ tag.value }}</span>
      </div>
    </div>

    <TransitionGroup name="msg" tag="div" class="chat-msgs" ref="msgContainer">
      <div v-for="(m, i) in store.messages" :key="m.id" :class="['chat-msg', m.role]">
        <div v-if="!(m.role === 'assistant' && m.content === '...' && store.streaming)" class="chat-bubble" v-html="m.role === 'assistant' ? renderMd(m.content) : escapeHtml(m.content).replace(/\n/g, '<br>')"></div>
        <div v-if="m.role === 'assistant' && m.content && i === store.messages.length - 1 && !store.streaming && store.messages.some(x => x.role === 'user')"
             :class="['dl-btn', m.content.includes('点击重试') || m.content.includes('Click to retry') ? 'retry-btn' : '']"
             @click="retryLastMessage(m)">
          {{ m.content.includes('点击重试') || m.content.includes('Click to retry') ? (currentLang.value === 'zh' ? '▶ 重试' : '▶ Retry') : t('download_btn') }}
        </div>
      </div>
      <div v-if="store.streaming && store.messages.length && store.messages[store.messages.length - 1].content === '...'" :key="'loading'" class="chat-msg assistant">
        <div class="chat-bubble">
          <div class="chat-loading"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>
        </div>
      </div>
    </TransitionGroup>

    <div class="chat-hint">{{ t('chat_hint') }}</div>
    <div class="chat-input-wrap">
      <textarea v-model="inputText" :placeholder="currentPlaceholder" rows="1"></textarea>
      <button @click="sendChat" :disabled="!inputText.trim() || store.streaming">{{ t('send_btn') }}</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import { useChatStore } from '../stores/chat'
import { usePredictionStore } from '../stores/prediction'
import { currentLang, t, LOCALE } from '../i18n'
import HistoryPanel from './HistoryPanel.vue'

const emit = defineEmits(['navigate'])
const store = useChatStore()
const predStore = usePredictionStore()

const inputText = ref('')
const showHistory = ref(false)
const showApiSettings = ref(false)
const msgContainer = ref(null)
const apiKey = ref('')
const apiUrl = ref('')
const apiModel = ref('')


const currentSkill = computed({
  get: () => store.currentSkill,
  set: (v) => store.switchSkill(v)
})

const skills = [
  { id: 'auto',           icon: '🤖', label: '自动判断', labelEn: 'Auto',      desc: 'AI automatic task detection' },
  { id: 'compatibility',  icon: '🔬', label: '相容性',   labelEn: 'Compatibility', desc: 'Predict API-excipient compatibility' },
  { id: 'experiment',     icon: '🧪', label: '实验设计',  labelEn: 'Experiment',  desc: 'Design compatibility experiment protocols' },
  { id: 'formulation',    icon: '💊', label: '剂型调研',  labelEn: 'Formulation', desc: 'Research approved & investigational dosage forms' },
  { id: 'patent',         icon: '📄', label: '专利分析',  labelEn: 'Patent',      desc: 'Extract patent details' },
  { id: 'competitive',    icon: '🔍', label: '竞品调研',  labelEn: 'Competitive', desc: 'Compare competitive landscape' },
  { id: 'packaging',      icon: '📦', label: '包材研究',  labelEn: 'Packaging',   desc: 'Packaging material research' },
  { id: 'project',        icon: '📋', label: '立项报告',  labelEn: 'Project',    desc: 'Generate project initiation report' },
]

const currentPlaceholder = computed(() => {
  if (currentSkill.value === 'auto') return t('chat_placeholder')
  const key = `placeholder_${currentSkill.value}`
  const custom = currentLang.value === 'zh' ? LOCALE.zh[key] : LOCALE.en[key]
  return custom || t('chat_placeholder')
})

const expOpen = ref(false)
const expSteps = ref(['pending', 'pending', 'pending', 'pending', 'pending'])
const expStatusText = ref('')
const expStatusClass = ref('')
const phaseLabels = ref(['', '', '', '', ''])
const sourcesOpen = ref(false)
const sources = ref([])
const parsedOpen = ref(false)
const parsedTags = ref([])

const PHASE_LABELS = [()=>t('patent_step'), ()=>t('literature_step'), ()=>t('clinical_step'), ()=>t('ml_step'), ()=>t('plan_step')]

function labelText(i) {
  const v = phaseLabels.value[i]
  return typeof v === 'function' ? v() : v
}

watch(currentLang, () => {
  phaseLabels.value = PHASE_LABELS
}, { immediate: true })

onMounted(() => {
  phaseLabels.value = PHASE_LABELS
  if (!store.messages.length) {
    store.addMessage('assistant', t('welcome_msg'))
  }
})

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function renderMd(text) {
  let html = ''
  const lines = text.split('\n')
  let inCode = false, codeBuf = []
  let inList = null
  let inConclusion = false, inShap = false
  let inTable = false

  function closeSection() {
    if (inConclusion) { html += '</div>'; inConclusion = false }
    if (inShap) { html += '</div>'; inShap = false }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()

    if (/^---+\s*$/.test(trimmed)) {
      closeSection()
      if (inList) { html += `</${inList}>`; inList = null }
      continue
    }

    if (trimmed === '结论摘要' || trimmed === 'Conclusion Summary') {
      closeSection()
      if (inList) { html += `</${inList}>`; inList = null }
      html += '<div style="background:rgba(129,199,132,0.12);border:1px solid rgba(129,199,132,0.25);border-radius:12px;padding:14px 16px;margin:8px 0">'
      html += '<div style="font-size:13px;font-weight:700;color:#81c784;margin-bottom:8px">📊 ' + (currentLang.value === 'zh' ? '结论摘要' : 'Summary') + '</div>'
      inConclusion = true
      continue
    }

    if (trimmed === 'SHAP关键影响因素' || trimmed === 'SHAP Key Features') {
      closeSection()
      if (inList) { html += `</${inList}>`; inList = null }
      html += '<div style="background:rgba(100,181,246,0.10);border:1px solid rgba(100,181,246,0.2);border-radius:12px;padding:14px 16px;margin:8px 0">'
      html += '<div style="font-size:13px;font-weight:700;color:#64b5f6;margin-bottom:8px">🔬 ' + (currentLang.value === 'zh' ? 'SHAP 关键影响因素' : 'SHAP Key Features') + '</div>'
      inShap = true
      continue
    }

    if (inConclusion) {
      const hasCompat = /相容|Compatible|Incompatible/i.test(trimmed)
      const hasProb = /[概率|Prob].*[\d.]+%/.test(trimmed)
      if (hasCompat && hasProb) {
        const isCompat = /不相容|Incompatible/i.test(trimmed) ? false : true
        const bgColor = isCompat ? 'rgba(129,199,132,0.15)' : 'rgba(239,83,80,0.12)'
        const bdColor = isCompat ? 'rgba(129,199,132,0.3)' : 'rgba(239,83,80,0.25)'
        const txtColor = isCompat ? '#2e7d32' : '#c62828'
        const pairName = trimmed.split(/[：:]/)[0] || trimmed
        const verdict = isCompat ? (currentLang.value === 'zh' ? '相容' : 'Compatible') : (currentLang.value === 'zh' ? '不相容' : 'Incompatible')
        const probMatch = trimmed.match(/[\d.]+(?=%)/)
        const probVal = probMatch ? probMatch[0] : ''
        html += `<div style="display:flex;align-items:center;justify-content:space-between;background:${bgColor};border:1px solid ${bdColor};border-radius:10px;padding:10px 14px;margin:6px 0">
          <span style="font-weight:600;color:#1d1d1f;font-size:13px">${escapeHtml(pairName)}</span>
          <span style="color:${txtColor};font-weight:700;font-size:14px">${verdict}</span>
          <span style="color:#0071e3;font-weight:600;font-size:14px">${probVal}%</span>
        </div>`
        continue
      }
    }

    if (/^```/.test(line)) {
      if (inCode) {
        html += `<pre class="md-codeblock"><code>${escapeHtml(codeBuf.join('\n'))}</code></pre>`
        codeBuf = []; inCode = false
      } else {
        if (inList) { html += `</${inList}>`; inList = null }
        inCode = true; codeBuf = []
      }
      continue
    }
    if (inCode) { codeBuf.push(line); continue }

    if (line.trim() === '') {
      if (inList) { html += `</${inList}>`; inList = null }
      if (inTable) { html += '</tbody></table>'; inTable = false }
      continue
    }

    // Markdown 表格: | ... | ... |
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      if (/^\|[\s\-:]+\|[\s\-:]+\|/.test(trimmed)) {
        if (!inTable) { inTable = true; tableHeader = [] }
        continue  // skip separator row
      }
      const cells = trimmed.split('|').filter((_, i, a) => i > 0 && i < a.length - 1)
      if (!inTable) {
        inTable = true
        html += '<table class="md-table"><thead><tr>'
        for (const c of cells) html += `<th>${escapeHtml(c.trim())}</th>`
        html += '</tr></thead><tbody>'
        continue
      }
      if (inTable) {
        html += '<tr>'
        for (const c of cells) html += `<td>${fmtInline(c.trim())}</td>`
        html += '</tr>'
        continue
      }
    }
    if (inTable) { html += '</tbody></table>'; inTable = false }

    if (/^####(\s|$)/.test(line)) {
      if (inList) { html += `</${inList}>`; inList = null }
      html += `<h4 class="md-h4">${fmtInline(line.replace(/^####\s*/, ''))}</h4>`
    } else if (/^###(\s|$)/.test(line)) {
      if (inList) { html += `</${inList}>`; inList = null }
      html += `<h3 class="md-h3">${fmtInline(line.replace(/^###\s*/, ''))}</h3>`
    } else if (/^##(\s|$)/.test(line)) {
      if (inList) { html += `</${inList}>`; inList = null }
      html += `<h2 class="md-h2">${fmtInline(line.replace(/^##\s*/, ''))}</h2>`
    } else if (/^\d+\.\s/.test(line)) {
      if (inList !== 'ol') { if (inList) html += `</${inList}>`; html += '<ol class="md-list">'; inList = 'ol' }
      html += `<li>${fmtInline(line.replace(/^\d+\.\s/, ''))}</li>`
    } else if (/^[-*]\s/.test(line)) {
      if (inList !== 'ul') { if (inList) html += `</${inList}>`; html += '<ul class="md-list">'; inList = 'ul' }
      html += `<li>${fmtInline(line.replace(/^[-*]\s/, ''))}</li>`
    } else {
      if (inList) { html += `</${inList}>`; inList = null }
      html += `<p class="md-p">${fmtInline(line)}</p>`
    }
  }
  if (inCode) {
    html += `<pre class="md-codeblock"><code>${escapeHtml(codeBuf.join('\n'))}</code></pre>`
  }
  if (inList) html += `</${inList}>`
  closeSection()
  return html
}

function fmtInline(s) {
  return s
    .replace(/\*\*(.+?)\*\*/g, '<strong class="md-strong">$1</strong>')
    .replace(/`([^`]+)`/g, '<code class="md-code">$1</code>')
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, `<em class="md-p">[${currentLang.value === 'zh' ? '图片' : 'Image'}: $1]</em>`)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="md-link" data-wv-link="$2">$1</a>')
    .replace(/(?<!=")(https?:\/\/[^\s<>"\]']+)(?!["])/g, '<a href="$1" class="md-link" data-wv-link="$1" target="_blank">$1</a>')
}

function sourceIcon(type) {
  const icons = { patent: '📄', pubmed: '📚', clinical: '🏥', web: '🔗' }
  return icons[type] || '🔗'
}

let _phaseTimer = null

function handlePhaseEvent(p) {
  const phase = p.phase
  const status = p.status
  const text = p.text || ''
  expOpen.value = true

  if (phase === 0 && status === 'error') {
    expStatusText.value = '⚠️ ' + text
    expStatusClass.value = 'running'
    return
  }

  if (phase >= 1 && phase <= 5) {
    const idx = phase - 1
    if (_phaseTimer) { clearTimeout(_phaseTimer); _phaseTimer = null }

    const runStep = () => {
      expSteps.value[idx] = 'running'
      expStatusText.value = text
      expStatusClass.value = 'running'
      if (idx > 0 && expSteps.value[idx - 1] === 'running') {
        expSteps.value[idx - 1] = 'done'
      }
    }

    if (status === 'done') {
      if (expSteps.value[idx] !== 'running') {
        runStep()
      }
      _phaseTimer = setTimeout(() => {
        expSteps.value[idx] = 'done'
        if (phase === 5) {
          expStatusText.value = currentLang.value === 'zh' ? '✅ 实验方案生成完成' : '✅ Plan generated'
          expStatusClass.value = 'done'
        }
      }, phase === 5 ? 300 : 400)
    } else if (status === 'running') {
      runStep()
    }
  }
}

function handleSourceEvent(srcs) {
  if (!srcs || !srcs.length) return
  sourcesOpen.value = true
  for (const s of srcs) {
    if (!sources.value.find(x => x.url === s.url)) {
      sources.value.push(s)
    }
  }

  const typeLabel = { patent: () => t('patent_step'), literature: () => t('literature_step'), clinical: () => t('clinical_step') }
  const typeSource = { patent: 'patent', literature: 'pubmed', clinical: 'clinical' }
  const byType = {}
  for (const s of srcs) {
    const t = s.type || 'literature'
    if (!byType[t]) byType[t] = []
    if (!byType[t].find(x => x.url === s.url)) byType[t].push(s)
  }
  const cards = Object.entries(byType).map(([t, items]) => ({
    label: (typeLabel[t] || (()=>t))(),
    source: typeSource[t] || t,
    status: 'done',
    count: items.length,
    results: items.map(s => ({ title: s.title || s.url, link: s.url }))
  }))
  if (cards.length) {
    predStore.searchData = cards
  }
}

function handleWebAction(action) {
  if (!action || !action.results) return
  const type = action.source || 'literature'
  const items = action.results.map(r => ({ ...r }))
  predStore.searchResults = { ...predStore.searchResults, [type]: items }

  const labelMap = {
    patent: () => t('patent_results'),
    pubmed: () => t('literature_results'),
    clinical: () => t('clinical_results')
  }
  predStore.searchData = [
    ...(predStore.searchData || []).filter(c => c.source !== type),
    { label: (labelMap[type] || (()=>type))(), source: type, status: 'done', count: items.length, results: items.map(r => ({ title: r.title, title_cn: r.title_cn || '', link: r.link })) }
  ]
}

function resetExpProgress() {
  expSteps.value = ['pending', 'pending', 'pending', 'pending', 'pending']
  expOpen.value = false
  expStatusText.value = ''
  expStatusClass.value = ''
  sourcesOpen.value = false
  sources.value = []
  parsedOpen.value = false
  parsedTags.value = []
  predStore.searchData = []
  predStore.parsedData = []
  predStore.searchResults = { patent: [], pubmed: [], clinical: [] }
}

function showParsedFields(parsed) {
  const tags = []
  const displayName = (raw, en) => en && en !== raw ? `${raw} → ${en}` : (raw || en || '')
  if (parsed.api_name || parsed.en_api) {
    const val = displayName(parsed.api_name, parsed.en_api)
    tags.push({ label: 'API', value: val, style: 'color:#0071e3;font-weight:600' })
  }
  if (parsed.exc1_name || parsed.en_exc1) {
    const val = displayName(parsed.exc1_name, parsed.en_exc1)
    tags.push({ label: 'Excipient 1', value: val, style: 'color:#2e7d32;font-weight:600' })
  }
  if (parsed.exc2_name || parsed.en_exc2) {
    const val = displayName(parsed.exc2_name, parsed.en_exc2)
    tags.push({ label: 'Excipient 2', value: val, style: 'color:#e65100;font-weight:600' })
  }
  if (parsed.condition) tags.push({ label: 'Condition', value: parsed.condition, style: 'color:#6b6b70;font-weight:600' })
  if (parsed.days) tags.push({ label: 'Days', value: parsed.days, style: 'color:#6b6b70;font-weight:600' })
  if (tags.length) {
    parsedTags.value = tags
    parsedOpen.value = true
    predStore.parsedData = tags
  } else {
    parsedOpen.value = false
    predStore.parsedData = []
  }

  if (parsed.en_api && parsed.en_exc1) {
    predStore.pendingForm.api = parsed.en_api
    predStore.pendingForm.exc1 = parsed.en_exc1
    predStore.pendingForm.exc2 = parsed.en_exc2 || ''
    predStore.pendingForm.days = parsed.days || ''
    predStore.pendingForm.condition = parsed.condition || ''
    predStore.pendingForm.trigger = true
  }
}

async function sendChat() {
  const q = inputText.value.trim()
  if (!q || store.streaming) return
  inputText.value = ''
  resetExpProgress()

  store.addMessage('user', q)
  store.streaming = true
  store.addMessage('assistant', '...')

  try {
    const resp = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: q,
        skill: currentSkill.value,
        ...(store.pageContent?.url ? {
          page_url: store.pageContent.url,
          page_content: store.pageContent.text,
        } : {}),
        ...getApiConfig()
      })
    })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let fullText = ''
    let buffer = ''
    // SSE timeout: 180s without data = abort (实验设计需更多时间)
    let sseTimer = setTimeout(() => {
      reader.cancel()
      if (!fullText) {
        fullText = currentLang.value === 'zh'
          ? '⏱ 请求超时，请稍后重试。长时间无响应可' + '▶ 点击重试'
          : '⏱ Request timeout. ' + '▶ Click to retry'
      }
    }, 180000)
    while (true) {
      let chunk
      try {
        const result = await reader.read()
        if (result.done) { clearTimeout(sseTimer); break }
        chunk = result
      } catch { clearTimeout(sseTimer); break }
      clearTimeout(sseTimer)
      sseTimer = setTimeout(() => {
        reader.cancel()
        if (!fullText) {
          fullText = currentLang.value === 'zh'
            ? '⏱ 请求超时，请稍后重试。长时间无响应可▶ 点击重试'
            : '⏱ Request timeout. ▶ Click to retry'
        }
      }, 180000)
      buffer += decoder.decode(chunk.value, { stream: true })
      let idx
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const msg = buffer.slice(0, idx)
        buffer = buffer.slice(idx + 2)
        for (const line of msg.split('\n')) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.skill) {
                // 自动模式检测到任务类型，切换 skill（不清除对话）
                if (currentSkill.value === 'auto' && data.skill !== 'auto') {
                  store.switchSkill(data.skill)
                }
              }
              if (data.c) {
                fullText += data.c
                store.messages[store.messages.length - 1].content = fullText
              }
              if (data.p) handlePhaseEvent(data.p)
              if (data.src) handleSourceEvent(data.src)
              if (data.w) handleWebAction(data.w)
              if (data.parsed && data.parsed.en_api && data.parsed.en_exc1) {
                predStore.pendingForm.api = data.parsed.en_api
                predStore.pendingForm.exc1 = data.parsed.en_exc1
                predStore.pendingForm.exc2 = data.parsed.en_exc2 || ''
                predStore.pendingForm.condition = data.parsed.condition || ''
                predStore.pendingForm.days = data.parsed.days || ''
                predStore.pendingForm.trigger = true
              }
              if (data.p) handlePhaseEvent(data.p)
              if (data.src) handleSourceEvent(data.src)
              if (data.w) handleWebAction(data.w)
              if (data.parsed) showParsedFields(data.parsed)
              if (data.parsed) {
              }
            } catch (e) {}
          }
        }
      }
    }
    if (!fullText) fullText = t('empty_reply')
    const linkSections = []
    for (const [type, items] of Object.entries(predStore.searchResults || {})) {
        if (items && items.length) {
          const typeLabelMap = { patent: () => t('patent_results'), pubmed: () => t('literature_results'), clinical: () => t('clinical_results') }
          const label = (typeLabelMap[type] || (() => type))()
          const links = items.map(r => `- [${r.title || r.link}](${r.link})`).join('\n')
          linkSections.push(`### ${label}\n${links}`)
        }
      }
    if (linkSections.length) {
      const sep = currentLang.value === 'zh' ? '\n\n---\n### 📎 参考来源\n' : '\n\n---\n### 📎 References\n'
      fullText += sep + linkSections.join('\n\n')
    }
    store.messages[store.messages.length - 1].content = fullText
    store.saveToHistory()
    // Save to backend
    fetch('/api/chat/save-history', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: store.messages, skill: currentSkill.value })
    }).catch(() => {})
  } catch (e) {
    store.messages[store.messages.length - 1].content = `${currentLang.value === 'zh' ? '请求失败' : 'Request failed'}: ${e.message}`
    store.messages[store.messages.length - 1].role = 'error'
  } finally {
    store.streaming = false
    scrollToBottom()
  }
}

function retryLastMessage(m) {
  if (!m.content.includes('点击重试') && !m.content.includes('Click to retry')) {
    downloadDocx(m.content)
    return
  }
  // 找到上一条用户消息
  const msgs = store.messages
  for (let i = msgs.length - 2; i >= 0; i--) {
    if (msgs[i].role === 'user') {
      // 移除超时消息 + 用户消息
      store.messages.splice(i)
      inputText.value = msgs[i].content
      // 自动发送
      setTimeout(() => sendChat(), 100)
      return
    }
  }
}

async function downloadDocx(content) {
  try {
    const resp = await fetch('/api/chat/export-docx', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: t('export_title'),
        api_name: document.querySelector('#api')?.value || t('export_unknown_api'),
        exc1_name: document.querySelector('#exc1')?.value || t('export_unknown_exc'),
        exc2_name: document.querySelector('#exc2')?.value || '',
        content
      })
    })
    if (!resp.ok) throw new Error(t('export_error'))
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const nameParts = [document.querySelector('#api')?.value || 'API', document.querySelector('#exc1')?.value || 'Excipient']
    if (document.querySelector('#exc2')?.value) nameParts.push(document.querySelector('#exc2')?.value)
    a.download = `${nameParts.join('+')}_${t('export_title')}_${new Date().toISOString().slice(0, 10)}.docx`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert(e.message)
  }
}


function newChat() {
  store.streaming = false
  predStore.clear()
  resetExpProgress()
  showHistory.value = false
  sources.value = []
  sourcesOpen.value = false
  parsedOpen.value = false
  store.messages = []
  const skillId = store.currentSkill
  const key = `skill_intro_${skillId}`
  const hint = currentLang.value === 'zh' ? LOCALE.zh[key] : LOCALE.en[key]
  nextTick(() => {
    store.addMessage('assistant', hint || t('welcome_msg'))
    scrollToBottom()
  })
}

function switchSkill(skillId) {
  store.switchSkill(skillId)
  store.streaming = false
  predStore.clear()
  resetExpProgress()
  showHistory.value = false
  sources.value = []
  sourcesOpen.value = false
  parsedOpen.value = false
  store.messages = []
  const key = `skill_intro_${skillId}`
  const hint = currentLang.value === 'zh' ? LOCALE.zh[key] : LOCALE.en[key]
  nextTick(() => {
    store.addMessage('assistant', hint || t('welcome_msg'))
    scrollToBottom()
  })

}

function loadHistory(id) {
  store.loadHistoryItem(id)
  showHistory.value = false
}

function saveApiSettings() {
  localStorage.setItem('ds_api_key', apiKey.value.trim())
  localStorage.setItem('ds_api_url', apiUrl.value.trim())
  localStorage.setItem('ds_model', apiModel.value.trim())
  showApiSettings.value = false
  store.addMessage('assistant', t('api_saved'))
}

function getApiConfig() {
  return {
    api_key: localStorage.getItem('ds_api_key') || undefined,
    api_url: localStorage.getItem('ds_api_url') || undefined,
    model: localStorage.getItem('ds_model') || undefined
  }
}

function onChatClick(e) {
  const link = e.target.closest('[data-wv-link]')
  if (link) {
    e.preventDefault()
    const url = link.getAttribute('data-wv-link')
    emit('navigate', url)
    window.open(url, '_blank')
  }
}

function onKeydown(e) {
}

function scrollToBottom() {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}

// ── Feedback ──

</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.sidebar-header {
  padding: 10px 16px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  flex-shrink: 0;
}
.sidebar-header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sidebar-user {
  font-size: 11px;
  color: #86868b;
  margin-top: 2px;
  padding-left: 1px;
}
.sidebar-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0;
}
.sidebar-close {
  background: none;
  border: none;
  color: #86868b;
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  line-height: 1;
  border-radius: 6px;
  transition: background .2s, color .2s;
}
.sidebar-close:hover {
  color: #1d1d1f;
  background: rgba(0,0,0,0.06);
}
.api-settings {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  display: none;
}
.api-settings.open {
  display: block;
}
.api-settings-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.api-settings-row label {
  flex: 0 0 50px;
  font-size: 11px;
  color: #86868b;
  margin: 0;
}
.api-settings-row input {
  flex: 1;
  background: rgba(245,245,247,0.7);
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 8px;
  padding: 6px 10px;
  color: #1d1d1f;
  font-size: 12px;
  outline: none;
  backdrop-filter: blur(8px);
}
.api-settings-row input:focus {
  border-color: #0071e3;
}
.api-settings-save {
  padding: 5px 14px;
  background: #34c759;
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  width: 100%;
  margin-top: 4px;
}
.api-settings-save:hover {
  opacity: .9;
}
.exp-progress {
  display: none;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  background: rgba(245,245,247,0.4);
}
.exp-progress.open {
  display: block;
}
.exp-steps {
  display: flex;
  gap: 0;
  position: relative;
  margin: 8px 0;
}
.exp-step {
  flex: 1;
  text-align: center;
  position: relative;
}
.exp-step-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 4px;
  font-size: 11px;
  font-weight: 600;
  transition: all .3s;
  border: 2px solid rgba(0,0,0,0.1);
  background: rgba(255,255,255,0.6);
  color: #aeaeb2;
}
.exp-step.done .exp-step-dot {
  background: #34c759;
  border-color: #34c759;
  color: #fff;
}
.exp-step.running .exp-step-dot {
  background: #0071e3;
  border-color: #0071e3;
  color: #fff;
  animation: pulse-dot 1.2s ease-in-out infinite;
}
.exp-step.pending .exp-step-dot {
  background: rgba(255,255,255,0.6);
  border-color: rgba(0,0,0,0.1);
  color: #aeaeb2;
}
.exp-step-label {
  font-size: 10px;
  color: #86868b;
  line-height: 1.2;
  max-width: 80px;
  margin: 0 auto;
}
.exp-step.done .exp-step-label {
  color: #34c759;
}
.exp-step.running .exp-step-label {
  color: #0071e3;
  font-weight: 500;
}
.exp-connector {
  position: absolute;
  top: 12px;
  left: calc(50% + 14px);
  right: calc(-50% + 14px);
  height: 2px;
  background: rgba(0,0,0,0.08);
  z-index: 0;
}
:deep(.exp-step.done + .exp-step .exp-connector),
:deep(.exp-step.done .exp-connector) {
  background: #34c759;
}
.exp-step.running + .exp-step .exp-connector {
  background: linear-gradient(90deg, #0071e3 0%, rgba(0,0,0,0.08) 100%);
}
@keyframes pulse-dot {
  0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(0,113,227,0.4); }
  50% { transform: scale(1.1); box-shadow: 0 0 0 6px rgba(0,113,227,0); }
}
.exp-status-text {
  font-size: 11px;
  color: #86868b;
  text-align: center;
  padding: 4px 0 0;
  min-height: 18px;
}
.exp-status-text.running {
  color: #0071e3;
}
.exp-status-text.done {
  color: #34c759;
}
.exp-sources {
  display: none;
  padding: 8px 16px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  background: rgba(245,245,247,0.3);
  max-height: 120px;
  overflow-y: auto;
}
.exp-sources.open {
  display: block;
}
.exp-sources-title {
  font-size: 11px;
  font-weight: 600;
  color: #86868b;
  margin-bottom: 4px;
}
.exp-source-item {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding: 2px 0;
  font-size: 11px;
  color: #6b6b70;
  line-height: 1.3;
}
.exp-source-icon {
  flex-shrink: 0;
  font-size: 10px;
  width: 16px;
  text-align: center;
}
.exp-source-link {
  color: #0071e3;
  text-decoration: none;
  word-break: break-all;
}
.exp-source-link:hover {
  text-decoration: underline;
}
.chat-parsed {
  display: none;
  padding: 8px 16px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  background: rgba(245,245,247,0.6);
  font-size: 12px;
  backdrop-filter: blur(8px);
  transition: background .2s;
}
.chat-parsed.open {
  display: block;
}
.chat-parsed:hover {
  background: rgba(245,245,247,0.85);
}
.chat-parsed-title {
  color: #34c759;
  font-weight: 600;
  margin-bottom: 3px;
}
.chat-parsed-content {
  display: flex;
  flex-wrap: wrap;
  gap: 3px 10px;
  color: #6b6b70;
}
.chat-msgs {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}
.chat-msg {
  margin-bottom: 12px;
  animation: fadeIn .25s;
}
.chat-msg.user {
  text-align: right;
}
.chat-msg.assistant {
  text-align: left;
}
.chat-msg.error {
  text-align: left;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
}

/* ── New Chat transition ── */
.msg-enter-active {
  transition: all 0.45s cubic-bezier(.25,.1,.25,1);
}
.msg-leave-active {
  transition: all 0.3s cubic-bezier(.4,0,.2,1);
  position: absolute;
  right: 0; left: 0;
}
.msg-move {
  transition: transform 0.3s ease;
}
.msg-enter-from {
  opacity: 0;
  transform: translateY(24px);
}
.msg-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}
.chat-bubble {
  display: inline-block;
  max-width: 90%;
  padding: 8px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
  text-align: left;
  white-space: pre-wrap;
  word-break: break-word;
}
.chat-msg.user .chat-bubble {
  background: rgba(0,113,227,0.85);
  color: #fff;
  border-bottom-right-radius: 3px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.15);
}
.chat-msg.assistant .chat-bubble {
  background: rgba(255,255,255,0.75);
  color: #1d1d1f;
  border-bottom-left-radius: 3px;
  border: 1px solid rgba(255,255,255,0.5);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.chat-msg.error .chat-bubble {
  background: rgba(255,235,238,0.8);
  color: #c62828;
  border: 1px solid rgba(239,154,154,0.5);
  backdrop-filter: blur(12px);
}
.chat-loading {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 4px 0;
}
.chat-loading .dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #0071e3;
  animation: typing 1.4s infinite ease-in-out both;
}
.chat-loading .dot:nth-child(1) { animation-delay: 0s; }
.chat-loading .dot:nth-child(2) { animation-delay: .16s; }
.chat-loading .dot:nth-child(3) { animation-delay: .32s; }
@keyframes typing {
  0%, 80%, 100% { opacity: .3; transform: scale(.7); }
  40% { opacity: 1; transform: scale(1); }
}
.dl-btn {
  display: inline-block;
  margin-top: 10px;
  padding: 6px 14px;
  font-size: 12px;
  cursor: pointer;
  border-radius: 8px;
  background: rgba(0,113,227,0.08);
  color: #0071e3;
  transition: background .2s;
  user-select: none;
}
.dl-btn:hover {
  background: rgba(0,113,227,0.15);
}
.retry-btn {
  background: rgba(255,152,0,0.12);
  color: #e65100;
  font-weight: 600;
}
.retry-btn:hover {
  background: rgba(255,152,0,0.22);
}
.skill-bar {
  display: flex;
  gap: 4px;
  padding: 6px 12px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  overflow-x: auto;
  flex-shrink: 0;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
}
.skill-bar::-webkit-scrollbar { display: none; }
.skill-pill {
  flex-shrink: 0;
  padding: 3px 8px;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 12px;
  background: rgba(255,255,255,0.6);
  color: #6b6b70;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all .2s;
  white-space: nowrap;
  line-height: 1.4;
}
.skill-pill:hover {
  background: rgba(0,113,227,0.08);
  border-color: rgba(0,113,227,0.2);
  color: #0071e3;
}
.skill-pill.active {
  background: #0071e3;
  border-color: #0071e3;
  color: #fff;
}
.chat-hint {
  font-size: 11px;
  color: #aeaeb2;
  padding: 4px 16px 0;
}

.chat-input-wrap {
  display: flex;
  gap: 6px;
  padding: 12px 16px;
  border-top: 1px solid rgba(0,0,0,0.06);
  flex-shrink: 0;
}
.chat-input-wrap textarea {
  flex: 1;
  padding: 6px 10px;
  background: rgba(245,245,247,0.7);
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 10px;
  color: #1d1d1f;
  font-size: 13px;
  outline: none;
  resize: none;
  min-height: 30px;
  max-height: 80px;
  font-family: inherit;
  line-height: 1.3;
  backdrop-filter: blur(8px);
}
.chat-input-wrap textarea:focus {
  border-color: #0071e3;
}
.chat-input-wrap textarea::placeholder {
  font-size: 10px;
  color: #aeaeb2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.chat-input-wrap button {
  padding: 8px 16px;
  background: #0071e3;
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all .25s;
}
.chat-input-wrap button:hover {
  background: #0077ed;
  box-shadow: 0 3px 10px rgba(0,113,227,0.2);
}
.chat-input-wrap button:active {
  transform: scale(.97);
}
.chat-input-wrap button:disabled {
  opacity: .5;
  cursor: not-allowed;
  transform: none;
}
:deep(.md-h2) {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 10px 0 4px;
  line-height: 1.3;
}
:deep(.md-h3) {
  font-size: 13px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 8px 0 3px;
  line-height: 1.3;
}
:deep(.md-h4) {
  font-size: 12px;
  font-weight: 600;
  color: #0071e3;
  margin: 6px 0 2px;
  line-height: 1.3;
}
:deep(.md-codeblock) {
  background: rgba(245,245,247,0.8);
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 10px;
  padding: 10px;
  margin: 6px 0;
  overflow-x: auto;
  font-size: 12px;
  color: #1d1d1f;
  line-height: 1.5;
  backdrop-filter: blur(8px);
}
:deep(.md-strong) {
  font-weight: 600;
}
:deep(.md-code) {
  background: rgba(245,245,247,0.8);
  padding: 1px 5px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  color: #c62828;
}
:deep(.md-link) {
  color: #0071e3;
  text-decoration: none;
  font-weight: 500;
}
:deep(.md-link):hover {
  text-decoration: underline;
}
:deep(.md-list) {
  margin: 3px 0;
  padding-left: 16px;
}
:deep(.md-list li) {
  margin: 2px 0;
}
:deep(.md-table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 12px;
  line-height: 1.5;
}
:deep(.md-table th) {
  background: rgba(0,0,0,0.04);
  font-weight: 600;
  padding: 6px 10px;
  text-align: left;
  border: 1px solid rgba(0,0,0,0.08);
  color: #1d1d1f;
}
:deep(.md-table td) {
  padding: 6px 10px;
  border: 1px solid rgba(0,0,0,0.06);
  color: #3a3a3c;
}
:deep(.md-table tr:nth-child(even)) {
  background: rgba(0,0,0,0.02);
}
:deep(.md-list li) {
  margin: 2px 0;
  line-height: 1.5;
}
:deep(.md-p) {
  margin: 3px 0;
  line-height: 1.6;
}

/* ── Feedback Button & Modal ── */
.sidebar-footer {
  flex-shrink: 0;
  padding: 6px 16px 10px;
  border-top: 1px solid rgba(0,0,0,0.04);
  text-align: center;
}
</style>
