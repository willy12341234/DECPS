import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'

export const usePredictionStore = defineStore('prediction', () => {
  const result = ref(null)
  const groupData = ref(null)
  const loading = ref(false)
  const searchData = ref([])
  const parsedData = ref([])
  const searchResults = ref({ patent: [], pubmed: [], clinical: [] })
  const pendingForm = reactive({ api: '', exc1: '', exc2: '', condition: '', days: '', trigger: false })
  const lastParsed = ref(null)

  async function predict(api, exc1, exc2 = '', days = '0', condition = '0') {
    loading.value = true
    try {
      const r = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api, excipient1: exc1, excipient2: exc2, days, condition })
      })
      result.value = await r.json()
    } finally { loading.value = false }
  }

  function clear() {
    result.value = null; groupData.value = null
    searchData.value = []; parsedData.value = []
    searchResults.value = { patent: [], pubmed: [], clinical: [] }
    pendingForm.api = ''; pendingForm.exc1 = ''; pendingForm.exc2 = ''; pendingForm.trigger = false
    lastParsed.value = null
  }

  return { result, groupData, searchData, parsedData, searchResults, pendingForm, lastParsed, loading, predict, clear }
})
