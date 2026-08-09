const api = require('../../utils/api')
const data = require('../../utils/data')

Page({
  data: { loading: true, error: '', user: {}, profile: null, profileCount: 0, taskCount: 0, assessment: null, recommendations: [] },
  onShow() { this.load() },
  onPullDownRefresh() { this.load().finally(() => wx.stopPullDownRefresh()) },
  async load() {
    this.setData({ loading: true, error: '' })
    try {
      const [meResult, profileResult, taskResult] = await Promise.all([
        api.me().catch(() => null), api.profiles(), api.taskHistory(100).catch(() => null),
      ])
      const user = data.body(meResult)
      const list = data.profileList(profileResult)
      const profile = data.activeProfile(profileResult)
      let assessment = null
      let recommendations = []
      if (profile) {
        const result = await api.assessment(profile.id).catch(() => null)
        assessment = data.body(result).assessment || null
        const raw = assessment?.recommendations || assessment?.pathAdjustmentPlan?.adjustments || []
        recommendations = (Array.isArray(raw) ? raw : []).map(item => typeof item === 'string' ? item : (item.title || item.action || item.description || '学习路径调整建议'))
      }
      this.setData({
        user: Object.keys(user || {}).length ? user : (wx.getStorageSync('currentUser') || {}),
        profile,
        profileCount: list.length,
        taskCount: data.tasks(taskResult).length,
        assessment,
        recommendations,
      })
    } catch (error) {
      this.setData({ error: error.message })
    } finally {
      this.setData({ loading: false })
    }
  },
  profile() { wx.navigateTo({ url: '/pages/profile/profile' }) },
  resources() { wx.switchTab({ url: '/pages/resources/resources' }) },
  async logout() {
    const confirmed = await new Promise(resolve => wx.showModal({ title: '退出登录', content: '退出后不会删除服务端学习数据。', success: result => resolve(result.confirm) }))
    if (!confirmed) return
    try { await api.logout() } catch (error) {}
    wx.removeStorageSync('authToken')
    wx.removeStorageSync('currentUser')
    getApp().globalData.user = {}
    wx.reLaunch({ url: '/pages/login/login' })
  },
})
