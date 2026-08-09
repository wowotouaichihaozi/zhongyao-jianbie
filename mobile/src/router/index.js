import { createRouter, createWebHistory } from 'vue-router'
import { getAuthToken } from '../stores/auth.js'

const routes = [
  { path: '/', redirect: '/home' },
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true, bare: true } },
  { path: '/home', name: 'home', component: () => import('../views/HomeView.vue') },
  { path: '/path', name: 'path', component: () => import('../views/PathView.vue') },
  { path: '/path/:stageId', name: 'path-stage', component: () => import('../views/PathView.vue') },
  { path: '/resources', name: 'resources', component: () => import('../views/ResourcesView.vue') },
  { path: '/resources/new', name: 'resource-new', component: () => import('../views/ResourceCreateView.vue'), meta: { subpage: true } },
  { path: '/resources/task/:taskId', name: 'resource-task', component: () => import('../views/ResourceTaskView.vue'), meta: { subpage: true } },
  { path: '/resources/task/:taskId/item/:itemIndex', name: 'resource-detail', component: () => import('../views/ResourceTaskView.vue'), meta: { subpage: true } },
  { path: '/practice/:sheetId', name: 'practice', component: () => import('../views/PracticeView.vue'), meta: { subpage: true } },
  { path: '/tutor', name: 'tutor', component: () => import('../views/TutorView.vue') },
  { path: '/profile', name: 'profile', component: () => import('../views/ProfileView.vue'), meta: { subpage: true } },
  { path: '/profile/collect', name: 'profile-collect', component: () => import('../views/ProfileCollectView.vue'), meta: { subpage: true } },
  { path: '/me', name: 'me', component: () => import('../views/MeView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/home' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.VITE_ROUTER_BASE || '/m/'),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  if (!to.meta.public && !getAuthToken()) return { name: 'login', query: { redirect: to.fullPath } }
  if (to.name === 'login' && getAuthToken()) return { name: 'home' }
  return true
})

export default router
