const api = require('../../utils/api')
const data = require('../../utils/data')

Page({
  data: {
    question: '', followUp: '', loading: false, error: '', answer: null,
    waitingStages: ['理解问题与学习上下文', '检索课程知识依据', '编排讲解与练习', '执行内容质量审核'],
    waitingIndex: 0,
  },
  onUnload() { this.stopWaiting() },
  input(e) { this.setData({ [e.currentTarget.dataset.field]: e.detail.value }) },
  startWaiting() {
    this.stopWaiting()
    this.setData({ waitingIndex: 0 })
    this.waiter = setInterval(() => this.setData({ waitingIndex: Math.min(this.data.waitingStages.length - 1, this.data.waitingIndex + 1) }), 3500)
  },
  stopWaiting() { if (this.waiter) clearInterval(this.waiter); this.waiter = null },
  async ask(e) {
    const followUp = Boolean(e?.currentTarget?.dataset?.followup)
    const text = (followUp ? this.data.followUp : this.data.question).trim()
    if (!text || this.data.loading) return
    this.setData({ loading: true, error: '' })
    this.startWaiting()
    try {
      const previous = this.data.answer || {}
      const response = await api.tutor({
        question: text,
        previousQuestion: previous.question || '',
        previousAnswer: previous.answerText || '',
        followUp,
      })
      const raw = data.body(response)
      const result = raw.result || raw
      const explanation = result.explanation || {}
      const answerText = result.answer || result.reply || result.summary || explanation.concept || (typeof explanation === 'string' ? explanation : '')
      const rawReferences = result.references || result.citations || result.knowledgeSources || []
      const references = (Array.isArray(rawReferences) ? rawReferences : []).map((item, index) => ({
        label: typeof item === 'string' ? item : (item.title || item.source || item.name || `来源 ${index + 1}`),
        detail: typeof item === 'object' ? (item.location || item.version || item.url || '') : '',
      }))
      const quality = result.qualityEvaluation || result.review || {}
      const steps = Array.isArray(explanation.steps) ? explanation.steps : []
      const practice = Array.isArray(result.practice) ? result.practice.map(item => typeof item === 'string' ? item : (item.question || item.title || '练习题')) : []
      const socratic = Array.isArray(result.socraticQuestions) ? result.socraticQuestions.map(item => typeof item === 'string' ? item : item.question) : []
      this.setData({
        answer: {
          question: text,
          title: result.title || '智能辅导回答',
          answerText: answerText || '服务端已返回结果，但没有可展示的回答文本。',
          analogy: explanation.analogy || '',
          steps,
          practice,
          socratic,
          references,
          qualityScore: Number(quality.score || 0),
          grounded: references.length > 0,
        },
        followUp: followUp ? '' : this.data.followUp,
      })
    } catch (error) {
      this.setData({ error: error.message })
    } finally {
      this.stopWaiting()
      this.setData({ loading: false })
    }
  },
})
