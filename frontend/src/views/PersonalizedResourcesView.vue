<template>
  <div class="resources-page">
    <div class="resources-header">
      <h1>个性化资源</h1>
      <p>基于学习画像智能推荐适配当前水平的学习资料</p>
    </div>

    <!-- 无学习画像引导提示条 -->
    <div v-if="!hasProfile" class="no-profile-banner">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="banner-icon">
        <path d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span>完成学习画像后才能生成个性化资源；已生成的历史资源仍可查看</span>
      <button class="banner-btn" @click="$router.push('/learning-profile')">前往评估</button>
    </div>

    <!-- 资源列表 -->
    <section class="resource-tools-section" aria-labelledby="resource-tools-title">
      <div class="resource-tools-head">
        <div>
          <h2 id="resource-tools-title">资源生成工具</h2>
          <p>从这里进入题库、课件、导图、视频生成和视频检索工具，独立页面更专注。</p>
        </div>
      </div>
      <div class="resource-tools-grid">
        <RouterLink
          v-for="tool in resourceTools"
          :key="tool.to"
          class="resource-tool-card"
          :class="tool.tone"
          :to="tool.to"
          target="_blank"
          rel="noopener noreferrer"
        >
          <span class="resource-tool-icon">
            <component :is="tool.icon" :size="28" :stroke-width="2.2" aria-hidden="true" />
          </span>
          <span class="resource-tool-copy">
            <strong>{{ tool.title }}</strong>
            <em>{{ tool.description }}</em>
          </span>
          <ArrowRight :size="20" :stroke-width="2.2" aria-hidden="true" />
        </RouterLink>
      </div>
    </section>

    <div class="resources-content">
      <div class="history-resources-head">
        <h2>历史资源</h2>
      </div>
      <!-- 分类标签栏 -->
      <div class="category-tabs">
        <button
          v-for="cat in categories"
          :key="cat.key"
          :class="['tab-btn', { active: activeCategory === cat.key }]"
          @click="activeCategory = cat.key"
        >
          {{ cat.label }}
        </button>
      </div>

      <!-- 操作栏 -->
      <div class="action-bar">
        <span class="resource-count">共 {{ filteredResources.length }} 个资源</span>
        <button class="generate-btn" @click="generateNewResource" :disabled="generating || !hasProfile">
          <svg v-if="!generating" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 4v16m8-8H4" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span v-if="generating" class="loading-spinner"></span>
          {{ generating ? '生成中...' : '生成新资源' }}
        </button>
      </div>

      <!-- 资源卡片网格 -->
      <div class="resources-grid">
        <div
          v-for="resource in filteredResources"
          :key="resource.id"
          class="resource-card"
          @click="openResource(resource)"
        >
          <div
            class="card-icon"
            :style="{
              background: getTypeColor(resource.type),
              color: getTypeIconColor(resource.type),
            }"
          >
            <svg v-if="resource.type === 'mindmap'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M4 6h16M4 12h10m-10 6h16" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="resource.type === 'ppt'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V7M3 7l9-4 9 4M3 7l9 4 9-4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="resource.type === 'video' || resource.type === 'generated_video'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="resource.type === 'animation'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="3" y="5" width="18" height="14" rx="2" />
              <path d="m10 9 5 3-5 3V9Z" stroke-linecap="round" stroke-linejoin="round" />
              <path d="M7 3v2m10-2v2M7 19v2m10-2v2" stroke-linecap="round" />
            </svg>
            <svg v-else-if="resource.type === 'code'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else-if="resource.type === 'simulator'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M9 3h6v3h3a2 2 0 012 2v8a2 2 0 01-2 2h-3v3H9v-3H6a2 2 0 01-2-2V8a2 2 0 012-2h3V3zM8 11h2m4 0h2M8 15h8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="card-content">
            <h3>{{ resource.title }}</h3>
            <p class="card-desc">{{ resource.description }}</p>
            <div class="card-footer">
              <span class="type-tag">{{ getTypeName(resource.type) }}</span>
              <time v-if="resource.createdAt" class="history-time" :datetime="resource.createdAt">
                {{ formatResourceTime(resource.createdAt) }}
              </time>
              <span class="match-score" :style="{ color: getMatchColor(resource.matchScore) }">
                匹配度 {{ resource.matchScore }}%
              </span>
              <span v-if="resourceQuality(resource).score" class="quality-badge">
                质量 {{ resourceQuality(resource).score }}
              </span>
              <span v-if="resourceCitationCount(resource)" class="citation-badge">
                引用 {{ resourceCitationCount(resource) }}
              </span>
              <span v-if="getEvaluation(resource.id)" class="learned-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                已学习
                <span class="badge-stars">
                  <svg v-for="s in 5" :key="s" viewBox="0 0 24 24" :fill="s <= getEvaluation(resource.id).rating ? '#f59e0b' : 'none'" :stroke="s <= getEvaluation(resource.id).rating ? '#f59e0b' : '#cbd5e1'" stroke-width="2" class="mini-star">
                    <path d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
                  </svg>
                </span>
              </span>
            </div>
          </div>
          <div class="card-arrow">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="filteredResources.length === 0" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <p>该分类暂无资源，点击"生成新资源"创建</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, markRaw, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, BookOpenCheck, Clapperboard, Cpu, Presentation, Search, Share2 } from 'lucide-vue-next'
import {
  getLearningProfiles,
  getGeneratedVideoTaskHistory,
  getXiaoZhiHistory,
  getXiaoZhiTask,
  startPersonalizedResourceAgentTask,
} from '../services/api.js'

