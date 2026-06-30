<template>
  <div v-if="show" class="card">
    <div v-if="predStore.parsedData && predStore.parsedData.length" class="parsed-section">
      <h2>{{ t('parsed_title') }}</h2>
      <div class="parsed-tags">
        <span v-for="(tag, i) in predStore.parsedData" :key="i" :style="tag.style" class="parsed-tag">
          {{ tag.label }}: {{ tag.value }}
        </span>
      </div>
    </div>

    <h2>🔍 {{ t('search_title') }}</h2>

    <div v-for="(card, ci) in searchCards" :key="ci" class="sp-card">
      <div class="sp-header">
        <div class="sp-label">{{ card.label }}</div>
          <div v-if="card.count" class="sp-count">{{ card.count }} {{ t('count_suffix') }}</div>
      </div>

      <div v-if="card.results && card.results.length" class="sp-results">
        <div v-for="(r, ri) in card.results" :key="ri" class="sp-item">
          <div class="sp-item-head">
            <div class="sp-item-title">
              <a :href="r.link" :data-wv-link="r.link" target="_blank" rel="noopener" @click="openLink(r.link, $event)">{{ itemIsZh(ci, ri) && r.title_cn ? r.title_cn : r.title }}</a>
            </div>
            <button class="sp-lang-btn" @click="toggleItemLang(ci, ri)" :title="itemIsZh(ci, ri) ? 'EN' : '中'">
              {{ itemIsZh(ci, ri) ? '中' : 'EN' }}
            </button>
          </div>

          <div v-if="card.source === 'patent'" class="sp-item-meta">
            <span v-if="r.patent_id" class="meta-tag">{{ label('patent_id', ci, ri) }}{{ sep(ci, ri) }}{{ r.patent_id }}</span>
            <span v-if="r.country" class="meta-tag flag">{{ countryFlag(r.country) }} {{ label('country_label', ci, ri) }}{{ sep(ci, ri) }}{{ r.country }}</span>
            <span v-if="r.year" class="meta-tag">{{ label('year', ci, ri) }}{{ sep(ci, ri) }}{{ r.year }}</span>
            <span v-if="r.inventor" class="meta-tag">{{ label('inventor', ci, ri) }}{{ sep(ci, ri) }}{{ r.inventor }}</span>
          </div>

          <div v-else-if="card.source === 'pubmed'" class="sp-item-meta">
            <span v-if="r.source" class="meta-tag">{{ label('source_article', ci, ri) }}{{ sep(ci, ri) }}{{ r.source }}</span>
            <span v-if="r.date" class="meta-tag">{{ label('date', ci, ri) }}{{ sep(ci, ri) }}{{ r.date }}</span>
            <span v-if="r.pmid" class="meta-tag">{{ label('pmid_label', ci, ri) }}{{ sep(ci, ri) }}{{ r.pmid }}</span>
          </div>

          <div v-else-if="card.source === 'clinical'" class="sp-item-meta">
            <span v-if="r.nct" class="meta-tag">{{ label('nct_label', ci, ri) }}{{ sep(ci, ri) }}{{ r.nct }}</span>
            <span v-if="r.phase" class="meta-tag">{{ label('phase_label', ci, ri) }}{{ sep(ci, ri) }}{{ r.phase }}</span>
            <span v-if="r.status" class="meta-tag">{{ label('status_label', ci, ri) }}{{ sep(ci, ri) }}{{ r.status }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { usePredictionStore } from '../stores/prediction'
import { currentLang, t, LOCALE } from '../i18n'

const emit = defineEmits(['navigate'])

function openLink(url, event) {
  emit('navigate', url)
}

function countryFlag(code) {
  if (!code || code.length !== 2) return ''
  return [...code.toUpperCase()].map(c => String.fromCodePoint(0x1F1E6 + c.charCodeAt(0) - 65)).join('')
}

function sep(ci, ri) { return (ci !== undefined ? itemIsZh(ci, ri) : currentLang.value === 'zh') ? '：' : ': ' }

const predStore = usePredictionStore()
const show = ref(false)
const searchCards = ref([])
const itemLangZh = ref(new Map())  // key: "ci-ri" → boolean (true=show Chinese labels)

function itemKey(ci, ri) { return `${ci}-${ri}` }
function itemIsZh(ci, ri) { return itemLangZh.value.get(itemKey(ci, ri)) ?? false }
function toggleItemLang(ci, ri) {
  const k = itemKey(ci, ri)
  const cur = itemLangZh.value.get(k)
  itemLangZh.value.set(k, !(cur ?? (currentLang.value === 'zh')))
  itemLangZh.value = new Map(itemLangZh.value)  // trigger reactivity
}
function label(key, ci, ri) {
  const isZh = ci !== undefined ? itemIsZh(ci, ri) : currentLang.value === 'zh'
  const zhLbl = LOCALE.zh[key]
  const enLbl = LOCALE.en[key]
  return isZh ? (zhLbl || enLbl || key) : (enLbl || zhLbl || key)
}

function rebuildCards() {
  const cards = []
  const data = predStore.searchData || []
  const results = predStore.searchResults || { patent: [], pubmed: [], clinical: [] }

  for (const d of data) {
    const src = d.source || ''
    const richResults = (results[src] || []).map(r => ({ ...r }))
    cards.push({
      label: d.label || src,
      source: src,
      status: d.status || 'done',
      count: d.count || richResults.length || 0,
      results: richResults.length ? richResults : (d.results || [])
    })
  }

  if (cards.length) {
    searchCards.value = cards
    show.value = true
  } else {
    searchCards.value = []
    show.value = false
  }
}

watch(() => predStore.searchData, rebuildCards, { deep: true })
watch(() => predStore.searchResults, rebuildCards, { deep: true })
watch(() => predStore.parsedData, (data) => {
  if (data && data.length) show.value = true
}, { deep: true })

watch(() => predStore.result, (res) => {
  if (!res) {
    if (!predStore.searchData.length) { show.value = false; searchCards.value = [] }
    return
  }
  if (res.search_data) rebuildCards()
}, { deep: true })
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
.parsed-section {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
}
.parsed-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.parsed-tag {
  background: rgba(245,245,247,0.7);
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 12px;
}
.sp-card {
  background: rgba(245,245,247,0.5);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 10px;
  border: 1px solid rgba(255,255,255,0.3);
  backdrop-filter: blur(8px);
}
.sp-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.sp-label {
  font-size: 13px;
  font-weight: 600;
  color: #1d1d1f;
}
.sp-count {
  font-size: 11px;
  color: #86868b;
  background: rgba(0,0,0,0.05);
  padding: 1px 8px;
  border-radius: 10px;
}
.sp-results {
  margin-top: 6px;
}
.sp-item {
  font-size: 12px;
  padding: 6px 0;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}
.sp-item:last-child { border-bottom: none; }
.sp-item-head {
  display: flex;
  align-items: center;
  gap: 6px;
}
.sp-item-title {
  flex: 1;
  min-width: 0;
}
.sp-item-title a {
  color: #0071e3;
  text-decoration: none;
  font-weight: 500;
}
.sp-item-title a:hover { text-decoration: underline; }
.sp-lang-btn {
  flex-shrink: 0;
  width: 28px;
  height: 18px;
  padding: 0;
  border: 1px solid rgba(0,0,0,0.12);
  border-radius: 4px;
  background: rgba(255,255,255,0.6);
  color: #6b6b70;
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
  transition: all .2s;
  line-height: 18px;
  text-align: center;
}
.sp-lang-btn:hover {
  background: #0071e3;
  border-color: #0071e3;
  color: #fff;
}
.sp-item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}
.meta-tag {
  font-size: 10px;
  color: #6b6b70;
  background: rgba(0,0,0,0.04);
  padding: 1px 6px;
  border-radius: 4px;
}
.meta-tag.flag {
  font-size: 12px;
  line-height: 1;
}
</style>
