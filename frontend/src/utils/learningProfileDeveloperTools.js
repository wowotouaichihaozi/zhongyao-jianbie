export const LEARNING_PROFILE_DEVELOPER_DIMENSIONS = Object.freeze({
  '专业/课程背景': '中医学专业大二学生，当前学习《中医诊断学》与中药学基础',
  '学习目标': ['夯实辨证基础', '准备期末考试', '提升病例分析能力'],
  '当前知识基础': '掌握阴阳五行、藏象与常见中药功效，四诊合参与证型判断仍需加强',
  '学习进度': '已完成望诊、闻诊和问诊基础，正在学习脉诊及八纲辨证',
  '薄弱知识点': ['脉象鉴别', '寒热真假辨析', '相似证型区分'],
  '易错点类型': ['概念混淆', '证据遗漏', '辨证结论过早'],
  '学习风格/认知偏好': ['案例驱动', '图示归纳', '先理解后记忆'],
  '资源形式偏好': ['知识图谱', '短视频讲解', '情境化练习题'],
  '可投入时间': '工作日每天 60 分钟，周末每天 2 小时',
  '难度接受程度': '中等偏难，希望先给思路提示，再独立完成综合病例',
  '补充信息': {
    fixture: true,
    purpose: 'developer-testing',
  },
})

export function createLearningProfileDeveloperFixture(now = Date.now()) {
  const dimensions = structuredClone(LEARNING_PROFILE_DEVELOPER_DIMENSIONS)
  const summary = '中医学专业大二学生，正在学习中医诊断学与中药学基础，目标是巩固辨证知识并提升病例分析能力。偏好案例、图示和短视频，每周可稳定投入约九小时。'
  const messages = [
    {
      id: `developer-user-${now}`,
      role: 'user',
      text: '请使用开发测试画像快速补全十个学习维度。',
      timestamp: now,
      source: 'developer-fixture',
      attachments: [],
    },
    {
      id: `developer-bot-${now}`,
      role: 'bot',
      text: '十个学习画像维度已使用本地测试数据补全。你可以继续修改信息，或前往画像报告生成正式分析。',
      timestamp: now + 1,
      source: 'developer-fixture',
      attachments: [],
    },
  ]

  return {
    dimensions,
    summary,
    scaleScores: [4, 4, 3, 3, 4, 3],
    messages,
    chatHistory: messages.map(message => ({
      role: message.role === 'bot' ? 'assistant' : 'user',
      content: message.text,
    })),
  }
}

export function isLearningProfileDeveloperShortcut(event) {
  return event?.key === 'F4' && !event.ctrlKey && !event.altKey && !event.metaKey
}