const router = useRouter()
const route = useRoute()

const resourceTools = [
  {
    title: 'AI 视频课程',
    description: '按学习画像生成讲解视频，自动配音、字幕与服务端剪辑。',
    to: '/personalized-resources/video-generator',
    icon: markRaw(Clapperboard),
    tone: 'tool-teal',
  },
  {
    title: '题库生成',
    description: '按章节和难度快速生成练习题单与考试。',
    to: '/personalized-resources/question-bank',
    icon: markRaw(BookOpenCheck),
    tone: 'tool-green',
  },
  {
    title: 'PPT生成',
    description: '根据主题和材料生成课程演示文稿。',
    to: '/personalized-resources/ppt',
    icon: markRaw(Presentation),
    tone: 'tool-blue',
  },
  {
    title: '思维导图',
    description: '把知识点整理成结构清晰的学习导图。',
    to: '/personalized-resources/mind-map',
    icon: markRaw(Share2),
    tone: 'tool-purple',
  },
  {
    title: '视频查找',
    description: '检索适合当前学习阶段的讲解视频。',
    to: '/personalized-resources/video-search',
    icon: markRaw(Search),
    tone: 'tool-teal',
  },
  {
    title: '单片机模拟器',
    description: '进入独立实验台，完成 Arduino 与 8051 单片机仿真实验。',
    to: '/personalized-resources/mcu-simulator',
    icon: markRaw(Cpu),
    tone: 'tool-orange',
  },
]

const categories = [
  { key: 'all', label: '全部' },
  { key: 'mindmap', label: '思维导图' },
  { key: 'ppt', label: 'PPT' },
  { key: 'video', label: '视频' },
  { key: 'generated_video', label: 'AI 视频生成' },
  { key: 'quiz', label: '练习题' },
  { key: 'simulator', label: '模拟器实验' },
]

const requestedCategory = String(route.query.category || '')
const activeCategory = ref(categories.some(item => item.key === requestedCategory) ? requestedCategory : 'all')
const generating = ref(false)
const resources = ref([])
const hasProfile = ref(false)
const profileData = ref(null)
const evaluations = ref([])
const hiddenResourceTypes = new Set(['document', 'animation', 'code'])

onMounted(async () => {
  loadEvaluations()
  await Promise.all([loadProfile(), loadResources()])
})

async function loadProfile() {
  try {
    const data = await getLearningProfiles()
    const activeId = Number(data?.activeReportId || 0)
    const activeProfile = (data?.profiles || []).find(item => Number(item?.id || 0) === activeId) || null
    hasProfile.value = Boolean(activeProfile)
    profileData.value = activeProfile
  } catch {
    hasProfile.value = false
    profileData.value = null
  }
}

async function loadResources() {
  const [historyResult, videoResult] = await Promise.allSettled([
    getXiaoZhiHistory(100),
    loadAllCompletedGeneratedVideos(),
  ])
  const response = historyResult.status === 'fulfilled' ? historyResult.value : {}
  const generatedVideoTasks = videoResult.status === 'fulfilled' ? videoResult.value : []
  const generatedVideoResources = generatedVideoTasks.flatMap(extractTaskResources)
  const backendResources = (response?.data?.tasks || []).flatMap(extractTaskResources)
  let legacyResources = []
  try {
    const saved = localStorage.getItem('personalizedResources')
    legacyResources = saved
      ? JSON.parse(saved).filter(item => item?.source === 'workflow-real-data' || item?.metadata)
      : []
  } catch {}
  const seen = new Set()
  resources.value = sortResourceHistory(
    [...generatedVideoResources, ...backendResources, ...legacyResources].filter(item => {
      const key = String(item?.id || `${item?.type}:${item?.title}`)
      if (!item || seen.has(key)) return false
      seen.add(key)
      return true
    }),
  )
}

async function loadAllCompletedGeneratedVideos() {
  const tasks = []
  let offset = 0
  while (true) {
    const page = await getGeneratedVideoTaskHistory({ status: 'complete', limit: 100, offset })
    const pageTasks = Array.isArray(page?.tasks) ? page.tasks : []
    tasks.push(...pageTasks)
    if (!page?.hasMore || pageTasks.length === 0) break
    offset += pageTasks.length
  }
  return tasks
}

function sortResourceHistory(items) {
  return [...items].sort((left, right) => {
    const leftTime = Date.parse(left?.createdAt || '') || 0
    const rightTime = Date.parse(right?.createdAt || '') || 0
    return rightTime - leftTime
  })
}

function loadEvaluations() {
  try {
    const raw = localStorage.getItem('resourceEvaluations')
    if (raw) evaluations.value = JSON.parse(raw)
  } catch {}
}

function getEvaluation(resourceId) {
  return evaluations.value.find(e => e.resourceId === resourceId)
}

function saveResources() {
  localStorage.setItem('personalizedResources', JSON.stringify(resources.value))
}

const taskResourceTypes = {
  question_bank: 'quiz',
  ppt: 'ppt',
  document: 'document',
  mindmap: 'mindmap',
  video: 'video',
  generated_video: 'generated_video',
  animation: 'animation',
  mcu: 'simulator',
}

