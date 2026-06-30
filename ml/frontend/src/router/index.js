import { createRouter, createWebHistory } from 'vue-router'

const MainLayout = () => import('../components/MainLayout.vue')
const routes = [
  { path: '/', name: 'Home', component: MainLayout },
]
const router = createRouter({ history: createWebHistory(), routes })

export default router
