<template>
  <div>
    <div v-if="title" style="font-size:13px;font-weight:600;color:#1d1d1f;margin-bottom:12px;text-align:center">{{ title }}</div>
    <div class="result-grid">
      <div class="result-card">
        <div class="lbl">{{ t('pred_lbl') }}</div>
        <div class="val" :style="{ color: isCompat ? '#2e7d32' : '#c62828', fontSize: '20px' }">
          {{ isCompat ? t('compatible') : t('incompatible') }}
        </div>
      </div>
      <div class="result-card">
        <div class="lbl">{{ t('prob_lbl') }}</div>
        <div class="val" style="color:#0071e3">{{ (data.prob * 100).toFixed(1) }}%</div>
      </div>
      <div class="result-card">
        <div class="lbl">{{ t('risk_lbl') }}</div>
        <div><span :class="'badge ' + badgeClass">{{ riskLabel }}</span></div>
      </div>
      <div class="result-card" v-if="data.impurity_count !== undefined">
        <div class="lbl">{{ t('count_lbl') }}</div>
        <div class="val" style="font-size:24px;color:#1d1d1f">{{ Math.round(data.impurity_count) }}</div>
      </div>
      <div class="result-card" v-if="data.total_impurity_pct !== undefined">
        <div class="lbl">{{ t('total_lbl') }}</div>
        <div class="val" style="font-size:24px;color:#1d1d1f">{{ fmtPct(data.total_impurity_pct) }}</div>
      </div>
      <div class="result-card" v-if="data.max_single_impurity_pct !== undefined">
        <div class="lbl">{{ t('max_lbl') }}</div>
        <div class="val" style="font-size:24px;color:#1d1d1f">{{ fmtPct(data.max_single_impurity_pct) }}</div>
      </div>
      <div class="result-card" v-if="data.smarts_matches !== undefined">
        <div class="lbl">{{ t('smarts_lbl') }}</div>
        <div class="val" :style="{ fontSize: '22px', color: data.smarts_matches > 0 ? '#c62828' : '#2e7d32' }">
          {{ data.smarts_matches }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { t } from '../i18n'

const props = defineProps({
  data: Object,
  title: String
})

const isCompat = computed(() => props.data.prob < 0.5)

const badgeClass = computed(() => {
  const map = { low: 'badge-low', medium: 'badge-medium', high: 'badge-high' }
  return map[props.data.level] || 'badge-low'
})

function fmtPct(v) {
  v = Number(v) || 0
  if (v >= 1) return v.toFixed(2) + '%'
  if (v >= 0.001) return v.toFixed(4) + '%'
  return v.toFixed(6) + '%'
}

const riskLabel = computed(() => {
  const map = {
    low: t('low_risk'),
    medium: t('medium_risk'),
    high: t('high_risk')
  }
  return map[props.data.level] || props.data.level
})
</script>

<style scoped>
.result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
}
.result-card {
  background: rgba(255,255,255,0.6);
  border-radius: 12px;
  padding: 18px;
  text-align: center;
  border: 1px solid rgba(255,255,255,0.6);
  backdrop-filter: blur(12px);
  transition: background .25s, box-shadow .25s, transform .25s;
}
.result-card:hover {
  background: rgba(255,255,255,0.85);
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  transform: translateY(-2px);
}
.result-card .val {
  font-size: 28px;
  font-weight: 600;
  margin: 6px 0;
}
.result-card .lbl {
  font-size: 12px;
  color: #86868b;
}
.badge {
  display: inline-block;
  padding: 4px 16px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
}
.badge-low {
  background: rgba(232,245,233,0.8);
  color: #2e7d32;
  border: 1px solid rgba(165,214,167,0.5);
}
.badge-medium {
  background: rgba(255,248,225,0.8);
  color: #f57f17;
  border: 1px solid rgba(255,224,130,0.5);
}
.badge-high {
  background: rgba(255,235,238,0.8);
  color: #c62828;
  border: 1px solid rgba(239,154,154,0.5);
}
</style>