function extractTaskResources(task) {
  if (!task || task.status !== 'complete') return []
  const result = task.result && typeof task.result === 'object' ? task.result : {}
  const taskType = String(task.taskType || '')
  let items = []

  if (taskType === 'personalized_resources') {
    items = Array.isArray(result.workflow?.resources) ? result.workflow.resources : []
  } else if (result.selectedResource && typeof result.selectedResource === 'object') {
    items = [result.selectedResource]
  } else if (taskType === 'generated_video') {
    const content = result.content && typeof result.content === 'object' ? result.content : {}
    items = [{
      type: 'generated_video',
      title: task.title,
      description: result.message || 'AI 讲解视频已生成并保存',
      content: {
        ...content,
        videoUrl: content.videoUrl || `/api/personalized-resources/generated-videos/${encodeURIComponent(task.taskId)}/file`,
        posterUrl: content.posterUrl || `/api/personalized-resources/generated-videos/${encodeURIComponent(task.taskId)}/poster`,
      },
      metadata: { taskId: task.taskId },
    }]
  } else {
    const payloadByType = {
      question_bank: result.questionGenerator,
      ppt: result.ppt,
      document: result.document,
      animation: result.animation,
    }
    const payload = payloadByType[taskType]
    if (payload && typeof payload === 'object') {
      items = [{
        type: taskResourceTypes[taskType],
        title: task.title,
        description: result.message,
        content: payload,
      }]
    }
  }

  const reviewScore = Number(result.orchestration?.review?.score || 0)
  return items.map((item, index) => {
    const itemType = String(item?.type || taskResourceTypes[taskType] || 'document')
    const route = String(item?.route || item?.actionRoute || (taskType !== 'personalized_resources' ? task.route : '') || '')
    return {
      id: `task:${task.taskId}:${item?.id || index}`,
      title: item?.title || task.title || getDefaultTitle(itemType),
      description: item?.description || result.message || getDefaultDesc(itemType),
      type: itemType,
      matchScore: Number(item?.matchScore || reviewScore || 80),
      content: item?.content ?? item,
      route,
      agent: result.orchestrator || 'xiaozhi-companion-agent',
      source: 'xiaozhi-task',
      metadata: {
        ...(item?.metadata || {}),
        taskId: task.taskId,
        runId: result.orchestration?.runId || '',
        reviewScore,
      },
      qualityEvaluation: item?.qualityEvaluation || item?.metadata?.qualityEvaluation || result.qualityEvaluation || {},
      knowledgeSources: item?.knowledgeSources || item?.metadata?.knowledgeSources || result.knowledgeSources || [],
      createdAt: task.createdAt || task.updatedAt || '',
    }
  })
}

function resourceQuality(resource) {
  const quality = resource?.qualityEvaluation || resource?.metadata?.qualityEvaluation
  return quality && typeof quality === 'object' ? quality : {}
}

function resourceCitationCount(resource) {
  const qualityCount = Number(resourceQuality(resource).citationCount || 0)
  const sources = Array.isArray(resource?.knowledgeSources)
    ? resource.knowledgeSources
    : (Array.isArray(resource?.metadata?.knowledgeSources) ? resource.metadata.knowledgeSources : [])
  return Math.max(qualityCount, sources.length)
}

