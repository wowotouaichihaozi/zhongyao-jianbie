export function hasAnswer(value) {
  if (value == null) return false
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.some(hasAnswer)
  if (typeof value === 'object') return Object.values(value).some(hasAnswer)
  return true
}
export function examAnswerState(item) {
  if (!hasAnswer(item?.user_answer ?? item?.userAnswer)) return 'unanswered'
  if (['pending', 'ungraded'].includes(item?.grading_status)) return 'ungraded'
  const correct = item?.correct ?? item?.isCorrect
  if ([true, 1, 'true'].includes(correct)) return 'correct'
  if ([false, 0, 'false'].includes(correct)) return 'incorrect'
  return 'ungraded'
}
export function examStats(exam) {
  const detail = Array.isArray(exam?.detail) ? exam.detail : exam?.detail?.items || exam?.detail?.details || []
  const counts = { correct: 0, incorrect: 0, unanswered: 0, ungraded: 0 }
  for (const item of detail) counts[examAnswerState(item)]++
  const graded = counts.correct + counts.incorrect
  return { ...counts, answered: graded + counts.ungraded, graded, accuracy: graded ? Math.round(counts.correct / graded * 100) : null }
}
export function learningResourceCompleted(type, entry = {}) {
  if (['quiz', 'question-bank', 'question_bank', 'question-generator', 'exam', 'exercise', 'questions'].includes(String(type || entry.resourceType || '').toLowerCase())) {
    return Boolean(entry.completionSource === 'exam-submission' && entry.examResultId && entry.submittedAt)
  }
  return Boolean((entry.viewedAt && entry.viewSource === 'learning-path-task-open') || (entry.completionSource === 'learning-feedback' && entry.learningFeedback?.outcome === 'completed'))
}
if (typeof window !== 'undefined') {
  try {
    const raw = localStorage.getItem('quizHistory')
    if (raw) {
      const entries = JSON.parse(raw)
      if (Array.isArray(entries) && entries.some(e => !e.answerEvidenceVersion)) {
        if (!localStorage.getItem('quizHistory.before-answered-only-v1')) localStorage.setItem('quizHistory.before-answered-only-v1', raw)
        localStorage.setItem('quizHistory', JSON.stringify(entries.map(entry => {
          if (entry.answerEvidenceVersion) return entry
          const wrong = Array.isArray(entry.wrongQuestions) ? entry.wrongQuestions.filter(e => hasAnswer(e.user_answer ?? e.userAnswer)) : []
          return { ...entry, answerEvidenceVersion: 1, evidenceScope: 'legacy-unlinked', legacyWeakTopics: entry.weakTopics || [], wrongQuestions: wrong, weakTopics: [...new Set(wrong.map(e => e.knowledge_point).filter(Boolean))] }
        })))
      }
    }
  } catch { /* Local cache repair must never block the page. */ }
}
