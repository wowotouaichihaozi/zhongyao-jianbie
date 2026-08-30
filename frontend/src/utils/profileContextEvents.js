export const XIAOZHI_PROFILE_CONTEXT_EVENT = 'xiaozhi-profile-context-changed'

export function dispatchXiaoZhiProfileContextChanged(profile = null) {
  const detail = {
    profileReportId: Number(profile?.id || profile?.profileReportId || 0),
    profileName: String(profile?.profileName || '学习画像'),
    version: Number(profile?.version || 1),
    changedAt: Date.now(),
  }
  window.dispatchEvent(new CustomEvent(XIAOZHI_PROFILE_CONTEXT_EVENT, { detail }))
  return detail
}
