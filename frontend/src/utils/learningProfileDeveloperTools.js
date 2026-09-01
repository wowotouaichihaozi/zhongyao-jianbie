export const LEARNING_PROFILE_DEVELOPER_DIMENSIONS = Object.freeze({
  '专业/课程背景': '电子信息工程专业大二学生，正在学习单片机与嵌入式系统基础',
  '学习目标': ['掌握 STM32 常用外设', '提升软硬件调试能力', '完成嵌入式综合项目'],
  '当前知识基础': '具备 C 语言基础，能够阅读基础例程，GPIO、中断和串口通信仍需加强',
  '学习进度': '已完成开发环境搭建和点灯实验，正在学习 GPIO 输入与外部中断',
  '薄弱知识点': ['GPIO 模式配置', '串口通信', '中断优先级与调试'],
  '易错点类型': ['时钟使能遗漏', '引脚与寄存器配置错误', '调试证据不足'],
  '学习风格/认知偏好': ['分步骤讲解', '代码例程驱动', '先实验再复盘'],
  '资源形式偏好': ['单片机实验', '代码例程', '短视频讲解'],
  '可投入时间': '工作日每天 2 小时，周末每天 5 小时',
  '难度接受程度': '中等偏难，希望先完成可运行的基础实验，再独立调试综合项目',
  '补充信息': {
    fixture: true,
    purpose: 'developer-testing',
  },
})

export function createLearningProfileDeveloperFixture(now = Date.now()) {
  const dimensions = structuredClone(LEARNING_PROFILE_DEVELOPER_DIMENSIONS)
  const summary = '电子信息工程专业大二学生，正在学习单片机与嵌入式系统，目标是掌握 STM32 常用外设并提升软硬件调试能力。偏好分步骤讲解、代码例程和实验实践，每周可稳定投入约二十小时。'
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
