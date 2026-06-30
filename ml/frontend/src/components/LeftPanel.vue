<template>
  <div class="card">
    <h2>{{ t('input_title') }}</h2>
    <div class="form-stack">
      <div class="row row-3">
        <div class="field">
          <label>{{ t('api_label') }}</label>
          <input id="api" v-model="api" :placeholder="t('api_label') + '...'">
        </div>
        <div class="field">
          <label>{{ t('exc1_label') }}</label>
          <input id="exc1" v-model="exc1" :placeholder="t('exc1_label') + '...'">
        </div>
        <div class="field">
          <label>{{ t('exc2_label') }}</label>
          <input v-model="exc2" placeholder="Optional">
        </div>
      </div>
      <div class="row row-2">
        <div class="field days-field">
          <label>{{ t('days_label') }}</label>
          <input v-model="days" type="number" min="0" placeholder="0">
        </div>
        <div class="field cond-field">
          <label>{{ t('cond_label') }}</label>
          <select v-model="condition" @change="onCondChange">
            <option v-for="(c, i) in condOptions" :key="i" :value="condValues[i]">{{ c }}</option>
          </select>
          <div v-if="condition === 'custom'" class="custom-cond">
            <span class="mini-field"><input v-model="customTemp" type="number" min="-20" max="200" step="1"> °C</span>
            <span class="mini-field"><input v-model="customHum" type="number" min="0" max="100" step="5"> RH%</span>
          </div>
        </div>
      </div>
      <div class="actions">
        <button class="btn" @click="doPredict" :disabled="!api || !exc1 || store.loading">
          <span v-if="store.loading" class="spinner-sm"></span>
          {{ store.loading ? '...' : t('predict_btn') }}
        </button>
      </div>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { usePredictionStore } from '../stores/prediction'
import { currentLang, t, LOCALE } from '../i18n'

const store = usePredictionStore()
const api = ref('')
const exc1 = ref('')
const exc2 = ref('')
const days = ref('0')
const condition = ref('0')
const customTemp = ref('25')
const customHum = ref('60')
const error = ref('')

const condValues = ['0', '高温50℃', '2', '3', '高湿RH92.5%', '1', 'custom']

const condOptions = computed(() => {
  const l = currentLang.value === 'zh' ? LOCALE.zh : LOCALE.en
  return l.cond_opts
})

function onCondChange() {
  if (condition.value === 'custom') {
    if (!customTemp.value) customTemp.value = '25'
    if (!customHum.value) customHum.value = '60'
  }
}

function getConditionValue() {
  if (condition.value === 'custom') {
    return `${customTemp.value || '25'}°C RH${customHum.value || '0'}%`
  }
  return condition.value
}

watch(() => store.result, (res) => {
  if (res && res.error) {
    error.value = res.error
  } else {
    error.value = ''
  }
})

watch(() => store.pendingForm.trigger, (trig) => {
  if (trig && store.pendingForm.api && store.pendingForm.exc1) {
    api.value = store.pendingForm.api
    exc1.value = store.pendingForm.exc1
    exc2.value = store.pendingForm.exc2 || ''
    if (store.pendingForm.days) days.value = store.pendingForm.days
    if (store.pendingForm.condition) {
      const c = store.pendingForm.condition
      if (/60\s*[°℃度]/.test(c) || /高温\s*60/.test(c)) condition.value = '2'
      else if (/50\s*[°℃度]/.test(c) || /高温\s*50/.test(c)) condition.value = '高温50℃'
      else if (/75\s*%?\s*RH/i.test(c) || /高湿\s*75/i.test(c)) condition.value = '3'
      else if (/92\.?\s*5\s*%?\s*RH/i.test(c) || /高湿\s*92/i.test(c)) condition.value = '高湿RH92.5%'
      else if (/光照|light|曝光/i.test(c)) condition.value = '1'
      else if (/正常|normal|25\s*[°℃度]/.test(c)) condition.value = '0'
      else if (/[°℃度]/.test(c) || /RH/i.test(c) || /\d+\s*%/.test(c)) {
        condition.value = 'custom'
        const tMatch = c.match(/(\d+)\s*[°℃度]C?/)
        if (tMatch) customTemp.value = tMatch[1]
        const hMatch = c.match(/(\d+)\s*%?\s*RH/i)
        if (hMatch) customHum.value = hMatch[1]
      } else condition.value = 'custom'
    }
    store.pendingForm.trigger = false
    setTimeout(() => doPredict(), 200)
  }
})

async function doPredict() {
  if (!api.value || !exc1.value) return
  error.value = ''
  const cond = getConditionValue()
  await store.predict(api.value, exc1.value, exc2.value, days.value, cond)
}
</script>

<style scoped>
*,
*::before,
*::after {
  box-sizing: border-box;
}
.card {
  background: rgba(255,255,255,0.75);
  border: 1px solid rgba(255,255,255,0.6);
  border-radius: 16px;
  padding: 18px 18px 16px;
  margin: 0 auto 16px auto;
  width: 100%;
  max-width: 100%;
  backdrop-filter: blur(24px);
  box-shadow: 0 8px 32px rgba(0,0,0,0.06), 0 2px 8px rgba(0,0,0,0.03);
  display: flex;
  flex-direction: column;
  align-items: stretch;
}
.card h2 {
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 12px;
  width: 100%;
  text-align: center;
}
.form-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}
.row {
  display: flex;
  gap: 10px;
  width: 100%;
}
.row-3 .field {
  flex: 1 1 0;
  min-width: 0;
}
.row-2 {
  align-items: flex-start;
}
.field {
  width: 100%;
}
.days-field {
  flex: 0 0 22%;
  min-width: 110px;
  max-width: 140px;
}
.cond-field {
  flex: 1 1 auto;
  min-width: 0;
}
.field label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #6b6b70;
  margin-bottom: 5px;
  text-align: left;
}
.field input, .field select {
  width: 100%;
  padding: 9px 11px;
  background: rgba(255,255,255,0.9);
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 10px;
  color: #1d1d1f;
  font-size: 14px;
  outline: none;
  transition: border-color .2s, box-shadow .25s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}
.field input:hover, .field select:hover {
  background: rgba(255,255,255,0.95);
  border-color: rgba(0,0,0,0.15);
}
.field input:focus, .field select:focus {
  border-color: #0071e3;
  box-shadow: 0 0 0 3px rgba(0,113,227,0.1);
  background: #fff;
}
.field input::placeholder {
  color: #aeaeb2;
}
.custom-cond {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  width: 100%;
  flex-wrap: wrap;
}
.mini-field {
  flex: 1;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}
.mini-field input {
  flex: 1;
  padding: 6px 7px;
  font-size: 13px;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 8px;
  outline: none;
  transition: border-color .2s;
  background: rgba(255,255,255,0.9);
}
.mini-field input:focus {
  border-color: #0071e3;
}
.actions {
  display: flex;
  justify-content: center;
  padding-top: 4px;
  width: 100%;
}
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 9px 18px;
  background: #0071e3;
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all .25s;
}
.btn:hover {
  background: #0077ed;
  box-shadow: 0 4px 14px rgba(0,113,227,0.25);
  transform: translateY(-1px);
}
.btn:active {
  transform: scale(.97);
}
.btn:disabled {
  opacity: .5;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}
.error-box {
  grid-column: 1 / -1;
  background: rgba(255,235,238,0.8);
  border: 1px solid rgba(239,154,154,0.5);
  border-radius: 12px;
  padding: 14px;
  color: #c62828;
  font-size: 13px;
  margin-top: 14px;
}
.spinner-sm {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .6s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