function initDefaultResources() {
  const defaults = [
    {
      id: Date.now(),
      title: 'STM32基础知识思维导图',
      description: '涵盖STM32架构、GPIO、定时器等核心知识点',
      type: 'mindmap',
      matchScore: 85,
      content: `mindmap
  root((STM32))
    架构
      Cortex-M3
      寄存器
      时钟系统
    GPIO
      输入模式
      输出模式
      复用功能
    定时器
      基本定时器
      通用定时器
      高级定时器
    通信
      USART
      SPI
      I2C`,
      createdAt: new Date().toISOString(),
    },
    {
      id: Date.now() + 1,
      title: '嵌入式C语言编程基础',
      description: '适合初学者的C语言PPT课件，包含指针、数组、结构体',
      type: 'ppt',
      matchScore: 78,
      content: `# 嵌入式C语言编程基础

## 第一页：C语言概述
- C语言是嵌入式开发的首选语言
- 特点：效率高、可移植性强、贴近硬件

## 第二页：数据类型
- int, char, float, double
- 指针类型
- 结构体

## 第三页：指针基础
- 指针是C语言的核心概念
- 指针与数组的关系
- 指针运算

## 第四页：结构体
- 结构体定义与使用
- 结构体指针
- 内存对齐

## 第五页：总结
- 掌握C语言是嵌入式开发的基础
- 多练习，多实践`,
      createdAt: new Date().toISOString(),
    },
    {
      id: Date.now() + 2,
      title: 'STM32 GPIO操作视频教程',
      description: '通过LED闪烁项目学习GPIO配置与操作',
      type: 'video',
      matchScore: 90,
      content: `# STM32 GPIO操作视频教程

## 课程大纲

### 第1节：GPIO概念介绍
- 什么是GPIO
- GPIO的工作模式
- 输入/输出配置

### 第2节：开发环境搭建
- 安装Keil MDK
- 配置STM32CubeMX
- 新建工程

### 第3节：LED闪烁代码
\`\`\`c
// 初始化GPIO
void LED_Init(void) {
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    __HAL_RCC_GPIOC_CLK_ENABLE();
    GPIO_InitStruct.Pin = GPIO_PIN_13;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);
}
\`\`\`

### 第4节：编译下载运行
- 编译项目
- 下载到开发板
- 观察LED闪烁效果

### 第5节：练习与总结
- 修改闪烁频率
- 添加多个LED控制`,
      createdAt: new Date().toISOString(),
    },
    {
      id: Date.now() + 3,
      title: 'STM32 UART串口通信示例',
      description: '完整的串口收发代码，带详细注释',
      type: 'code',
      matchScore: 82,
      content: `# STM32 UART串口通信示例

## uart_example.c

\`\`\`c
#include "stm32f1xx_hal.h"
#include <string.h>

UART_HandleTypeDef huart1;

// UART初始化
void UART1_Init(void) {
    huart1.Instance = USART1;
    huart1.Init.BaudRate = 115200;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    HAL_UART_Init(&huart1);
}

// 发送字符串
void UART_SendString(char *str) {
    HAL_UART_Transmit(&huart1, (uint8_t *)str, strlen(str), 1000);
}

// 接收数据
uint8_t rxBuffer[1];
void UART_Receive(void) {
    HAL_UART_Receive_IT(&huart1, rxBuffer, 1);
}

// 主函数
int main(void) {
    HAL_Init();
    SystemClock_Config();
    UART1_Init();
    UART_SendString("Hello STM32!\\r\\n");

    while (1) {
        UART_Receive();
        HAL_Delay(100);
    }
}
\`\`\`

## 关键点说明
1. 波特率设置为115200
2. 使用中断方式接收数据
3. 发送使用阻塞方式`,
      createdAt: new Date().toISOString(),
    },
    {
      id: Date.now() + 4,
      title: 'GPIO配置练习题',
      description: '检验GPIO配置知识掌握程度',
      type: 'quiz',
      matchScore: 88,
      content: `# GPIO配置练习题

## 题目1：GPIO模式选择
**问题：** 在STM32中，如果要读取一个按键的状态，GPIO应该配置为哪种模式？

A. 推挽输出
B. 开漏输出
C. 上拉输入
D. 模拟输入

**答案：** C. 上拉输入
**解析：** 按键通常需要读取高/低电平，使用上拉输入模式，按键未按下时为高电平，按下时为低电平。

---

## 题目2：GPIO速度配置
**问题：** LED闪烁项目中，GPIO的输出速度应该设置为？

A. 低速
B. 中速
C. 高速
D. 以上都可以

**答案：** A. 低速
**解析：** LED控制不需要高速翻转，低速即可满足需求，还能降低功耗。

---

## 题目3：复用功能
**问题：** STM32的UART1_TX引脚通常对应哪个引脚？

A. PA9
B. PA10
C. PB6
D. PB7

**答案：** A. PA9
**解析：** STM32F103系列中，USART1_TX默认复用在PA9引脚。`,
      createdAt: new Date().toISOString(),
    },
  ]

  resources.value = defaults
  saveResources()
}

const filteredResources = computed(() => {
  const visibleResources = resources.value.filter(r => !hiddenResourceTypes.has(String(r?.type || '')))
  if (activeCategory.value === 'all') return visibleResources
  return visibleResources.filter(r => r.type === activeCategory.value)
})

function getTypeName(type) {
  const names = {
    document: '课程讲义',
    mindmap: '思维导图',
    ppt: 'PPT',
    video: '视频',
    generated_video: 'AI 视频生成',
    animation: '动画微课',
    code: '代码示例',
    quiz: '练习题',
    simulator: '模拟器实验',
  }
  return names[type] || type
}

const resourceTypePalettes = {
  document: { background: '#eef2ff', foreground: '#4f46e5' },
  mindmap: { background: '#f3e8ff', foreground: '#7c3aed' },
  ppt: { background: '#e8f1ff', foreground: '#2563eb' },
  video: { background: '#e5f8f6', foreground: '#0f8f8a' },
  generated_video: { background: '#dff4f1', foreground: '#0e777d' },
  animation: { background: '#fff0f3', foreground: '#c2415d' },
  code: { background: '#e8f7ef', foreground: '#177a4e' },
  quiz: { background: '#fff7df', foreground: '#a16207' },
  simulator: { background: '#fff1e7', foreground: '#d66a08' },
}

function getTypeColor(type) {
  return resourceTypePalettes[type]?.background || '#eef3f1'
}

function getTypeIconColor(type) {
  return resourceTypePalettes[type]?.foreground || '#176f4b'
}

function getMatchColor(score) {
  return score >= 80 ? '#202424' : score >= 60 ? '#555c5b' : '#747b7a'
}

function openResource(resource) {
  const target = String(resource?.route || '')
  if (target) {
    if (/^https?:\/\//i.test(target)) {
      window.open(target, '_blank', 'noopener,noreferrer')
    } else if (resource?.type === 'generated_video') {
      window.open(router.resolve(target).href, '_blank', 'noopener,noreferrer')
    } else {
      router.push(target)
    }
    return
  }
  localStorage.setItem('currentResourceDetail', JSON.stringify(resource))
  router.push({ name: 'resource-detail', query: { id: resource.id } })
}

function wait(milliseconds) {
  return new Promise(resolve => window.setTimeout(resolve, milliseconds))
}

async function waitForResourceTask(taskId) {
  for (let attempt = 0; attempt < 180; attempt += 1) {
    const response = await getXiaoZhiTask(taskId)
    const task = response?.data?.task
    if (!task) throw new Error('后台资源任务不存在')
    if (task.status === 'complete') return task
    if (task.status === 'failed') throw new Error(task.error || task.result?.qualityError || '资源任务未通过审核')
    await wait(1500)
  }
  throw new Error('资源任务仍在后台运行，请稍后在历史资源中查看')
}

