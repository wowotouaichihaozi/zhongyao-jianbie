const api = require('../../utils/api')
const data = require('../../utils/data')

Page({
  data: { loading: true, error: '', profile: null, weeks: [], progress: 0, generation: null, updatedAt: '' },
  onShow() { this.load() },
  onPullDownRefresh() { this.load().finally(() => wx.stopPullDownRefresh()) },
  async load() {
    this.setData({ loading: true, error: '' })
    try {
      const [profileResult, pathResult] = await Promise.all([api.profiles(), api.pathConfig()])
      const profile = data.activeProfile(profileResult)
      const value = data.body(pathResult)
      const weeks = data.weeks(pathResult)
      const done = weeks.filter(item => item.state === 'done').length
      this.setData({
        profile,
        weeks,
        progress: weeks.length ? Math.round(done / weeks.length * 100) : 0,
        generation: value.meta?.backgroundGeneration || null,
        updatedAt: value.updatedAt || value.meta?.savedAt || '',
      })
    } catch (error) {
      this.setData({ error: error.message })
    } finally {
      this.setData({ loading: false })
    }
  },
  profile() { wx.navigateTo({ url: '/pages/profile/profile' }) },
  resources() { wx.switchTab({ url: '/pages/resources/resources' }) },
})
