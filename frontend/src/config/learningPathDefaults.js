export const defaultLearningPathConfig = {
  version: 1,
  meta: {
    eyebrow: '学习路径',
    title: '智能周学习路径',
    placeholderWeekLabel: '...',
    placeholderTitle: '后续周数',
  },
  planner: {
    agent: 'learning-path-planner-agent',
    source: 'default-rule',
    division: ['目标拆解', '概念建模', '示例跟做', '实操验证', '专项测评', '复盘迭代'],
  },
  weeks: [
    {
      id: 'week-1-embedded-foundation',
      order: 1,
      weekLabel: '第一周',
      title: '嵌入式基础与开发环境',
      description: '完成目标拆解、概念建模、示例跟做和第一次实操验证',
      status: 'current',
      icon: 'cpu',
      tone: 'green',
      xp: 150,
      enabled: true,
      placeholder: false,
    },
    {
      id: 'week-2-gpio-practice',
      order: 2,
      weekLabel: '第二周',
      title: 'GPIO 输入输出实操',
      description: '围绕 GPIO 建立配置思路并完成可运行实验',
      status: 'locked',
      icon: 'book-open',
      tone: 'green',
      xp: 180,
      enabled: true,
      placeholder: false,
    },
    {
      id: 'week-3-uart-debug',
      order: 3,
      weekLabel: '第三周',
      title: '串口通信与调试链路',
      description: '跑通串口收发、日志输出和调试定位流程',
      status: 'locked',
      icon: 'clipboard-check',
      tone: 'green',
      xp: 210,
      enabled: true,
      placeholder: false,
    },
    {
      id: 'week-4-timer-interrupt',
      order: 4,
      weekLabel: '第四周',
      title: '定时器 PWM 与中断响应',
      description: '完成定时器、PWM、中断的案例跟做和专项测评',
      status: 'locked',
      icon: 'target',
      tone: 'green',
      xp: 240,
      enabled: true,
      placeholder: false,
    },
    {
      id: 'week-5-sensor-project',
      order: 5,
      weekLabel: '第五周',
      title: '传感器采集与项目案例',
      description: '把传感器采集、数据处理和小项目联调结合起来',
      status: 'locked',
      icon: 'layers',
      tone: 'green',
      xp: 270,
      enabled: true,
      placeholder: false,
    },
    {
      id: 'week-6-integrated-training',
      order: 6,
      weekLabel: '第六周',
      title: '综合项目实训与复盘',
      description: '完成综合任务、整理证据并更新下一轮学习重点',
      status: 'locked',
      icon: 'rocket',
      tone: 'green',
      xp: 320,
      enabled: true,
      placeholder: false,
    },
  ],
  stages: {},
}

const defaultStageNodeCoords = [
  { x: 112, y: 420, popX: 180, popY: 250 },
  { x: 402, y: 292, popX: 402, popY: 122 },
  { x: 646, y: 316, popX: 646, popY: 270 },
  { x: 942, y: 369, popX: 942, popY: 198 },
  { x: 1188, y: 284, popX: 1188, popY: 114 },
  { x: 1398, y: 185, popX: 1260, popY: 112 },
]

const defaultStageNodeBlueprints = [
  ['目标拆解', '查看画像', '/learning-profile', '把本周主题拆成概念、代码、实验和测评目标，明确验收标准。'],
  ['概念建模', '生成导图', '/personalized-resources/mind-map', '围绕本周主题整理知识结构图，标出关键概念、前置知识和易错点。'],
  ['示例跟做', '查看资源', '/personalized-resources', '跟做一个最小可运行示例，理解配置流程、关键代码和运行现象。'],
  ['实操验证', '进入实验', '/personalized-resources/mcu-simulator', '在开发板或模拟器完成一个小实验，记录代码、接线和现象。'],
  ['专项测评', '进入测评', '/personalized-resources/question-bank', '完成针对性题目或代码改错题，检查本周知识是否真正掌握。'],
  ['复盘迭代', '整理资源', '/personalized-resources', '整理错因、实验证据和下一周要继续追踪的问题。'],
]

function createDefaultStage(week) {
  return {
    id: week.id,
    weekLabel: week.weekLabel,
    title: `${week.weekLabel}学习路径`,
    hint: '点击节点查看任务',
    board: {
      width: 1440,
      height: 640,
      initialScale: 1,
      minScale: 0.68,
      maxScale: 1.42,
    },
    nodes: defaultStageNodeBlueprints.map(([title, actionText, actionRoute, description], index) => {
      const coords = defaultStageNodeCoords[index]
      const state = index === 0 ? 'done' : (index === 1 && week.order === 1 ? 'current' : 'locked')
      return {
        id: String(index + 1).padStart(2, '0'),
        label: String(index + 1).padStart(2, '0'),
        title,
        statusText: state === 'done' ? '已完成' : (state === 'current' ? '进行中' : '待解锁'),
        description: `${week.weekLabel} · ${week.title}：${description}`,
        state,
        ...coords,
        actionText,
        actionRoute,
      }
    }),
  }
}

defaultLearningPathConfig.stages = Object.fromEntries(
  defaultLearningPathConfig.weeks.map((week) => [week.id, createDefaultStage(week)]),
)

// The backend planner supplies the actual profile-based weeks and task nodes.
// Keep frontend-only fallback neutral so it cannot reintroduce a fixed STM32 week.
defaultLearningPathConfig.version = 2
defaultLearningPathConfig.meta = {
  ...defaultLearningPathConfig.meta,
  title: '个性化周学习计划',
  needsRegeneration: true,
  refreshRecommended: false,
  persisted: false,
  savedAt: '',
  generationState: 'idle',
  taskResourceModel: 'profile-routed-resources-v13-semantic-fingerprint-video-coverage',
  totalWeeks: 6,
}
defaultLearningPathConfig.planner = {
  agent: 'learning-path-planner-agent',
  source: 'bootstrap',
  division: [],
}
defaultLearningPathConfig.weeks = []
defaultLearningPathConfig.stages = {}

export function cloneLearningPathConfig(config = defaultLearningPathConfig) {
  return JSON.parse(JSON.stringify(config))
}
