import { createRouter, createWebHistory } from 'vue-router'
import { getCurrentUser } from '../services/api.js'
import { clearAuthSession, getAuthToken, readCurrentUser, setAuthSession } from '../stores/auth.js'
import { safeInternalRedirect } from '../utils/authRedirect.js'

const AuthPage = () => import('../views/AuthPage.vue')
const QuestionGeneratorView = () => import('../views/QuestionGeneratorView.vue')
const QuestionExamSessionView = () => import('../views/QuestionExamSessionView.vue')
const LearningProfileView = () => import('../views/LearningProfileView.vue')
const LearningProfileSubmitView = () => import('../views/LearningProfileSubmitView.vue')
const LearningProfileUploadView = () => import('../views/LearningProfileUploadView.vue')
const LearningPathView = () => import('../views/LearningPathView.vue')
const LearningPathStageDetailView = () => import('../views/LearningPathStageDetailView.vue')
const PersonalizedResourcesView = () => import('../views/PersonalizedResourcesView.vue')
const ResourceDetailView = () => import('../views/ResourceDetailView.vue')
const DigitalHumanInterviewView = () => import('../views/DigitalHumanInterviewView.vue')
const UserProfileView = () => import('../views/UserProfileView.vue')
const PptGeneratorView = () => import('../views/PptGeneratorView.vue')
const PptWorkbenchView = () => import('../views/PptWorkbenchView.vue')
const PptGeneratingView = () => import('../views/PptGeneratingView.vue')
const MindMapView = () => import('../views/MindMapView.vue')
const VideoSearchView = () => import('../views/VideoSearchView.vue')
const VideoGeneratorView = () => import('../views/VideoGeneratorView.vue')
const LearningAnimationView = () => import('../views/LearningAnimationView.vue')
const EffectAssessmentView = () => import('../views/EffectAssessmentView.vue')
const LearningDocumentView = () => import('../views/LearningDocumentView.vue')
const SmartTutorView = () => import('../views/SmartTutorView.vue')
const KnowledgeBaseView = () => import('../views/KnowledgeBaseView.vue')
const KnowledgeNetworkView = () => import('../views/KnowledgeNetworkOriginalEmbedView.vue')
const AgentDigitalTwinView = () => import('../views/AgentDigitalTwinView.vue')

const CODEX_PREVIEW_AUTH_KEY = 'codexPreviewAuth'

function hasCodexPreviewAuth(to) {
  const isLocalHost = ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)
  if (!isLocalHost) return false
  if (to.query.codexPreview === '1') {
    localStorage.setItem(CODEX_PREVIEW_AUTH_KEY, '1')
  }
  return localStorage.getItem(CODEX_PREVIEW_AUTH_KEY) === '1'
}

function ensureCodexPreviewSession() {
  setAuthSession({
    id: 'codex-preview-user',
    username: 'codex-preview',
    displayName: 'Codex Preview',
    role: 'user',
    token: 'codex-preview-token',
  })
}

async function hasValidLogin(to) {
  if (hasCodexPreviewAuth(to)) {
    ensureCodexPreviewSession()
    return true
  }
  const token = getAuthToken()
  if (!token) return false
  if (readCurrentUser().id) return true
  try {
    const user = await getCurrentUser()
    setAuthSession({ ...user, token })
    return Boolean(user?.id)
  } catch {
    return false
  }
}

