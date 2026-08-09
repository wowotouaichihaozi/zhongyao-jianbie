const api = require('../../utils/api')
const data = require('../../utils/data')

Page({
  data: { loading: true, error: '', displayName: '学习者', greeting: '你好', todayLabel: '', profile: null, weeks: [], tasks: [], progress: 0, currentWeek: null, runningCount: 0 },
  onShow() { if (wx.getStorageSync('authToken')) this.load(); else wx.reLaunch({ url: '/pages/login/login' }) },
  onPullDownRefresh() { this.load().finally(() => wx.stopPullDownRefresh()) },
  async load() {
    this.setData({ loading: true, error: '' })
    try {
      const [profileResult, pathResult, taskResult] = await Promise.all([
        api.profiles().catch(() => null), api.pathConfig().catch(() => null), api.taskHistory(40).catch(() => null),
      ])
      const profile = data.activeProfile(profileResult)
      const weeks = data.weeks(pathResult)
      const tasks = data.tasks(taskResult).map(item => ({ ...item, statusLabel: ({ queued: '排队中', running: '生成中', complete: '已完成', failed: '失败', waiting: '待确认' })[item.status] || item.status }))
      const currentWeek = weeks.find(item => item.state === 'current') || weeks.find(item => item.state === 'available') || weeks[0] || null
      const progress = weeks.length ? Math.round(weeks.filter(item => item.state === 'done').length / weeks.length * 100) : 0
      const user = wx.getStorageSync('currentUser') || {}
      const now = new Date()
      const greeting = now.getHours() < 11 ? '早上好' : now.getHours() < 18 ? '下午好' : '晚上好'
      const todayLabel = `${now.getMonth() + 1} 月 ${now.getDate()} 日`
      this.setData({ profile, weeks, tasks: tasks.slice(0, 4), currentWeek, progress, runningCount: tasks.filter(item => ['queued', 'running'].includes(item.status)).length, displayName: user.displayName || user.username || '学习者', greeting, todayLabel })
    } catch (error) {
      this.setData({ error: error.message })
    } finally {
      this.setData({ loading: false })
    }
  },
  profile() { wx.navigateTo({ url: '/pages/profile/profile' }) },
  path() { wx.switchTab({ url: '/pages/path/path' }) },
  resources() { wx.switchTab({ url: '/pages/resources/resources' }) },
  tutor() { wx.switchTab({ url: '/pages/tutor/tutor' }) },
})