async function generateNewResource() {
  if (generating.value) return
  generating.value = true

  try {
    if (!hasProfile.value) {
      router.push('/learning-profile')
      return
    }
    const analysis = profileData.value?.aiAnalysis || {}
    const focus = analysis.weaknesses?.[0] || analysis.weakPoints?.[0] || '当前学习目标与薄弱点'
    const response = await startPersonalizedResourceAgentTask({
      resourceType: 'personalized_resources',
      topic: `${focus}个性化资源包`,
      prompt: '根据当前激活画像、学习路径与最近学习证据生成多类型资源包。',
      params: {
        profileReportId: profileData.value?.id,
      },
    })
    const task = response?.data?.task
    if (!task?.taskId) throw new Error('资源智能体未创建后台任务')
    await waitForResourceTask(task.taskId)
    await loadResources()
  } catch (e) {
    console.error('生成资源失败:', e)
    const msg = e.message || '生成失败，请稍后重试'
    alert(msg.includes('AI API') ? msg : `生成失败：${msg}`)
  } finally {
    generating.value = false
  }
}

function getDefaultTitle(type) {
  const titles = {
    mindmap: '嵌入式学习思维导图',
    ppt: '嵌入式学习课件',
    video: '嵌入式视频教程',
    generated_video: 'AI 学习讲解视频',
    code: '嵌入式代码示例',
    quiz: '嵌入式练习题',
  }
  return titles[type]
}

function getDefaultDesc(type) {
  return `基于您的学习画像生成的${getTypeName(type)}资源`
}

function formatResourceTime(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
</script>

<style scoped>
.resources-page {
  position: relative;
  height: calc(100vh - 72px);
  min-height: calc(100vh - 72px);
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
  background: #f8f8f8;
  padding: 42px 24px 64px;
}

.resources-page::before,
.resources-page::after {
  display: none;
}

.resources-page::before {
  width: 250px;
  height: 250px;
  right: -34px;
  top: 118px;
  opacity: 0.45;
  background: repeating-linear-gradient(-35deg, rgba(167, 226, 213, 0.42) 0 2px, transparent 2px 8px);
}

.resources-page::after {
  width: 255px;
  height: 255px;
  left: -108px;
  top: 420px;
  opacity: 0.32;
  background: repeating-linear-gradient(-35deg, rgba(167, 226, 213, 0.45) 0 2px, transparent 2px 8px);
}

.resources-corner-illustration {
  position: fixed;
  left: 0;
  bottom: 0;
  z-index: 1;
  width: 168px;
  max-width: 14vw;
  pointer-events: none;
  user-select: none;
}

.resources-page::-webkit-scrollbar {
  width: 10px;
}

.resources-page::-webkit-scrollbar-track {
  background: #edf6f2;
}

.resources-page::-webkit-scrollbar-thumb {
  border: 2px solid #edf6f2;
  border-radius: 999px;
  background: #b8ddd1;
}

.resources-page::-webkit-scrollbar-thumb:hover {
  background: #8ecfba;
}

.resources-header {
  position: relative;
  z-index: 2;
  max-width: 1260px;
  text-align: left;
  margin: 0 auto 24px;
}

.resources-header h1 {
  font-size: 32px;
  font-weight: 700;
  color: #173533;
  margin: 0 0 10px;
  line-height: 1.2;
}

.resources-header h1 {
  font-size: 0;
}

.resources-header h1::before {
  content: "个性化资源";
  font-size: 32px;
}

.resources-header p {
  font-size: 15px;
  color: #64748b;
  margin: 0;
}

.resources-header p {
  font-size: 0;
}

.resources-header p::before {
  content: "基于学习画像智能推荐，适配当前水平的学习资料";
  font-size: 15px;
}

.no-profile-banner {
  max-width: 1200px;
  margin: 0 auto 24px;
  padding: 12px 20px;
  background: linear-gradient(135deg, #fef9ee, #fef3cd);
  border: 1px solid #f59e0b33;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: #92400e;
}

.banner-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  color: #f59e0b;
}

.banner-btn {
  margin-left: auto;
  padding: 6px 16px;
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: transform 0.2s, box-shadow 0.2s;
}

.banner-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(31, 188, 191, 0.3);
}

.resource-tools-section {
  position: relative;
  z-index: 2;
  max-width: 1260px;
  margin: 0 auto 16px;
  padding: 24px 30px 28px;
  border: 1px solid #e5e7e7;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: none;
}

.resource-tools-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding-left: 0;
  border-left: 0;
  border-radius: 0;
}

.resource-tools-head h2 {
  margin: 0 0 6px;
  color: #1f3433;
  font-size: 24px;
  font-weight: 700;
}

.resource-tools-head h2 {
  font-size: 0;
}

.resource-tools-head h2::before {
  content: "资源生成工具";
  font-size: 24px;
}

.resource-tools-head p {
  margin: 0;
  color: #6f8581;
  font-size: 14px;
}

.resource-tools-head p {
  font-size: 0;
}

.resource-tools-head p::before {
  content: "生成题库、PPT、导图并连接视频与实验";
  font-size: 14px;
}

.resource-tools-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.resource-tool-card {
  aspect-ratio: auto;
  min-height: 104px;
  padding: 14px;
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) 24px;
  align-items: center;
  gap: 10px;
  color: #1f3433;
  text-decoration: none;
  border: 1px solid #e5e7e7;
  border-radius: 6px;
  background: #ffffff;
  box-shadow: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.resource-tool-card:hover {
  transform: none;
  border-color: #b9c3c0;
  box-shadow: none;
}

