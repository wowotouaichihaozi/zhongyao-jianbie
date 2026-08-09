const api = require('../../utils/api')

Page({
  data: {
    username: '',
    password: '',
    captchaAnswer: '',
    captchaId: '',
    captchaQuestion: '',
    loading: false,
    error: '',
  },
  onLoad() {
    if (wx.getStorageSync('authToken')) {
      wx.switchTab({ url: '/pages/home/home' })
      return
    }
    this.loadCaptcha()
  },
  async loadCaptcha(details = {}) {
    try {
      const result = details.captchaId ? details : await api.captcha()
      this.setData({ captchaId: result.captchaId || '', captchaQuestion: result.question || '', captchaAnswer: '' })
    } catch (error) {
      this.setData({ error: error.message })
    }
  },
  input(e) { this.setData({ [e.currentTarget.dataset.field]: e.detail.value }) },
  async submit() {
    const { username, password, captchaAnswer, captchaId, captchaQuestion } = this.data
    if (!username.trim() || !password) return this.setData({ error: '请输入账号和密码' })
    if (captchaQuestion && !captchaAnswer.trim()) return this.setData({ error: '请输入验证码计算结果' })
    this.setData({ loading: true, error: '' })
    try {
      const user = await api.login({ username: username.trim(), password, captchaAnswer: captchaAnswer.trim(), captchaId })
      if (!user.token) throw new Error('登录响应中没有会话令牌')
      wx.setStorageSync('authToken', user.token)
      const currentUser = { ...user }
      delete currentUser.token
      wx.setStorageSync('currentUser', currentUser)
      getApp().globalData.user = currentUser
      wx.switchTab({ url: '/pages/home/home' })
    } catch (error) {
      this.setData({ error: error.message })
      await this.loadCaptcha(error.details || {})
    } finally {
      this.setData({ loading: false })
    }
  },
})
