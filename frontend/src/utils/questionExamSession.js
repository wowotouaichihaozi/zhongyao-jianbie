export function resolveExamQuestions(payload = {}) {
  const candidates = [
    payload?.sheet?.question_bank?.questions,
    payload?.sheet?.questions,
    payload?.questions,
  ]

  const populated = candidates.find(candidate => Array.isArray(candidate) && candidate.length > 0)
  if (populated) return populated

  const empty = candidates.find(Array.isArray)
  return empty || []
}

export function elapsedSecondsSince(startedAt, now = Date.now()) {
  const start = Number(startedAt)
  const current = Number(now)
  if (!Number.isFinite(start) || start <= 0 || !Number.isFinite(current) || current <= start) return 0
  return Math.floor((current - start) / 1000)
}