.resource-tool-icon {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: #176b50;
  background: #edf5f2;
}

.resource-tool-copy {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.resource-tool-copy strong {
  color: #213a39;
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.resource-tool-copy em {
  color: #667a77;
  font-size: 11px;
  font-style: normal;
  line-height: 1.45;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.resource-tool-card > svg {
  width: 18px;
  height: 18px;
  padding: 0;
  border: 0;
  border-radius: 0;
  color: #7a8381;
}

.resource-tool-card.tool-gold .resource-tool-icon {
  color: #9a7129;
  background: #fbf3e3;
}

.resource-tool-card.tool-gold {
  border-color: #eadcbc;
}

.resource-tool-card.tool-gold > svg {
  color: #9a7129;
}

.resource-tool-card.tool-blue .resource-tool-icon {
  color: #2f7de1;
  background: #e6f0ff;
}

.resource-tool-card.tool-blue {
  border-color: #d7e6ff;
}

.resource-tool-card.tool-blue > svg {
  color: #2f7de1;
}

.resource-tool-card.tool-purple .resource-tool-icon {
  color: #7c3aed;
  background: #f0e7ff;
}

.resource-tool-card.tool-purple {
  border-color: #e4d6ff;
}

.resource-tool-card.tool-purple > svg {
  color: #7c3aed;
}

.resource-tool-card.tool-teal .resource-tool-icon {
  color: #f26a2e;
  background: #fff0e8;
}

.resource-tool-card.tool-teal {
  border-color: #f6dacb;
}

.resource-tool-card.tool-teal > svg {
  color: #f26a2e;
}

.resource-tool-card.tool-orange .resource-tool-icon {
  color: #0e9f6e;
  background: #e5f9ef;
}

.resource-tool-card.tool-orange {
  border-color: #d3f0e1;
}

.resource-tool-card.tool-orange > svg {
  color: #0e9f6e;
}

.resource-tool-card.tool-coral .resource-tool-icon {
  color: #c2415d;
  background: #fff0f3;
}

.resource-tool-card.tool-coral {
  border-color: #f4d6dc;
}

.resource-tool-card.tool-coral > svg {
  color: #c2415d;
}

.resource-tool-card.tool-red .resource-tool-icon {
  color: #b94a3c;
  background: #fff0ed;
}

.resource-tool-card.tool-red {
  border-color: #f2d2cb;
}

.resource-tool-card.tool-red > svg {
  color: #b94a3c;
}

.resources-content {
  position: relative;
  z-index: 2;
  max-width: 1260px;
  margin: 0 auto;
  padding: 28px 30px 34px;
  border: 1px solid #e5e7e7;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: none;
}

.history-resources-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin: 0 0 16px;
  padding-left: 0;
  border-left: 0;
  border-radius: 0;
}

.history-resources-head h2 {
  margin: 0;
  color: #1f3433;
  font-size: 24px;
  font-weight: 700;
}

.history-resources-head h2::before {
  content: "历史资源";
}

.history-resources-head h2 {
  font-size: 0;
}

.history-resources-head h2::before {
  font-size: 24px;
}

.history-resources-head h2::after {
  content: "按生成时间记录智能体为当前用户保存的学习资源";
  display: block;
  margin-top: 4px;
  color: #6f8581;
  font-size: 14px;
  font-weight: 400;
}

.category-tabs {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  margin-bottom: 20px;
  justify-content: flex-start;
}

.tab-btn {
  min-width: 76px;
  padding: 9px 20px;
  border: 1px solid #e7edf0;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 999px;
  font-size: 14px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  border-color: #21b978;
  color: #21b978;
}

.tab-btn.active {
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border-color: transparent;
}

.action-bar {
  position: absolute;
  top: 28px;
  right: 30px;
  display: flex;
  justify-content: flex-start;
  align-items: center;
  margin-bottom: 0;
}

.resource-count {
  display: none;
  font-size: 14px;
  color: #64748b;
}

.generate-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 0 24px;
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  font-size: 0;
}

.generate-btn::after {
  content: "生成新资源";
  font-size: 14px;
  font-weight: 600;
}

.history-generate-btn {
  flex: 0 0 auto;
  box-shadow: 0 12px 24px rgba(17, 122, 81, 0.2);
}

.generate-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(31, 188, 191, 0.3);
}

.generate-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.generate-btn svg {
  width: 18px;
  height: 18px;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.resources-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px 18px;
}

.resource-card {
  min-height: 132px;
  background: rgba(255, 255, 255, 0.96);
  border-radius: 14px;
  padding: 20px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 10px 28px rgba(31, 72, 66, 0.06);
  border: 1px solid #edf2f1;
}

.resource-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  border-color: #21b978;
}

.card-icon {
  width: 58px;
  height: 58px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-icon svg {
  width: 24px;
  height: 24px;
  color: currentColor;
}

.card-content {
  flex: 1;
  min-width: 0;
}

.card-content h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1f3f3b;
  margin: 0 0 8px;
  line-height: 1.4;
}

