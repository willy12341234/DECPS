<template>
  <div class="history-panel">
    <div class="h-header">
      <span>{{ t('sidebar_title') }} · {{ t('history_title') }}</span>
      <button class="h-btn" @click="exportAll" :title="t('export_all')">📥</button>
    </div>
    <div class="h-list">
      <div v-if="!histories.length" class="h-empty">{{ t('history_none') }}</div>
      <div v-for="h in histories" :key="h.id" class="h-item" @click="$emit('load', h.id)">
        <div class="h-preview">
          <span v-if="h.skill" class="h-skill">{{ skillLabel(h.skill) }}</span>
          <span class="h-text">{{ h.preview }}</span>
          <button class="h-del" @click.stop="$emit('delete', h.id)">✕</button>
        </div>
        <div class="h-time">{{ h.time }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { currentLang, t, LOCALE } from '../i18n'

const props = defineProps({
  histories: Array
})

const emit = defineEmits(['load', 'delete'])

function skillLabel(skillId) {
  const key = `skill_${skillId}`
  return currentLang.value === 'zh' ? (LOCALE.zh[key] || skillId) : (LOCALE.en[key] || skillId)
}

function exportAll() {
  const data = JSON.stringify({ histories: arguments[0] }, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `chat_history_${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.history-panel {
  border-bottom: 1px solid rgba(0,0,0,0.06);
  max-height: 250px;
  overflow-y: auto;
  background: rgba(245,245,247,0.6);
}
.h-header {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  color: #1d1d1f;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}
.h-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: #86868b;
  transition: color .2s;
}
.h-btn:hover {
  color: #0071e3;
}
.h-empty {
  padding: 20px;
  text-align: center;
  font-size: 12px;
  color: #86868b;
}
.h-item {
  padding: 8px 12px;
  cursor: pointer;
  font-size: 12px;
  border-bottom: 1px solid rgba(0,0,0,0.03);
  transition: background .2s;
}
.h-item:hover {
  background: rgba(0,113,227,0.06);
}
.h-preview {
  font-weight: 500;
  color: #1d1d1f;
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}
.h-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  flex: 1;
}
.h-skill {
  flex-shrink: 0;
  font-size: 9px;
  font-weight: 600;
  color: #fff;
  background: #0071e3;
  border-radius: 4px;
  padding: 1px 5px;
  line-height: 1.4;
}
.h-del {
  margin-left: auto;
  background: rgba(0,0,0,0.03);
  border: 1px solid rgba(0,0,0,0.06);
  color: #999;
  cursor: pointer;
  font-size: 12px;
  min-width: 22px;
  height: 22px;
  padding: 0;
  border-radius: 4px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all .2s;
}
.h-del:hover {
  color: #c62828;
  background: rgba(198,40,40,0.1);
  border-color: rgba(198,40,40,0.2);
}
.h-del:hover {
  color: #c62828;
}
.h-time {
  font-size: 10px;
  color: #86868b;
  margin-top: 2px;
}
</style>
