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
      title: '中医基础理论与整体观念',
      description: '理解阴阳五行、藏象与气血津液的核心关系',
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
      title: '八纲辨证基础',
      description: '围绕表里、寒热、虚实、阴阳建立辨证框架',
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
      title: '四诊合参与舌脉辨析',
      description: '归纳望闻问切信息并形成证候判断依据',
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
      title: '中药性味归经',
      description: '掌握常用中药功效、归经与配伍注意事项',
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
      title: '方剂组成与配伍',
      description: '结合君臣佐使分析常用方剂组成与功效',
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
      title: '综合医案辨析与复盘',
      description: '完成医案辨证、治法方药推演并复盘证据链',
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
  ['目标拆解', '查看画像', '/learning-profile', '把本周主题拆成理论、辨证、医案和测评目标，明确验收标准。'],
  ['概念建模', '生成导图', '/personalized-resources/mind-map', '围绕本周主题整理知识结构图，标出关键概念、前置知识和易错点。'],
  ['案例跟学', '查看资源', '/personalized-resources', '跟随一个典型医案，理解四诊信息、病机、治法和方药之间的关系。'],
  ['医案辨析', '生成辨析课件', '/personalized-resources/ppt', '完成一个基础医案辨析，记录证候依据、鉴别要点和治法方药。'],
  ['专项测评', '进入测评', '/personalized-resources/question-bank', '完成针对性题目或医案辨析题，检查本周知识是否真正掌握。'],
  ['复盘迭代', '整理资源', '/personalized-resources', '整理错因、医案证据和下一周要继续追踪的问题。'],
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
// Keep frontend-only fallback neutral so it cannot reintroduce a fixed course week.
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
