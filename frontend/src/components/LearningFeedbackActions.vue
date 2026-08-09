<template>
  <div v-if="canSubmitFeedback" class="learning-feedback-actions" :class="{ compact }">
    <span v-if="feedbackOutcome" class="feedback-saved">
      <CheckCircle2 :size="15" />
      {{ outcomeLabel }}
    </span>
    <button
      v-if="feedbackOutcome !== 'completed'"
      type="button"
      :disabled="feedbackSaving"
      @click="submitOutcome('completed')"
    >
      <LoaderCircle v-if="feedbackSaving" :size="15" class="spin" />
      <CheckCircle2 v-else :size="15" />
      完成学习
    </button>
    <button
      v-if="feedbackOutcome !== 'needs_review'"
      type="button"
      :disabled="feedbackSaving"
      @click="submitOutcome('needs_review')"
    >
      <LoaderCircle v-if="feedbackSaving" :size="15" class="spin" />
      <RotateCcw v-else :size="15" />
      需要巩固
    </button>
    <small v-if="feedbackError">{{ feedbackError }}</small>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { CheckCircle2, LoaderCircle, RotateCcw } from 'lucide-vue-next'
import { getLearningFeedback, submitLearningFeedback } from '../services/api.js'
import { markNodeCacheComplete, setNodeCache } from '../services/learningPathNodeCache.js'

const props = defineProps({
  task: { type: Object, default: null },
  cacheKey: { type: String, default: '' },
  routePath: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})

const emit = defineEmits(['submitted'])
const feedbackOutcome = ref('')
const feedbackSaving = ref(false)
const feedbackError = ref('')
const feedbackLoadedFor = ref('')

const taskId = computed(() => String(props.task?.taskId || '').trim())
const taskType = computed(() => String(props.task?.taskType || props.task?.type || '').trim())
const canSubmitFeedback = computed(() => taskId.value && props.task?.status === 'complete')
const outcomeLabel = computed(() => ({
  completed: '已计入学习完成',
  needs_review: '已加入巩固依据',
  blocked: '已记录学习阻塞',
})[feedbackOutcome.value] || '学习结果已记录')

watch(
  () => [taskId.value, props.task?.status],
  () => {
    if (feedbackLoadedFor.value !== taskId.value) {
      feedbackOutcome.value = ''
      feedbackError.value = ''
    }
    if (canSubmitFeedback.value) void loadFeedback()
  },
  { immediate: true },
)

async function loadFeedback() {
  if (!taskId.value || feedbackLoadedFor.value === taskId.value) return
  feedbackLoadedFor.value = taskId.value
  try {
    const response = await getLearningFeedback({ taskId: taskId.value, limit: 1 })
    feedbackOutcome.value = String(response?.data?.feedbacks?.[0]?.outcome || '')
  } catch {
    feedbackLoadedFor.value = ''
  }
}

async function submitOutcome(outcome) {
  if (!canSubmitFeedback.value || feedbackSaving.value) return
  feedbackSaving.value = true
  feedbackError.value = ''
  try {
    const response = await submitLearningFeedback({
      taskId: taskId.value,
      topic: props.task?.title || props.task?.result?.topic || '当前学习资源',
      resourceType: taskType.value,
      outcome,
      difficulty: outcome === 'completed' ? 'appropriate' : 'hard',
      helpful: outcome === 'completed' ? true : null,
      route: props.routePath,
      cacheKey: props.cacheKey,
    })
    const feedback = response?.data?.feedback || {}
    feedbackOutcome.value = String(feedback.outcome || outcome)
    syncNodeCache(feedback)
    emit('submitted', feedback)
  } catch (error) {
    feedbackError.value = error?.response?.data?.msg || error?.message || '反馈记录失败'
  } finally {
    feedbackSaving.value = false
  }
}

function syncNodeCache(feedback) {
  if (!props.cacheKey) return
  if (feedback?.pathCache && typeof feedback.pathCache === 'object') {
    setNodeCache(props.cacheKey, feedback.pathCache)
    return
  }
  const patch = {
    learningFeedback: {
      feedbackId: feedback.id,
      outcome: feedbackOutcome.value,
      updatedAt: feedback.updatedAt || new Date().toISOString(),
    },
  }
  if (feedbackOutcome.value === 'completed') markNodeCacheComplete(props.cacheKey, patch)
  else setNodeCache(props.cacheKey, { ...patch, status: 'running', completedAt: null, completionSource: null })
}
</script>

<style scoped>
.learning-feedback-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
}

.learning-feedback-actions button,
.feedback-saved {
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0 10px;
  border: 1px solid #cfe6dc;
  border-radius: 5px;
  background: #fff;
  color: #286b53;
  font-size: 12px;
  font-weight: 750;
}

.learning-feedback-actions button {
  cursor: pointer;
}

.learning-feedback-actions button:disabled {
  cursor: wait;
  opacity: 0.58;
}

.feedback-saved {
  border-color: #bce1d1;
  background: #edf8f3;
  color: #14704d;
}

.learning-feedback-actions small {
  flex-basis: 100%;
  color: #b24b3c;
  font-size: 11px;
}

.learning-feedback-actions.compact button,
.learning-feedback-actions.compact .feedback-saved {
  min-height: 30px;
  padding: 0 9px;
  font-size: 11px;
}

.spin {
  animation: spin 0.85s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