.card-desc {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.type-tag {
  padding: 4px 10px;
  background: rgba(31, 188, 191, 0.1);
  color: #117a51;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.history-time {
  color: #7a8583;
  font-size: 11px;
  white-space: nowrap;
}

.match-score {
  font-size: 13px;
  font-weight: 600;
}

.quality-badge,
.citation-badge {
  padding: 3px 7px;
  border: 1px solid #d8e8e1;
  border-radius: 4px;
  color: #365f50;
  background: #f3f8f5;
  font-size: 11px;
  font-weight: 700;
}

.citation-badge {
  color: #71571f;
  border-color: #eadfbd;
  background: #fbf8ed;
}

.card-arrow {
  color: #94a3b8;
  flex-shrink: 0;
  margin-top: 4px;
}

.card-arrow svg {
  width: 20px;
  height: 20px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #94a3b8;
}

.empty-state svg {
  width: 48px;
  height: 48px;
  margin-bottom: 16px;
}

.empty-state p {
  font-size: 14px;
  margin: 0;
}

.learned-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  background: #10b98118;
  color: #059669;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.learned-badge svg {
  width: 14px;
  height: 14px;
}

.badge-stars {
  display: inline-flex;
  align-items: center;
  margin-left: 2px;
}

.mini-star {
  width: 12px;
  height: 12px;
}

/* The resource hub follows the same flat black-and-white system as the docs UI. */
.resources-page {
  color: #202323;
  background: #fbfbfb;
  scrollbar-color: #c4c9c8 #f1f2f2;
}

.resources-page::-webkit-scrollbar-track {
  background: #f1f2f2;
}

.resources-page::-webkit-scrollbar-thumb {
  border-color: #f1f2f2;
  background: #c4c9c8;
}

.resources-header {
  border-color: #e3e6e5;
}

.resources-header h1,
.resource-tools-head h2,
.history-resources-head h2,
.resource-tool-copy strong,
.card-content h3 {
  color: #171919;
}

.resources-header p,
.resource-tools-head p,
.resource-tool-copy em,
.card-desc,
.resource-count {
  color: #747b7a;
}

.no-profile-banner {
  border-color: #dfe3e2;
  border-radius: 6px;
  background: #ffffff;
  color: #4f5655;
}

.no-profile-banner svg {
  color: #5d6463;
}

