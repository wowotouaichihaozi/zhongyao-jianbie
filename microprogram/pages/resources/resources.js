const api = require('../../utils/api')
const data = require('../../utils/data')
const { absoluteApiUrl } = require('../../utils/request')

const TYPES = [
  { value: 'question_bank', label: '智能题库', hint: '练习与解析' },
  { value: 'document', label: '学习文档', hint: '结构化讲义' },
  { value: 'ppt', label: '演示文稿', hint: '教学 PPT' },
  { value: 'mindmap', label: '思维导图', hint: '知识结构' },
  { value: 'video', label: '视频检索', hint: '匹配公开视频' },
  { value: 'generated_video', label: 'AI 讲解视频', hint: '确认后生成' },
  { value: 'animation', label: '教学动画', hint: '机制演示' },
]

Page({
  data: {
    types: TYPES,
    selectedType: 'question_bank',
    topic: '',
    prompt: '',
    resolutionOptions: ['480p', '720p', '1080p'],
    ratings: [1, 2, 3, 4, 5],
    resolutionIndex: 1,
    loading: true,
    submitting: false,
    error: '',
    tasks: [],
    selectedTask: null,
    startingVideo: false,
    feedbackRating: 0,
    feedbackNote: '',
    feedbackSaving: false,
  },
  onShow() { this.loadTasks(); this.startPolling() },
  onHide() { this.stopPolling() },
  onUnload() { this.stopPolling() },
  onPullDownRefresh() { this.loadTasks().finally(() => wx.stopPullDownRefresh()) },
  input(e) { this.setData({ [e.currentTarget.dataset.field]: e.detail.value }) },
  chooseType(e) { this.setData({ selectedType: e.currentTarget.dataset.value }) },
  resolution(e) { this.setData({ resolutionIndex: Number(e.detail.value) }) },
  startPolling() {
    this.stopPolling()
    this.poller = setInterval(() => {
      if (this.data.tasks.some(item => ['queued', 'running'].includes(item.status))) this.loadTasks(true)
    }, 5000)
  },
  stopPolling() { if (this.poller) clearInterval(this.poller); this.poller = null },
  async loadTasks(silent = false) {
    if (!silent) this.setData({ loading: true, error: '' })
    try {
      const result = await api.taskHistory(80)
      const tasks = data.tasks(result).map(item => ({ ...item, progressValue: data.progress(item), statusLabel: this.statusLabel(item.status) }))
      this.setData({ tasks })
    } catch (error) {
      if (!silent) this.setData({ error: error.message })
    } finally {
      if (!silent) this.setData({ loading: false })
    }
  },
  statusLabel(status) {
    return ({ queued: '排队中', running: '生成中', complete: '已完成', failed: '失败', waiting: '待确认' })[status] || status || '未知'
  },
  async submit() {
    const topic = this.data.topic.trim()
    if (!topic) return this.setData({ error: '请输入学习主题' })
    this.setData({ submitting: true, error: '' })
    try {
      const resolution = this.data.resolutionOptions[this.data.resolutionIndex]
      const result = await api.createResourceTask({
        resourceType: this.data.selectedType,
        topic,
        prompt: this.data.prompt.trim() || topic,
        params: { resolution },
      })
      const created = data.body(result).task
      wx.showToast({ title: this.data.selectedType === 'generated_video' ? '提示词已保存' : '任务已创建', icon: 'success' })
      this.setData({ topic: '', prompt: '' })
      await this.loadTasks()
      if (created?.taskId || created?.id) this.openTask({ currentTarget: { dataset: { id: created.taskId || created.id } } })
    } catch (error) {
      this.setData({ error: error.message })
    } finally {
      this.setData({ submitting: false })
    }
  },
  async openTask(e) {
    const id = String(e.currentTarget.dataset.id || '')
    if (!id) return
    wx.showLoading({ title: '读取任务' })
    try {
      const response = await api.task(id)
      const value = data.body(response)
      const task = value.task || value
      const result = task.result || {}
      const selected = result.selectedResource || {}
      const content = selected.content || {}
      this.setData({
        selectedTask: {
          ...task,
          status: data.normalizeTaskState(task.status),
          statusLabel: this.statusLabel(data.normalizeTaskState(task.status)),
          progressValue: data.progress(task),
          resultTitle: selected.title || result.title || task.title || '任务结果',
          resultSummary: selected.description || result.summary || result.message || task.error || '',
          resultUrl: absoluteApiUrl(content.downloadUrl || content.fileUrl || content.videoUrl || selected.url || ''),
          resolution: content.resolution || result.content?.resolution || '720p',
          resourceType: selected.type || task.taskType || '',
        },
        feedbackRating: 0,
        feedbackNote: '',
      })
    } catch (error) {
      this.setData({ error: error.message })
    } finally {
      wx.hideLoading()
    }
  },
  closeTask() { this.setData({ selectedTask: null }) },
  noop() {},
  chooseRating(e) { this.setData({ feedbackRating: Number(e.currentTarget.dataset.rating) }) },
  feedbackInput(e) { this.setData({ feedbackNote: e.detail.value }) },
  async submitFeedback() {
    const task = this.data.selectedTask
    if (!task || !this.data.feedbackRating) return
    this.setData({ feedbackSaving: true, error: '' })
    try {
      await api.submitFeedback({
        taskId: task.taskId,
        topic: task.resultTitle || task.title,
        rating: this.data.feedbackRating,
        note: this.data.feedbackNote.trim(),
        outcome: 'completed',
        resourceType: task.resourceType || task.taskType,
      })
      wx.showToast({ title: '学习反馈已记录', icon: 'success' })
      this.setData({ feedbackRating: 0, feedbackNote: '' })
    } catch (error) {
      this.setData({ error: error.message })
    } finally {
      this.setData({ feedbackSaving: false })
    }
  },
  async startVideo() {
    const task = this.data.selectedTask
    if (!task || task.status !== 'waiting' || task.taskType !== 'generated_video') return
    const confirmed = await new Promise(resolve => wx.showModal({
      title: '确认生成 AI 视频',
      content: `将按 ${task.resolution || '720p'} 启动媒体模型并在后台生成，是否继续？`,
      confirmText: '确认启动',
      success: result => resolve(result.confirm),
    }))
    if (!confirmed) return
    this.setData({ startingVideo: true, error: '' })
    try {
      await api.startVideoTask(task.taskId, { model: 'seedance-1.5', resolution: task.resolution || '720p' })
      wx.showToast({ title: '视频任务已启动', icon: 'success' })
      await this.openTask({ currentTarget: { dataset: { id: task.taskId } } })
      await this.loadTasks(true)
    } catch (error) {
      this.setData({ error: error.message })
    } finally {
      this.setData({ startingVideo: false })
    }
  },
  copyResult() {
    const task = this.data.selectedTask
    const text = task?.resultUrl || task?.resultSummary || ''
    if (text) wx.setClipboardData({ data: text })
  },
})
