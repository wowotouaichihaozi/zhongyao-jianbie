const api = require('../../utils/api')
const data = require('../../utils/data')

Page({
  data: {
    loading: true,
    sending: false,
    error: '',
    profiles: [],
    active: null,
    messages: [{ role: 'assistant', content: '我是岐小智。请先告诉我，你目前学习的中医课程，以及最想提升的经典、方药或辨证能力。' }],
    input: '',
    completeness: 0,
    missing: [],
    missingText: '',
    statusText: '等待开始',
  },
  onLoad() { this.loadProfiles() },
  onPullDownRefresh() { this.loadProfiles().finally(() => wx.stopPullDownRefresh()) },
  async loadProfiles() {
    this.setData({ loading: true, error: '' })
    try {
      const result = await api.profiles()
      this.setData({ profiles: data.profileList(result), active: data.activeProfile(result) })
    } catch (error) {
      this.setData({ error: error.message })
    } finally {
      this.setData({ loading: false })
    }
  },
  input(e) { this.setData({ input: e.detail.value }) },
  async send() {
    const text = this.data.input.trim()
    if (!text || this.data.sending) return
    const messages = [...this.data.messages, { role: 'user', content: text }]
    this.setData({ messages, input: '', sending: true, error: '', statusText: '正在分析回答并更新画像维度' })
    try {
      const response = await api.profileChat({ message: text, messages })
      const result = data.body(response)
      const reply = result.reply || result.question || result.message || '已记录这条学习信息，请继续补充你的学习经历。'
      const nextMessages = [...messages, { role: 'assistant', content: reply }]
      const completeness = Math.max(0, Math.min(100, Number(result.completeness || 0)))
      const complete = result.status === 'complete' || result.needFollowup === false
      this.setData({
        messages: nextMessages,
        completeness,
        missing: result.missingProfileDimensions || result.missingFields || [],
        missingText: (result.missingProfileDimensions || result.missingFields || []).join('、'),
        statusText: complete ? '画像已生成，正在同步个性化路径' : '继续对话以补全画像',
      })
      if (complete) {
        await this.loadProfiles()
        wx.showToast({ title: '画像已更新', icon: 'success' })
      }
    } catch (error) {
      this.setData({ error: error.message, statusText: '本轮未保存，请重试' })
    } finally {
      this.setData({ sending: false })
    }
  },
  async activate(e) {
    const id = Number(e.currentTarget.dataset.id)
    if (!id) return
    this.setData({ loading: true, error: '' })
    try {
      await api.activateProfile(id)
      await this.loadProfiles()
      wx.showToast({ title: '已切换画像', icon: 'success' })
    } catch (error) {
      this.setData({ error: error.message, loading: false })
    }
  },
  async reset() {
    const confirmed = await new Promise(resolve => wx.showModal({ title: '重新采集画像', content: '将清空当前对话进度，但不会删除已生成画像。', success: result => resolve(result.confirm) }))
    if (!confirmed) return
    try {
      await api.resetProfileChat()
      this.setData({
        messages: [{ role: 'assistant', content: '我们重新开始。请告诉我你的专业、年级和当前正在学习的中医课程。' }],
        completeness: 0,
        missing: [],
        missingText: '',
        statusText: '等待开始',
        error: '',
      })
    } catch (error) {
      this.setData({ error: error.message })
    }
  },
})
