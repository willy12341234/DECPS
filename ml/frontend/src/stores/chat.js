import { defineStore } from 'pinia'
import { ref } from 'vue'

function storageKey() {
  const key = 'chatHistories_user'
  const old = localStorage.getItem('chatHistories')
  if (old && !localStorage.getItem(key)) {
    localStorage.setItem(key, old)
    localStorage.removeItem('chatHistories')
  }
  return key
}

export const useChatStore = defineStore('chat', () => {
  let _msgId = 0
  const messages = ref([])
  const history = ref(JSON.parse(localStorage.getItem(storageKey()) || '[]'))
  const streaming = ref(false)
  const currentSkill = ref('auto')
  const pageContent = ref(null)

  function addMessage(role, content) {
    messages.value.push({ id: ++_msgId, role, content })
  }

  function clear() {
    messages.value = []
    saveToHistory()
  }

  function switchSkill(skillId) {
    currentSkill.value = skillId
  }

  function saveToHistory() {
    if (!messages.value.length) return
    const first = messages.value.find(m => m.role === 'user')
    if (!first) return
    history.value.unshift({
      id: Date.now(),
      time: new Date().toLocaleString('zh-CN'),
      preview: first.content.slice(0, 60),
      skill: currentSkill.value,
      messages: JSON.parse(JSON.stringify(messages.value)),
    })
    if (history.value.length > 50) history.value.length = 50
    localStorage.setItem(storageKey(), JSON.stringify(history.value))
  }

  function loadHistoryItem(id) {
    const item = history.value.find(h => h.id === id)
    if (item) {
      messages.value = JSON.parse(JSON.stringify(item.messages))
      if (item.skill) currentSkill.value = item.skill
    }
  }

  function deleteHistoryItem(id) {
    history.value = history.value.filter(h => h.id !== id)
    localStorage.setItem(storageKey(), JSON.stringify(history.value))
  }

  return { messages, history, streaming, currentSkill, addMessage, clear, saveToHistory, loadHistoryItem, deleteHistoryItem, switchSkill }
})
