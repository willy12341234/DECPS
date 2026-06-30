<template>
  <div class="app">
    <div class="main">
      <header class="main-header">
        <div>
          <h1>{{ t('title') }}</h1>
          <p>{{ t('subtitle') }}</p>
        </div>
        <div class="lang-toggle" @click="toggleLang"><span class="lang-icon">🌐</span>
          <div class="lang-slider" :class="currentLang === 'en' ? 'en' : ''"></div>
          <span class="lang-opt" :class="currentLang === 'zh' ? 'active' : ''">中文</span>
          <span class="lang-opt" :class="currentLang === 'en' ? 'active' : ''">English</span>
        </div>
      </header>
      <div class="main-scroll">
        <LeftPanel v-if="showInputForm" />
        <div v-if="showSkillContext" class="skill-context">
          <div class="skill-context-icon">{{ skillIcon }}</div>
          <div class="skill-context-info">
            <div class="skill-context-title">{{ skillTitle }}</div>
            <div class="skill-context-desc">{{ skillDesc }}</div>
          </div>
        </div>
        <SearchProcess />
        <ResultPanel v-if="showPrediction" />
      </div>
    </div>
    <div class="sidebar">
      <ChatPanel />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { currentLang, t, toggleLang } from '../i18n'
import { useChatStore } from '../stores/chat'
import LeftPanel from './LeftPanel.vue'
import SearchProcess from './SearchProcess.vue'
import ResultPanel from './ResultPanel.vue'
import ChatPanel from './ChatPanel.vue'

const chatStore = useChatStore()

const showPrediction = computed(() => {
  // 所有 skill 都显示主面板（搜索过程/结果），但非相容性时隐藏左侧输入面板
  return true
})

const showInputForm = computed(() => {
  const s = chatStore.currentSkill
  return s === 'auto' || s === 'compatibility' || s === 'experiment'
})

const _SKILL_INFO = {
  compatibility: { icon: '🔬', title: '原辅料相容性预测', desc: '输入 API 和辅料名称，自动预测杂质风险、生成 SHAP 解释和化学机制分析。' },
  experiment:    { icon: '🧪', title: '实验方案设计', desc: '自动设计原辅料相容性实验方案，包含配比、条件、时间点、检测方法。' },
  formulation:   { icon: '💊', title: '剂型调研', desc: '查询药品已批准和临床在研的剂型信息，支持已批/在研/专利剂型多维度分析。' },
  patent:        { icon: '📄', title: '专利深度分析', desc: '从专利中提取适应症、药理、处方组成、临床效果、用法用量等关键信息。' },
  competitive:   { icon: '🔍', title: '竞品调研', desc: '对比多品种的开发状态、已批产品、专利布局，识别差距和机会。' },
  packaging:     { icon: '📦', title: '包材研究', desc: '检索包装变更历史和原因，对比不同包材方案的优劣势。' },
  project:       { icon: '📋', title: '立项报告', desc: '综合多源数据自动生成结构化立项调研报告。' },
  auto:          { icon: '🤖', title: '自动判断', desc: '直接输入需求，AI 自动判断任务类型并切换对应技能。' },
}

const showSkillContext = computed(() => {
  const s = chatStore.currentSkill
  return s !== 'compatibility' && s !== 'auto' && s !== 'experiment'
})

const skillIcon = computed(() => {
  const info = _SKILL_INFO[chatStore.currentSkill]
  return info ? info.icon : '🤖'
})

const skillTitle = computed(() => {
  const info = _SKILL_INFO[chatStore.currentSkill]
  return info ? info.title : ''
})

const skillDesc = computed(() => {
  const info = _SKILL_INFO[chatStore.currentSkill]
  return info ? info.desc : ''
})
</script>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  overflow: hidden;
  padding: 10px;
  gap: 10px;
  background: linear-gradient(135deg, #f5f5f7 0%, #e8ecf1 50%, #f0f2f5 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #1d1d1f;
}
.main {
  flex: 13;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 28px 28px;
  min-width: 0;
  background: rgba(255,255,255,0.65);
  border: 1px solid rgba(255,255,255,0.6);
  border-radius: 18px;
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow: 0 4px 24px rgba(0,0,0,0.04);
}
.main-header {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: 28px;
}
.main-header h1 {
  font-size: 22px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 4px;
  letter-spacing: -0.3px;
}
.main-header p {
  font-size: 13px;
  color: #86868b;
}
.main-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.sidebar {
  flex: 10;
  flex-shrink: 0;
  background: rgba(255,255,255,0.65);
  border: 1px solid rgba(255,255,255,0.6);
  border-radius: 18px;
  backdrop-filter: blur(30px);
  -webkit-backdrop-filter: blur(30px);
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 24px rgba(0,0,0,0.04);
  overflow: hidden;
}
.lang-icon {
  font-size: 16px;
  line-height: 1;
  display: flex;
  align-items: center;
  margin: 0 4px 0 2px;
}
.lang-toggle {
  position: relative;
  display: inline-flex;
  align-items: center;
  background: rgba(0,0,0,0.06);
  border-radius: 20px;
  padding: 3px;
  cursor: pointer;
  -webkit-user-select: none;
  user-select: none;
  backdrop-filter: blur(8px);
  border: 1px solid rgba(0,0,0,0.05);
  flex-shrink: 0;
  margin-top: 2px;
  transition: background .25s;
}
.lang-toggle:hover {
  background: rgba(0,0,0,0.1);
}
.lang-slider {
  position: absolute;
  top: 3px;
  left: 3px;
  width: calc(50% - 3px);
  height: calc(100% - 6px);
  background: rgba(255,255,255,0.9);
  border-radius: 17px;
  transition: transform .35s cubic-bezier(.25,.1,.25,1);
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  pointer-events: none;
}
.lang-slider.en {
  transform: translateX(100%);
}
.lang-opt {
  position: relative;
  z-index: 1;
  padding: 4px 14px;
  font-size: 12px;
  font-weight: 500;
  color: #6b6b70;
  transition: color .25s;
  text-align: center;
  min-width: 44px;
}
.lang-opt.active {
  color: #1d1d1f;
}
.skill-context {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  margin-bottom: 16px;
  background: rgba(255,255,255,0.55);
  border: 1px solid rgba(0,0,0,0.05);
  border-radius: 14px;
  backdrop-filter: blur(12px);
}
.skill-context-icon {
  font-size: 32px;
  line-height: 1;
  flex-shrink: 0;
}
.skill-context-info {
  flex: 1;
  min-width: 0;
}
.skill-context-title {
  font-size: 16px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 2px;
}
.skill-context-desc {
  font-size: 12px;
  color: #86868b;
  line-height: 1.5;
}
</style>