const routes = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    name: 'login',
    component: AuthPage,
  },
  {
    path: '/question-generator',
    name: 'question-generator',
    component: QuestionGeneratorView,
    meta: { requiresAuth: true },
  },
  {
    path: '/question-generator/exam-session',
    name: 'question-generator-exam-session',
    component: QuestionExamSessionView,
    meta: { requiresAuth: true },
  },
  {
    path: '/mcu-simulator/:board?/:projectId?',
    redirect: '/personalized-resources',
  },
  {
    path: '/learning-profile',
    name: 'learning-profile',
    component: LearningProfileView,
    meta: { requiresAuth: true },
  },
  {
    path: '/learning-profile/submit',
    name: 'learning-profile-submit',
    component: LearningProfileSubmitView,
    meta: { requiresAuth: true },
  },
  {
    path: '/learning-profile/upload',
    name: 'learning-profile-upload',
    component: LearningProfileUploadView,
    meta: { requiresAuth: true },
  },
  {
    path: '/learning-profile/chat',
    name: 'learning-profile-chat',
    redirect: { path: '/learning-profile', query: { collect: 'chat' } },
    meta: { requiresAuth: true },
  },
  {
    path: '/learning-path',
    name: 'learning-path',
    redirect: { name: 'learning-path-stage-detail', params: { stageId: 'overview' } },
    meta: { requiresAuth: true },
  },
  {
    path: '/effect-assessment',
    name: 'effect-assessment',
    component: EffectAssessmentView,
    meta: { requiresAuth: true },
  },
  {
    path: '/smart-tutor',
    name: 'smart-tutor',
    component: SmartTutorView,
    meta: { requiresAuth: true },
  },
  {
    path: '/learning-path/weeks',
    name: 'learning-path-weeks',
    redirect: { name: 'learning-path-stage-detail', params: { stageId: 'overview' } },
    meta: { requiresAuth: true },
  },
  {
    path: '/learning-path/week/:stageId',
    name: 'learning-path-week-detail',
    component: LearningPathView,
    meta: { requiresAuth: true },
  },
  {
    path: '/learning-path/stage/:stageId',
    name: 'learning-path-stage-detail',
    component: LearningPathStageDetailView,
    beforeEnter: (to) => {
      const stageId = String(to.params.stageId || '')
      if (stageId === 'overview') return true
      const normalizedStageId = ['courseware-recommend', 'profile-diagnosis'].includes(stageId)
        ? 'week-1-embedded-foundation'
        : stageId
      return {
        name: 'learning-path-week-detail',
        params: { stageId: normalizedStageId },
        query: to.query,
        hash: to.hash,
      }
    },
    meta: { requiresAuth: true },
  },
  {
    path: '/personalized-resources',
    name: 'personalized-resources',
    component: PersonalizedResourcesView,
    meta: { requiresAuth: true },
  },
  {
    path: '/personalized-resources/knowledge-base',
    name: 'personalized-resource-knowledge-base',
    component: KnowledgeBaseView,
    meta: { requiresAuth: true },
  },
  {
    path: '/knowledge-network',
    name: 'knowledge-network',
    component: KnowledgeNetworkView,
    meta: { requiresAuth: true },
  },
  {
    path: '/personalized-resources/knowledge-network',
    redirect: '/knowledge-network',
  },
  {
    path: '/agent-digital-twin',
    name: 'agent-digital-twin',
    component: AgentDigitalTwinView,
    meta: { requiresAuth: true },
  },
  {
    path: '/ai-coding',
    redirect: '/personalized-resources',
  },
  {
    path: '/personalized-resources/question-bank',
    name: 'personalized-resource-question-bank',
    component: QuestionGeneratorView,
    meta: { requiresAuth: true, noNavbar: true, resourceTool: true },
  },
  {
    path: '/personalized-resources/ppt',
    name: 'personalized-resource-ppt',
    component: PptWorkbenchView,
    meta: { requiresAuth: true, noNavbar: true, resourceTool: true },
  },
  {
    path: '/personalized-resources/document',
    name: 'personalized-resource-document',
    component: LearningDocumentView,
    meta: { requiresAuth: true, noNavbar: true, resourceTool: true },
  },
  {
    path: '/personalized-resources/mind-map',
    name: 'personalized-resource-mind-map',
    component: MindMapView,
    meta: { requiresAuth: true, noNavbar: true, resourceTool: true },
  },
{
    path: '/personalized-resources/video-search',
    name: 'personalized-resource-video-search',
    component: VideoSearchView,
    meta: { requiresAuth: true, noNavbar: true, resourceTool: true },
  },
  {
    path: '/personalized-resources/video-generator',
    name: 'personalized-resource-video-generator',
    component: VideoGeneratorView,
    meta: { requiresAuth: true, noNavbar: true, resourceTool: true },
  },
  {
    path: '/personalized-resources/animation',
    name: 'personalized-resource-animation',
    component: LearningAnimationView,
    meta: { requiresAuth: true, noNavbar: true, resourceTool: true },
  },
  {
    path: '/personalized-resources/mcu-simulator/:board?/:projectId?',
    redirect: '/personalized-resources',
  },
  {
    path: '/resource-detail',
    name: 'resource-detail',
    component: ResourceDetailView,
    meta: { requiresAuth: true },
  },
  {
    path: '/digital-human-interview',
    alias: '/interview-avatar',
    name: 'digital-human-interview',
    component: DigitalHumanInterviewView,
    meta: { requiresAuth: true },
  },
  {
    path: '/ppt-generator',
    name: 'ppt-generator',
    component: PptGeneratorView,
    meta: { requiresAuth: true },
  },
  {
    path: '/mind-map',
    name: 'mind-map',
    component: MindMapView,
    meta: { requiresAuth: true },
  },
  {
    path: '/video-search',
    name: 'video-search',
    component: VideoSearchView,
    meta: { requiresAuth: true },
  },
  {
    path: '/ppt-generator/generating/:sessionId',
    name: 'ppt-generating',
    component: PptGeneratingView,
    meta: { requiresAuth: true, noNavbar: true, resourceTool: true },
  },
  {
    path: '/user-profile',
    name: 'user-profile',
    component: UserProfileView,
    meta: { requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  if (to.meta.requiresAuth && !(await hasValidLogin(to))) {
    clearAuthSession()
    return {
      name: 'login',
      query: { redirect: safeInternalRedirect(to.fullPath) },
    }
  }
  return true
})

export default router
