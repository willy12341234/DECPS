<template>
  <div class="webview-card">
    <div class="wv-header">
      <div class="wv-addr-bar">
        <span class="wv-addr-icon">🔗</span>
        <input
          v-model="inputUrl"
          class="wv-addr-input"
          :placeholder="t('wv_addr_placeholder')"
          @keydown.enter="navigateTo(inputUrl)"
        />
        <button class="wv-open-btn" :title="t('wv_open_new')" @click="openNewTab">↗</button>
      </div>
    </div>

    <div v-if="!currentUrl" class="wv-empty">
      <div class="wv-empty-icon">🔗</div>
      <p class="wv-empty-title">{{ t('wv_empty_title') }}</p>
      <p class="wv-empty-desc">{{ t('wv_empty_desc') }}</p>
    </div>

    <div v-else-if="loading" class="wv-loading">
      <div class="wv-spinner"></div>
      <p>{{ t('wv_loading') }}</p>
    </div>

    <div v-else class="wv-iframe-wrap">
      <iframe
        ref="iframeRef"
        :src="proxyUrl"
        class="wv-iframe"
        frameborder="0"
      ></iframe>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { t } from '../i18n'
import { useChatStore } from '../stores/chat'

const props = defineProps({
  url: { type: String, default: '' }
})
const emit = defineEmits(['navigate'])

const store = useChatStore()
const inputUrl = ref('')
const currentUrl = ref('')
const iframeRef = ref(null)
const loading = ref(false)
let loadTimer = null

const proxyUrl = computed(() => {
  if (!currentUrl.value) return ''
  return '/api/proxy-page?url=' + encodeURIComponent(currentUrl.value)
})

watch(() => props.url, (val) => {
  if (val) navigateTo(val)
})

function navigateTo(url) {
  if (!url) return
  let finalUrl = url.trim()
  if (!/^https?:\/\//i.test(finalUrl)) finalUrl = 'https://' + finalUrl
  inputUrl.value = finalUrl
  currentUrl.value = finalUrl
  loading.value = true
  if (loadTimer) clearTimeout(loadTimer)
  loadTimer = setTimeout(() => { loading.value = false }, 8000)

  fetchPageText(finalUrl)
}

async function fetchPageText(url) {
  try {
    const r = await fetch('/api/fetch-page', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    })
    if (r.ok) {
      const d = await r.json()
      if (d.content) {
        store.pageContent = { url, title: d.title || url, text: d.content.slice(0, 10000) }
      }
    }
  } catch {}
}

function openNewTab() {
  if (currentUrl.value) window.open(currentUrl.value, '_blank')
}

function onMessage(e) {
  if (e.data?.type === 'wv-navigate') {
    navigateTo(e.data.url)
  }
}

onMounted(() => window.addEventListener('message', onMessage))
onBeforeUnmount(() => window.removeEventListener('message', onMessage))
</script>

<style scoped>
.webview-card {
  background: rgba(255,255,255,0.72);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255,255,255,0.5);
  border-radius: 16px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.02);
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.wv-header {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  flex-shrink: 0;
}
.wv-addr-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(245,245,247,0.7);
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 10px;
  padding: 4px 10px;
}
.wv-addr-icon { font-size: 13px; flex-shrink: 0; }
.wv-addr-input {
  flex: 1;
  border: none;
  background: none;
  font-size: 12px;
  color: #1d1d1f;
  outline: none;
  font-family: monospace;
}
.wv-addr-input::placeholder { color: #aeaeb2; }
.wv-open-btn {
  flex-shrink: 0;
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #86868b;
  padding: 2px 4px;
  border-radius: 4px;
  transition: all .2s;
}
.wv-open-btn:hover { color: #0071e3; background: rgba(0,113,227,0.08); }
.wv-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}
.wv-empty-icon { font-size: 40px; margin-bottom: 12px; opacity: .5; }
.wv-empty-title { font-size: 15px; font-weight: 600; color: #1d1d1f; margin: 0 0 6px; }
.wv-empty-desc { font-size: 12px; color: #86868b; margin: 0; line-height: 1.6; }
.wv-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  font-size: 13px;
  color: #86868b;
}
.wv-spinner {
  width: 28px; height: 28px;
  border: 3px solid rgba(0,0,0,0.06);
  border-top-color: #0071e3;
  border-radius: 50%;
  animation: wvSpin .7s linear infinite;
}
@keyframes wvSpin { to { transform: rotate(360deg); } }
.wv-iframe-wrap {
  flex: 1;
  position: relative;
}
.wv-iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>