.resource-tools-section,
.resources-content {
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.resource-tools-section {
  padding: 0;
}

.resources-content {
  padding: 26px 0 34px;
}

.resource-tool-card,
.resource-tool-card.tool-gold,
.resource-tool-card.tool-blue,
.resource-tool-card.tool-purple,
.resource-tool-card.tool-teal,
.resource-tool-card.tool-orange,
.resource-tool-card.tool-coral,
.resource-tool-card.tool-red {
  min-height: 104px;
  border-color: #e1e4e3;
  border-radius: 6px;
  background: #ffffff;
  box-shadow: none;
}

.resource-tool-card:hover {
  border-color: #aeb5b4;
  background: #f8f9f9;
  transform: none;
}

.resource-tool-card .resource-tool-icon,
.resource-tool-card.tool-gold .resource-tool-icon,
.resource-tool-card.tool-blue .resource-tool-icon,
.resource-tool-card.tool-purple .resource-tool-icon,
.resource-tool-card.tool-teal .resource-tool-icon,
.resource-tool-card.tool-orange .resource-tool-icon,
.resource-tool-card.tool-coral .resource-tool-icon,
.resource-tool-card.tool-red .resource-tool-icon {
  border: 1px solid #e2e5e4;
  border-radius: 6px;
  background: #f0f1f1;
  color: #303534;
}

.resource-tool-card > svg,
.resource-tool-card.tool-gold > svg,
.resource-tool-card.tool-blue > svg,
.resource-tool-card.tool-purple > svg,
.resource-tool-card.tool-teal > svg,
.resource-tool-card.tool-orange > svg,
.resource-tool-card.tool-coral > svg,
.resource-tool-card.tool-red > svg {
  color: #737a79;
}

.category-tabs {
  gap: 6px;
}

.tab-btn {
  min-width: 68px;
  padding: 8px 14px;
  border-color: #dfe3e2;
  border-radius: 6px;
  background: #ffffff;
  color: #5e6564;
}

.tab-btn:hover,
.tab-btn.active {
  border-color: #9ab8aa;
  background: #edf5f1;
  color: #176f4b;
}

.generate-btn,
.generate-btn:hover:not(:disabled) {
  min-height: 40px;
  border: 1px solid #176f4b;
  border-radius: 6px;
  background: #176f4b;
  color: #ffffff;
  box-shadow: none;
  transform: none;
}

.resource-card {
  min-height: 126px;
  border-color: #e1e4e3;
  border-radius: 6px;
  background: #ffffff;
  box-shadow: none;
}

.resource-card:hover {
  border-color: #aeb5b4;
  background: #fafafa;
  box-shadow: none;
  transform: none;
}

.card-icon {
  border: 1px solid #e1e4e3;
  border-radius: 6px;
}

.card-icon svg {
  color: currentColor;
  fill: none;
}

.card-arrow,
.card-arrow svg,
.mini-star {
  color: #4e5554;
  fill: currentColor;
}

.type-tag,
.learned-badge,
.quality-badge,
.citation-badge {
  border: 1px solid #dfe3e2;
  border-radius: 4px;
  background: #f1f2f2;
  color: #4c5352;
}

.empty-state,
.empty-state svg {
  color: #858b8a;
}

@media (max-width: 1100px) {
  .resource-tools-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .resources-page {
    padding: 24px 16px calc(128px + env(safe-area-inset-bottom));
    scroll-padding-bottom: calc(128px + env(safe-area-inset-bottom));
  }

  .resource-tools-section {
    padding: 18px;
  }

  .resource-tools-grid {
    grid-template-columns: 1fr;
  }

  .resources-header h1 {
    font-size: 22px;
  }

  .category-tabs {
    gap: 6px;
  }

  .tab-btn {
    padding: 6px 14px;
    font-size: 13px;
  }

  .resources-grid {
    grid-template-columns: 1fr;
  }

  .resource-card {
    padding: 16px;
  }

  .action-bar {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .generate-btn {
    justify-content: center;
    min-height: 44px;
  }

  .banner-btn,
  .tab-btn {
    min-height: 44px;
  }

  .resource-card,
  .tool-card {
    scroll-margin-bottom: calc(128px + env(safe-area-inset-bottom));
  }
}

/* Resource hub refresh: hover effects only use composited properties, so cards never reflow. */
.resources-page {
  min-height: 100%;
  padding: 36px 56px 64px;
  background: #ffffff;
}

.resources-page::before,
.resources-page::after {
  display: none;
}

.resources-header {
  max-width: none;
  margin: 0 0 22px;
  padding-bottom: 22px;
  border-bottom: 1px solid #e7ebef;
}

.resources-header h1,
.resources-header h1::before,
.resource-tools-head h2,
.resource-tools-head h2::before,
.history-resources-head h2,
.history-resources-head h2::before {
  color: #171d26;
}

.resources-header p,
.resources-header p::before,
.resource-tools-head p,
.resource-tools-head p::before,
.history-resources-head h2::after {
  color: #657080;
}

.resource-tools-section,
.resources-content {
  max-width: none;
  margin: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.resource-tools-section {
  padding-bottom: 40px;
}

.resource-tools-head {
  margin-bottom: 20px;
}

.resource-tools-grid {
  gap: 16px;
}

.resource-tool-card {
  min-height: 132px;
  padding: 18px 16px;
  grid-template-columns: 48px minmax(0, 1fr) 18px;
  border-color: #e8edf2;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(19, 31, 45, 0.02);
  will-change: transform;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}

.resource-tool-card:hover {
  transform: translateY(-5px);
  border-color: #b9d9cd;
  box-shadow: 0 12px 24px rgba(23, 72, 58, 0.12);
}

.resource-tool-card:focus-visible,
.resource-card:focus-visible {
  outline: 3px solid rgba(16, 150, 102, 0.24);
  outline-offset: 3px;
}

.resource-tool-card .resource-tool-icon {
  width: 46px;
  height: 46px;
  border-radius: 8px;
  transition: transform 180ms ease;
}

.resource-tool-card:hover .resource-tool-icon {
  transform: scale(1.07) rotate(-3deg);
}

.resource-tool-card > svg {
  transition: transform 180ms ease;
}

.resource-tool-card:hover > svg {
  transform: translateX(4px);
}

.resource-tool-copy strong {
  color: #151b24;
}

.resource-tool-copy em {
  color: #657080;
  font-size: 12px;
}

.resources-content {
  padding-top: 4px;
}

.history-resources-head {
  margin-bottom: 16px;
}

.history-resources-head h2::after {
  display: none;
}

.category-tabs {
  gap: 12px;
  margin-bottom: 18px;
}

.tab-btn {
  min-width: 0;
  padding: 8px 18px;
  border-radius: 7px;
  color: #4b5563;
  background: #ffffff;
  transition: color 160ms ease, background-color 160ms ease, border-color 160ms ease, transform 160ms ease;
}

.tab-btn:hover {
  transform: translateY(-1px);
  border-color: #8bcdb5;
  color: #087a55;
}

.tab-btn.active {
  color: #087a55;
  border-color: #a6d9c4;
  background: #ecf8f2;
}

.action-bar {
  top: 4px;
  right: 0;
}

.generate-btn {
  min-height: 42px;
  padding: 0 18px;
  border-radius: 6px;
  background: #07855b;
  box-shadow: 0 4px 10px rgba(7, 133, 91, 0.16);
  transition: transform 180ms ease, background-color 180ms ease, box-shadow 180ms ease;
}

.generate-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  background: #056c4a;
  box-shadow: 0 9px 18px rgba(7, 133, 91, 0.24);
}

.resources-grid {
  gap: 16px;
}

.resource-card {
  position: relative;
  min-height: 184px;
  padding: 22px;
  border: 1px solid #e7ebef;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: none;
  will-change: transform;
  transition: transform 200ms ease, box-shadow 200ms ease, border-color 200ms ease;
}

.resource-card:hover {
  transform: translateY(-5px);
  border-color: #92cdb7;
  box-shadow: 0 14px 30px rgba(22, 59, 49, 0.13);
}

.card-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  transition: transform 200ms ease;
}

.resource-card:hover .card-icon {
  transform: scale(1.06) rotate(-3deg);
}

.card-content h3 {
  padding-right: 20px;
  color: #171d26;
}

.card-desc {
  color: #657080;
}

.card-arrow {
  position: absolute;
  top: 24px;
  right: 20px;
  color: #44505f;
  transition: transform 200ms ease, color 200ms ease;
}

.resource-card:hover .card-arrow {
  color: #07855b;
  transform: translateX(4px);
}

.type-tag,
.quality-badge,
.citation-badge,
.learned-badge {
  border-radius: 4px;
}

@media (max-width: 1100px) {
  .resources-page {
    padding: 32px 28px 52px;
  }

  .resource-tools-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .resources-page {
    padding: 24px 18px 44px;
  }

  .resource-tools-grid,
  .resources-grid {
    grid-template-columns: 1fr;
  }

  .resource-tool-card,
  .resource-card {
    min-height: 0;
  }

  .history-resources-head {
    padding-right: 148px;
  }
}
</style>
