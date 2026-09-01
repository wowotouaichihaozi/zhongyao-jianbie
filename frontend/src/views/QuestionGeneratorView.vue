<template>
  <div class="app-shell">
    <main class="qg-page" :class="{ 'exam-mode': activeModule === 'exam' && examStarted, 'resource-tool-standalone': isResourceToolPage }">
      <button v-if="isResourceToolPage" type="button" class="resource-return-button" @click="goBackToResources">
        <ArrowLeft :size="18" :stroke-width="2.2" aria-hidden="true" />
        <span>返回个性化资源</span>
      </button>
      <div class="qg-workbench">
        <aside class="qg-module-sidebar" aria-label="question generator modules">
          <div class="qg-module-brand">
            <div>
              <h1>{{ '\u9898\u5e93\u751f\u6210\u4e2d\u5fc3' }}</h1>
            </div>
          </div>
          <nav class="qg-module-nav">
            <button
              v-for="item in moduleNavItems"
              :key="item.key"
              type="button"
              class="qg-module-nav-item"
              :class="{ active: activeModule === item.key }"
              @click="selectQuestionModule(item.key)"
            >
              <component :is="item.icon" :size="20" :stroke-width="2.2" aria-hidden="true" />
              <span>{{ item.label }}</span>
            </button>
          </nav>
          <div class="qg-module-tip">
            <strong>{{ '\u6700\u8fd1\u751f\u6210' }} {{ questionSheets.length || 0 }} {{ '\u5957\u9898\u5e93' }}</strong>
            <span>{{ '\u5f53\u524d\u914d\u7f6e' }} {{ totalCount || 0 }} {{ '\u9898' }}</span>
          </div>
          <div class="qg-sidebar-deco" aria-hidden="true">
            <div class="qg-sidebar-books">{{ '\ud83d\udcda' }}</div>
            <p>{{ '\u667a\u80fd\u751f\u6210\uff0c\u9ad8\u6548\u5b66\u4e60' }}<br />{{ '\u7cbe\u51c6\u7ec3\u4e60\uff0c\u63d0\u5347\u6548\u679c' }}</p>
          </div>
        </aside>

        <section class="qg-workspace">
          <section v-if="activeModule === 'dashboard'" class="qg-module-panel qg-dashboard-panel">
            <div class="qg-module-head">
              <div>
                <h2>{{ '\u9898\u5e93\u4eea\u8868\u76d8' }}</h2>
              </div>
              <button type="button" class="qg-soft-btn qg-refresh-btn" @click="loadHistory">
                <RefreshCw :size="18" :stroke-width="2.2" aria-hidden="true" />
                <span>{{ '\u5237\u65b0\u6570\u636e' }}</span>
              </button>
            </div>
            <div class="qg-stat-grid">
              <div v-for="stat in dashboardStats" :key="stat.label" class="qg-stat-card">
                <div class="qg-stat-icon" :class="`qg-stat-icon--${stat.tone}`">
                  <component :is="stat.icon" :size="26" :stroke-width="2.2" aria-hidden="true" />
                </div>
                <div class="qg-stat-copy">
                  <span>{{ stat.label }}</span>
                  <strong>{{ stat.value }}</strong>
                  <em>{{ stat.hint }}</em>
                </div>
              </div>
            </div>
            <div class="qg-dashboard-grid">
              <div class="qg-glass-card qg-chart-card">
                <div class="qg-card-title">{{ '\u6700\u8fd1 7 \u5929\u505a\u9898\u8d8b\u52bf' }}</div>
                <p class="qg-card-note">{{ weeklyTrendNote }}</p>
                <div class="qg-line-chart" aria-label="weekly trend chart">
                  <div class="qg-y-axis" aria-hidden="true">
                    <span v-for="tick in trendYAxisTicks" :key="tick">{{ tick }}</span>
                  </div>
                  <svg class="qg-trend-svg" viewBox="0 0 560 172" preserveAspectRatio="none" aria-hidden="true">
                    <defs>
                      <linearGradient id="qgTrendFill" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stop-color="#20c997" stop-opacity="0.28" />
                        <stop offset="100%" stop-color="#20c997" stop-opacity="0.03" />
                      </linearGradient>
                    </defs>
                    <line v-for="y in [20, 53, 86, 119, 152]" :key="y" x1="0" x2="560" :y1="y" :y2="y" class="qg-grid-line" />
                    <polygon :points="trendAreaPoints" fill="url(#qgTrendFill)" />
                    <polyline :points="trendLinePoints" class="qg-trend-line" />
                    <circle
                      v-for="point in trendChartDots"
                      :key="point.day"
                      :cx="point.x"
                      :cy="point.y"
                      r="5"
                      class="qg-trend-dot"
                    />
                  </svg>
                  <div class="qg-x-axis" aria-hidden="true">
                    <span v-for="item in weeklyTrend" :key="item.day">{{ item.day }}</span>
                  </div>
                </div>
                <div class="qg-panel-foot">{{ weeklyTrendSummary }}</div>
              </div>
              <div class="qg-glass-card qg-accuracy-card">
                <div class="qg-card-title">{{ '\u5404\u9898\u578b\u6b63\u786e\u7387' }}</div>
                <p class="qg-card-note">{{ typeAccuracyNote }}</p>
                <div class="qg-progress-list">
                  <div v-for="item in typeAccuracy" :key="item.name" class="qg-progress-row">
                    <span>{{ item.name }}</span>
                    <div><i :style="{ width: item.value + '%' }"></i></div>
                    <strong>{{ item.value }}%</strong>
                  </div>
                  <p v-if="!typeAccuracy.length" class="qg-card-empty">暂无真实作答数据</p>
                </div>
              </div>
            </div>
            <div class="qg-dashboard-grid qg-dashboard-grid-bottom">
              <div class="qg-glass-card qg-mastery-card">
                <div class="qg-card-title">{{ '\u5404\u7ae0\u8282\u638c\u63e1\u60c5\u51b5' }}</div>
                <p class="qg-card-note">{{ chapterMasteryNote }}</p>
                <div class="qg-chip-cloud">
                  <span v-for="item in chapterMastery" :key="item.name">{{ item.name }} {{ item.value }}%</span>
                  <p v-if="!chapterMastery.length" class="qg-card-empty">完成一次考试后生成知识点掌握数据</p>
                </div>
                <div class="qg-panel-foot qg-review-foot">
                  <Sparkles :size="16" :stroke-width="2.2" aria-hidden="true" />
                  <span>{{ priorityReviewText }}</span>
                </div>
              </div>
              <div class="qg-glass-card qg-activity-card">
                <div class="qg-card-title">{{ '\u6700\u8fd1\u6d3b\u52a8' }}</div>
                <p class="qg-card-note">{{ '\u6700\u8fd1\u751f\u6210\u4e0e\u8003\u8bd5\u8bb0\u5f55\u4f1a\u4fdd\u5b58\u5728\u9898\u5e93\u5386\u53f2\u4e2d\u3002' }}</p>
                <div class="qg-activity-list">
                  <button
                    v-for="item in recentActivities"
                    :key="item.id"
                    type="button"
                    @click="item.action && item.action()"
                  >
                    <span :class="['qg-activity-icon', `qg-activity-${item.kind || 'file'}`]">
                      <component :is="item.icon || File" :size="18" :stroke-width="2.2" aria-hidden="true" />
                    </span>
                    <span class="qg-activity-copy">
                      <span class="qg-activity-title-row">
                        <em>{{ item.tag || item.type }}</em>
                        <strong>{{ item.title }}</strong>
                      </span>
                    </span>
                    <time>{{ item.time }}</time>
                  </button>
                  <p v-if="!recentActivities.length" class="qg-card-empty">暂无题单或考试记录</p>
                </div>
                <div class="qg-activity-foot">
                  <span>{{ '\u5171' }} {{ recentActivities.length }} {{ '\u6761\u8fd1\u671f\u6d3b\u52a8' }}</span>
                  <button type="button" @click="selectQuestionModule('history')">{{ '\u67e5\u770b\u5168\u90e8' }} &gt;</button>
                </div>
              </div>
            </div>
          </section>

          <section v-else-if="activeModule === 'config'" class="qg-module-panel">
            <div class="qg-module-head">
              <div>
                <h2>题目配置</h2>
              </div>
              <button type="button" class="qg-primary-btn qg-config-goto-btn" aria-label="去生成题单" title="去生成题单" @click="activeModule = 'generate'">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M5 12h13m0 0-5-5m5 5-5 5" />
                </svg>
              </button>
            </div>
                        <div class="qg-config-dashboard">
              <div class="qg-config-summary-grid">
                <div class="qg-config-summary-card">
                  <i class="qg-config-summary-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4h10M7 8h10M7 12h7M6 20h12a2 2 0 0 0 2-2V4H4v14a2 2 0 0 0 2 2Z" /></svg></i>
                  <span>总题数</span><strong>{{ totalCount }}</strong><em>当前题型累计</em>
                </div>
                <div class="qg-config-summary-card">
                  <i class="qg-config-summary-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3h8l2 4-6 14L6 7l2-4Zm-2 4h12M9.5 7 12 21 14.5 7" /></svg></i>
                  <span>总分</span><strong>{{ previewTotalScore }}</strong><em>按分值自动计算</em>
                </div>
                <div class="qg-config-summary-card">
                  <i class="qg-config-summary-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 7v5l3 2M8 2h8M12 22a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z" /></svg></i>
                  <span>预计完成</span><strong>{{ estimatedMinutes }} 分钟</strong><em>模拟练习时长</em>
                </div>
                <div class="qg-config-summary-card">
                  <i class="qg-config-summary-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 8h10M7 12h6m-5 8h8a4 4 0 0 0 4-4V8a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v8a4 4 0 0 0 4 4Zm8-8 2 2 3-4" /></svg></i>
                  <span>生成策略</span><strong>{{ autoDistribute ? '智能分配' : '手动配置' }}</strong><em>任务规划智能体</em>
                </div>
              </div>
              <div class="qg-config-board-grid">
                <section class="qg-config-board-block qg-config-types-block">
                  <div class="qg-card-title">题目类型与分值</div>
                  <div class="qg-type-config-list qg-type-config-list-board">
                    <div v-for="qt in questionTypes" :key="qt.key" class="qg-type-config-row" :class="{ disabled: !qt.enabled }">
                      <label><input v-model="qt.enabled" type="checkbox" /><span :style="{ background: qt.color }"></span>{{ questionTypeLabel(qt) }}</label>
                      <input v-model.number="qt.count" type="number" min="0" max="50" :disabled="!qt.enabled || autoDistribute" />
                      <em>题</em>
                      <input v-model.number="qt.score" type="number" min="0" step="0.5" :disabled="!qt.enabled" />
                      <em>分/题</em>
                    </div>
                  </div>
                </section>
                <section class="qg-config-board-block">
                  <div class="qg-card-title qg-difficulty-title">
                    <span>难度比例</span>
                  </div>
                  <label class="qg-check-line qg-config-auto-line"><input v-model="autoDistribute" type="checkbox" /><span>由任务规划智能体根据资料自动分配题型数量</span></label>
                  <label v-if="autoDistribute" class="qg-field compact qg-target-count-field"><span>目标题量</span><input v-model.number="targetQuestionCount" type="number" min="1" max="50" /></label>
                  <div class="qg-difficulty-grid qg-difficulty-grid-board">
                    <label v-for="item in difficultyRatios" :key="item.key" :class="{ locked: difficultyLocks[item.key] }">
                      <button type="button" class="qg-lock-ratio-btn" :class="{ locked: difficultyLocks[item.key] }" :aria-label="difficultyLocks[item.key] ? `解锁${item.label}` : `锁定${item.label}`" :title="difficultyLocks[item.key] ? `解锁${item.label}` : `锁定${item.label}`" @click.prevent="toggleDifficultyLock(item.key)">
                        <svg v-if="difficultyLocks[item.key]" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10V8a5 5 0 0 1 10 0v2M6 10h12v10H6V10Zm6 5v2" /></svg>
                        <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="M9 10V8a5 5 0 0 1 9-3M6 10h12v10H6V10Zm6 5v2" /></svg>
                      </button>
                      <span>{{ item.label }}</span>
                      <input v-model.number="item.value" type="range" min="0" max="100" :disabled="difficultyLocks[item.key]" />
                      <strong>{{ item.value }}%</strong>
                    </label>
                  </div>
                </section>
                <section class="qg-config-board-block">
                  <div class="qg-card-title">生成选项</div>
                  <div class="qg-switch-grid qg-switch-grid-board">
                    <label><input v-model="generationOptions.analysis" type="checkbox" /> 生成答案解析</label>
                    <label><input v-model="generationOptions.tags" type="checkbox" /> 生成知识点标签</label>
                    <label><input v-model="generationOptions.variants" type="checkbox" /> 生成错题变式</label>
                  </div>
                  <div class="qg-preview-dist qg-config-dist-board">
                    <p v-for="qt in enabledQuestionTypes" :key="qt.key"><span>{{ questionTypeLabel(qt) }}</span><em>{{ autoDistribute ? '智能分配' : (qt.count + ' 题') }}</em></p>
                  </div>
                </section>
                <section class="qg-config-board-block">
                  <div class="qg-card-title">课程与要求</div>
                  <div class="qg-form-grid qg-form-grid-board">
                    <label class="qg-field"><span>课程名称</span><input v-model="courseName" placeholder="可选填写" /></label>
                    <label class="qg-field"><span>章节 / 主题</span><input v-model="chapterName" placeholder="可选填写" /></label>
                    <label class="qg-field"><span>额外要求</span><textarea v-model="constraints" rows="2" placeholder="可选填写"></textarea></label>
                  </div>
                </section>
              </div>
            </div></section>

          <section v-else-if="activeModule === 'generate'" class="qg-module-panel qg-generate-panel">
            <div class="qg-module-head">
              <div>
                <h2>生成题单</h2>
              </div>
              <button type="button" class="qg-primary-btn qg-generate-sheet-btn" :disabled="loadingXiaoZhiQuestionTask || generating || !canGenerate" @click="generate">
                {{ loadingXiaoZhiQuestionTask ? '读取题单...' : (generating ? '生成中...' : '生成题单') }}
              </button>
            </div>
            <div v-if="errorMsg" class="qg-generate-error-banner">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/></svg>
              <div class="qg-generate-error-text">
                <strong>生成失败</strong>
                <span>{{ errorMsg }}</span>
              </div>
              <button type="button" class="qg-generate-retry-btn" @click="generate">重试</button>
            </div>
            <div v-if="loadingXiaoZhiQuestionTask" class="qg-xiaozhi-task-loading" role="status" aria-live="polite">
              <span class="qg-xiaozhi-task-spinner" aria-hidden="true"></span>
              <div>
                <strong>正在打开嵌小智生成的题单</strong>
                <span>{{ streamMessage || '正在读取后台任务与题目，请稍候...' }}</span>
              </div>
            </div>
            <div v-else class="qg-upload-layout">
              <div class="qg-glass-card qg-generate-input-panel">
                <div class="qg-setting-section qg-profile-merge-section qg-upload-profile-section">
                  <div class="qg-card-title">薄弱知识点</div>
                  <div class="qg-tag-editor">
                    <span>生成侧重点</span>
                    <div class="qg-tag-list">
                      <button v-for="wp in selectedWeakPoints" :key="wp" type="button" @click="removeWeakTag(wp)">{{ wp }} ×</button>
                      <input v-model="newWeakTag" placeholder="输入后回车添加，如 GPIO" @keydown.enter.prevent="addWeakTag" />
                      <button type="button" class="qg-mini-add" @click="addWeakTag">添加</button>
                    </div>
                  </div>
                  <p class="qg-muted-line">这些标签会作为题库生成参数，用于匹配知识点和难度。</p>
                </div>
                <div
                  class="qg-upload-zone"
                  :class="{ active: isDragging, 'has-files': uploadedFiles.length }"
                  @dragover.prevent="isDragging = true"
                  @dragleave.prevent="isDragging = false"
                  @drop.prevent="handleDrop"
                  @click="fileInput?.click()"
                >
                  <input ref="fileInput" type="file" multiple accept=".txt,.md,.pdf,.docx,.doc,.pptx,.ppt" hidden @change="handleFileSelect" />
                  <svg v-if="!uploadedFiles.length" viewBox="0 0 24 24"><path d="M12 16V4m0 0 4 4m-4-4-4 4M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></svg>
                  <strong v-if="!uploadedFiles.length">拖拽资料到这里，或点击选择文件</strong>
                  <span v-if="!uploadedFiles.length">支持 PDF / Word / PPT / TXT / Markdown</span>
                <div v-if="uploadedFiles.length" class="qg-file-icon-grid">
                  <button
                    v-for="(item, index) in uploadedFiles"
                    :key="item.file.name + index"
                    type="button"
                    class="qg-file-icon-card"
                    :class="{ active: selectedMaterialIndex === index }"
                    @click.stop="selectMaterialPreview(index)"
                  >
                    <span class="qg-file-remove-dot" @click.stop="removeFile(index)">×</span>
                    <span class="qg-file-badge">{{ fileKind(item.file.name) }}</span>
                    <strong>{{ item.file.name }}</strong>
                  </button>
                </div>
                </div>
                <label class="qg-field wide"><span>或直接粘贴资料内容</span><textarea v-model="pastedText" rows="5" placeholder="粘贴讲义、笔记或章节内容..."></textarea></label>
              </div>
              <div class="qg-glass-card qg-sheet-preview-card">
                <div class="qg-card-title qg-preview-title">{{ resultBank?.questions?.length ? '题单预览' : (selectedMaterialPreview ? '文件预览' : '题单预览') }}</div>
                <div v-if="resultBank?.questions?.length && !generating" class="qg-sheet-complete-banner" role="status" aria-live="polite">
                  <span class="qg-sheet-complete-icon">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M20 6 9 17l-5-5" />
                    </svg>
                  </span>
                  <div>
                    <strong>题单生成完成</strong>
                    <em>已生成 {{ resultBank.questions.length }} 道题，结果已在下方题单预览区展示。</em>
                  </div>
                </div>
                <div class="qg-question-preview-stage qg-large-preview-stage" :class="{ generating, 'has-file': selectedMaterialPreview && !resultBank?.questions?.length, 'has-questions': resultBank?.questions?.length }">
                  <template v-if="generating">
                    <div class="qg-ai-log-head">AI 实时调试信息</div>
                    <pre>{{ streamMessage || streamBatchType || streamRawOutput || '正在解析资料、规划题型并生成题目...' }}</pre>
                  </template>
                  <template v-else-if="resultBank?.questions?.length">
                    <article v-for="(q, index) in resultBank.questions" :key="q.id || index" class="qg-preview-question-row">
                      <strong>{{ index + 1 }}. {{ q.stem }}</strong>
                       <span>{{ q.type || '题目' }} · {{ scoreForQuestion(q) }} 分</span>
                    </article>
                  </template>
                  <template v-else-if="selectedMaterialPreview">
                    <div class="qg-file-preview-panel">
                      <span class="qg-file-preview-icon">{{ fileKind(selectedMaterialPreview.file.name) }}</span>
                      <strong>{{ selectedMaterialPreview.file.name }}</strong>
                      <em>{{ formatSize(selectedMaterialPreview.file.size) }}</em>
                      <pre class="qg-file-preview-text">{{ selectedMaterialPreview.previewLoading ? '正在读取文件...' : selectedMaterialPreview.previewText }}</pre>
                    </div>
                  </template>
                  <template v-else>
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 19.5A2.5 2.5 0 0 0 6.5 22H20V4H6.5A2.5 2.5 0 0 0 4 6.5v13ZM8 8h8M8 12h7M8 16h5" />
                    </svg>
                    <strong>题单预览区</strong>
                    <span>上传资料并点击生成后，题目将在这里预览。</span>
                  </template>
                </div>
              </div>
            </div>
          </section>

          <section v-else-if="activeModule === 'exam'" class="qg-module-panel qg-exam-inline-panel">
            <!-- Exam in progress: full layout with floating answer card -->
            <div v-if="examStarted && !examSubmitted" class="qg-exam-full-layout">
              <div class="qg-exam-full-topbar">
                <div class="qg-exam-full-title">
                  <h2>{{ selectedSheet?.title || '模拟考试' }}</h2>
                  <span>题量：{{ selectedQuestions.length }} · 满分：{{ examResult.total_score }}</span>
                </div>
                <div class="qg-exam-full-timer">
                  <button type="button" class="qg-timer-mode-btn" @click="toggleTimerMode" :title="timerMode === 'countup' ? '切换为倒计时' : '切换为正计时'">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                    <span>{{ timerMode === 'countup' ? '正计时' : '倒计时' }}</span>
                  </button>
                  <span class="qg-timer-value">{{ formattedElapsedTime }}</span>
                  <span v-if="timerMode === 'countdown'" class="qg-timer-target">/ {{ formattedCountdownTarget }}</span>
                </div>
                <button type="button" class="qg-exam-full-finish-btn" @click="handleExamAction">结束考试</button>
              </div>
              <div class="qg-exam-full-body">
                <div class="qg-exam-full-paper">
                  <div v-for="(q, idx) in selectedQuestions" :key="q.id || idx" :id="'exam-q-' + idx" class="qg-exam-full-question">
                    <div class="qg-exam-q-header">
                      <span class="qg-exam-q-num">{{ idx + 1 }}</span>
                      <span class="qg-exam-q-type">{{ q.type || '选择题' }}</span>
                      <span class="qg-exam-q-score">{{ scoreForQuestion(q) }} 分</span>
                    </div>
                    <p class="qg-exam-q-stem">{{ q.stem }}</p>
                    <div v-if="hasChoiceOptions(q)" class="qg-exam-q-options">
                      <label v-for="option in q.options" :key="option" class="qg-exam-q-option" :class="{ selected: isChecked(idx, option, q) }">
                        <input
                          :type="isMultiQuestion(q) ? 'checkbox' : 'radio'"
                          :name="'exam-q-' + idx"
                          :checked="isChecked(idx, option, q)"
                          @change="updateChoiceAnswer(idx, option, q, $event)"
                        />
                        <span class="qg-exam-q-option-text">{{ option }}</span>
                      </label>
                    </div>
                    <textarea v-else v-model="examAnswers[idx]" rows="3" placeholder="请输入答案..." class="qg-exam-q-textarea"></textarea>
                  </div>
                </div>
                <aside class="qg-exam-floating-card">
                  <div class="qg-exam-card-timer">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                    <span>{{ formattedElapsedTime }}</span>
                    <button type="button" class="qg-card-timer-toggle" @click="toggleTimerMode" :title="timerMode === 'countup' ? '切换倒计时' : '切换正计时'">
                      {{ timerMode === 'countup' ? '正计时' : '倒计时' }}
                    </button>
                  </div>
                  <div class="qg-exam-card-header">
                    <span class="qg-exam-card-title">答题卡</span>
                    <span class="qg-exam-card-progress">{{ answeredCount }}/{{ selectedQuestions.length }}</span>
                  </div>
                  <div class="qg-exam-card-progress-bar">
                    <div class="qg-exam-card-progress-fill" :style="{ width: (answeredCount / selectedQuestions.length * 100) + '%' }"></div>
                  </div>
                  <div class="qg-exam-card-grid">
                    <button v-for="(q, idx) in selectedQuestions" :key="idx" type="button" class="qg-exam-card-btn" :class="{ done: hasExamAnswer(idx), current: idx === currentExamQuestion, flagged: flaggedQuestions.has(idx) }" @click="scrollToExamQuestion(idx)" @contextmenu.prevent="toggleFlagQuestion(idx)">{{ idx + 1 }}</button>
                  </div>
                  <div class="qg-exam-card-legend">
                    <span class="qg-legend-item"><i class="qg-legend-dot current"></i>当前</span>
                    <span class="qg-legend-item"><i class="qg-legend-dot answered"></i>已答</span>
                    <span class="qg-legend-item"><i class="qg-legend-dot unanswered"></i>未答</span>
                    <span class="qg-legend-item"><i class="qg-legend-dot flagged-dot"></i>标记</span>
                  </div>
                </aside>
              </div>
            </div>

            <!-- Exam result display -->
            <div v-else-if="examSubmitted" class="qg-exam-result-panel">
              <div class="qg-exam-result-card">
                <div class="qg-exam-score-ring-wrap">
                  <svg class="qg-exam-score-ring" viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r="52" fill="none" stroke="var(--border, rgba(31, 188, 188, 0.1))" stroke-width="8"/>
                    <circle cx="60" cy="60" r="52" fill="none" :stroke="examResult.score / examResult.total_score >= 0.6 ? '#22c55e' : '#ef4444'" stroke-width="8" stroke-linecap="round" :stroke-dasharray="326.73" :stroke-dashoffset="326.73 - (326.73 * (examResult.question_count ? examResult.correct_count / examResult.question_count : 0))" transform="rotate(-90 60 60)" style="transition: stroke-dashoffset 1s ease"/>
                  </svg>
                  <div class="qg-exam-score-ring-text">
                    <span class="qg-exam-score-ring-pct">{{ examResult.question_count ? Math.round(examResult.correct_count / examResult.question_count * 100) : 0 }}%</span>
                    <span class="qg-exam-score-ring-label">正确率</span>
                  </div>
                </div>
                <h2>{{ examResult.score / examResult.total_score >= 0.6 ? '考试通过' : '继续加油' }}</h2>
                <div class="qg-exam-result-score">
                  <span class="qg-exam-score-big">{{ examResult.score }}</span>
                  <span class="qg-exam-score-total">/ {{ examResult.total_score }} 分</span>
                </div>
                <div class="qg-exam-result-stats">
                  <div class="qg-exam-stat-item"><strong>{{ examResult.correct_count }}</strong><span>正确</span></div>
                  <div class="qg-exam-stat-item"><strong>{{ examResult.question_count - examResult.correct_count }}</strong><span>错误</span></div>
                  <div class="qg-exam-stat-item"><strong>{{ formattedElapsedTime }}</strong><span>用时</span></div>
                  <div class="qg-exam-stat-item"><strong>{{ examResult.question_count }}</strong><span>总题数</span></div>
                </div>
                <div v-if="examResult.detail && examResult.detail.filter(d => !d.correct).length" class="qg-exam-wrong-review">
                  <h3>错题回顾（{{ examResult.detail.filter(d => !d.correct).length }} 题）</h3>
                  <div v-for="(item, idx) in examResult.detail.filter(d => !d.correct)" :key="idx" class="qg-exam-wrong-item">
                    <div class="qg-exam-wrong-header">
                      <span class="qg-exam-wrong-type">{{ item.type || '题目' }}</span>
                      <span v-if="item.question?.knowledge_point" class="qg-exam-wrong-kp">{{ item.question.knowledge_point }}</span>
                    </div>
                    <p class="qg-exam-wrong-stem">{{ item.stem }}</p>
                    <p class="qg-exam-wrong-answer">你的答案：<span class="wrong">{{ item.user_answer || '未作答' }}</span></p>
                    <p class="qg-exam-wrong-answer">正确答案：<span class="correct">{{ item.answer }}</span></p>
                    <p v-if="item.analysis" class="qg-exam-wrong-analysis">{{ item.analysis }}</p>
                  </div>
                </div>
                <div class="qg-exam-sync-hint">
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                  <span>考试记录已保存到题库历史</span>
                </div>
                <div v-if="weakKnowledgePoints.length" class="qg-exam-weak-summary">
                  <h3>知识点薄弱项</h3>
                  <div class="qg-weak-tags">
                    <span v-for="kp in weakKnowledgePoints" :key="weakPointLabel(kp)" class="qg-weak-tag">{{ weakPointLabel(kp) }}</span>
                  </div>
                </div>

                <div class="qg-exam-result-answer-card">
                  <h3>答题卡总览</h3>
                  <div class="qg-result-card-grid">
                    <button v-for="(q, idx) in selectedQuestions" :key="idx" type="button"
                      class="qg-result-card-btn"
                      :class="{ correct: !wrongQuestionIndices.has(idx), wrong: wrongQuestionIndices.has(idx) }"
                      @click="scrollToExamQuestion(idx)">
                      {{ idx + 1 }}
                    </button>
                  </div>
                  <div class="qg-result-card-legend">
                    <span class="qg-legend-item"><i class="qg-legend-dot answered"></i>正确</span>
                    <span class="qg-legend-item"><i class="qg-legend-dot wrong-dot"></i>错误</span>
                    <span class="qg-legend-item"><i class="qg-legend-dot unanswered"></i>未答</span>
                  </div>
                </div>
                <div class="qg-exam-ai-score-panel" :class="{ active: aiScoreMessage }">
                  <div>
                    <strong>AI 评分智能体</strong>
                    <span>{{ aiScoreMessage || '如果你对当前自动评分不满意，可以提交给 AI 评分智能体复评。' }}</span>
                  </div>
                  <button type="button" class="qg-primary-btn" :disabled="aiScoring" @click="requestAiRescore">
                    {{ aiScoring ? 'AI 评分中...' : '交给 AI 评分' }}
                  </button>
                </div>
                <div class="qg-exam-result-actions">
                  <button type="button" class="qg-primary-btn" @click="resetExam">重新考试</button>
                  <button type="button" class="qg-soft-btn" @click="activeModule = 'history'">查看历史记录</button>
                  <button type="button" class="qg-soft-btn" @click="activeModule = 'dashboard'">返回仪表盘</button>
                </div>
              </div>
            </div>

            <!-- Pre-exam: sheet selection -->
            <div v-else class="qg-exam-pre-panel">
              <div class="qg-module-head">
                <div><h2>考试中心</h2></div>
              </div>
              <div class="qg-exam-pre-toolbar">
                <button type="button" class="qg-soft-btn" @click="enterSheetSelectMode">选择题单</button>
                <button type="button" class="qg-primary-btn" :disabled="!canLaunchSelectedExam" @click="handleExamAction">开始考试</button>
              </div>
              <div class="qg-glass-card">
                <div class="qg-card-title">当前试卷</div>
                <div v-if="!selectedSheet" class="qg-empty-state">请先选择一份题单，然后开始考试。</div>
                <div v-else-if="selectedQuestions.length" class="qg-exam-pre-info">
                  <span>{{ selectedSheet.title }}</span>
                  <span>{{ selectedQuestions.length }} 题 · {{ examResult.total_score }} 分</span>
                </div>
                <div v-else class="qg-empty-state">当前题单没有可用题目，请重新选择或生成题单。</div>
              </div>
            </div>
          </section>

          <section v-else class="qg-module-panel">
            <div class="qg-module-head">
              <div>
                <h2>历史记录</h2>
              </div>
              <button type="button" class="qg-soft-btn" @click="loadHistory">刷新记录</button>
            </div>
            <div class="qg-history-workbench">
              <div class="qg-glass-card">
                <div class="qg-filter-row">
                  <button v-for="item in historyFilters" :key="item.key" type="button" :class="{ active: historyFilter === item.key }" @click="historyFilter = item.key">{{ item.label }}</button>
                </div>
                <div class="qg-history-table">
                  <div v-for="item in filteredHistoryRows" :key="item.id" class="qg-history-row" :class="{ 'is-running': item.status === 'running' }">
                    <strong>{{ item.title }}</strong>
                    <span :class="{ 'qg-history-status-running': item.status === 'running' }">{{ item.type }}</span>
                    <em>{{ item.course }}</em>
                    <small>{{ item.count }} 题</small>
                    <time>{{ item.status === 'running' ? formatGenerationTaskTime(item.time) : item.time }}</time>
                    <div v-if="item.status === 'running'" class="qg-history-progress" role="status" aria-live="polite">
                      <div class="qg-history-progress-bar">
                        <i :style="{ width: generationTaskProgress(item.raw) + '%' }"></i>
                      </div>
                      <span>{{ item.raw?.payload?.message || '题单正在后台生成，进度会自动刷新' }}</span>
                    </div>
                    <button type="button" @click="openHistoryRow(item)">{{ item.kind === 'task' ? '查看进度' : (examSelectingSheet && item.kind === 'sheet' ? '选择' : '查看') }}</button>
                    <button type="button" :disabled="item.kind === 'task'" @click="printHistory">导出</button>
                    <button type="button" :disabled="item.kind === 'task'">删除</button>
                  </div>
                </div>
              </div>
              <aside class="qg-glass-card qg-history-side">
                <div class="qg-card-title">详情区域</div>
                <div v-if="!historyDetail" class="qg-empty-state qg-history-placeholder">
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M12 8v5l3 2M4 12a8 8 0 1 0 2.35-5.65M4 4v5h5" />
                  </svg>
                  <strong>暂无选中记录</strong>
                  <span>点击左侧历史记录后展示题目预览、答案解析和生成参数。</span>
                </div>
                <template v-else>
                  <h3>{{ historyDetail.title }}</h3>
                  <p v-if="historyDetail.score !== undefined">考试得分：{{ historyDetail.score }} / {{ historyDetail.total_score }} · 正确：{{ historyDetail.correct_count }} / {{ historyDetail.question_count }}</p>
                  <p v-else>{{ historyDetail.course_name || '未指定课程' }} 路 {{ historyDetail.target_topic || '综合练习' }}</p>
                  <article v-for="(item, idx) in historyDetailQuestions.slice(0, 4)" :key="idx" class="qg-history-preview">
                    <strong>{{ idx + 1 }}. {{ item.question?.stem || item.stem }}</strong>
                    <span>答案：{{ item.answer || item.question?.answer || '待查看' }}</span>
                    <em>{{ item.analysis || item.question?.analysis || '暂无解析' }}</em>
                  </article>
                </template>
              </aside>
            </div>
          </section>
        </section>
      </div>

    </main>
  </div>
</template>

<script setup>
import { computed, markRaw, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  CheckCircle2,
  ClipboardCheck,
  ClipboardList,
  Cpu,
  Download,
  File,
  FileText,
  History,
  LayoutDashboard,
  ListChecks,
  RefreshCw,
  Sparkles,
} from 'lucide-vue-next'
import {
  getQuestionGeneratorConfig,
  getQuestionGeneratorHistory,
  getQuestionGeneratorStatus,
  getXiaoZhiTask,
  requestQuestionGeneratorAiScore,
  saveQuestionGeneratorConfig,
  saveQuestionGeneratorExamResult,
  startQuestionGeneration,
} from '../services/api.js'
import { useGlobalDebug } from '../stores/globalDebug.js'
import {
  getNodeCache,
  hydrateNodeCachesFromServer,
  markNodeCacheComplete,
  markNodeCacheError,
  markNodeCacheStarted,
  setNodeCache,
} from '../services/learningPathNodeCache.js'
import { resolveExamQuestions } from '../utils/questionExamSession.js'

const activeTab = ref('generate')
const activeModule = ref('dashboard')
const router = useRouter()
const route = useRoute()
const isResourceToolPage = computed(() => route.meta?.resourceTool === true || route.path.startsWith('/personalized-resources/'))
let xiaozhiQuestionTaskTimer = null
const loadingXiaoZhiQuestionTask = ref(Boolean(String(route.query.xzTask || '').trim()))

function goBackToResources() {
  router.push('/personalized-resources')
}

const moduleNavItems = [
  { key: 'dashboard', label: '\u4eea\u8868\u76d8', icon: LayoutDashboard },
  { key: 'config', label: '\u9898\u76ee\u914d\u7f6e', icon: ListChecks },
  { key: 'generate', label: '\u751f\u6210\u9898\u5355', icon: Download },
  { key: 'exam', label: '\u8003\u8bd5', icon: ClipboardCheck },
  { key: 'history', label: '\u5386\u53f2\u8bb0\u5f55', icon: History },
]
const difficultyRatios = reactive([
  { key: 'easy', label: '简单题比例', value: 30 },
  { key: 'medium', label: '中等题比例', value: 50 },
  { key: 'hard', label: '困难题比例', value: 20 },
])
const difficultyLocks = reactive({ easy: false, medium: false, hard: false })
let normalizingDifficulty = false
let lastDifficultyValues = difficultyRatios.map(item => item.value)
function toggleDifficultyLock(key) {
  difficultyLocks[key] = !difficultyLocks[key]
  lastDifficultyValues = difficultyRatios.map(item => Number(item.value) || 0)
}
watch(
  () => difficultyRatios.map(item => Number(item.value) || 0),
  (values) => {
    if (normalizingDifficulty) return
    const changedIndex = values.findIndex((value, index) => value !== lastDifficultyValues[index])
    if (changedIndex < 0) return
    normalizingDifficulty = true
    const changedItem = difficultyRatios[changedIndex]
    if (difficultyLocks[changedItem.key]) {
      difficultyRatios[changedIndex].value = lastDifficultyValues[changedIndex]
      nextTick(() => { normalizingDifficulty = false })
      return
    }
    const lockedOtherIndexes = [0, 1, 2].filter(index => index !== changedIndex && difficultyLocks[difficultyRatios[index].key])
    const lockedTotal = lockedOtherIndexes.reduce((sum, index) => sum + Math.max(0, Number(difficultyRatios[index].value) || 0), 0)
    const maxChangedValue = Math.max(0, 100 - lockedTotal)
    const otherIndexes = [0, 1, 2].filter(index => index !== changedIndex && !difficultyLocks[difficultyRatios[index].key])
    const changedValue = otherIndexes.length
      ? Math.max(0, Math.min(maxChangedValue, Math.round(values[changedIndex])))
      : maxChangedValue
    difficultyRatios[changedIndex].value = changedValue
    const rest = Math.max(0, 100 - lockedTotal - changedValue)
    const previousOtherTotal = otherIndexes.reduce((sum, index) => sum + Math.max(0, Number(lastDifficultyValues[index]) || 0), 0)
    if (otherIndexes.length === 0) {
      // All remaining ratio is held by locked items.
    } else if (otherIndexes.length === 1) {
      difficultyRatios[otherIndexes[0]].value = rest
    } else if (previousOtherTotal <= 0) {
      difficultyRatios[otherIndexes[0]].value = rest
      difficultyRatios[otherIndexes[1]].value = 0
    } else {
      const first = Math.round(rest * (Math.max(0, Number(lastDifficultyValues[otherIndexes[0]]) || 0) / previousOtherTotal))
      difficultyRatios[otherIndexes[0]].value = first
      difficultyRatios[otherIndexes[1]].value = rest - first
    }
    lastDifficultyValues = difficultyRatios.map(item => Number(item.value) || 0)
    nextTick(() => { normalizingDifficulty = false })
  },
)

const generationOptions = reactive({ analysis: true, tags: true, variants: false })
const materialOptions = reactive({ knowledge: true, chapter: true, generate: true, analysis: true })
const examConfig = reactive({ duration: 45, shuffle: true, showAnswer: false })
const historyFilter = ref('all')
const historyFilters = [
  { key: 'all', label: '全部' },
  { key: 'sheet', label: '题库记录' },
  { key: 'exam', label: '考试记录' },
]
const examModes = ['快速组卷', '随机组卷', '按章节组卷', '模拟考试']
const configCollapsed = ref(false)
const mobileConfigExpanded = ref(false)
const historyExpanded = ref(false)
const navTabs = [
  { key: 'generate', label: '生成题单' },
  { key: 'exam', label: '考试' },
  { key: 'history', label: '历史记录' },
]
const isDragging = ref(false)
const fileInput = ref(null)
const uploadedFiles = ref([])
const selectedMaterialIndex = ref(-1)
const pastedText = ref('')
const courseName = ref('')
const chapterName = ref('')
const studentProfile = ref('')
const constraints = ref('')
const selectedWeakPoints = ref([])
const newWeakTag = ref('')
const autoDistribute = ref(false)
const targetQuestionCount = ref(8)
const generating = ref(false)

// --- 閰嶇疆鑷姩淇濆瓨 ---
let configLoaded = false
let saveConfigTimer = null

function collectConfig() {
  return {
    questionTypes: questionTypes.map(qt => ({
      key: qt.key, enabled: qt.enabled, count: qt.count, score: qt.score,
    })),
    difficultyRatios: difficultyRatios.map(d => ({ key: d.key, value: d.value })),
    difficultyLocks: { ...difficultyLocks },
    generationOptions: { ...generationOptions },
    autoDistribute: autoDistribute.value,
    targetQuestionCount: targetQuestionCount.value,
    courseName: courseName.value,
    chapterName: chapterName.value,
    constraints: constraints.value,
  }
}

function applyConfig(config) {
  if (!config || typeof config !== 'object') return
  if (Array.isArray(config.questionTypes)) {
    config.questionTypes.forEach(saved => {
      const qt = questionTypes.find(q => q.key === saved.key)
      if (qt) {
        if (typeof saved.enabled === 'boolean') qt.enabled = saved.enabled
        if (typeof saved.count === 'number') qt.count = saved.count
        if (typeof saved.score === 'number') qt.score = saved.score
      }
    })
  }
  if (Array.isArray(config.difficultyRatios)) {
    config.difficultyRatios.forEach(saved => {
      const d = difficultyRatios.find(item => item.key === saved.key)
      if (d && typeof saved.value === 'number') d.value = saved.value
    })
  }
  if (config.difficultyLocks && typeof config.difficultyLocks === 'object') {
    Object.keys(config.difficultyLocks).forEach(key => {
      if (key in difficultyLocks) difficultyLocks[key] = config.difficultyLocks[key]
    })
  }
  if (config.generationOptions && typeof config.generationOptions === 'object') {
    Object.assign(generationOptions, config.generationOptions)
  }
  if (typeof config.autoDistribute === 'boolean') autoDistribute.value = config.autoDistribute
  if (typeof config.targetQuestionCount === 'number') targetQuestionCount.value = config.targetQuestionCount
  if (typeof config.courseName === 'string') courseName.value = config.courseName
  if (typeof config.chapterName === 'string') chapterName.value = config.chapterName
  if (typeof config.constraints === 'string') constraints.value = config.constraints
}

function saveConfig() {
  if (!configLoaded) return
  if (saveConfigTimer) clearTimeout(saveConfigTimer)
  saveConfigTimer = setTimeout(() => {
    saveQuestionGeneratorConfig(collectConfig()).catch(() => {})
  }, 500)
}

async function loadConfig() {
  try {
    const result = await getQuestionGeneratorConfig()
    if (result && result.config) {
      applyConfig(result.config)
    }
  } catch {
    // First use or unavailable saved config: continue with page defaults.
  } finally {
    configLoaded = true
    applyRoutePrefill()
  }
}

const errorMsg = ref('')
const questionSearchQuery = ref('')
const questionSortMode = ref('default')
const sortDropdownOpen = ref(false)
const sortLabelMap = { default: '默认排序', 'id-asc': '题号升序', 'id-desc': '题号降序', 'diff-asc': '难度升序', 'diff-desc': '难度降序' }
const showOnlyFavorites = ref(false)
const activeTypeFilter = ref('')
const activeDiffFilter = ref('')
const favoritedQuestions = ref(new Set())
const selectedQuestionIds = ref(new Set())
const expandedQuestionIds = ref(new Set())
const revealedAnswerIds = ref(new Set())
const copiedQuestionIds = ref(new Set())
const resultBank = ref(null)
const exportBtnLabel = ref('')
const exportDropdownOpen = ref(false)
const currentSheet = ref(null)
const streamMessage = ref('')
const streamBatchType = ref('')
const streamJsonOutput = ref('')
const streamRawOutput = ref('')
const liveQuestions = ref([])
const agentOutputs = ref([])
const agentRawBuffers = reactive({})
const agentQuestionDrafts = reactive({})
const extractProgress = reactive({})
const questionSheets = ref([])
const examResults = ref([])
const activeGenerationTask = ref(null)
const selectedSheet = ref(null)
const examSelectingSheet = ref(false)
const examAnswers = ref([])
const examStarted = ref(false)
const examSubmitted = ref(false)
const examResult = ref({ score: 0, total_score: 100, correct_count: 0, question_count: 0, detail: [] })
const weakKnowledgePoints = ref([])
watch(examStarted, (val) => {
  document.body.classList.toggle('exam-scroll-override', val)
})
const cumulativeWeakPoints = ref([])
const recentQuizHistory = ref([])
let generationStatusTimer = null
const GENERATION_TASK_STORAGE_KEY = 'question-generator:active-task'

watch(
  () => route.query.xzTask,
  (taskId) => {
    syncXiaoZhiQuestionTask(String(taskId || ''))
  },
  { immediate: true },
)

const diffRank = { '基础': 1, '简单': 1, '提升': 2, '中等': 2, '中': 2, '困难': 3, '难': 3 }

const displayQuestions = computed(() => {
  if (!resultBank.value?.questions) return []
  let list = [...resultBank.value.questions]

  // Filter by favorites
  if (showOnlyFavorites.value) {
    list = list.filter((item, idx) => {
      const qid = item.id || `Q${idx + 1}`
      return favoritedQuestions.value.has(qid)
    })
  }

  // Filter by type tag
  if (activeTypeFilter.value) {
    list = list.filter(item => (item.type || '') === activeTypeFilter.value)
  }

  // Filter by difficulty tag
  if (activeDiffFilter.value) {
    list = list.filter(item => {
      let d = item.difficulty || '中等'
      if (d.includes('基础') || d.includes('简单')) d = '简单'
      else if (d.includes('提升') || d.includes('中')) d = '中等'
      else d = '困难'
      return d === activeDiffFilter.value
    })
  }

  // Filter by search
  const q = questionSearchQuery.value.trim().toLowerCase()
  if (q) {
    list = list.filter(item => {
      const stem = (item.stem || '').toLowerCase()
      const answer = (item.answer || '').toLowerCase()
      const kp = (item.knowledge_point || '').toLowerCase()
      const analysis = (item.analysis || '').toLowerCase()
      const opts = (item.options || []).join(' ').toLowerCase()
      const mistake = (item.mistake_alert || '').toLowerCase()
      return stem.includes(q) || answer.includes(q) || kp.includes(q) || analysis.includes(q) || opts.includes(q) || mistake.includes(q)
    })
  }

  // Sort
  const mode = questionSortMode.value
  const parseId = (q, fallback) => {
    const raw = q.id || q._id || ''
    const m = String(raw).match(/\d+/)
    return m ? parseInt(m[0], 10) : fallback
  }
  if (mode === 'id-asc') {
    list.sort((a, b) => parseId(a, 0) - parseId(b, 0))
  } else if (mode === 'id-desc') {
    list.sort((a, b) => parseId(b, 0) - parseId(a, 0))
  } else if (mode === 'diff-asc') {
    list.sort((a, b) => (diffRank[a.difficulty] || 2) - (diffRank[b.difficulty] || 2))
  } else if (mode === 'diff-desc') {
    list.sort((a, b) => (diffRank[b.difficulty] || 2) - (diffRank[a.difficulty] || 2))
  }

  return list
})

// 缂佺喕顓搁幗妯款洣 computed
const displayTypeStats = computed(() => {
  const stats = {}
  for (const q of displayQuestions.value) {
    const t = q.type || '未分类'
    stats[t] = (stats[t] || 0) + 1
  }
  return stats
})

function normalizeDifficultyText(value) {
  const d = String(value || '中等')
  if (d.includes('基础') || d.includes('简单') || d.toLowerCase().includes('easy')) return '简单'
  if (d.includes('困难') || d.includes('难') || d.toLowerCase().includes('hard')) return '困难'
  return '中等'
}

const displayDiffStats = computed(() => {
  const stats = {}
  for (const q of displayQuestions.value) {
    const d = normalizeDifficultyText(q.difficulty)
    stats[d] = (stats[d] || 0) + 1
  }
  return stats
})

const allDiffStats = computed(() => {
  const all = resultBank.value?.questions
  if (!all) return {}
  const stats = {}
  for (const q of all) {
    const d = normalizeDifficultyText(q.difficulty)
    stats[d] = (stats[d] || 0) + 1
  }
  return stats
})

function diffStatsClass(diff) {
  if (diff === '简单') return 'qg-stats-easy'
  if (diff === '中等') return 'qg-stats-medium'
  return 'qg-stats-hard'
}

const diffDistribution = computed(() => {
  const total = displayQuestions.value.length
  if (!total) return []
  const stats = { '简单': 0, '中等': 0, '困难': 0 }
  for (const q of displayQuestions.value) stats[normalizeDifficultyText(q.difficulty)]++
  return [
    { label: '简单', count: stats['简单'], pct: Math.round(stats['简单'] / total * 100), color: '#16a34a' },
    { label: '中等', count: stats['中等'], pct: Math.round(stats['中等'] / total * 100), color: '#ea580c' },
    { label: '困难', count: stats['困难'], pct: Math.round(stats['困难'] / total * 100), color: '#dc2626' },
  ]
})

const allDiffDistribution = computed(() => {
  const all = resultBank.value?.questions
  if (!all || !all.length) return []
  const total = all.length
  const stats = { '简单': 0, '中等': 0, '困难': 0 }
  for (const q of all) stats[normalizeDifficultyText(q.difficulty)]++
  return [
    { label: '简单', count: stats['简单'], pct: Math.round(stats['简单'] / total * 100), color: '#16a34a' },
    { label: '中等', count: stats['中等'], pct: Math.round(stats['中等'] / total * 100), color: '#ea580c' },
    { label: '困难', count: stats['困难'], pct: Math.round(stats['困难'] / total * 100), color: '#dc2626' },
  ]
})

function toggleTypeFilter(type) {
  activeTypeFilter.value = activeTypeFilter.value === type ? '' : type
}

function toggleDiffFilter(diff) {
  activeDiffFilter.value = activeDiffFilter.value === diff ? '' : diff
}

function clearTagFilters() {
  activeTypeFilter.value = ''
  activeDiffFilter.value = ''
}

const hasActiveTagFilter = computed(() => !!activeTypeFilter.value || !!activeDiffFilter.value)

const filterStatusText = computed(() => {
  const parts = []
  if (activeDiffFilter.value) parts.push(activeDiffFilter.value + '难度')
  if (activeTypeFilter.value) parts.push(activeTypeFilter.value)
  return parts.join(' × ')
})

const quizScore = computed(() => {
  if (!resultBank.value) return 0
  return quizSubmitted.value.reduce((sum, submitted, idx) => {
    if (!submitted) return sum
    const q = resultBank.value.questions[idx]
    return sum + (quizCheckCorrect(idx) ? scoreForQuestion(q) : 0)
  }, 0)
})
const quizTotalScore = computed(() => {
  if (!resultBank.value) return 0
  return bankTotalScore(resultBank.value.questions)
})
const quizAllSubmitted = computed(() => {
  if (!resultBank.value) return false
  return quizSubmitted.value.length === resultBank.value.questions.length && quizSubmitted.value.every(Boolean)
})
const quizWeakPoints = computed(() => {
  if (!resultBank.value || !quizAllSubmitted.value) return []
  const kpMap = new Map()
  resultBank.value.questions.forEach((q, idx) => {
    const kp = q.knowledge_point || q.type || '未知'
    if (!kpMap.has(kp)) kpMap.set(kp, { name: kp, total: 0, wrong: 0 })
    const stat = kpMap.get(kp)
    stat.total++
    if (!quizCheckCorrect(idx)) stat.wrong++
  })
  return [...kpMap.values()].filter(s => s.wrong > 0).sort((a, b) => a.wrong - b.wrong)
})
const filterDifficulty = ref('')
const filterType = ref('')
const showDetailModal = ref(false)
const selectedQuestionDetail = ref(null)
const examSaved = ref(false)
const examStartAt = ref(0)
const examElapsedSeconds = ref(0)
const currentExamQuestion = ref(0)
const timerMode = ref('countup') // 'countup' or 'countdown'
const countdownTarget = ref(30 * 60) // 榛樿30鍒嗛挓鍊掕鏃?
const aiScoring = ref(false)
const aiScoreMessage = ref('')
let examTimer = 0
let examScrollObserver = null
const historyDetail = ref(null)
const historyPrintRef = ref(null)
const printingHistory = ref(false)
const historyTab = ref('sheets')
const quizAnswers = ref([])
const quizSubmitted = ref([])
const answerCardRef = ref(null)
const answerCardPos = reactive({ x: -1, y: -1 })
const answerCardDragging = ref(false)
const cardMinimized = ref(false)
const flaggedQuestions = ref(new Set())

function toggleFlagQuestion(index) {
  if (flaggedQuestions.value.has(index)) {
    flaggedQuestions.value.delete(index)
  } else {
    flaggedQuestions.value.add(index)
  }
  flaggedQuestions.value = new Set(flaggedQuestions.value)
}
let dragStartX = 0
let dragStartY = 0
let dragPosStartX = 0
let dragPosStartY = 0
const { addLog, setSection } = useGlobalDebug()

const maxQuestionCount = 50

const questionTypes = reactive([
  { key: 'single', label: '单选题', type: '单选题', enabled: true, count: 3, score: 2, color: '#3b82f6' },
  { key: 'multi', label: '多选题', type: '多选题', enabled: false, count: 2, score: 3, color: '#8b5cf6' },
  { key: 'judge', label: '判断题', type: '判断题', enabled: false, count: 2, score: 1, color: '#10b981' },
  { key: 'fill', label: '填空题', type: '填空题', enabled: true, count: 3, score: 2, color: '#f59e0b' },
  { key: 'short', label: '简答题', type: '简答题', enabled: false, count: 2, score: 6, color: '#ef4444' },
  { key: 'calc', label: '计算题', type: '计算题', enabled: false, count: 2, score: 8, color: '#58d89c' },
  { key: 'app', label: '综合应用题', type: '综合应用题', enabled: false, count: 2, score: 10, color: '#ec4899' },
])

// 閰嶇疆鍙樻洿鑷姩淇濆瓨锛堢洃鍚墍鏈夐厤缃浉鍏崇姸鎬侊級
watch(
  () => [
    ...questionTypes.map(qt => `${qt.enabled}:${qt.count}:${qt.score}`),
    ...difficultyRatios.map(d => d.value),
    difficultyLocks.easy, difficultyLocks.medium, difficultyLocks.hard,
    generationOptions.analysis, generationOptions.tags, generationOptions.variants,
    autoDistribute.value,
    targetQuestionCount.value,
    courseName.value,
    chapterName.value,
    constraints.value,
  ],
  () => { saveConfig() },
)

const totalCount = computed(() =>
  autoDistribute.value
    ? Number(targetQuestionCount.value || 0)
    : questionTypes.reduce((sum, qt) => sum + (qt.enabled ? Number(qt.count || 0) : 0), 0),
)

const totalScore = computed(() =>
  Number(questionTypes.reduce((sum, qt) => {
    if (!qt.enabled) return sum
    const count = autoDistribute.value ? 0 : Number(qt.count || 0)
    return sum + count * Number(qt.score || 0)
  }, 0).toFixed(1)),
)

const enabledTypeCount = computed(() => questionTypes.filter(qt => qt.enabled).length)

const ratioText = computed(() => {
  const total = totalCount.value
  if (!total) return ''
  return questionTypes
    .filter(qt => qt.enabled && qt.count > 0)
    .map(qt => `${qt.label} ${Math.round((qt.count / total) * 100)}%`)
    .join('、')
})

const canGenerate = computed(() =>
  (uploadedFiles.value.length > 0 || pastedText.value.trim()) &&
  totalCount.value > 0 &&
  totalCount.value <= maxQuestionCount &&
  enabledTypeCount.value > 0,
)
const enabledQuestionTypes = computed(() => questionTypes.filter(qt => qt.enabled))
const previewTotalScore = computed(() => {
  if (!autoDistribute.value) return totalScore.value
  const avgScore = enabledQuestionTypes.value.length
    ? enabledQuestionTypes.value.reduce((sum, qt) => sum + Number(qt.score || 0), 0) / enabledQuestionTypes.value.length
    : 0
  return Number((Number(targetQuestionCount.value || 0) * avgScore).toFixed(1))
})
const estimatedMinutes = computed(() => Math.max(5, Math.ceil(Number(totalCount.value || 0) * 1.6)))
const uploadProgress = computed(() => {
  if (generating.value) return 68
  if (uploadedFiles.value.length || pastedText.value.trim()) return 100
  return 0
})
const dashboardStats = computed(() => {
  const examCount = dashboardExamResults.value.length
  return [
    { label: '累计题目数', value: cumulativeQuestionCount.value, hint: '历史题单与考试题目', icon: FileText, tone: 'blue' },
    { label: '正确率', value: examCount ? `${latestAccuracy.value}%` : '--', hint: '最近一次考试', icon: CheckCircle2, tone: 'green' },
    { label: '已生成题库', value: questionSheets.value.length, hint: '历史题单', icon: Cpu, tone: 'orange' },
    { label: '已完成考试', value: examCount, hint: '模拟考试记录', icon: ClipboardList, tone: 'purple' },
  ]
})
const dashboardExamResults = computed(() => (
  examResults.value.length ? examResults.value : recentQuizHistory.value
))
const cumulativeQuestionCount = computed(() => {
  const sheetTotal = questionSheets.value.reduce((sum, item) => sum + Number(item.question_count || item.question_bank?.questions?.length || 0), 0)
  const examTotal = dashboardExamResults.value.reduce((sum, item) => sum + Number(item.question_count || item.detail?.length || 0), 0)
  return sheetTotal + examTotal
})
const weeklyTrend = computed(() => {
  const days = []
  const counts = new Map()
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  for (let offset = 6; offset >= 0; offset -= 1) {
    const date = new Date(today)
    date.setDate(today.getDate() - offset)
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
    counts.set(key, 0)
    days.push({ key, day: `周${'日一二三四五六'[date.getDay()]}` })
  }
  dashboardExamResults.value.forEach((item) => {
    const rawDate = item.created_at || item.timestamp
    const parsed = rawDate ? new Date(rawDate) : null
    if (!parsed || Number.isNaN(parsed.getTime())) return
    const key = `${parsed.getFullYear()}-${String(parsed.getMonth() + 1).padStart(2, '0')}-${String(parsed.getDate()).padStart(2, '0')}`
    if (!counts.has(key)) return
    counts.set(key, counts.get(key) + Number(item.question_count || item.detail?.length || 0))
  })
  return days.map(item => ({ ...item, value: counts.get(item.key) || 0 }))
})
const trendYAxisMax = computed(() => {
  const peak = Math.max(0, ...weeklyTrend.value.map(item => Number(item.value) || 0))
  if (!peak) return 4
  return Math.max(4, Math.ceil(peak / 4) * 4)
})
const trendYAxisTicks = computed(() => [1, 0.75, 0.5, 0.25, 0].map(ratio => Math.round(trendYAxisMax.value * ratio)))
const trendChartDots = computed(() => {
  const left = 22
  const right = 540
  const top = 20
  const bottom = 152
  return weeklyTrend.value.map((item, index) => {
    const x = left + ((right - left) / 6) * index
    const y = bottom - (Math.max(0, Math.min(trendYAxisMax.value, Number(item.value) || 0)) / trendYAxisMax.value) * (bottom - top)
    return { ...item, x: Number(x.toFixed(1)), y: Number(y.toFixed(1)) }
  })
})
const trendLinePoints = computed(() => trendChartDots.value.map(point => `${point.x},${point.y}`).join(' '))
const trendAreaPoints = computed(() => {
  const points = trendChartDots.value.map(point => `${point.x},${point.y}`).join(' ')
  return `22,152 ${points} 540,152`
})
const weeklyTrendSummary = computed(() => {
  const total = weeklyTrend.value.reduce((sum, item) => sum + item.value, 0)
  if (!total) return '最近 7 天暂无作答记录'
  const peak = weeklyTrend.value.reduce((best, item) => item.value > best.value ? item : best, weeklyTrend.value[0])
  return `最高活跃：${peak.day} · 近 7 天完成 ${total} 题`
})
const weeklyTrendNote = computed(() => (
  weeklyTrend.value.some(item => item.value > 0)
    ? '趋势按真实考试提交记录统计。'
    : '完成考试后，这里会展示最近 7 天的真实做题趋势。'
))
const typeAccuracy = computed(() => {
  const stats = new Map()
  dashboardExamResults.value.forEach((exam) => {
    if (!Array.isArray(exam.detail)) return
    exam.detail.forEach((item) => {
      const name = String(item.type || item.question?.type || '其他题型').trim() || '其他题型'
      const current = stats.get(name) || { name, total: 0, correct: 0 }
      current.total += 1
      if (item.correct) current.correct += 1
      stats.set(name, current)
    })
  })
  return Array.from(stats.values())
    .map(item => ({ name: item.name, value: Math.round((item.correct / item.total) * 100), total: item.total }))
    .sort((a, b) => b.total - a.total || a.name.localeCompare(b.name))
})
const typeAccuracyNote = computed(() => (
  typeAccuracy.value.length
    ? '按已提交考试中的真实题型统计。'
    : '尚无可统计的题型作答记录。'
))
const chapterMastery = computed(() => {
  const weak = cumulativeWeakPoints.value.slice(0, 4)
  return weak.map(item => ({ name: item.name, value: Math.round((item.accuracy || 0) * 100) }))
})
const chapterMasteryNote = computed(() => (
  chapterMastery.value.length
    ? '根据历次考试错题汇总当前薄弱知识点。'
    : '尚无可用于诊断的错题数据。'
))
const priorityReviewText = computed(() => (
  chapterMastery.value.length
    ? `优先复习：${chapterMastery.value.slice(0, 2).map(item => item.name).join('、')}`
    : '完成考试后生成优先复习建议'
))
const recentActivities = computed(() => {
  const rows = []
  questionSheets.value.slice(0, 2).forEach(item => rows.push({
    id: `sheet-${item.id}`,
    kind: 'sheet',
    type: '题库',
    tag: '题库',
    title: item.title || '最近生成的题库',
    time: item.created_at || '刚刚',
    icon: FileText,
    action: () => { viewSheet(item); activeModule.value = 'history' },
  }))
  examResults.value.slice(0, 2).forEach(item => rows.push({
    id: `exam-${item.id}`,
    kind: 'exam',
    type: '考试',
    tag: '考试',
    title: item.title || '最近完成的考试',
    time: item.created_at || item.timestamp || '刚刚',
    icon: ClipboardCheck,
    action: () => { viewExamResult(item); activeModule.value = 'history' },
  }))
  return rows.slice(0, 3)
})
const selectedMaterialPreview = computed(() => {
  if (selectedMaterialIndex.value < 0) return null
  return uploadedFiles.value[selectedMaterialIndex.value] || null
})
const filteredHistoryRows = computed(() => {
  const runningTask = activeGenerationTask.value?.status === 'running' ? activeGenerationTask.value : null
  const runningMeta = runningTask?.meta || runningTask?.payload?.meta || {}
  const rows = [
    ...(runningTask ? [{
      id: `task-${runningTask.taskId || runningMeta.taskId || 'running'}`,
      raw: runningTask,
      kind: 'task',
      title: runningMeta.title || '题单正在生成中',
      type: '生成中',
      course: runningMeta.course_name || '后台任务',
      count: runningMeta.question_count || 0,
      time: runningTask.updated_at || runningMeta.created_at || '刚刚',
      status: 'running',
    }] : []),
    ...questionSheets.value.map(item => ({
      id: `sheet-${item.id}`,
      raw: item,
      kind: 'sheet',
      title: item.title || '未命名题库',
      type: '题库记录',
      course: item.course_name || '未指定课程',
      count: item.question_count || item.question_bank?.questions?.length || 0,
      time: item.created_at || '-',
    })),
    ...examResults.value.map(item => ({
      id: `exam-${item.id}`,
      raw: item,
      kind: 'exam',
      title: item.title || '模拟考试',
      type: '考试记录',
      course: item.course_name || '未指定课程',
      count: item.question_count || item.detail?.length || 0,
      time: item.created_at || item.timestamp || '-',
    })),
  ]
  if (historyFilter.value === 'all') return rows
  if (historyFilter.value === 'sheet') return rows.filter(item => item.kind === 'sheet' || item.kind === 'task')
  return rows.filter(item => item.kind === historyFilter.value)
})
const latestAccuracy = computed(() => {
  if (!dashboardExamResults.value.length) return 0
  const latest = dashboardExamResults.value[0]
  if (!latest.question_count) return 0
  return Math.round((latest.correct_count / latest.question_count) * 100)
})
const selectedQuestions = computed(() => resolveExamQuestions({ sheet: selectedSheet.value }))
const canLaunchSelectedExam = computed(() => Boolean(selectedSheet.value && selectedQuestions.value.length))
const answeredCount = computed(() => examAnswers.value.filter(a => Array.isArray(a) ? a.length > 0 : Boolean(String(a || '').trim())).length)
const historyDetailQuestions = computed(() => {
  if (!historyDetail.value) return []
  if (historyDetail.value.question_bank) return historyDetail.value.question_bank.questions || []
  return historyDetail.value.detail || []
})


const formattedElapsedTime = computed(() => {
  let seconds
  if (timerMode.value === 'countdown') {
    seconds = Math.max(0, countdownTarget.value - examElapsedSeconds.value)
  } else {
    seconds = examElapsedSeconds.value
  }
  const minuteText = String(Math.floor(seconds / 60)).padStart(2, '0')
  const secondText = String(seconds % 60).padStart(2, '0')
  return `${minuteText}:${secondText}`
})

const formattedCountdownTarget = computed(() => {
  const total = countdownTarget.value
  const minuteText = String(Math.floor(total / 60)).padStart(2, '0')
  const secondText = String(total % 60).padStart(2, '0')
  return `${minuteText}:${secondText}`
})

const timerDisplayLabel = computed(() => timerMode.value === 'countdown' ? '倒计时' : '正计时')

const wrongQuestionIndices = computed(() => {
  if (!examResult.value?.detail) return new Set()
  const indices = new Set()
  examResult.value.detail.forEach((item, idx) => {
    if (!item.correct) indices.add(idx)
  })
  return indices
})

const formattedElapsedMinutes = computed(() => {
  const minutes = Math.floor(examElapsedSeconds.value / 60)
  return `${minutes} min`
})

const answerCardStyle = computed(() => {
  if (answerCardPos.x < 0) {
    return { right: '32px', top: '140px' }
  }
  return { left: answerCardPos.x + 'px', top: answerCardPos.y + 'px', right: 'auto' }
})

function toggleAnswerCard(e) {
  e?.preventDefault?.()
  e?.stopPropagation?.()
  cardMinimized.value = !cardMinimized.value
}

function startDrag(e) {
  answerCardDragging.value = true
  const point = e.touches ? e.touches[0] : e
  dragStartX = point.clientX
  dragStartY = point.clientY
  if (answerCardPos.x < 0) {
    const rect = answerCardRef.value?.getBoundingClientRect()
    if (rect) {
      answerCardPos.x = rect.left
      answerCardPos.y = rect.top
    }
  }
  dragPosStartX = answerCardPos.x
  dragPosStartY = answerCardPos.y
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchmove', onDrag, { passive: false })
  document.addEventListener('touchend', stopDrag)
}

function onDrag(e) {
  if (!answerCardDragging.value) return
  if (e.cancelable) e.preventDefault()
  const point = e.touches ? e.touches[0] : e
  let nx = dragPosStartX + (point.clientX - dragStartX)
  let ny = dragPosStartY + (point.clientY - dragStartY)
  nx = Math.max(0, Math.min(nx, window.innerWidth - 260))
  ny = Math.max(0, Math.min(ny, window.innerHeight - 60))
  answerCardPos.x = nx
  answerCardPos.y = ny
}

function stopDrag() {
  answerCardDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)
}

/* 棰樺簱鐢熸垚钖勫急鐐归厤缃?*/

function isWeakPoint(knowledgePoint) {
  if (!knowledgePoint) return false
  const kp = String(knowledgePoint).toLowerCase()
  return selectedWeakPoints.value.some(wp => {
    const w = String(wp).toLowerCase()
    return kp.includes(w) || w.includes(kp)
  })
}

function toggleWeakPoint(wp) {
  const idx = selectedWeakPoints.value.indexOf(wp)
  if (idx >= 0) {
    selectedWeakPoints.value.splice(idx, 1)
  } else {
    selectedWeakPoints.value.push(wp)
  }
  updateProfileInput()
}

function addWeakTag() {
  const tag = newWeakTag.value.trim()
  if (!tag) return
  if (!selectedWeakPoints.value.includes(tag)) {
    selectedWeakPoints.value.push(tag)
  }
  newWeakTag.value = ''
  updateProfileInput()
}

function removeWeakTag(tag) {
  const idx = selectedWeakPoints.value.indexOf(tag)
  if (idx >= 0) selectedWeakPoints.value.splice(idx, 1)
  updateProfileInput()
}

function generateSimilarQuestion(q) {
  const kp = q.knowledge_point || ''

  // Add knowledge point to weak tags if not present
  if (kp && !selectedWeakPoints.value.includes(kp)) {
    selectedWeakPoints.value.push(kp)
  }
  updateProfileInput()

  // Switch to generate tab and scroll to top config area
  activeTab.value = 'generate'
  mobileConfigExpanded.value = true
  nextTick(() => {
    const sidebar = document.querySelector('.qg-left-sidebar .qg-sidebar-scroll')
    if (sidebar) sidebar.scrollTop = 0
    const panel = document.querySelector('.qg-left-sidebar')
    if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function copyQuestion(q, idx) {
  const qid = q.id || `Q${idx + 1}`
  const lines = []
  lines.push('【' + qid + '】' + (q.type || '') + '（' + scoreForQuestion(q) + '分）')
  lines.push('知识点：' + (q.knowledge_point || '-'))
  lines.push('难度：' + (q.difficulty || '-'))
  lines.push('')
  lines.push(q.stem || '')
  if (q.options && q.options.length) {
    q.options.forEach(opt => { lines.push(opt) })
  }
  lines.push('')
  lines.push('【正确答案】' + (q.answer || '-'))
  if (q.analysis) lines.push('【解析】' + q.analysis)
  if (q.mistake_alert) lines.push('【易错提醒】' + q.mistake_alert)
  const text = lines.join('\n')

  navigator.clipboard.writeText(text).then(() => {
    copiedQuestionIds.value.add(qid)
    copiedQuestionIds.value = new Set(copiedQuestionIds.value)
    setTimeout(() => {
      copiedQuestionIds.value.delete(qid)
      copiedQuestionIds.value = new Set(copiedQuestionIds.value)
    }, 1500)
  }).catch(() => {
    // Fallback for older browsers
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.cssText = 'position:fixed;left:-9999px'
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    copiedQuestionIds.value.add(qid)
    copiedQuestionIds.value = new Set(copiedQuestionIds.value)
    setTimeout(() => {
      copiedQuestionIds.value.delete(qid)
      copiedQuestionIds.value = new Set(copiedQuestionIds.value)
    }, 1500)
  })
}

function updateProfileInput() {
  const parts = []
  if (selectedWeakPoints.value.length) parts.push('薄弱知识点：' + selectedWeakPoints.value.join('、'))
  studentProfile.value = parts.join('、')
}

onMounted(() => {
  applyRoutePrefill()
  if (route.query.module === 'exam') {
    activeModule.value = 'exam'
    activeTab.value = 'exam'
  }
  const configPromise = loadConfig()
  restoreGenerationTask()
  const historyPromise = loadHistory()
  const cachePromise = hydrateNodeCachesFromServer()
  syncGenerationStatus()
  loadRecentQuizHistory()
  Promise.allSettled([configPromise, historyPromise, cachePromise]).then(() => {
    handleLearningNodeQuestionEntry()
  })
})

function applyRoutePrefill() {
  const module = String(route.query.module || '').trim()
  const course = String(route.query.course || '').trim()
  const chapter = String(route.query.chapter || route.query.topic || '').trim()
  const count = Number(route.query.count)
  if (module && moduleNavItems.some((item) => item.key === module)) {
    activeModule.value = module
    activeTab.value = module
  }
  if (course) courseName.value = course
  if (chapter) chapterName.value = chapter
  ;[course, chapter].filter(Boolean).forEach((tag) => {
    if (!selectedWeakPoints.value.includes(tag)) selectedWeakPoints.value.push(tag)
  })
  if ((course || chapter) && !pastedText.value.trim() && !uploadedFiles.value.length) {
    const topic = [course, chapter].filter(Boolean).join(' ')
    pastedText.value = `请围绕 ${topic} 生成嵌入式学习小测，重点覆盖基础概念、GPIO 配置流程、常见易错点和简单实践理解。`
  }
  if (Number.isFinite(count) && count > 0) {
    targetQuestionCount.value = Math.min(50, Math.max(1, Math.round(count)))
    autoDistribute.value = true
  }
  if ((course || chapter || Number.isFinite(count)) && !questionTypes.some((qt) => qt.enabled)) {
    questionTypes.forEach((qt) => {
      qt.enabled = ['single', 'judge', 'fill', 'short'].includes(qt.key)
    })
  }
}

function learningQuestionCacheKey() {
  return String(route.query.cacheKey || '').trim()
}

function restoreLearningNodeQuestionSheet() {
  const cacheKey = learningQuestionCacheKey()
  if (!cacheKey) return false
  const cache = getNodeCache(cacheKey)
  const sheetId = String(cache?.sheetId || '').trim()
  const sheet = questionSheets.value.find((item) => String(item.id) === sheetId)
    || questionSheets.value.find((item) => cache?.title && item.title === cache.title)
  if (!sheet) return false
  viewSheet(sheet)
  activeModule.value = 'history'
  activeTab.value = 'history'
  historyFilter.value = 'sheet'
  setNodeCache(cacheKey, {
    status: 'complete',
    resourceType: 'question-bank',
    title: sheet.title || 'STM32 题库练习小测',
    sheetId: sheet.id,
    questionCount: sheet.question_count || sheet.question_bank?.questions?.length || 0,
    route: `${route.path}?module=history&cacheKey=${encodeURIComponent(cacheKey)}`,
    lastOpenedAt: Date.now(),
  })
  return true
}

function handleLearningNodeQuestionEntry() {
  if (String(route.query.xzTask || '').trim()) return
  if (restoreLearningNodeQuestionSheet()) return
  const cache = getNodeCache(learningQuestionCacheKey())
  const staleRestore = route.query.restore === '1' && cache?.status === 'running' && !cache?.taskId && !cache?.sheetId
  if ((route.query.autostart !== '1' && !staleRestore) || generating.value || activeGenerationTask.value?.status === 'running') return
  if (canGenerate.value) {
    generate()
  }
}

function markLearningNodeQuestionComplete(sheet, bank) {
  const cacheKey = learningQuestionCacheKey()
  if (!cacheKey) return
  markNodeCacheComplete(cacheKey, {
    resourceType: 'question-bank',
    title: sheet?.title || bank?.title || 'STM32 题库练习小测',
    sheetId: sheet?.id || '',
    questionCount: sheet?.question_count || bank?.questions?.length || 0,
    route: `${route.path}?module=history&cacheKey=${encodeURIComponent(cacheKey)}`,
  })
}

function loadRecentQuizHistory() {
  try {
    const raw = localStorage.getItem('quizHistory')
    if (raw) {
      const history = JSON.parse(raw)
      if (Array.isArray(history)) {
        recentQuizHistory.value = history.slice(-5).reverse()
      }
    }
  } catch {}
  // Also load cumulative weak points from history
  try {
    const raw = localStorage.getItem('quizHistory')
    if (raw) {
      const history = JSON.parse(raw)
      if (Array.isArray(history)) {
        buildCumulativeWeakPoints(history)
      }
    }
  } catch {}
}
onUnmounted(() => {
  stopExamTimer()
  stopGenerationStatusPolling()
  stopXiaoZhiQuestionTaskPolling()
  if (saveConfigTimer) { clearTimeout(saveConfigTimer); saveConfigTimer = null }
  if (examScrollObserver) { examScrollObserver.disconnect(); examScrollObserver = null }
  document.body.classList.remove('exam-scroll-override')
  stopDrag()
})

function handleDrop(e) {
  isDragging.value = false
  addFiles(Array.from(e.dataTransfer.files))
}

function handleFileSelect(e) {
  addFiles(Array.from(e.target.files))
}

function addFiles(files) {
  const startIndex = uploadedFiles.value.length
  const entries = files.map(file => ({ file: markRaw(file), previewText: '', previewLoading: false }))
  uploadedFiles.value.push(...entries)
  if (files.length && selectedMaterialIndex.value < 0) {
    selectedMaterialIndex.value = startIndex
  }
  entries.forEach((_, idx) => loadFilePreview(startIndex + idx))
}

async function loadFilePreview(index) {
  const item = uploadedFiles.value[index]
  if (!item) return
  const kind = fileKind(item.file.name)
  if (!['TXT', 'MD'].includes(kind)) {
    item.previewText = kind + ' 文件已选择。该类型正文会通过上传生成接口解析；当前预览显示文件名、类型和大小。'
    return
  }
  item.previewLoading = true
  try {
    const text = await item.file.text()
    item.previewText = String(text || '').slice(0, 5000)
  } catch {
    item.previewText = '文件读取失败，请重新选择文件。'
  } finally {
    item.previewLoading = false
  }
}

function removeFile(index) {
  uploadedFiles.value.splice(index, 1)
  if (!uploadedFiles.value.length) {
    selectedMaterialIndex.value = -1
  } else if (selectedMaterialIndex.value === index) {
    selectedMaterialIndex.value = Math.min(index, uploadedFiles.value.length - 1)
  } else if (selectedMaterialIndex.value > index) {
    selectedMaterialIndex.value -= 1
  }
}

function selectMaterialPreview(index) {
  selectedMaterialIndex.value = index
}

function fileKind(name) {
  const ext = String(name || '').split('.').pop()?.toUpperCase() || 'FILE'
  if (ext === 'DOC') return 'DOC'
  if (ext === 'DOCX') return 'DOCX'
  if (ext === 'PPT' || ext === 'PPTX') return 'PPT'
  if (ext === 'PDF') return 'PDF'
  if (ext === 'MD' || ext === 'MARKDOWN') return 'MD'
  if (ext === 'TXT') return 'TXT'
  return ext.slice(0, 4)
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function selectQuestionModule(key) {
  activeModule.value = key
  if (key !== 'history') examSelectingSheet.value = false
  if (key === 'exam') {
    activeTab.value = 'exam'
    if (!selectedSheet.value && questionSheets.value.length) {
      startExamFromSheet(questionSheets.value[0])
    } else if (!selectedSheet.value && resultBank.value?.questions?.length) {
      startExamFromResult()
    }
  }
  else if (key === 'history') activeTab.value = 'history'
  else activeTab.value = 'generate'
}

function enterSheetSelectMode() {
  examSelectingSheet.value = true
  historyFilter.value = 'sheet'
  activeTab.value = 'history'
  activeModule.value = 'history'
}

function questionTypeLabel(qt) {
  const labels = {
    single: '单选题',
    multi: '多选题',
    judge: '判断题',
    fill: '填空题',
    short: '简答题',
    calc: '计算题',
    app: '综合应用题',
  }
  return labels[qt.key] || qt.label || qt.type || '题型'
}

function openHistoryRow(item) {
  if (item.kind === 'task') {
    activeTab.value = 'generate'
    activeModule.value = 'generate'
    syncGenerationStatus()
    return
  }
  if (examSelectingSheet.value && item.kind === 'sheet') {
    startExamFromSheet(item.raw)
    examSelectingSheet.value = false
    activeTab.value = 'exam'
    activeModule.value = 'exam'
    return
  }
  if (item.kind === 'exam') viewExamResult(item.raw)
  else if (item.kind === 'sheet') viewSheet(item.raw)
  else historyDetail.value = {
    id: item.id,
    title: item.title,
    course_name: item.course,
    target_topic: '综合练习',
    question_bank: { questions: [] },
  }
}

function diffClass(d) {
  const normalized = normalizeDifficultyText(d)
  if (normalized === '简单') return 'qg-diff-easy'
  if (normalized === '中等') return 'qg-diff-medium'
  return 'qg-diff-hard'
}

function typeClass(t) {
  const type = String(t || '')
  if (type.includes('单选')) return 'qg-type-single'
  if (type.includes('多选')) return 'qg-type-multi'
  if (type.includes('填空')) return 'qg-type-fill'
  if (type.includes('简答')) return 'qg-type-essay'
  return 'qg-type-default'
}

function diffTooltip(d) {
  const normalized = normalizeDifficultyText(d)
  if (normalized === '简单') return '简单难度：考查基本概念和核心知识点'
  if (normalized === '中等') return '中等难度：考查知识运用和综合分析能力'
  return '困难难度：考查深度理解和综合应用能力'
}

function typeTooltip(t) {
  const type = String(t || '')
  if (type.includes('单选')) return '单选题：从多个选项中选择一个正确答案'
  if (type.includes('多选')) return '多选题：从多个选项中选择所有正确答案'
  if (type.includes('填空')) return '填空题：在空白处填写正确内容'
  if (type.includes('简答')) return '简答题：用文字阐述对问题的理解'
  return ''
}

function highlightText(text, query) {
  if (!text || !query || !query.trim()) return escapeHtml(text || '')
  const escaped = escapeHtml(text)
  const q = query.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return escaped.replace(new RegExp(`(${q})`, 'gi'), '<mark class="qg-search-highlight">$1</mark>')
}

function truncatedStem(q) {
  const text = q.stem || ''
  const truncated = text.length > 60 ? text.slice(0, 60) + '...' : text
  return highlightText(truncated, questionSearchQuery.value)
}

const _fieldAliases = { top: 'stem', question: 'stem', content: 'stem', body: 'stem', explanation: 'analysis', solution: 'analysis', knowledge: 'knowledge_point', 'knowledge-point': 'knowledge_point' }

function normalizeQuestion(q) {
  if (!q || typeof q !== 'object') return null
  const nq = { ...q }
  for (const [alias, target] of Object.entries(_fieldAliases)) {
    if (alias in nq && !(target in nq)) {
      nq[target] = nq[alias]
    }
  }
  return nq
}

function isValidQuestion(q) {
  return q && typeof q === 'object' &&
    typeof q.stem === 'string' && q.stem.trim() &&
    typeof q.type === 'string' && q.type.trim() &&
    typeof q.answer === 'string' && q.answer.trim()
}

function extractCompleteObjects(raw) {
  const results = []
  let depth = 0
  let start = -1
  for (let i = 0; i < raw.length; i++) {
    if (raw[i] === '{') {
      if (depth === 0) start = i
      depth++
    } else if (raw[i] === '}') {
      depth--
      if (depth === 0 && start >= 0) {
        results.push(raw.slice(start, i + 1))
        start = -1
      }
    }
  }
  return results
}

function extractQuestionsFromRaw(raw) {
  if (!raw) return []
  const questions = []
  const seen = new Set()

  const addFromParsed = (parsed) => {
    const arr = Array.isArray(parsed?.questions) ? parsed.questions : []
    for (const q of arr) {
      const nq = normalizeQuestion(q)
      if (isValidQuestion(nq) && !seen.has(nq.stem)) {
        seen.add(nq.stem)
        questions.push(nq)
      }
    }
  }

  // 1) 鐏忔繆鐦€瑰本鏆ｇ憴锝嗙€?
  try {
    addFromParsed(JSON.parse(raw))
    if (questions.length) return questions
  } catch {}

  // 2) 閫愪釜鎻愬彇瀹屾暣 JSON 瀵硅薄
  for (const objStr of extractCompleteObjects(raw)) {
    if (!objStr.includes('"stem"') && !objStr.includes('"questions"')) continue
    try { addFromParsed(JSON.parse(objStr)) } catch {}
  }
  if (questions.length) return questions

  // 3) 浠庢祦寮忎笉瀹屾暣 JSON 涓敤姝ｅ垯閫愰鎻愬彇
  const stemRegex = /"stem"\s*:\s*"((?:[^"\\]|\\.)*)"/g
  let match
  while ((match = stemRegex.exec(raw)) !== null) {
    const stem = match[1].replace(/\\"/g, '"').replace(/\\n/g, '\n').replace(/\\\\/g, '\\')
    if (!stem.trim() || seen.has(stem)) continue

    const pos = match.index
    const objStart = raw.lastIndexOf('{', pos)
    const afterStem = raw.slice(pos)

    const typeMatch = afterStem.match(/"type"\s*:\s*"((?:[^"\\]|\\.)*)"/)
    const answerMatch = afterStem.match(/"answer"\s*:\s*"((?:[^"\\]|\\.)*)"/)
    const analysisMatch = afterStem.match(/"analysis"\s*:\s*"((?:[^"\\]|\\.)*)"/)

    if (!typeMatch || !answerMatch) continue

    const nq = normalizeQuestion({
      stem,
      type: typeMatch[1].replace(/\\"/g, '"'),
      answer: answerMatch[1].replace(/\\"/g, '"'),
      analysis: analysisMatch ? analysisMatch[1].replace(/\\"/g, '"') : '',
    })
    if (isValidQuestion(nq) && !seen.has(nq.stem)) {
      seen.add(nq.stem)
      questions.push(nq)
    }
  }

  return questions
}

function updateLiveQuestions() {
  const extracted = extractQuestionsFromRaw(streamRawOutput.value)
  if (extracted.length > liveQuestions.value.length) {
    liveQuestions.value = extracted
  }
}

function rebuildLiveQuestionsFromAgents() {
  const orderedNames = agentOutputs.value
    .map(item => item.name)
    .filter(name => Array.isArray(agentQuestionDrafts[name]))
  const seen = new Set()
  const merged = []
  orderedNames.forEach((name) => {
    agentQuestionDrafts[name].forEach((question) => {
      const key = `${question.type || ''}-${question.stem || ''}`
      if (!question.stem || seen.has(key)) return
      seen.add(key)
      merged.push(question)
    })
  })
  liveQuestions.value = merged.map((question, index) => ({
    ...question,
    id: question.id || `Q${index + 1}`,
  }))
}

function agentLabel(name = '') {
  const labelMap = {
    document_parser_agent: '文档解析智能体',
    task_planner_agent: '任务规划智能体',
    route_by_requested_types: '按需派发路由',
    aggregate_batches: '题库汇总智能体',
    single_choice_agent: '单选题智能体',
    multiple_choice_agent: '多选题智能体',
    true_false_agent: '判断题智能体',
    fill_blank_agent: '填空题智能体',
    short_answer_agent: '简答题智能体',
    calculation_agent: '计算题智能体',
    application_agent: '应用题智能体',
  }
  if (labelMap[name]) return labelMap[name]
  return String(name).replace(/_agent$/, '智能体').replaceAll('_', ' ')
}

function agentStatusText(status) {
  const statusMap = {
    running: '运行中',
    done: '完成',
    error: '异常',
    idle: '等待',
  }
  return statusMap[status] || status || '等待'
}

function formatAgentPreview(output) {
  if (!output) return ''
  if (typeof output === 'string') return output.slice(0, 1200)
  const compact = { ...output }
  if (Array.isArray(compact.questions)) {
    compact.questions = compact.questions.slice(0, 3)
    compact.question_count = output.questions.length
  }
  return JSON.stringify(compact, null, 2).slice(0, 1600)
}

function upsertAgentOutput(payload = {}) {
  const name = payload.agent || payload.question_type && `${payload.question_type}_agent`
  if (!name) return
  const index = agentOutputs.value.findIndex(item => item.name === name)
  const current = index >= 0 ? agentOutputs.value[index] : {
    name,
    label: agentLabel(name),
    status: 'idle',
    message: '',
    preview: '',
  }
  const next = {
    ...current,
    status: payload.status || (payload.stage === 'agent_output' ? 'done' : 'running'),
    message: payload.message || current.message,
    preview: payload.output ? formatAgentPreview(payload.output) : current.preview,
  }
  if (index >= 0) {
    agentOutputs.value.splice(index, 1, next)
  } else {
    agentOutputs.value.push(next)
  }
  if (payload.stage === 'agent_output' && Array.isArray(payload.output?.questions)) {
    agentQuestionDrafts[name] = payload.output.questions.map(normalizeQuestion).filter(isValidQuestion)
    rebuildLiveQuestionsFromAgents()
  }
}

function appendAgentDelta(payload = {}) {
  const name = payload.agent || payload.question_type && `${payload.question_type}_agent`
  if (!name) return
  upsertAgentOutput({
    agent: name,
    status: 'running',
    message: `${agentLabel(name)}正在生成题目...`,
  })
  const index = agentOutputs.value.findIndex(item => item.name === name)
  if (index < 0) return
  agentRawBuffers[name] = `${agentRawBuffers[name] || ''}${payload.content || ''}`
  const content = agentRawBuffers[name]
  const extracted = extractQuestionsFromRaw(content)
  if (extracted.length) {
    agentQuestionDrafts[name] = extracted
    rebuildLiveQuestionsFromAgents()
  }
  agentOutputs.value.splice(index, 1, {
    ...agentOutputs.value[index],
    preview: content.slice(-1600),
  })
}

async function loadHistory() {
  try {
    const history = await getQuestionGeneratorHistory()
    questionSheets.value = history.question_sheets || []
    examResults.value = history.exam_results || []
    if (history.active_task) {
      applyGenerationStatus(history.active_task)
    }
  } catch (e) {
    console.warn('加载题库历史失败:', e)
    questionSheets.value = []
    examResults.value = []
  }
}

function stopXiaoZhiQuestionTaskPolling() {
  if (xiaozhiQuestionTaskTimer) {
    window.clearInterval(xiaozhiQuestionTaskTimer)
    xiaozhiQuestionTaskTimer = null
  }
}

function startXiaoZhiQuestionTaskPolling(taskId) {
  stopXiaoZhiQuestionTaskPolling()
  if (!taskId) return
  xiaozhiQuestionTaskTimer = window.setInterval(() => {
    loadXiaoZhiQuestionTask(taskId)
  }, 2500)
}

async function syncXiaoZhiQuestionTask(taskId) {
  if (!taskId) {
    loadingXiaoZhiQuestionTask.value = false
    stopXiaoZhiQuestionTaskPolling()
    return
  }
  loadingXiaoZhiQuestionTask.value = true
  await loadXiaoZhiQuestionTask(taskId)
}

async function loadXiaoZhiQuestionTask(taskId) {
  if (!taskId) return
  try {
    const response = await getXiaoZhiTask(taskId)
    const task = response?.data?.task
    if (!task) {
      loadingXiaoZhiQuestionTask.value = false
      errorMsg.value = '未找到对应的题库任务，请返回学习路径后重试。'
      return
    }
    await applyXiaoZhiQuestionTask(task)
    if (['queued', 'running'].includes(task.status)) {
      startXiaoZhiQuestionTaskPolling(taskId)
    } else {
      stopXiaoZhiQuestionTaskPolling()
    }
  } catch (error) {
    loadingXiaoZhiQuestionTask.value = false
    generating.value = false
    errorMsg.value = error?.response?.data?.msg || error?.message || '读取题库任务失败，请稍后重试。'
    stopXiaoZhiQuestionTaskPolling()
  }
}

async function applyXiaoZhiQuestionTask(task) {
  if (['queued', 'running'].includes(task.status)) {
    loadingXiaoZhiQuestionTask.value = true
    activeModule.value = 'generate'
    activeTab.value = 'generate'
    generating.value = true
    streamMessage.value = task.status === 'queued' ? '嵌小智题库任务已排队...' : '嵌小智正在生成题库...'
    return
  }

  loadingXiaoZhiQuestionTask.value = false
  generating.value = false
  if (task.status === 'failed') {
    activeModule.value = 'generate'
    activeTab.value = 'generate'
    errorMsg.value = task.error || '题库任务生成失败'
    return
  }

  const result = task.result || {}
  const sheet = result.sheet || result.questionGenerator?.question_sheet || null
  const bank = result.questionGenerator?.question_bank || sheet?.question_bank || null
  if (!sheet && !bank) {
    activeModule.value = 'generate'
    activeTab.value = 'generate'
    errorMsg.value = '题库任务已结束，但没有返回有效题目，请返回学习路径后重新生成。'
    return
  }

  if (bank?.questions?.length) {
    resultBank.value = bank
    resultBank.value.questions.forEach((q, i) => { q._idx = i; q._id = q.id || `Q${i + 1}` })
  }

  await loadHistory()
  const savedSheet = sheet?.id
    ? questionSheets.value.find(item => String(item.id) === String(sheet.id))
    : questionSheets.value.find(item => item.title === sheet?.title)
  const resolvedSheet = {
    ...(savedSheet || sheet || {
      title: bank?.title || task.title,
      course_name: bank?.course_name || '',
      target_topic: bank?.target_topic || result.topic || '',
      question_count: bank?.questions?.length || 0,
    }),
  }
  if (!resolvedSheet.question_bank && bank) resolvedSheet.question_bank = bank
  currentSheet.value = resolvedSheet
  startExamFromSheet(resolvedSheet)
  viewSheet(resolvedSheet)
  markLearningNodeQuestionComplete(resolvedSheet, bank)
  historyFilter.value = 'sheet'
  activeTab.value = 'history'
  activeModule.value = 'history'
}

function persistGenerationTask(task) {
  activeGenerationTask.value = task || null
  if (task?.status === 'running') {
    localStorage.setItem(GENERATION_TASK_STORAGE_KEY, JSON.stringify({
      taskId: task.taskId,
      status: task.status,
      meta: task.meta || task.payload?.meta || {},
      payload: task.payload || {},
      updated_at: task.updated_at || new Date().toLocaleString(),
    }))
  } else {
    localStorage.removeItem(GENERATION_TASK_STORAGE_KEY)
  }
}

function restoreGenerationTask() {
  try {
    const raw = localStorage.getItem(GENERATION_TASK_STORAGE_KEY)
    if (!raw) return
    const task = JSON.parse(raw)
    if (task?.status === 'running') {
      activeGenerationTask.value = task
      generating.value = true
      streamMessage.value = task.payload?.message || '后台仍在生成题单...'
      startGenerationStatusPolling()
    }
  } catch {
    localStorage.removeItem(GENERATION_TASK_STORAGE_KEY)
  }
}

function generationTaskProgress(task) {
  const payload = task?.payload || {}
  const stage = String(payload.stage || '')
  if (stage === 'start') return 8
  if (stage === 'extracting') return 14
  if (stage === 'extract_file_start' || stage === 'extract_cache_hit') {
    const total = Math.max(1, Number(payload.total || 1))
    const index = Math.max(1, Number(payload.index || 1))
    return Math.min(34, 14 + Math.round(((index - 1) / total) * 18))
  }
  if (stage === 'extract_file_done') {
    const total = Math.max(1, Number(payload.total || 1))
    const index = Math.max(1, Number(payload.index || 1))
    return Math.min(38, 18 + Math.round((index / total) * 20))
  }
  if (stage === 'agent_input') return 42
  if (stage === 'model_stream_start' || stage === 'type_batch_start') return 50
  if (stage === 'agent_start') return 58
  if (stage === 'model_delta') return 68
  if (stage === 'agent_output') return 82
  if (stage === 'complete') return 100
  return generating.value ? 64 : 12
}

function formatGenerationTaskTime(value) {
  if (!value) return '刚刚'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function stopGenerationStatusPolling() {
  if (generationStatusTimer) {
    clearInterval(generationStatusTimer)
    generationStatusTimer = null
  }
}

function startGenerationStatusPolling() {
  if (!generationStatusTimer) {
    generationStatusTimer = setInterval(syncGenerationStatus, 1500)
  }
}

async function syncGenerationStatus() {
  try {
    const status = await getQuestionGeneratorStatus()
    applyGenerationStatus(status)
  } catch (e) {
    console.warn('同步题库生成状态失败:', e)
  }
}

function applyGenerationStatus(status) {
  if (!status || status.status === 'idle') {
    persistGenerationTask(null)
    return
  }
  const payload = status.payload || {}

  if (status.status === 'running') {
    generating.value = true
    errorMsg.value = ''
    persistGenerationTask(status)
    streamMessage.value = payload.message || streamMessage.value || '后端仍在生成题单...'
    if (payload.agent) upsertAgentOutput(payload)
    updateExtractProgress(payload)
    if (status.event === 'delta' && payload.content) {
      streamRawOutput.value = payload.content
      if (payload.agent || payload.question_type) upsertAgentOutput(payload)
    } else if (status.event && status.event !== 'delta') {
      streamJsonOutput.value = JSON.stringify(payload, null, 2)
    }
    startGenerationStatusPolling()
    return
  }

  stopGenerationStatusPolling()
  generating.value = false

  if (status.status === 'complete' && status.result) {
    persistGenerationTask(null)
    const result = status.result
    resultBank.value = result.question_bank
    if (resultBank.value?.questions) {
      resultBank.value.questions.forEach((q, i) => { q._idx = i; q._id = q.id || `Q${i + 1}` })
    }
    selectedMaterialIndex.value = -1
    currentSheet.value = result.question_sheet
    streamMessage.value = payload.message || '题单已生成完成'
    streamJsonOutput.value = JSON.stringify(result, null, 2)
    markLearningNodeQuestionComplete(result.question_sheet, result.question_bank)
    loadHistory()
    return
  }

  if (status.status === 'error') {
    activeGenerationTask.value = status
    localStorage.removeItem(GENERATION_TASK_STORAGE_KEY)
    errorMsg.value = status.error?.error || payload.response?.error || '题库生成失败，请稍后重试'
    const cacheKey = learningQuestionCacheKey()
    if (cacheKey) {
      markNodeCacheError(cacheKey, {
        resourceType: 'question-bank',
        title: [courseName.value, chapterName.value].filter(Boolean).join(' ') || 'STM32 题库练习小测',
        error: errorMsg.value,
      })
    }
  }
}

function quickPracticeFromProfile() {
  if (!selectedWeakPoints.value.length) return
  // Auto-enable single choice and fill-in-blank for quick practice
  questionTypes.forEach(qt => {
    if (qt.type === '单选题' || qt.type === '填空题') {
      qt.enabled = true
      qt.count = Math.max(qt.count, 2)
    } else {
      qt.enabled = false
    }
  })
  autoDistribute.value = false
  // If no learning material provided, synthesize context from weak points so backend doesn't reject
  if (!pastedText.value.trim() && !uploadedFiles.value.length && selectedWeakPoints.value.length) {
    const wpText = selectedWeakPoints.value.join('、')
    pastedText.value = '快速练习模式：请针对以下嵌入式薄弱知识点生成练习题。知识点包括：' + wpText + '。每道题需包含知识点标签和解析，贴近实际嵌入式开发场景。'
  }
  generate()
}

async function generate() {
  stopGenerationStatusPolling()
  errorMsg.value = ''
  resultBank.value = null
  streamMessage.value = '正在生成中，已发送给智能体处理。'
  streamBatchType.value = ''
  streamJsonOutput.value = ''
  streamRawOutput.value = ''
  liveQuestions.value = []
  agentOutputs.value = []
  Object.keys(agentRawBuffers).forEach(key => delete agentRawBuffers[key])
  Object.keys(agentQuestionDrafts).forEach(key => delete agentQuestionDrafts[key])
  Object.keys(extractProgress).forEach(key => delete extractProgress[key])
  generating.value = true
  let backgroundStarted = false

  try {
    const selectedQuestionTypes = questionTypes.filter(qt => qt.enabled && (autoDistribute.value || qt.count > 0))
    const preferredTypes = selectedQuestionTypes.map(qt => qt.type)
    const questionTypeCounts = autoDistribute.value
      ? {}
      : Object.fromEntries(selectedQuestionTypes.map(qt => [qt.type, Number(qt.count)]))
    const questionTypeScores = Object.fromEntries(selectedQuestionTypes.map(qt => [qt.type, Number(qt.score || 0)]))
    const difficultyPayload = Object.fromEntries(difficultyRatios.map(item => [item.key, Number(item.value || 0)]))
    const generationPayload = {
      analysis: Boolean(generationOptions.analysis),
      tags: Boolean(generationOptions.tags),
      variants: Boolean(generationOptions.variants),
    }
    const agentInput = {
      files: uploadedFiles.value.map(item => ({
        name: item.file.name,
        size: item.file.size,
        type: item.file.type || 'unknown',
      })),
      pastedTextLength: pastedText.value.trim().length,
      courseName: courseName.value,
      chapterName: chapterName.value,
      studentProfile: studentProfile.value,
      constraints: constraints.value,
      preferredTypes,
      questionTypeCounts,
      questionTypeScores,
      questionCount: totalCount.value,
      totalScore: previewTotalScore.value,
      autoDistribute: autoDistribute.value,
      difficultyRatios: difficultyPayload,
      difficultyLocks: { ...difficultyLocks },
      generationOptions: generationPayload,
    }
    streamJsonOutput.value = JSON.stringify({ stage: 'agent_input', agentInput }, null, 2)
    const formData = new FormData()

    uploadedFiles.value.forEach(item => formData.append('files', item.file))
    formData.append('pasted_text', pastedText.value)
    formData.append('course_name', courseName.value)
    formData.append('chapter_name', chapterName.value)
    formData.append('student_profile', studentProfile.value)
    formData.append('constraints', constraints.value)
    formData.append('preferred_question_types', JSON.stringify(preferredTypes))
    formData.append('question_type_counts', JSON.stringify(questionTypeCounts))
    formData.append('question_type_scores', JSON.stringify(questionTypeScores))
    formData.append('total_score', String(previewTotalScore.value))
    formData.append('question_count', String(totalCount.value))
    formData.append('auto_distribute', autoDistribute.value ? '1' : '0')
    formData.append('difficulty_ratios', JSON.stringify(difficultyPayload))
    formData.append('difficulty_locks', JSON.stringify({ ...difficultyLocks }))
    formData.append('generation_options', JSON.stringify(generationPayload))
    formData.append('force_real_agent', '1')

    addLog({ stage: 'request', agentInput }, 'info', '题库生成')
    const status = await startQuestionGeneration(formData)
    backgroundStarted = true
    applyGenerationStatus(status)
    const startedTaskId = String(status.taskId || status.payload?.taskId || '').trim()
    if (startedTaskId) {
      await router.replace({
        query: {
          ...route.query,
          autostart: undefined,
          xzTask: startedTaskId,
        },
      })
    }
    const cacheKey = learningQuestionCacheKey()
    if (cacheKey) {
      markNodeCacheStarted(cacheKey, {
        resourceType: 'question-bank',
        title: [courseName.value, chapterName.value].filter(Boolean).join(' ') || 'STM32 题库练习小测',
        taskId: status.taskId || status.payload?.taskId || '',
        route: route.fullPath,
      })
    }
    streamMessage.value = status.payload?.message || '后台生成任务已启动，可以切换页面或稍后回来查看进度。'
    await loadHistory()
    setSection('question-generator', {
      title: '题库生成智能体',
      items: [
        { label: '任务状态', value: '后台生成中' },
        { label: '任务编号', value: String(status.taskId || status.payload?.taskId || '-') },
        { label: '生成题量', value: String(totalCount.value || 0) + ' 题' },
      ],
    })
    addLog({ stage: 'background-started', status }, 'success', '题库生成')
  } catch (err) {
    errorMsg.value = err.response?.data?.error || err.message || '生成失败，请稍后重试'
    const cacheKey = learningQuestionCacheKey()
    if (cacheKey) {
      markNodeCacheError(cacheKey, {
        resourceType: 'question-bank',
        title: [courseName.value, chapterName.value].filter(Boolean).join(' ') || 'STM32 题库练习小测',
        error: errorMsg.value,
      })
    }
    addLog({ stage: 'error', message: err.message, response: err.response?.data }, 'error', '题库生成')
  } finally {
    if (!backgroundStarted) generating.value = false
  }
}

function startExamFromResult() {
  if (!resultBank.value?.questions?.length) return
  const sheet = {
    id: currentSheet.value?.id || ('gen-' + Date.now()),
    title: resultBank.value.title || '题库练习',
    course_name: resultBank.value.course_name || '',
    target_topic: resultBank.value.target_topic || '',
    question_count: resultBank.value.questions.length,
    created_at: currentSheet.value?.created_at || new Date().toLocaleString(),
    question_bank: resultBank.value
  }
  startExamFromSheet(sheet)
}

function startExamFromSheet(sheet) {
  if (!sheet) return
  stopExamTimer()
  selectedSheet.value = sheet
  examAnswers.value = selectedQuestions.value.map(q => (isMultiQuestion(q) ? [] : ''))
  examStarted.value = false
  examSubmitted.value = false
  examElapsedSeconds.value = 0
  examStartAt.value = 0
  examResult.value = { score: 0, total_score: sheetTotalScore(sheet), correct_count: 0, question_count: selectedQuestions.value.length, detail: [] }
  weakKnowledgePoints.value = []
  aiScoreMessage.value = ''
  aiScoring.value = false
  answerCardPos.x = -1
  answerCardPos.y = -1
  cardMinimized.value = false
  activeTab.value = 'exam'
  activeModule.value = 'exam'
}

function startExamTimer() {
  if (!selectedQuestions.value.length) return false
  examStarted.value = true
  examSubmitted.value = false
  examStartAt.value = Date.now()
  examElapsedSeconds.value = 0
  currentExamQuestion.value = 0
  if (timerMode.value === 'countdown') {
    countdownTarget.value = Math.max(300, (selectedQuestions.value.length * 2 + 5) * 60)
  }
  stopExamTimer()
  examTimer = window.setInterval(() => {
    examElapsedSeconds.value = Math.floor((Date.now() - examStartAt.value) / 1000)
    if (timerMode.value === 'countdown' && examElapsedSeconds.value >= countdownTarget.value) {
      submitExam()
    }
  }, 1000)
  nextTick(setupExamScrollObserver)
  return true
}

function toggleTimerMode() {
  timerMode.value = timerMode.value === 'countup' ? 'countdown' : 'countup'
  if (timerMode.value === 'countdown' && examStarted.value) {
    countdownTarget.value = Math.max(300, (selectedQuestions.value.length * 2 + 5) * 60)
  }
}

function stopExamTimer() {
  if (examTimer) {
    window.clearInterval(examTimer)
    examTimer = 0
  }
}

function setupExamScrollObserver() {
  if (examScrollObserver) { examScrollObserver.disconnect(); examScrollObserver = null }
  const targets = selectedQuestions.value.map((_, idx) => document.getElementById('exam-q-' + idx)).filter(Boolean)
  if (!targets.length) return
  examScrollObserver = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        const idx = parseInt(entry.target.id.replace('exam-q-', ''), 10)
        if (!isNaN(idx)) currentExamQuestion.value = idx
      }
    }
  }, { rootMargin: '-20% 0px -60% 0px', threshold: 0 })
  targets.forEach(el => examScrollObserver.observe(el))
}

async function handleExamAction() {
  if (!examStarted.value) {
    if (!canLaunchSelectedExam.value) return
    openExamSessionInNewTab()
    return
  }
  await submitExam()
}

function openExamSessionInNewTab() {
  if (!canLaunchSelectedExam.value) return

  // 淇濆瓨鑰冭瘯鏁版嵁鍒?sessionStorage
  const examData = {
    sheet: selectedSheet.value,
    questions: selectedQuestions.value,
    total_score: sheetTotalScore(selectedSheet.value),
  }
  sessionStorage.setItem('qgExamSessionData', JSON.stringify(examData))

  // 鍦ㄦ柊鏍囩椤垫墦寮€鑰冭瘯鐣岄潰
  const examUrl = window.location.origin + '/question-generator/exam-session'
  window.open(examUrl, '_blank')
}

function openExamSession() {
  if (!canLaunchSelectedExam.value || !startExamTimer()) return
  examAnswers.value = selectedQuestions.value.map(q => (isMultiQuestion(q) ? [] : ''))
  examResult.value = { score: 0, total_score: sheetTotalScore(selectedSheet.value), correct_count: 0, question_count: selectedQuestions.value.length, detail: [] }
}

function isMultiQuestion(q) {
  return String(q.type || '').includes('多选')
}

function hasChoiceOptions(q) {
  const type = String(q?.type || '')
  const isChoiceType = type.includes('单选') || type.includes('多选') || type.includes('判断') || /single|multi|choice|judge|true|false/i.test(type)
  return isChoiceType && Array.isArray(q?.options) && q.options.length > 0
}

function weakPointLabel(kp) {
  return typeof kp === 'string' ? kp : (kp?.name || kp?.knowledge_point || '未知')
}

function optionKey(option) {
  return String(option).trim().match(/^[A-Z]/i)?.[0]?.toUpperCase() || String(option).trim()
}

function updateChoiceAnswer(index, option, question, event) {
  const key = optionKey(option)
  if (isMultiQuestion(question)) {
    const next = Array.isArray(examAnswers.value[index]) ? [...examAnswers.value[index]] : []
    if (event.target.checked && !next.includes(key)) next.push(key)
    if (!event.target.checked) next.splice(next.indexOf(key), 1)
    examAnswers.value[index] = next.sort()
    return
  }
  examAnswers.value[index] = key
}

function isChecked(index, option, question) {
  const key = optionKey(option)
  const answer = examAnswers.value[index]
  return isMultiQuestion(question) ? Array.isArray(answer) && answer.includes(key) : answer === key
}

function hasExamAnswer(index) {
  const answer = examAnswers.value[index]
  return Array.isArray(answer) ? answer.length > 0 : Boolean(String(answer || '').trim())
}

function scrollToExamQuestion(index) {
  document.getElementById('exam-q-' + index)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function resetExam() {
  examStarted.value = false
  examSubmitted.value = false
  currentExamQuestion.value = 0
  aiScoreMessage.value = ''
  aiScoring.value = false
  examResult.value = { score: 0, total_score: sheetTotalScore(selectedSheet.value), correct_count: 0, question_count: selectedQuestions.value.length, detail: [] }
  examAnswers.value = selectedQuestions.value.map(q => (isMultiQuestion(q) ? [] : ''))
}

function normalizeAnswer(value) {
  if (Array.isArray(value)) return value.map(item => String(item).trim().toUpperCase()).sort().join('')
  return String(value || '').replace(/\s+/g, '').replace(/[，。；、？！,.!?]/g, '').toUpperCase()
}

function isCorrect(question, userAnswer) {
  const type = String(question.type || '')
  const standard = normalizeAnswer(question.answer)
  const user = normalizeAnswer(userAnswer)
  if (!user) return false
  if (type.includes('简答') || type.includes('计算') || type.includes('代码') || type.includes('操作')) {
    return user.length >= 4 && (standard.includes(user) || user.includes(standard.slice(0, Math.min(standard.length, 12))))
  }
  return user === standard || standard.startsWith(user) || user.startsWith(standard)
}

async function submitExam() {
  if (!selectedQuestions.value.length) return
  aiScoreMessage.value = ''
  aiScoring.value = false
  const questions = selectedQuestions.value
  const detail = questions.map((question, index) => {
    const userAnswer = examAnswers.value[index]
    const correct = isCorrect(question, userAnswer)
    const questionScore = scoreForQuestion(question)
    return {
      question,
      user_answer: userAnswer,
      correct,
      score: correct ? questionScore : 0,
      full_score: questionScore,
      answer: question.answer,
      analysis: question.analysis,
      type: question.type,
      stem: question.stem,
    }
  })
  const correctCount = detail.filter(item => item.correct).length
  const score = Number(detail.reduce((sum, item) => sum + Number(item.score || 0), 0).toFixed(1))
  const totalExamScore = Number(detail.reduce((sum, item) => sum + Number(item.full_score || 0), 0).toFixed(1))
  stopExamTimer()
  if (examStartAt.value) {
    examElapsedSeconds.value = Math.floor((Date.now() - examStartAt.value) / 1000)
  }
  examResult.value = {
    sheet_id: selectedSheet.value.id,
    title: selectedSheet.value.title,
    score,
    total_score: totalExamScore,
    correct_count: correctCount,
    question_count: questions.length,
    duration_seconds: examElapsedSeconds.value,
    answers: examAnswers.value,
    detail,
  }
  examStarted.value = false
  examSubmitted.value = true
  if (examScrollObserver) { examScrollObserver.disconnect(); examScrollObserver = null }
  document.body.classList.remove('exam-scroll-override')
  stopExamTimer()
  await saveQuestionGeneratorExamResult(examResult.value)
  await loadHistory()

  // Build per-knowledge-point stats for weak point analysis
  const kpStats = new Map()
  detail.forEach((item) => {
    const kp = item.question?.knowledge_point || item.type || '未知'
    if (!kpStats.has(kp)) {
      kpStats.set(kp, { name: kp, total: 0, wrong: 0 })
    }
    const stat = kpStats.get(kp)
    stat.total++
    if (!item.correct) stat.wrong++
  })
  const allKpResults = []
  kpStats.forEach((stat) => {
    const accuracy = stat.total > 0 ? (stat.total - stat.wrong) / stat.total : 0
    allKpResults.push({ name: stat.name, total: stat.total, wrong: stat.wrong, accuracy })
  })
  allKpResults.sort((a, b) => a.accuracy - b.accuracy)
  const weakPoints = allKpResults.filter(kp => kp.wrong > 0)
  weakKnowledgePoints.value = weakPoints

  // Merge with existing history for cumulative tracking
  let quizHistory = []
  try { quizHistory = JSON.parse(localStorage.getItem('quizHistory') || '[]') } catch {}
  const examRecord = {
    score,
    total: totalExamScore,
    correct_count: correctCount,
    question_count: questions.length,
    weakTopics: weakPoints.map(t => t.name),
    knowledgePoints: allKpResults,
    wrongQuestions: detail.filter(d => !d.correct).map(d => ({
      stem: d.question?.stem || '',
      type: d.type,
      correct_answer: d.question?.answer || '',
      user_answer: d.user_answer || '',
      knowledge_point: d.question?.knowledge_point || d.type || '未知',
    })),
    title: selectedSheet.value?.title || '题库练习',
    sheet_id: selectedSheet.value?.id,
    course_name: selectedSheet.value?.course_name || courseName.value || '',
    stage: selectedSheet.value?.stage || selectedSheet.value?.stageId || '',
    duration_seconds: examElapsedSeconds.value,
    timestamp: new Date().toISOString(),
  }
  quizHistory.push(examRecord)
  if (quizHistory.length > 20) quizHistory = quizHistory.slice(-20)
  localStorage.setItem('quizHistory', JSON.stringify(quizHistory))

  // Compute cumulative weak points across all exams for display
  buildCumulativeWeakPoints(quizHistory)
}

async function requestAiRescore() {
  if (!examResult.value?.detail?.length || aiScoring.value) return
  aiScoring.value = true
  aiScoreMessage.value = ''
  try {
    const result = await requestQuestionGeneratorAiScore({
      sheet_id: examResult.value.sheet_id,
      title: examResult.value.title,
      score: examResult.value.score,
      total_score: examResult.value.total_score,
      detail: examResult.value.detail,
    })
    examResult.value = {
      ...examResult.value,
      score: result.score,
      total_score: result.total_score || examResult.value.total_score,
      correct_count: result.correct_count,
      question_count: result.question_count || examResult.value.question_count,
      detail: result.detail || examResult.value.detail,
      aiSummary: result.aiSummary,
      aiScoreSource: result.source,
    }
    aiScoreMessage.value = result.aiSummary || 'AI 评分已完成，当前分数已更新。'
    const weakPoints = (examResult.value.detail || [])
      .filter(item => !item.correct)
      .map(item => item.question?.knowledge_point || item.type || '未知')
      .filter(Boolean)
    weakKnowledgePoints.value = [...new Set(weakPoints)]
    await saveQuestionGeneratorExamResult(examResult.value)
    await loadHistory()
  } catch (error) {
    aiScoreMessage.value = error.response?.data?.msg || error.response?.data?.message || error.message || 'AI 评分失败，请稍后再试。'
  } finally {
    aiScoring.value = false
  }
}

function buildCumulativeWeakPoints(history) {
  const kpMap = new Map()
  for (const exam of history) {
    if (!Array.isArray(exam.knowledgePoints)) continue
    for (const kp of exam.knowledgePoints) {
      if (!kpMap.has(kp.name)) {
        kpMap.set(kp.name, { name: kp.name, total: 0, wrong: 0 })
      }
      const stat = kpMap.get(kp.name)
      stat.total += kp.total || 0
      stat.wrong += kp.wrong || 0
    }
  }
  const result = []
  kpMap.forEach((stat) => {
    if (stat.wrong > 0) {
      result.push({
        name: stat.name,
        total: stat.total,
        wrong: stat.wrong,
        accuracy: stat.total > 0 ? (stat.total - stat.wrong) / stat.total : 0,
      })
    }
  })
  result.sort((a, b) => a.accuracy - b.accuracy)
  cumulativeWeakPoints.value = result.slice(0, 8)
}

function scoreForQuestion(question) {
  const explicitScore = Number(question.score ?? question.points)
  if (Number.isFinite(explicitScore) && explicitScore > 0) return Number(explicitScore.toFixed(1))
  const config = questionTypes.find(qt => String(question.type || '').includes(qt.type) || qt.type.includes(String(question.type || '')))
  return Number((config?.score || 0).toFixed(1))
}

function sheetTotalScore(sheet) {
  const questions = resolveExamQuestions({ sheet })
  return Number(questions.reduce((sum, question) => sum + scoreForQuestion(question), 0).toFixed(1))
}

function bankTotalScore(questions) {
  return Number((questions || []).reduce((sum, question) => sum + scoreForQuestion(question), 0).toFixed(1))
}

function questionDistributionText(questions) {
  const counts = new Map()
  ;(questions || []).forEach((question) => {
    const type = String(question.type || '未分类')
    counts.set(type, (counts.get(type) || 0) + 1)
  })
  return Array.from(counts.entries()).map(([type, count]) => type + ' ' + count + '题').join('；') || '暂无题目'
}

function scoreDistributionText(questions) {
  const groups = new Map()
  ;(questions || []).forEach((question) => {
    const type = String(question.type || '未分类')
    const score = scoreForQuestion(question)
    const current = groups.get(type) || { count: 0, score, total: 0 }
    current.count += 1
    current.score = score
    current.total = Number((current.total + score).toFixed(1))
    groups.set(type, current)
  })
  return Array.from(groups.entries())
    .map(([type, item]) => type + ' ' + item.score + '分/题 x ' + item.count + ' = ' + item.total + '分')
    .join('；') || '暂无分值'
}

function cleanSummary(summary) {
  return String(summary || '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 220)
}

function hasAnswer(index) {
  const answer = examAnswers.value[index]
  return Array.isArray(answer) ? answer.length > 0 : Boolean(String(answer || '').trim())
}

function questionAnchor(index) {
  return 'qg-question-' + index
}

function scrollToQuestion(index) {
  document.getElementById(questionAnchor(index))?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function displayAnswer(answer) {
  return Array.isArray(answer) ? answer.join('、') : String(answer || '')
}

function viewSheet(sheet) {
  historyDetail.value = sheet
}

function viewExamResult(result) {
  historyDetail.value = result
}

function scoreLevel(result) {
  if (!result.total_score) return ''
  const pct = result.score / result.total_score
  if (pct >= 0.85) return 'level-great'
  if (pct >= 0.6) return 'level-good'
  return 'level-low'
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function quizSelectOption(qIdx, opt) {
  if (quizSubmitted.value[qIdx]) return
  const key = optionKey(opt)
  const q = resultBank.value.questions[qIdx]
  if (!quizAnswers.value[qIdx]) quizAnswers.value[qIdx] = isMultiQuestion(q) ? [] : ''
  if (isMultiQuestion(q)) {
    const arr = Array.isArray(quizAnswers.value[qIdx]) ? [...quizAnswers.value[qIdx]] : []
    const i = arr.indexOf(key)
    if (i >= 0) arr.splice(i, 1)
    else arr.push(key)
    quizAnswers.value[qIdx] = arr.sort()
  } else {
    quizAnswers.value[qIdx] = key
  }
}

function quizSubmitOne(qIdx) {
  const q = resultBank.value.questions[qIdx]
  const answer = quizAnswers.value[qIdx]
  if (!answer || (Array.isArray(answer) && answer.length === 0)) return
  quizSubmitted.value[qIdx] = true
}

function quizCheckCorrect(qIdx) {
  if (!resultBank.value || !quizSubmitted.value[qIdx]) return false
  const q = resultBank.value.questions[qIdx]
  return isCorrect(q, quizAnswers.value[qIdx])
}

function buildPrintQuestionHtml(item, index, isExam) {
  const question = item.question || item
  const options = Array.isArray(question.options) && question.options.length
    ? '<div class="options">' + question.options.map(option => '<p>' + escapeHtml(option) + '</p>').join('') + '</div>'
    : ''
  const resultBadge = isExam
    ? '<span class="badge ' + (item.correct ? 'ok' : 'wrong') + '">' + (item.correct ? '正确' : '错误') + '</span>'
    : ''
  const userAnswer = isExam
    ? '<p><strong>作答：</strong>' + escapeHtml(displayAnswer(item.user_answer) || '未作答') + '</p>'
    : ''
  const score = isExam && item.full_score !== undefined
    ? '<span class="score">' + escapeHtml(item.score || 0) + ' / ' + escapeHtml(item.full_score) + ' 分</span>'
    : '<span class="score">' + escapeHtml(scoreForQuestion(question)) + ' 分</span>'

  return '<article class="question">' +
    '<div class="question-head"><div><strong>Q' + (index + 1) + '</strong>' +
    '<span>' + escapeHtml(item.type || question.type || '题目') + '</span>' + resultBadge + '</div>' + score + '</div>' +
    '<p class="stem">' + escapeHtml(item.stem || question.stem || '') + '</p>' +
    options + userAnswer +
    '<p><strong>答案：</strong>' + escapeHtml(item.answer || question.answer || '') + '</p>' +
    '<p><strong>解析：</strong>' + escapeHtml(item.analysis || question.analysis || '') + '</p>' +
    '</article>'
}

function buildHistoryPrintHtml() {
  const detail = historyDetail.value
  const questions = historyDetailQuestions.value
  const isExam = detail?.score !== undefined
  const title = isExam ? '考试情况' : '当前题单'
  const subtitle = isExam
    ? '得分 ' + detail.score + ' / ' + detail.total_score + ' 分 · 答对 ' + (detail.correct_count || 0) + ' / ' + (detail.question_count || questions.length) + ' 题'
    : (detail.course_name || '') + ' ' + (detail.target_topic || '') + ' · 共 ' + questions.length + ' 题 · 总分 ' + bankTotalScore(questions) + ' 分'
  const meta = [
    detail.title,
    detail.created_at ? '生成/考试时间：' + detail.created_at : '',
    isExam ? '' : questionDistributionText(questions),
  ].filter(Boolean).map(text => '<p>' + escapeHtml(text) + '</p>').join('')
  const body = questions.map((item, index) => buildPrintQuestionHtml(item, index, isExam)).join('')
  const style = '<style>body{font-family:Microsoft YaHei,Arial,sans-serif;color:#263f3d;padding:24px;line-height:1.65}.question{border:1px solid #bfe7e4;padding:12px;margin:0 0 12px}.question-head{display:flex;justify-content:space-between;color:#15966f}.badge{padding:1px 8px;border-radius:999px;background:#e8fff4}.wrong{background:var(--surface, rgba(255, 255, 255, 0.94))1ee}.score{font-weight:700}.summary{font-weight:700}.meta p{margin:2px 0;color:#617976}</style>'
  return '<!doctype html><html><head><meta charset="utf-8"><title>' + escapeHtml(title) + '</title>' + style + '</head><body><header><h1>' + escapeHtml(title) + '</h1><p class="summary">' + escapeHtml(subtitle) + '</p><div class="meta">' + meta + '</div></header><main>' + body + '</main></body></html>'
}

function printHistory() {
  if (!historyDetail.value) return
  const frame = document.createElement('iframe')
  frame.style.position = 'fixed'
  frame.style.right = '0'
  frame.style.bottom = '0'
  frame.style.width = '0'
  frame.style.height = '0'
  frame.style.border = '0'
  document.body.appendChild(frame)

  const printWindow = frame.contentWindow
  const printDocument = frame.contentDocument || printWindow?.document
  if (!printWindow || !printDocument) {
    frame.remove()
    return
  }

  printDocument.open()
  printDocument.write(buildHistoryPrintHtml())
  printDocument.close()
  printWindow.focus()
  printWindow.print()
  window.setTimeout(() => frame.remove(), 1000)
}

function updateExtractProgress(data) {
  if (!data?.stage || !String(data.stage).startsWith('extract_') || !data.file) return
  const key = data.index + '-' + data.file
  const statusMap = {
    extract_file_start: 'running',
    extract_cache_hit: 'cached',
    extract_file_done: data.cached ? 'cached' : 'done',
    extract_file_error: 'error',
  }
  extractProgress[key] = {
    ...extractProgress[key],
    file: data.file,
    fileType: data.fileType || '文件',
    index: data.index,
    total: data.total,
    message: data.message || '',
    status: statusMap[data.stage] || 'running',
  }
}

function toggleFavoriteQuestion(qid) {
  const newSet = new Set(favoritedQuestions.value)
  if (newSet.has(qid)) {
    newSet.delete(qid)
  } else {
    newSet.add(qid)
  }
  favoritedQuestions.value = newSet
}

function toggleSelectQuestion(qid) {
  const newSet = new Set(selectedQuestionIds.value)
  if (newSet.has(qid)) {
    newSet.delete(qid)
  } else {
    newSet.add(qid)
  }
  selectedQuestionIds.value = newSet
}

const isAllSelected = computed(() => {
  const dq = displayQuestions.value
  if (!dq.length) return false
  return dq.every(q => selectedQuestionIds.value.has(q._id || q.id))
})

const isPartialSelected = computed(() => {
  const dq = displayQuestions.value
  if (!dq.length) return false
  const selectedCount = dq.filter(q => selectedQuestionIds.value.has(q._id || q.id)).length
  return selectedCount > 0 && selectedCount < dq.length
})

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedQuestionIds.value = new Set()
  } else {
    const newSet = new Set(displayQuestions.value.map(q => q._id || q.id))
    selectedQuestionIds.value = newSet
  }
}

function batchDeleteSelected() {
  const count = selectedQuestionIds.value.size
  if (!count) return
  const confirmed = window.confirm('确定要删除选中的 ' + count + ' 道题目吗？此操作不可撤销。')
  if (!confirmed) return
  if (!resultBank.value?.questions) return
  resultBank.value.questions = resultBank.value.questions.filter(q => {
    const qid = q._id || q.id
    return !selectedQuestionIds.value.has(qid)
  })
  selectedQuestionIds.value = new Set()
}

function toggleExpandQuestion(qid) {
  const newSet = new Set(expandedQuestionIds.value)
  if (newSet.has(qid)) {
    newSet.delete(qid)
  } else {
    // Accordion: collapse all others, expand only this one
    newSet.clear()
    newSet.add(qid)
  }
  expandedQuestionIds.value = newSet
}

function expandAllQuestions() {
  const newSet = new Set()
  displayQuestions.value.forEach((q, idx) => {
    newSet.add(q.id || ('Q' + (idx + 1)))
  })
  expandedQuestionIds.value = newSet
}

function collapseAllQuestions() {
  expandedQuestionIds.value = new Set()
}

function toggleRevealAnswer(qid) {
  const newSet = new Set(revealedAnswerIds.value)
  if (newSet.has(qid)) {
    newSet.delete(qid)
  } else {
    newSet.add(qid)
  }
  revealedAnswerIds.value = newSet
}

function getSelectedQuestions() {
  if (!resultBank.value?.questions) return []
  return resultBank.value.questions.filter(q => {
    const qid = q._id || q.id
    return selectedQuestionIds.value.has(qid)
  })
}

function buildQuestionText(questions, bank, title) {
  const lines = []
  lines.push('='.repeat(60))
  lines.push(title + '：' + (bank?.title || '未命名'))
  if (bank?.course_name) lines.push('课程：' + bank.course_name)
  if (bank?.target_topic) lines.push('主题：' + bank.target_topic)
  lines.push('题目数量：' + questions.length + ' 题')
  lines.push('='.repeat(60))
  lines.push('')
  questions.forEach((q, idx) => {
    lines.push('【第 ' + (idx + 1) + ' 题】')
    lines.push('题型：' + (q.type || '未知'))
    lines.push('难度：' + (q.difficulty || '未知'))
    lines.push('知识点：' + (q.knowledge_point || '未标注'))
    lines.push('分值：' + scoreForQuestion(q) + ' 分')
    lines.push('题干：' + (q.stem || ''))
    if (q.options?.length) {
      lines.push('选项：')
      q.options.forEach(opt => { lines.push('  ' + opt) })
    }
    lines.push('答案：' + (q.answer || ''))
    if (q.analysis) lines.push('解析：' + q.analysis)
    if (q.mistake_alert) lines.push('易错提醒：' + q.mistake_alert)
    lines.push('')
    lines.push('-'.repeat(40))
    lines.push('')
  })
  return lines.join('\n')
}

function downloadTextFile(content, filename, type = 'text/plain;charset=utf-8') {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  exportBtnLabel.value = '已导出'
  setTimeout(() => { exportBtnLabel.value = '' }, 2000)
}

function exportSelectedQuestions() {
  const questions = getSelectedQuestions()
  if (!questions.length) return
  const bank = resultBank.value
  const datePart = new Date().toISOString().slice(0, 10)
  downloadTextFile(buildQuestionText(questions, bank, '选中题目'), '选中题目_' + datePart + '.txt')
}

function printSelectedQuestions() {
  const questions = getSelectedQuestions()
  if (!questions.length) return
  printQuestionList(questions, resultBank.value, '选中题目')
}

function exportQuestions() {
  if (!resultBank.value?.questions?.length) return
  const bank = resultBank.value
  const exportData = {
    title: bank.title || '未命名',
    course_name: bank.course_name || '',
    target_topic: bank.target_topic || '',
    export_time: new Date().toISOString(),
    total_count: bank.questions.length,
    questions: bank.questions.map((q, idx) => ({
      index: idx + 1,
      type: q.type || '未知',
      difficulty: q.difficulty || '未知',
      knowledge_point: q.knowledge_point || '未标注',
      score: scoreForQuestion(q),
      stem: q.stem || '',
      options: q.options || [],
      answer: q.answer || '',
      analysis: q.analysis || '',
      mistake_alert: q.mistake_alert || '',
    })),
  }
  const datePart = new Date().toISOString().slice(0, 10)
  downloadTextFile(JSON.stringify(exportData, null, 2), '题库_' + datePart + '.json', 'application/json;charset=utf-8')
}

function exportQuestionsAsTxt() {
  if (!resultBank.value?.questions?.length) return
  const datePart = new Date().toISOString().slice(0, 10)
  downloadTextFile(buildQuestionText(resultBank.value.questions, resultBank.value, '题库导出'), '题库导出_' + datePart + '.txt')
}

function printQuestionList(questions, bank, title) {
  const rows = questions.map((q, idx) => {
    const options = q.options?.length ? '<div>' + q.options.map(o => '<p>' + escapeHtml(o) + '</p>').join('') + '</div>' : ''
    return '<section class="pq-card"><h3>Q' + (idx + 1) + ' ' + escapeHtml(q.type || '') + '</h3><p>' + escapeHtml(q.stem || '') + '</p>' + options + '<p><strong>答案：</strong>' + escapeHtml(q.answer || '') + '</p><p><strong>解析：</strong>' + escapeHtml(q.analysis || '') + '</p></section>'
  }).join('')
  const html = '<!doctype html><html><head><meta charset="utf-8"><title>' + escapeHtml(title) + '</title><style>body{font-family:Microsoft YaHei,Arial,sans-serif;padding:24px;color:#1f3d39}.pq-card{border:1px solid #cde9df;padding:14px;margin-bottom:12px;page-break-inside:avoid}h1{font-size:22px}</style></head><body><h1>' + escapeHtml(title + ' - ' + (bank?.title || '题库')) + '</h1>' + rows + '</body></html>'
  const frame = document.createElement('iframe')
  frame.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0'
  document.body.appendChild(frame)
  const printWindow = frame.contentWindow
  const printDocument = frame.contentDocument || printWindow?.document
  if (!printWindow || !printDocument) { frame.remove(); return }
  printDocument.open()
  printDocument.write(html)
  printDocument.close()
  printWindow.focus()
  printWindow.print()
  window.setTimeout(() => frame.remove(), 1000)
}

function printQuestions() {
  if (!resultBank.value?.questions?.length) return
  printQuestionList(resultBank.value.questions, resultBank.value, '题库')
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: var(--surface-soft, #f7fafc);
}

.qg-page {
  height: calc(100vh - 64px);
  padding: 24px 28px 28px;
  box-sizing: border-box;
  overflow: hidden;
}

/* ===== Page Header (removed - title moved to sidebar) ===== */

.qg-tabs,
.qg-mode-switcher {
  display: flex;
  gap: 2px;
  position: sticky;
  top: 0;
  z-index: 5;
  margin: 0 0 8px;
  padding: 2px;
  background: var(--surface-soft, #f7fafc);
  border-radius: 6px;
  flex-shrink: 0;
}

.qg-mode-switcher {
  gap: 0;
  background: transparent;
  padding: 0 0 6px;
  border-bottom: 1px solid var(--border, rgba(31, 188, 188, 0.15));
  margin-bottom: 10px;
}

.qg-tabs button,
.qg-secondary-btn,
.qg-link-btn {
  border: 1px solid var(--border, rgba(31, 188, 188, 0.15));
  background: var(--surface-strong, var(--surface, rgba(255, 255, 255, 0.98)));
  color: var(--text-soft, #717b83);
  border-radius: 8px;
  padding: 8px 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 600;
}
.qg-secondary-btn:hover:not(:disabled) {
  background: var(--primary-soft, rgba(31, 188, 188, 0.1));
  border-color: var(--border-strong, rgba(31, 188, 188, 0.25));
  color: var(--primary-deep, #1fbcbc);
  box-shadow: 0 2px 6px rgba(31, 188, 188, 0.12);
}
.qg-secondary-btn:active:not(:disabled) {
  transform: scale(0.97);
}
.qg-secondary-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.qg-tabs button {
  flex: 1;
  min-width: 0;
  padding: 5px 8px;
  white-space: nowrap;
  font-size: 13px;
}

.qg-mode-btn {
  flex: 1;
  min-width: 0;
  padding: 4px 6px;
  white-space: nowrap;
  font-size: 12px;
  border: none;
  background: transparent;
  color: var(--text-soft, #717b83);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s ease;
  font-weight: 500;
}
.qg-mode-btn:hover {
  background: var(--surface, rgba(255,255,255,0.95));
  color: var(--text-main, #1e293b);
}
.qg-mode-btn.active {
  color: var(--primary-deep, #1fbcbc);
  background: var(--primary-soft, rgba(31,188,188,0.1));
  font-weight: 700;
}

.qg-tabs button:hover {
  background: var(--surface, rgba(255, 255, 255, 0.98));
  color: var(--text-main, #1e293b);
}

.qg-tabs button.active {
  color: var(--primary-deep, #1fbcbc);
  background: var(--primary-soft, rgba(31, 188, 188, 0.1));
  border-color: var(--border-strong, rgba(31, 188, 188, 0.25));
  font-weight: 700;
}

/* ===== Unified grid layout ===== */

.qg-main-layout {
  display: grid;
  gap: 20px;
  height: 100%;
  min-height: 0;
  width: 100%;
}

.qg-main-layout.layout-generate {
  grid-template-columns: minmax(260px, 28%) minmax(0, 1fr);
}

.qg-main-layout.layout-generate.has-ai-sidebar {
  grid-template-columns: minmax(260px, 28%) minmax(0, 1fr) minmax(280px, 22%);
}

.qg-main-layout.layout-exam,
.qg-main-layout.layout-history {
  grid-template-columns: minmax(260px, 28%) minmax(0, 1fr);
}

.qg-panel {
  background: var(--surface, rgba(255, 255, 255, 0.98));
  border: 1px solid var(--border, rgba(31, 188, 188, 0.15));
  border-radius: 12px;
  padding: 20px;
  overflow-y: auto;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

/* ===== Left sidebar ===== */

.qg-left-sidebar {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.qg-mobile-config-toggle {
  display: none;
}

.qg-sidebar-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

/* 鍥哄畾鍦ㄤ晶鏍忓簳閮ㄧ殑鐢熸垚鎸夐挳 */
.qg-generate-fixed-wrap {
  flex: 0 0 auto;
  padding: 12px 16px 16px;
  background: linear-gradient(to top, var(--surface, rgba(255, 255, 255, 0.94)) 70%, rgba(255,255,255,0.9) 100%);
  border-top: 1px solid #f0f0f0;
  position: sticky;
  bottom: 0;
  z-index: 10;
}
.qg-generate-fixed-wrap .qg-generate-btn {
  width: 100%;
  margin: 0;
}
.qg-generate-fixed-wrap .qg-error {
  margin: 0 0 8px;
  text-align: center;
}

.qg-result {
  display: flex;
  flex-direction: column;
}

/* ===== AI 鏉堟挸鍤笟褎鐖?===== */

.qg-sidebar {
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #f8fafc 0%, #f8fafc 100%);
  border: 1px solid rgba(31, 188, 188, 0.15);
  border-radius: 12px;
}

.qg-sidebar .qg-panel-title {
  margin: 0 0 12px;
  color: var(--text-main, #1e293b);
  font-size: 15px;
  font-weight: 600;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(31, 188, 188, 0.12);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.qg-sidebar .qg-panel-title::before {
  content: '';
  font-size: 14px;
}

.qg-sidebar-idle {
  flex: 1;
  display: grid;
  place-items: center;
  text-align: center;
  color: #6a7f7c;
  font-size: 13px;
  padding: 20px 12px;
  line-height: 1.6;
}

.qg-sidebar-idle::before {
  content: '';
  font-size: 32px;
  margin-bottom: 12px;
  opacity: 0.6;
}

.qg-sidebar-process {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  min-height: 0;
}

.qg-sidebar-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(31, 188, 188, 0.06);
  color: #2563eb;
  font-size: 13px;
  flex-shrink: 0;
}

.qg-spinner.sm {
  width: 18px;
  height: 18px;
  border-width: 2px;
  flex-shrink: 0;
}

.qg-live-questions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.qg-live-title {
  font-size: 13px;
  color: #1fbcbc;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.qg-live-title::before {
  content: '';
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #1fbcbc;
  animation: qg-pulse 1.2s ease-in-out infinite;
}

.qg-live-mini {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid rgba(31, 188, 188, 0.14);
  background: rgba(255, 255, 255, 0.95);
  animation: qg-fade-in 0.3s ease-out;
}

.qg-live-mini-id {
  font-weight: 800;
  color: #1fbcbc;
  font-size: 12px;
  margin-right: 6px;
}

.qg-live-mini-type,
.qg-live-mini-diff {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(31, 188, 188, 0.1);
  margin-right: 4px;
}

.qg-live-mini-stem {
  margin: 6px 0 0;
  font-size: 12px;
  color: #334155;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.qg-sidebar-json {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.qg-sidebar-json h4 {
  margin: 0 0 8px;
  font-size: 12px;
  color: #6a7f7c;
  flex-shrink: 0;
}

.qg-sidebar-json pre {
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 10px;
  border-radius: 6px;
  background: #f8fafc;
  border: 1px solid rgba(31, 188, 188, 0.1);
  font-size: 11px;
  line-height: 1.5;
  color: #334155;
  font-family: "Cascadia Code", "Consolas", monospace;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.qg-agent-stream {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}

.qg-agent-stream.done {
  margin-top: 4px;
}

.qg-agent-stream h4 {
  margin: 0;
  font-size: 12px;
  color: #52706d;
}

.qg-agent-card {
  border: 1px solid rgba(31, 188, 188, 0.15);
  border-radius: 8px;
  padding: 9px 10px;
  background: var(--surface, rgba(255, 255, 255, 0.98));
}

.qg-agent-card.is-running {
  border-color: rgba(31, 188, 188, 0.3);
  background: rgba(31, 188, 188, 0.05);
}

.qg-agent-card.is-done {
  border-color: rgba(31, 188, 188, 0.25);
  background: rgba(31, 188, 188, 0.05);
}

.qg-agent-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.qg-agent-card-head strong {
  font-size: 12px;
  color: #1e293b;
}

.qg-agent-card-head span {
  flex-shrink: 0;
  font-size: 11px;
  color: #2563eb;
}

.qg-agent-message {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.45;
  color: #475569;
}

.qg-agent-card pre {
  max-height: 160px;
  overflow: auto;
  margin: 8px 0 0;
  padding: 8px;
  border-radius: 6px;
  background: rgba(248, 250, 252, 0.95);
  color: #334155;
  font-size: 11px;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
}

.qg-sidebar-done {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.qg-sidebar-done-msg {
  margin: 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(31, 188, 188, 0.1);
  color: #1fbcbc;
  font-size: 13px;
  font-weight: 700;
  text-align: center;
}

.qg-sidebar-stat {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(31, 188, 188, 0.04);
  border: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-sidebar-stat span {
  font-size: 12px;
  color: #717b83;
}

.qg-sidebar-stat strong {
  font-size: 18px;
  color: #2563eb;
}

.qg-result-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.qg-export-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 14px;
  background: rgba(31, 188, 188, 0.03);
  border-radius: 10px;
  border: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-export-bar .qg-secondary-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  padding: 6px 12px;
  border-radius: 7px;
}

.qg-export-bar .qg-secondary-btn:hover:not(:disabled) {
  background: rgba(31, 188, 188, 0.1);
  border-color: rgba(31, 188, 188, 0.25);
  color: var(--primary-deep, #1fbcbc);
}

.qg-export-bar .qg-secondary-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.qg-export-icon {
  font-size: 14px;
}

.qg-search-wrap {
  position: relative;
  flex: 1;
  min-width: 180px;
  display: flex;
  align-items: center;
}
.qg-search-icon {
  position: absolute;
  left: 10px;
  color: #999;
  pointer-events: none;
  z-index: 1;
}
.qg-search-input {
  width: 100%;
  padding: 7px 30px 7px 32px;
  font-size: 13px;
  border: 1px solid rgba(31, 188, 188, 0.22);
  border-radius: 6px;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  color: #333;
  outline: none;
  transition: border-color 0.2s;
}
.qg-search-input:focus {
  border-color: rgba(31, 188, 188, 0.5);
  box-shadow: 0 0 0 2px rgba(31, 188, 188, 0.1);
}
.qg-search-input::placeholder {
  color: #aaa;
}
.qg-search-clear {
  position: absolute;
  right: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: none;
  background: rgba(0,0,0,0.06);
  border-radius: 50%;
  color: #888;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.qg-search-clear:hover {
  background: rgba(0,0,0,0.12);
  color: #333;
}
.qg-search-highlight {
  background: linear-gradient(135deg, #ffe066 0%, #ffb347 100%);
  color: #333;
  padding: 1px 3px;
  border-radius: 3px;
  box-shadow: 0 0 0 1px rgba(255, 179, 71, 0.3);
  font-weight: 500;
}

.qg-sort-dropdown {
  position: relative;
  display: inline-block;
}
.qg-sort-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  font-size: 13px;
  border: 1px solid var(--border, rgba(31, 188, 188, 0.1));
  border-radius: 7px;
  background: var(--surface-strong, var(--surface, rgba(255, 255, 255, 0.94)));
  color: var(--text-main, #24342d);
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  font-weight: 600;
}
.qg-sort-btn:hover {
  border-color: rgba(31, 188, 188, 0.4);
  box-shadow: 0 1px 4px rgba(31, 188, 188, 0.1);
}
.qg-sort-btn:focus-visible {
  border-color: rgba(31, 188, 188, 0.5);
  outline: none;
}
.qg-sort-icon {
  color: rgba(31, 188, 188, 0.6);
  flex-shrink: 0;
}
.qg-sort-btn-label {
  font-weight: 500;
}
.qg-sort-chevron {
  transition: transform 0.2s ease;
  flex-shrink: 0;
}
.qg-sort-chevron.is-open {
  transform: rotate(180deg);
}
.qg-sort-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 140px;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border: 1px solid rgba(31, 188, 188, 0.18);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1), 0 1px 4px rgba(0, 0, 0, 0.06);
  z-index: 100;
  padding: 4px;
  animation: qg-sort-menu-in 0.15s ease;
}
@keyframes qg-sort-menu-in {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}
.qg-sort-menu-item {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 7px 10px;
  font-size: 13px;
  color: #333;
  background: transparent;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s, color 0.15s;
}
.qg-sort-menu-item:hover {
  background: rgba(31, 188, 188, 0.06);
}
.qg-sort-menu-item.is-active {
  background: rgba(31, 188, 188, 0.1);
  color: #1fbcae;
  font-weight: 600;
}
.qg-sort-check {
  color: #1fbcae;
  font-size: 13px;
  flex-shrink: 0;
  width: 14px;
}

.qg-export-dropdown {
  position: relative;
  display: inline-block;
}
.qg-export-dropdown .qg-secondary-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.qg-export-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 150px;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border: 1px solid rgba(31, 188, 188, 0.18);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1), 0 1px 4px rgba(0, 0, 0, 0.06);
  z-index: 100;
  padding: 4px;
  animation: qg-sort-menu-in 0.15s ease;
}
.qg-export-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  color: var(--text-main, #24342d);
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease;
}
.qg-export-menu-item:hover {
  background: var(--primary-soft, rgba(31, 188, 188, 0.1));
  color: var(--primary-deep, #1fbcbc);
}
.qg-export-menu-icon {
  font-size: 14px;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
}

.qg-search-empty,
.qg-search-count {
  font-size: 13px;
  color: #888;
  margin-bottom: 12px;
  padding-left: 2px;
}
.qg-search-empty {
  color: #c0392b;
}

.qg-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 2px solid rgba(31, 188, 188, 0.18);
  margin-bottom: 20px;
}

.qg-panel-title {
  margin: 0 0 12px;
  color: var(--primary-deep, #1fbcbc);
  font-size: 15px;
  font-weight: 700;
  flex-shrink: 0;
  letter-spacing: 0.2px;
}

.qg-section {
  margin-bottom: 16px;
}

.qg-section:first-child {
  background: linear-gradient(135deg, rgba(31, 188, 188, 0.03), rgba(31, 188, 188, 0.02));
  border: 1px solid rgba(31, 188, 188, 0.1);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 14px;
}

.qg-label {
  display: block;
  margin-bottom: 6px;
  color: #1a3a35 !important;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.qg-left-sidebar .qg-label {
  color: #1a3a35 !important;
}

.qg-input,
.qg-textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid rgba(31, 188, 188, 0.2);
  font-size: 14px;
  color: #294443;
  outline: none;
  font-family: inherit;
}

.qg-row {
  display: flex;
  gap: 12px;
}

.qg-half {
  flex: 1;
}

.qg-dropzone {
  border: 2px dashed rgba(31, 188, 188, 0.25);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  cursor: pointer;
  background: rgba(31, 188, 188, 0.02);
}

.qg-dropzone-active,
.qg-dropzone:hover {
  border-color: #1fbcbc;
  background: rgba(31, 188, 188, 0.05);
}

.qg-dropzone-icon {
  display: inline-block;
  width: 40px;
  height: 40px;
  line-height: 40px;
  border-radius: 50%;
  background: rgba(31, 188, 188, 0.1);
  color: #2563eb;
  font-size: 24px;
}

.qg-dropzone-hint p,
.qg-muted {
  color: #6a7f7c;
}

.qg-dropzone-sub,
.qg-hint,
.qg-file-size,
.qg-sheet-item small {
  font-size: 12px;
  color: #8fa3a0;
}

.qg-file-item,
.qg-type-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 0;
}

.qg-file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.qg-file-remove {
  border: none;
  background: none;
  color: #d65745;
  cursor: pointer;
}

.qg-type-row {
  padding: 8px 10px;
  border-radius: 6px;
  background: rgba(31, 188, 188, 0.04);
}

.qg-type-row.is-auto-distribute {
  background: rgba(31, 188, 188, 0.025);
  border: 1px dashed rgba(31, 188, 188, 0.18);
}

.qg-type-row.is-disabled {
  opacity: 0.62;
}

.qg-type-row.is-enabled {
  border-left: 3px solid var(--type-color, #1fbcbe);
  background: color-mix(in srgb, var(--type-color, #1fbcbe) 6%, transparent);
}

.qg-auto-row,
.qg-auto-total {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  color: #294443;
  font-size: 13px;
}

.qg-auto-row {
  padding: 9px 10px;
  border-radius: 8px;
  background: rgba(31, 188, 188, 0.05);
  border: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-type-check {
  display: flex;
  gap: 8px;
  align-items: center;
}

.qg-type-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.qg-type-check:hover .qg-type-dot {
  transform: scale(1.3);
}

.qg-num-input {
  width: 54px;
  padding: 6px;
  border-radius: 5px;
  border: 1px solid rgba(31, 188, 188, 0.2);
}

.qg-score-input {
  width: 64px;
  padding: 6px;
  border-radius: 5px;
  border: 1px solid rgba(31, 188, 188, 0.2);
}

.qg-type-count {
  display: flex;
  align-items: center;
  gap: 6px;
}

.qg-type-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.qg-type-grid.is-auto-distribute {
  grid-template-columns: 1fr;
}

.qg-type-row {
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.qg-type-row .qg-type-count {
  width: 100%;
  justify-content: flex-start;
}

.qg-auto-badge {
  min-width: 82px;
  padding: 6px 8px;
  border-radius: 5px;
  background: rgba(16, 194, 127, 0.1);
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  text-align: center;
}

.qg-auto-hint {
  margin-top: -4px;
}

.qg-generate-btn {
  width: 100%;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #1fbcbc 0%, #1fbcbc 100%);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  font-size: 16px;
  font-weight: 800;
  cursor: pointer;
  margin-top: 16px;
  flex-shrink: 0;
  transition: box-shadow 0.25s ease, transform 0.15s ease, filter 0.25s ease;
  box-shadow: 0 4px 14px rgba(31, 188, 188, 0.3), 0 1px 3px rgba(0,0,0,0.1);
  letter-spacing: 0.5px;
  position: sticky;
  bottom: 0;
  z-index: 5;
  text-shadow: 0 1px 2px rgba(0,0,0,0.15);
}
.qg-generate-btn:hover:not(:disabled) {
  box-shadow: 0 6px 20px rgba(31, 188, 188, 0.4), 0 2px 6px rgba(0,0,0,0.12);
  filter: brightness(1.1);
  transform: translateY(-1px);
}
.qg-generate-btn:active:not(:disabled) {
  transform: scale(0.98);
  box-shadow: 0 2px 6px rgba(31, 188, 188, 0.25);
}

.qg-generate-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.qg-generate-btn.compact {
  width: auto;
  padding: 8px 16px;
}

.qg-generate-btn.full {
  width: 100%;
  margin-top: 12px;
}

.qg-exam-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.qg-timer,
.qg-answer-timer {
  color: #2563eb;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.qg-answer-timer {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 10px;
  background: rgba(31, 188, 188, 0.05);
  font-size: 15px;
}

.qg-timer-icon {
  font-size: 14px;
  opacity: 0.7;
}

.qg-card-submit-btn {
  width: 100%;
  border: none;
  border-radius: 12px;
  padding: 10px 16px;
  background: linear-gradient(135deg, #1fbcbc, #18b8b6);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  margin-top: 10px;
  flex-shrink: 0;
  transition: all 0.2s ease;
  letter-spacing: 0.5px;
}

.qg-card-submit-btn:hover {
  filter: brightness(1.08);
  box-shadow: 0 4px 16px rgba(16, 194, 127, 0.3);
  transform: translateY(-1px);
}

.qg-card-submit-btn:active {
  transform: translateY(0);
}

.qg-card-handle-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  z-index: 2;
}

.qg-card-toggle-btn {
  width: 24px;
  height: 24px;
  border: 1px solid rgba(31, 188, 188, 0.18);
  border-radius: 6px;
  background: rgba(31, 188, 188, 0.05);
  color: #6a7f7c;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
  touch-action: manipulation;
}

.qg-card-toggle-btn:hover {
  background: rgba(31, 188, 188, 0.12);
  color: #2563eb;
  border-color: rgba(31, 188, 188, 0.25);
}

.qg-card-minimized {
  width: auto !important;
  min-width: 120px;
  padding: 0 12px 10px;
}

.qg-card-minimized .qg-answer-card-handle {
  padding: 10px 0 6px;
  margin-bottom: 0;
  border-bottom: none;
}

.qg-mini-timer {
  font-size: 14px;
  font-weight: 800;
  color: #2563eb;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5px;
}

.qg-error {
  color: #c84d3c;
  background: #fdf0ee;
  border: 1px solid #f5c6be;
  border-radius: 6px;
  padding: 8px 12px;
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.4;
}

.qg-generate-error-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  margin: 0 0 16px;
  background: linear-gradient(135deg, #fef2f2 0%, var(--surface, rgba(255, 255, 255, 0.94))1f0 100%);
  border: 1px solid #fecaca;
  border-radius: 10px;
  color: #991b1b;
}

.qg-generate-error-banner svg {
  flex-shrink: 0;
  color: #ef4444;
}

.qg-generate-error-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.qg-generate-error-text strong {
  font-size: 14px;
}

.qg-generate-error-text span {
  font-size: 13px;
  color: #7f1d1d;
}

.qg-generate-retry-btn {
  flex-shrink: 0;
  padding: 8px 20px;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.qg-generate-retry-btn:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

.qg-result-empty,
.qg-result-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #7b908d;
}

.qg-empty-illustration {
  width: 180px;
  margin-bottom: 8px;
  opacity: 0.8;
}

.qg-empty-illustration svg {
  width: 100%;
  height: auto;
}

.qg-empty-text {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #5f7471;
}

.qg-empty-sub {
  margin: 0;
  font-size: 13px;
  color: #8fa3a0;
}

.qg-empty-weak-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
  max-width: 400px;
}

.qg-empty-weak-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  color: #0d9488;
  background: linear-gradient(135deg, rgba(31, 188, 188, 0.1), rgba(16, 194, 127, 0.08));
  border: 1px solid rgba(31, 188, 188, 0.22);
  border-radius: 20px;
  transition: all 0.2s ease;
}

.qg-empty-weak-tag:hover {
  background: linear-gradient(135deg, rgba(31, 188, 188, 0.16), rgba(16, 194, 127, 0.14));
  border-color: rgba(31, 188, 188, 0.35);
  transform: translateY(-1px);
}

.qg-hint-text {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #8fa3a0;
  line-height: 1.5;
}

.qg-empty-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.qg-empty-workflow {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 8px 16px;
  background: rgba(31, 188, 188, 0.05);
  border-radius: 20px;
  font-size: 12px;
  color: #7b908d;
}

.qg-workflow-step {
  font-weight: 500;
  color: #5f7471;
}

.qg-empty-weak-preview {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
  max-width: 400px;
}

.qg-empty-weak-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  color: #0d9488;
  background: linear-gradient(135deg, rgba(31, 188, 188, 0.1), rgba(16, 194, 127, 0.08));
  border: 1px solid rgba(31, 188, 188, 0.22);
  border-radius: 20px;
  transition: all 0.2s ease;
}

.qg-empty-weak-more {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  color: #8fa3a0;
  background: rgba(143, 163, 160, 0.1);
  border-radius: 20px;
}

.qg-workflow-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 10px 16px;
  background: rgba(31, 188, 188, 0.03);
  border: 1px solid rgba(31, 188, 188, 0.1);
  border-radius: 10px;
  font-size: 13px;
  color: #7b908d;
}

.qg-workflow-hint .qg-workflow-step {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 6px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.qg-workflow-hint .qg-workflow-done {
  background: rgba(16, 194, 127, 0.1);
  color: #10b584;
}

.qg-workflow-hint .qg-workflow-active {
  background: rgba(31, 188, 188, 0.12);
  color: #1fbcbe;
  font-weight: 600;
}

.qg-workflow-arrow {
  color: #c1cecb;
  font-size: 14px;
}

.qg-empty-sync-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 4px 0 0 0;
  font-size: 11px;
  color: #8fa3a0;
}

.qg-empty-profile-preview {
  background: linear-gradient(135deg, rgba(31, 188, 188, 0.03), rgba(16, 194, 127, 0.03));
  border: 1px solid rgba(31, 188, 188, 0.1);
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 20px;
  max-width: 460px;
  width: 100%;
  animation: qg-fade-in 0.35s ease;
}

.qg-profile-preview-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.qg-profile-preview-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.qg-profile-preview-badge {
  font-size: 11px;
  color: #1fbcbe;
  background: rgba(31, 188, 188, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.qg-profile-preview-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.qg-profile-preview-tag {
  font-size: 12px;
  color: #e76f00;
  background: rgba(231, 111, 0, 0.08);
  border: 1px solid rgba(231, 111, 0, 0.15);
  padding: 3px 10px;
  border-radius: 12px;
  font-weight: 500;
}

.qg-profile-preview-label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
  font-weight: 500;
}

.qg-profile-preview-weakpoints {
  margin-bottom: 12px;
}

.qg-profile-preview-config {
  margin-bottom: 12px;
}

.qg-profile-preview-summary {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #475569;
}

.qg-weak-tag-preview {
  font-size: 12px;
  color: #e76f00;
  background: rgba(231, 111, 0, 0.08);
  border: 1px solid rgba(231, 111, 0, 0.15);
  padding: 3px 10px;
  border-radius: 12px;
  font-weight: 500;
}

.qg-more-tag {
  font-size: 11px;
  color: #64748b;
  background: rgba(100, 116, 139, 0.1);
  padding: 3px 8px;
  border-radius: 10px;
}

.qg-preview-dot {
  color: #cbd5e1;
}

.qg-preview-badge {
  font-size: 11px;
  color: #1fbcbe;
  background: rgba(31, 188, 188, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.qg-profile-preview-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #1fbcbc;
  margin: 0;
  font-weight: 500;
}

.qg-empty-icon-wrap {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(31, 188, 188, 0.06), rgba(16, 194, 127, 0.06));
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4px;
}

.qg-config-status {
  display: flex;
  gap: 12px;
  margin: 16px 0;
  flex-wrap: wrap;
}

.qg-status-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(16, 184, 126, 0.08);
  border: 1px solid rgba(16, 184, 126, 0.2);
  border-radius: 20px;
  font-size: 13px;
  color: #059669;
}

.qg-status-item svg {
  flex-shrink: 0;
}

.qg-weak-status {
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.qg-weak-inline-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.qg-weak-inline-tag {
  display: inline-block;
  padding: 2px 8px;
  background: rgba(16, 184, 126, 0.12);
  border: 1px solid rgba(16, 184, 126, 0.25);
  border-radius: 10px;
  font-size: 11px;
  color: #047857;
}

.qg-weak-inline-more {
  display: inline-block;
  padding: 2px 6px;
  background: rgba(107, 114, 128, 0.1);
  border: 1px solid rgba(107, 114, 128, 0.2);
  border-radius: 10px;
  font-size: 11px;
  color: #6b7280;
}

.qg-steps-guide {
  display: flex;
  gap: 0;
  margin: 20px 0;
  padding: 16px 24px;
  background: linear-gradient(135deg, rgba(31, 188, 188, 0.05) 0%, rgba(16, 194, 127, 0.06) 100%);
  border: 1px solid rgba(31, 188, 188, 0.12);
  border-radius: 12px;
  max-width: 520px;
}

.qg-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #94a3b8;
  position: relative;
  white-space: nowrap;
}

.qg-step:not(:last-child)::after {
  content: '';
  width: 28px;
  height: 1px;
  background: #d1d5db;
  margin: 0 8px;
  flex-shrink: 0;
}

.qg-step.is-done {
  color: #10b981;
  font-weight: 500;
}

.qg-step-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.qg-step.is-done .qg-step-num {
  background: #10b981;
  color: var(--surface, rgba(255, 255, 255, 0.94));
}

.qg-step-check {
  flex-shrink: 0;
}

.qg-quick-status {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  width: 100%;
  max-width: 420px;
  margin-bottom: 16px;
}

.qg-status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(100, 116, 139, 0.04);
  border: 1px solid rgba(100, 116, 139, 0.1);
  border-radius: 8px;
  font-size: 12px;
  color: #8fa3a0;
  transition: all 0.2s ease;
}

.qg-status-item.is-active {
  background: rgba(31, 188, 188, 0.05);
  border-color: rgba(31, 188, 188, 0.18);
  color: #294443;
}

.qg-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #d1d5db;
  flex-shrink: 0;
}

.qg-status-item.is-active .qg-status-dot {
  background: #1fbcbc;
}

.qg-empty-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 16px 0;
  padding: 16px;
  background: rgba(31, 188, 188, 0.03);
  border-radius: 10px;
  border: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-empty-step {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #5f7471;
  transition: color 0.2s ease;
}

.qg-empty-step.is-done {
  color: #1fbcbc;
}

.qg-empty-step.is-done .qg-step-num {
  background: linear-gradient(135deg, #1fbcbc, #1fbcbc);
  box-shadow: 0 2px 6px rgba(16, 194, 127, 0.3);
}

.qg-step-num {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1fbcbc, #18b8b6);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.qg-example-card {
  width: 100%;
  max-width: 400px;
  padding: 16px;
  background: var(--surface, rgba(255, 255, 255, 0.98));
  border-radius: 10px;
  border: 1px solid rgba(31, 188, 188, 0.15);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.qg-example-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.qg-example-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: rgba(31, 188, 188, 0.1);
  color: #1fbcbc;
  border-radius: 4px;
  font-weight: 600;
}

.qg-example-type {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}

.qg-example-score {
  font-size: 12px;
  color: #94a3b8;
  margin-left: auto;
}

.qg-example-stem {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #334155;
  line-height: 1.6;
}

.qg-example-options {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.qg-example-options p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  padding: 6px 10px;
  background: rgba(31, 188, 188, 0.04);
  border-radius: 6px;
}

.qg-examples-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  width: 100%;
}

.qg-type-fill {
  background: rgba(59, 130, 246, 0.1) !important;
  color: #3b82f6 !important;
}

.qg-type-judge {
  background: rgba(249, 115, 22, 0.1) !important;
  color: #f97316 !important;
}

.qg-btn-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 50%;
  animation: qg-spin 0.8s linear infinite;
  margin-right: 8px;
  vertical-align: middle;
}

@keyframes qg-spin {
  to {
    transform: rotate(360deg);
  }
}

.qg-generating-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(31, 188, 188, 0.06);
  color: #2563eb;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 14px;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 2;
  backdrop-filter: blur(8px);
}

.qg-batch-tag {
  margin-left: auto;
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(31, 188, 188, 0.12);
  font-size: 12px;
  font-weight: 700;
  color: #1fbcbc;
  flex-shrink: 0;
}

.qg-sidebar-counter {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 6px;
  padding: 14px;
  border-radius: 10px;
  background: rgba(31, 188, 188, 0.06);
  border: 1px solid rgba(31, 188, 188, 0.12);
}

.qg-counter-label {
  font-size: 13px;
  color: #64748b;
}

.qg-counter-num {
  font-size: 28px;
  font-weight: 800;
  color: #1fbcbc;
}

.qg-live-questions {
  margin-top: 16px;
  border-top: 2px solid rgba(31, 188, 188, 0.25);
  padding-top: 12px;
}

.qg-live-title {
  font-size: 14px;
  color: #1fbcbc;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.qg-live-title::before {
  content: '';
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #1fbcbc;
  animation: qg-pulse 1.2s ease-in-out infinite;
}

@keyframes qg-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.qg-question-live {
  animation: qg-fade-in 0.3s ease-out;
}

@keyframes qg-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.qg-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(31, 188, 188, 0.15);
  border-top-color: #1fbcbc;
  border-radius: 50%;
  animation: qg-spin 0.8s linear infinite;
}

@keyframes qg-spin {
  to { transform: rotate(360deg); }
}

.qg-result-header,
.qg-score-banner {
  padding: 14px;
  border-radius: 8px;
  background: rgba(31, 188, 188, 0.06);
  margin-bottom: 14px;
}

.qg-result-meta {
  color: #717b83;
}

.qg-distribution {
  display: grid;
  gap: 8px;
  margin: 14px 0;
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(31, 188, 188, 0.14);
}

.qg-distribution div,
.qg-score-detail {
  display: grid;
  gap: 4px;
}

.qg-distribution strong {
  color: #1e293b;
  font-size: 13px;
}

.qg-distribution span,
.qg-score-detail span {
  color: #64748b;
  font-size: 13px;
}

.qg-question-card,
.qg-sheet-item {
  display: block;
  width: 100%;
  text-align: left;
  box-sizing: border-box;
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid rgba(37, 99, 235, 0.1);
  border-radius: 8px;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  color: #294443;
  position: relative;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08), 0 1px 3px rgba(23, 83, 85, 0.05);
  transition: box-shadow 0.25s ease, transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
  cursor: pointer;
}

.qg-question-card:hover {
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.12), 0 4px 12px rgba(23, 83, 85, 0.08);
  border-color: rgba(37, 99, 235, 0.3);
  transform: translateY(-2px);
}

.qg-question-card.qg-card-selected {
  border-color: rgba(37, 99, 235, 0.35);
  border-left: 4px solid #2563eb;
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.05) 0%, rgba(255, 255, 255, 1) 12%);
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.15), 0 4px 12px rgba(37, 99, 235, 0.1);
}

.qg-card-checkbox-wrap {
  position: absolute;
  top: 12px;
  left: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  z-index: 2;
}

.qg-card-checkbox-wrap input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: #2563eb;
  cursor: pointer;
}

.qg-question-card .qg-card-checkbox-wrap ~ .qg-question-head {
  padding-left: 20px;
}

.qg-card-fav-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: none;
  border: none;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  color: #c0c0c0;
  transition: color 0.2s, transform 0.15s;
  z-index: 2;
  padding: 2px;
}

.qg-card-fav-btn:hover {
  transform: scale(1.2);
}

.qg-card-fav-btn.is-favorited {
  color: #f59e0b;
  text-shadow: 0 1px 4px rgba(245, 158, 11, 0.3);
}

.qg-card-copy-btn {
  position: absolute;
  top: 8px;
  right: 36px;
  background: none;
  border: none;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  color: #a0a0a0;
  transition: color 0.2s, transform 0.15s;
  z-index: 2;
  padding: 2px;
}

.qg-card-copy-btn:hover {
  color: #2563eb;
  transform: scale(1.2);
}

.qg-diff-dropdown-wrap {
  display: inline-flex;
  align-items: center;
}
.qg-diff-dropdown {
  padding: 6px 28px 6px 10px;
  font-size: 13px;
  border: 1px solid rgba(31, 188, 188, 0.2);
  border-radius: 6px;
  background: var(--surface, rgba(255, 255, 255, 0.98)) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E") no-repeat right 8px center;
  -webkit-appearance: none;
  appearance: none;
  color: #334155;
  outline: none;
  cursor: pointer;
  transition: border-color 0.2s;
}
.qg-diff-dropdown:focus {
  border-color: rgba(31, 188, 188, 0.5);
  box-shadow: 0 0 0 2px rgba(31, 188, 188, 0.1);
}
.qg-diff-dropdown-active {
  border-color: rgba(31, 188, 188, 0.5);
  background-color: rgba(31, 188, 188, 0.04);
  font-weight: 600;
  color: #1fbcbc;
}

.qg-fav-filter-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  padding: 6px 12px;
  border-radius: 7px;
  border: 1px solid var(--border, rgba(31, 188, 188, 0.15));
  background: var(--surface-strong, var(--surface, rgba(255, 255, 255, 0.98)));
  cursor: pointer;
  user-select: none;
  transition: all 0.2s;
  font-weight: 600;
  color: var(--text-soft, #717b83);
}
.qg-fav-filter-toggle:hover {
  background: var(--primary-soft, rgba(31, 188, 188, 0.08));
  border-color: var(--border-strong, rgba(31, 188, 188, 0.2));
  color: var(--primary-deep, #1fbcbc);
}

.qg-fav-filter-toggle input[type="checkbox"] {
  display: none;
}

.qg-fav-filter-toggle .qg-fav-star-icon {
  font-size: 15px;
  color: #c0c0c0;
  transition: color 0.2s;
}

.qg-fav-filter-toggle.active {
  border-color: #f59e0b;
  background: rgba(245, 158, 11, 0.06);
}

.qg-fav-filter-toggle.active .qg-fav-star-icon {
  color: #f59e0b;
}

.qg-selected-btn {
  background: rgba(37, 99, 235, 0.08) !important;
  border-color: rgba(37, 99, 235, 0.3) !important;
  color: #2563eb !important;
}

.qg-selected-btn:hover {
  background: rgba(37, 99, 235, 0.15) !important;
}

.qg-select-all-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  padding: 6px 12px;
  border-radius: 7px;
  border: 1px solid var(--border, rgba(31, 188, 188, 0.15));
  background: var(--surface-strong, var(--surface, rgba(255, 255, 255, 0.98)));
  cursor: pointer;
  user-select: none;
  transition: all 0.2s;
  font-weight: 600;
  color: var(--text-soft, #717b83);
}
.qg-select-all-toggle:hover {
  background: var(--primary-soft, rgba(31, 188, 188, 0.08));
  border-color: var(--border-strong, rgba(31, 188, 188, 0.2));
  color: var(--primary-deep, #1fbcbc);
}
.qg-select-all-toggle input[type="checkbox"] {
  width: 15px;
  height: 15px;
  accent-color: var(--primary, #1fbcbc);
  cursor: pointer;
}
.qg-select-all-toggle.is-all-selected {
  border-color: var(--primary, #1fbcbc);
  background: rgba(31, 188, 188, 0.08);
  color: var(--primary-deep, #1fbcbc);
}
.qg-select-all-toggle.is-partial-selected {
  border-color: rgba(31, 188, 188, 0.4);
  background: rgba(31, 188, 188, 0.05);
}

.qg-selected-count {
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  font-weight: 700;
  color: var(--primary-deep, #1fbcbc);
  padding: 6px 10px;
  background: rgba(31, 188, 188, 0.08);
  border-radius: 7px;
}

.qg-batch-delete-btn {
  background: rgba(239, 68, 68, 0.08) !important;
  border-color: rgba(239, 68, 68, 0.3) !important;
  color: #ef4444 !important;
}
.qg-batch-delete-btn:hover {
  background: rgba(239, 68, 68, 0.15) !important;
}

.qg-delete-icon {
  font-size: 14px;
}

.qg-sheet-item.active {
  border-color: #1fbcbc;
  background: rgba(31, 188, 188, 0.06);
}

.qg-sheet-item strong {
  display: block;
  font-size: 14px;
  color: #1e293b;
  line-height: 1.4;
  margin-bottom: 4px;
}

.qg-sheet-course {
  display: block;
  font-size: 13px;
  color: #2563eb;
  font-weight: 600;
}

.qg-sheet-topic {
  display: block;
  font-size: 12px;
  color: #717b83;
  margin-top: 2px;
}

.qg-question-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
  width: 100%;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-question-id {
  font-weight: 800;
  color: #2563eb;
  font-size: 12.5px;
  min-width: 28px;
}

.qg-question-type,
.qg-question-diff,
.qg-question-score,
.qg-status-chip {
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11.5px;
  background: rgba(31, 188, 188, 0.1);
}

.qg-question-score {
  color: #2563eb;
  background: rgba(31, 188, 188, 0.1);
}

/* 闅惧害鏍囩棰滆壊 */
.qg-diff-easy {
  color: #16a34a;
  background: #f0fdf4;
  border: 1px solid rgba(22, 163, 74, 0.15);
  font-weight: 600;
}
.qg-diff-medium {
  color: #d97706;
  background: #fffbeb;
  border: 1px solid rgba(217, 119, 6, 0.15);
  font-weight: 600;
}
.qg-diff-hard {
  color: #dc2626;
  background: #fef2f2;
  border: 1px solid rgba(220, 38, 38, 0.15);
  font-weight: 600;
}

/* 棰樺瀷鏍囩棰滆壊 */
.qg-question-type {
  font-weight: 600;
  cursor: help;
  transition: transform 0.15s, box-shadow 0.15s;
}
.qg-question-type:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}
.qg-type-single {
  color: #2563eb;
  background: rgba(37, 99, 235, 0.12);
}
.qg-type-multi {
  color: #7c3aed;
  background: rgba(124, 58, 237, 0.12);
}
.qg-type-fill {
  color: #16a34a;
  background: rgba(22, 163, 74, 0.12);
}
.qg-type-essay {
  color: #6b7280;
  background: rgba(107, 114, 128, 0.12);
}
.qg-type-default {
  color: #1fbcbc;
  background: rgba(31, 188, 188, 0.12);
}

/* 闅惧害鍒嗗竷缁熻鏉?*/
.qg-diff-bar-wrap {
  width: 100%;
  margin: 6px 0 2px;
}
.qg-diff-bar {
  display: flex;
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  background: #f1f5f9;
}
.qg-diff-bar-seg {
  display: block;
  min-width: 2px;
  transition: width 0.3s ease;
}
.qg-diff-bar-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 11.5px;
  font-weight: 600;
}
.qg-diff-bar-label {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

/* 闅惧害鏍囩鎮仠鏁堟灉 */
.qg-question-diff {
  cursor: help;
  transition: transform 0.15s, box-shadow 0.15s;
}
.qg-question-diff:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

/* 缂佺喕顓搁幗妯款洣 */
.qg-stats-summary {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  margin-bottom: 12px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.04), rgba(31, 188, 188, 0.04));
  border: 1px solid rgba(37, 99, 235, 0.12);
  border-radius: 10px;
  flex-wrap: wrap;
}
.qg-gen-profile-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.1), rgba(59, 130, 246, 0.12));
  border: 1px solid rgba(37, 99, 235, 0.2);
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  color: #2563eb;
  margin-right: auto;
}
.qg-gen-profile-tag-icon {
  font-size: 13px;
}
.qg-stats-total {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.qg-stats-num {
  font-size: 22px;
  font-weight: 800;
  color: #2563eb;
}
.qg-stats-label {
  font-size: 13px;
  color: #64748b;
}
.qg-stats-filter-hint {
  font-size: 11px;
  color: #94a3b8;
  margin-left: 2px;
}
.qg-stats-divider {
  width: 1px;
  height: 24px;
  background: rgba(31, 188, 188, 0.2);
  flex-shrink: 0;
}
.qg-stats-group {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.qg-stats-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  color: #475569;
  background: rgba(100, 116, 139, 0.08);
}
.qg-stats-chip strong {
  font-weight: 700;
}
.qg-stats-type-chip {
  color: #2563eb;
  background: rgba(37, 99, 235, 0.08);
}
.qg-stats-easy {
  color: #16a34a;
  background: rgba(22, 163, 74, 0.1);
}
.qg-stats-easy strong { color: #16a34a; }
.qg-stats-medium {
  color: #ea580c;
  background: rgba(234, 88, 12, 0.1);
}
.qg-stats-medium strong { color: #ea580c; }
.qg-stats-hard {
  color: #dc2626;
  background: rgba(220, 38, 38, 0.1);
}
.qg-stats-hard strong { color: #dc2626; }
.qg-stats-chip {
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}
.qg-stats-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}
.qg-chip-active.qg-stats-type-chip {
  background: #2563eb;
  color: var(--surface, rgba(255, 255, 255, 0.94));
}
.qg-chip-active.qg-stats-type-chip strong { color: var(--surface, rgba(255, 255, 255, 0.94)); }
.qg-chip-active.qg-stats-easy {
  background: #16a34a;
  color: var(--surface, rgba(255, 255, 255, 0.98));
}
.qg-chip-active.qg-stats-easy strong { color: var(--surface, rgba(255, 255, 255, 0.98)); }
.qg-chip-active.qg-stats-medium {
  background: #ea580c;
  color: var(--surface, rgba(255, 255, 255, 0.98));
}
.qg-chip-active.qg-stats-medium strong { color: var(--surface, rgba(255, 255, 255, 0.98)); }
.qg-chip-active.qg-stats-hard {
  background: #dc2626;
  color: var(--surface, rgba(255, 255, 255, 0.98));
}
.qg-chip-active.qg-stats-hard strong { color: var(--surface, rgba(255, 255, 255, 0.98)); }
.qg-stats-empty {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
}
.qg-stats-empty-icon {
  font-size: 18px;
}
.qg-stats-empty-text {
  font-size: 14px;
  color: #94a3b8;
  font-weight: 500;
}
.qg-filter-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  margin-bottom: 10px;
  background: rgba(37, 99, 235, 0.05);
  border: 1px solid rgba(37, 99, 235, 0.15);
  border-radius: 8px;
  font-size: 13px;
  color: #334155;
}
.qg-filter-status-label {
  color: #64748b;
  font-size: 12px;
}
.qg-filter-status-text {
  font-weight: 600;
  color: #2563eb;
}
.qg-filter-clear-btn {
  margin-left: auto;
  padding: 3px 10px;
  font-size: 12px;
  color: #dc2626;
  background: rgba(220, 38, 38, 0.08);
  border: 1px solid rgba(220, 38, 38, 0.2);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.qg-filter-clear-btn:hover {
  background: rgba(220, 38, 38, 0.15);
}
.qg-inline-clear-btn {
  margin-left: auto;
  padding: 3px 12px;
  font-size: 12px;
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.08);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.qg-inline-clear-btn:hover {
  color: #64748b;
  background: rgba(148, 163, 184, 0.18);
  border-color: rgba(148, 163, 184, 0.35);
}
.qg-batch-btn {
  color: #1fbcbc;
  background: rgba(31, 188, 188, 0.08);
  border-color: rgba(31, 188, 188, 0.2);
}
.qg-batch-btn:hover {
  color: #1fbcbc;
  background: rgba(31, 188, 188, 0.15);
  border-color: rgba(31, 188, 188, 0.35);
}

/* 绌哄垪琛ㄥ紩瀵?*/
.qg-empty-guide {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
  text-align: center;
}
.qg-empty-guide-icon {
  margin-bottom: 12px;
  opacity: 0.7;
}
.qg-empty-guide-text {
  font-size: 16px;
  font-weight: 600;
  color: #475569;
  margin: 0 0 6px;
}
.qg-empty-guide-sub {
  font-size: 13px;
  color: #94a3b8;
  margin: 0;
  max-width: 320px;
}

.qg-status-chip.ok,
.qg-answer-card button.ok {
  background: linear-gradient(135deg, rgba(31, 188, 188, 0.15), rgba(31, 188, 188, 0.08));
  color: #1fbcbc;
  border-color: rgba(31, 188, 188, 0.3);
}

.qg-answer-card button.wrong {
  background: linear-gradient(135deg, rgba(214, 87, 69, 0.15), rgba(200, 77, 60, 0.08));
  color: #b84c3f;
  border-color: rgba(214, 87, 69, 0.3);
}

.qg-option {
  margin: 4px 0;
  line-height: 1.5;
  font-size: 13.5px;
}

.answer-option {
  display: flex;
  gap: 8px;
  align-items: baseline;
}

.qg-answer-block,
.qg-answer-review {
  border-top: 1px dashed rgba(31, 188, 188, 0.2);
  margin-top: 10px;
  padding-top: 8px;
}

.answer-textarea {
  min-height: 88px;
}

.qg-card-clickable {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  cursor: pointer;
  padding: 6px 10px;
  transition: background 0.15s;
  border-radius: 6px;
}

.qg-card-clickable:hover {
  background: rgba(31, 188, 188, 0.04);
}

.qg-expand-hint {
  display: inline-block;
  margin-top: 8px;
  font-size: 12px;
  color: #2563eb;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.qg-card-clickable:hover .qg-expand-hint {
  opacity: 1;
}

.qg-card-expanded {
  border-left: 4px solid #2563eb;
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.04) 0%, rgba(255, 255, 255, 1) 12%);
  box-shadow: 0 4px 20px rgba(37, 99, 235, 0.12), 0 2px 8px rgba(23, 83, 85, 0.06);
}

/* ===== Card Collapsible Body ===== */
.qg-card-body {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease, margin-top 0.3s ease, opacity 0.25s ease;
  opacity: 0;
  margin-top: 0;
}

.qg-card-body.is-open {
  max-height: 800px;
  margin-top: 8px;
  opacity: 1;
}

.qg-card-body-inner {
  overflow: hidden;
}

/* Arrow icon */
.qg-card-arrow {
  flex-shrink: 0;
  margin-left: 8px;
  color: #94a3b8;
  transition: transform 0.3s ease, color 0.2s;
  transform: rotate(-90deg);
}

.qg-arrow-open {
  transform: rotate(0deg);
  color: #2563eb;
}

/* Question stem */
.qg-question-stem {
  margin: 4px 0;
  line-height: 1.55;
  font-size: 14px;
  color: #334155;
}

/* Collapsed stem */
.qg-stem-collapsed {
  display: inline;
  margin: 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.4;
}

/* Knowledge point tag */
.qg-question-kp {
  padding: 2px 7px;
  border-radius: 5px;
  font-size: 11.5px;
  font-weight: 500;
  color: #1fbcbc;
  background: rgba(31, 188, 188, 0.1);
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Options container */
.qg-question-options {
  padding-left: 2px;
  margin-top: 2px;
}

/* Answer section in expanded body */
.qg-answer-section {
  border-top: 1px dashed rgba(37, 99, 235, 0.18);
  padding-top: 10px;
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.qg-answer-section p {
  margin: 4px 0;
  line-height: 1.55;
  font-size: 13.5px;
}

/* Answer row: highlight */
.qg-answer-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: linear-gradient(135deg, rgba(31, 188, 188, 0.08), rgba(31, 188, 188, 0.12));
  border: 1px solid rgba(31, 188, 188, 0.2);
  border-radius: 8px;
}

.qg-answer-label {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  color: #1fbcbc;
  background: rgba(31, 188, 188, 0.12);
  padding: 2px 8px;
  border-radius: 4px;
}

.qg-answer-value {
  font-size: 14px;
  font-weight: 600;
  color: #1fbcbc;
  line-height: 1.5;
}

/* Analysis block: gray background */
.qg-analysis-block {
  padding: 10px 14px;
  background: #f0f4f8;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  border-left: 3px solid #94a3b8;
}

.qg-analysis-label {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  background: #e2e8f0;
  padding: 2px 8px;
  border-radius: 4px;
  margin-bottom: 6px;
}

.qg-analysis-text {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.65;
  color: #475569;
}

/* Mistake alert block */
.qg-mistake-block {
  padding: 8px 14px;
  background: rgba(251, 191, 36, 0.08);
  border: 1px solid rgba(251, 191, 36, 0.25);
  border-radius: 8px;
  border-left: 3px solid #f59e0b;
}

.qg-mistake-label {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  color: #b45309;
  background: rgba(251, 191, 36, 0.2);
  padding: 2px 8px;
  border-radius: 4px;
  margin-bottom: 4px;
}

.qg-mistake-text {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.55;
  color: #92400e;
}

.qg-answer-expand {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.35s ease, opacity 0.25s ease, padding 0.3s ease;
  opacity: 0;
  padding-top: 0;
}

.qg-answer-expand.is-open {
  max-height: 600px;
  opacity: 1;
  padding-top: 12px;
}

.qg-answer-toggle-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding: 8px 14px;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.04), rgba(37, 99, 235, 0.08));
  border: 1px dashed rgba(37, 99, 235, 0.25);
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
  user-select: none;
}

.qg-answer-toggle-bar:hover {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(37, 99, 235, 0.14));
  border-color: rgba(37, 99, 235, 0.4);
}

.qg-answer-toggle-icon {
  font-size: 14px;
  line-height: 1;
}

.qg-answer-toggle-text {
  font-size: 13px;
  color: #2563eb;
  font-weight: 500;
}

.qg-answer-expand-inner {
  border-top: 1px dashed rgba(37, 99, 235, 0.18);
  padding-top: 10px;
}

.qg-answer-expand-inner p {
  margin: 6px 0;
  line-height: 1.6;
}

.qg-collapse-btn {
  display: inline-block;
  margin-top: 10px;
  padding: 4px 14px;
  font-size: 13px;
  color: #2563eb;
  background: rgba(37, 99, 235, 0.06);
  border: 1px solid rgba(37, 99, 235, 0.2);
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.qg-collapse-btn:hover {
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
}

.qg-card-actions-bar {
  display: flex;
  gap: 8px;
  padding: 8px 0 0;
  margin-top: 6px;
  border-top: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-card-expanded .qg-card-actions-bar {
  display: flex;
}

.qg-similar-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  color: #1fbcbc;
  background: rgba(31, 188, 188, 0.06);
  border: 1px solid rgba(31, 188, 188, 0.18);
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s, color 0.15s, transform 0.15s, box-shadow 0.2s;
}

.qg-similar-btn:hover {
  background: rgba(31, 188, 188, 0.12);
  color: #1fbcbc;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(31, 188, 188, 0.15);
}

.qg-similar-btn:active {
  transform: translateY(0);
  box-shadow: none;
}

.qg-similar-icon {
  font-size: 14px;
  display: inline-flex;
  align-items: center;
}

.qg-copy-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  color: #2563eb;
  background: rgba(37, 99, 235, 0.06);
  border: 1px solid rgba(37, 99, 235, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s, color 0.15s, transform 0.15s, box-shadow 0.2s;
}

.qg-copy-btn:hover {
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.15);
}

.qg-copy-btn:active {
  transform: translateY(0);
  box-shadow: none;
}

.qg-copy-icon {
  font-size: 14px;
  display: inline-flex;
  align-items: center;
}

.qg-answer-card {
  display: flex;
  flex-direction: column;
  position: fixed;
  z-index: 60;
  width: 252px;
  max-height: calc(100vh - 120px);
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(31, 188, 188, 0.15);
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.1);
  border-radius: 20px;
  backdrop-filter: blur(16px) saturate(140%);
  padding: 0 16px 16px;
  overflow: hidden;
}

.qg-answer-card-accent {
  height: 3px;
  margin: 0 -16px 0;
  background: linear-gradient(90deg, #1fbcbc, #1fbcbc, #1fbcbc);
  border-radius: 20px 20px 0 0;
  flex-shrink: 0;
}

.qg-answer-card-handle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0 10px;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(31, 188, 188, 0.1);
  cursor: grab;
  user-select: none;
}

.qg-answer-card-handle:active {
  cursor: grabbing;
}

.qg-card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-height: 30px;
  cursor: grab;
}

.qg-grip-dots {
  display: grid;
  grid-template-columns: repeat(2, 4px);
  gap: 3px;
  padding: 2px;
  opacity: 0.35;
}

.qg-grip-dots i {
  display: block;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #94a3b8;
}

.qg-answer-card-handle strong {
  font-size: 14px;
  color: #1e293b;
  letter-spacing: 0.3px;
}

.qg-answer-count {
  font-size: 12px;
  color: #2563eb;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(31, 188, 188, 0.08);
}

.qg-answer-card-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 4px 2px 4px 0;
}

.qg-answer-card-body::-webkit-scrollbar {
  width: 4px;
}

.qg-answer-card-body::-webkit-scrollbar-track {
  background: transparent;
}

.qg-answer-card-body::-webkit-scrollbar-thumb {
  background: rgba(31, 188, 188, 0.2);
  border-radius: 999px;
}

.qg-answer-card-body::-webkit-scrollbar-thumb:hover {
  background: rgba(31, 188, 188, 0.4);
}

/* 浜ゅ嵎缁撴灉鍥炬爣 */
.qg-result-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 800;
  flex-shrink: 0;
}

.qg-icon-correct {
  background: rgba(31, 188, 188, 0.15);
  color: #1fbcbc;
}

.qg-icon-wrong {
  background: rgba(214, 87, 69, 0.14);
  color: #c84d3c;
}

.qg-question-card.qg-correct {
  border-color: rgba(31, 188, 188, 0.3);
  background: linear-gradient(135deg, rgba(240, 253, 252, 0.96), rgba(255, 255, 255, 0.96));
}

.qg-question-card.qg-wrong {
  border-color: rgba(214, 87, 69, 0.25);
  background: linear-gradient(135deg, rgba(255, 245, 243, 0.96), rgba(255, 255, 255, 0.96));
}

.qg-answer-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 7px;
}

.qg-answer-grid button {
  width: 100%;
  min-width: 0;
  aspect-ratio: 1;
  border: 1.5px solid rgba(31, 188, 188, 0.15);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.92);
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  color: #64748b;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.qg-answer-grid button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(31, 188, 188, 0.15);
  border-color: rgba(31, 188, 188, 0.3);
  color: #2563eb;
}

/* ===== 鍝嶅簲寮忓竷灞€ ===== */

/* 骞虫澘妯睆 */
@media (max-width: 1024px) {
  .qg-page {
    padding: 12px 16px;
  }

  .qg-main-layout.layout-generate {
    grid-template-columns: minmax(220px, 20%) minmax(0, 1fr);
  }

  .qg-main-layout.layout-exam,
  .qg-main-layout.layout-history {
    grid-template-columns: minmax(220px, 20%) minmax(0, 1fr);
  }

  .qg-answer-card {
    width: 236px;
    max-height: calc(100vh - 100px);
  }

  .qg-sidebar {
    grid-column: 1 / -1;
    max-height: 240px;
  }

  .qg-sidebar-process {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 10px;
  }

  .qg-sidebar-status {
    width: 100%;
  }

  .qg-live-questions {
    flex: 1;
    min-width: 240px;
  }

  .qg-sidebar-json {
    flex: 1;
    min-width: 240px;
    max-height: 160px;
  }

  .qg-result {
    min-height: 50vh;
  }

}

/* 骞虫澘绔栧睆 / 澶у睆鎵嬫満 */
@media (max-width: 768px) {
  .qg-page {
    padding: 10px 12px;
    height: auto;
    min-height: calc(100vh - 64px);
  }

  .qg-main-layout {
    grid-template-columns: 1fr;
    gap: 12px;
    height: auto;
    min-height: calc(100vh - 84px);
  }

  .qg-main-layout.layout-generate,
  .qg-main-layout.layout-exam,
  .qg-main-layout.layout-history {
    grid-template-columns: 1fr;
  }

  .qg-left-sidebar {
    grid-column: 1 / -1;
    order: 0;
    max-height: none;
    overflow: hidden;
  }

  .qg-sidebar {
    display: none;
  }

  .qg-result,
  .qg-exam-main,
  .qg-history-main {
    grid-column: 1 / -1;
  }

  .qg-tabs {
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 14px;
    padding: 7px;
  }

  .qg-tabs button {
    flex: 1;
    min-width: 0;
    padding: 7px 10px;
    font-size: 13px;
  }

  .qg-panel {
    padding: 14px;
  }

  .qg-panel-title {
    font-size: 16px;
  }

  .qg-row {
    flex-direction: column;
    gap: 0;
  }

  .qg-left-sidebar .qg-sidebar-scroll {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    overflow-y: hidden;
    max-height: none;
    padding-bottom: 4px;
    scroll-snap-type: x proximity;
  }

  .qg-left-sidebar .qg-panel-title {
    flex: 0 0 180px;
    margin: 0;
    align-self: stretch;
    display: flex;
    align-items: center;
  }

  .qg-left-sidebar .qg-section,
  .qg-left-sidebar .qg-row,
  .qg-left-sidebar .qg-generate-btn,
  .qg-left-sidebar > .qg-sidebar-scroll > .qg-error,
  .qg-left-sidebar .qg-muted,
  .qg-left-sidebar .qg-sheet-item,
  .qg-left-sidebar .qg-history-tabs,
  .qg-left-sidebar .qg-history-list {
    flex: 0 0 min(82vw, 360px);
    scroll-snap-align: start;
  }

  .qg-left-sidebar .qg-row {
    display: flex;
    flex-direction: row;
    gap: 10px;
  }

  .qg-left-sidebar .qg-row .qg-section {
    flex: 1 1 0;
    min-width: 0;
  }

  .qg-type-row {
    flex-wrap: wrap;
    gap: 6px;
  }

  .qg-type-count {
    width: 100%;
    justify-content: flex-end;
  }

  .qg-question-head {
    gap: 6px;
  }

  .qg-question-card {
    padding: 12px;
  }

  .qg-answer-card {
    width: 216px;
    max-height: 45vh;
    border-radius: 16px;
    padding: 0 12px 12px;
  }

  .qg-answer-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }

  .qg-score-banner strong {
    font-size: 20px;
  }

  .qg-left-sidebar .qg-sidebar-scroll {
    max-height: none;
  }
}

/* 閹靛婧€ (<=480px) */
@media (max-width: 480px) {
  .qg-page {
    padding: 8px;
  }

  .qg-panel {
    padding: 10px;
    border-radius: 6px;
  }

  .qg-left-sidebar .qg-sidebar-scroll {
    gap: 10px;
  }

  .qg-left-sidebar .qg-panel-title,
  .qg-left-sidebar .qg-section,
  .qg-left-sidebar .qg-row,
  .qg-left-sidebar .qg-generate-btn,
  .qg-left-sidebar > .qg-sidebar-scroll > .qg-error,
  .qg-left-sidebar .qg-muted,
  .qg-left-sidebar .qg-sheet-item,
  .qg-left-sidebar .qg-history-tabs,
  .qg-left-sidebar .qg-history-list {
    flex-basis: min(88vw, 340px);
  }

  .qg-tabs {
    margin-bottom: 12px;
    padding: 6px;
  }

  .qg-panel-title {
    font-size: 15px;
    margin: 0 0 8px;
  }

  .qg-section {
    margin-bottom: 8px;
  }

  .qg-label {
    font-size: 12px;
  }

  .qg-input,
  .qg-textarea {
    padding: 7px 10px;
    font-size: 13px;
  }

  .qg-dropzone {
    padding: 12px;
  }

  .qg-dropzone-icon {
    width: 32px;
    height: 32px;
    line-height: 32px;
    font-size: 20px;
  }

  .qg-generate-btn {
    padding: 10px 14px;
    font-size: 14px;
  }

  .qg-question-stem {
    font-size: 13px;
  }

  .qg-answer-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }

  .qg-answer-card {
    max-height: 40vh;
    border-radius: 14px;
    padding: 0 10px 10px;
  }
}

.qg-answer-grid button.done {
  background: linear-gradient(135deg, rgba(31, 188, 188, 0.12), rgba(31, 188, 188, 0.08));
  border-color: rgba(31, 188, 188, 0.25);
  color: #2563eb;
}

.qg-answer-grid button.ok {
  background: linear-gradient(135deg, rgba(31, 188, 188, 0.15), rgba(31, 188, 188, 0.1));
  border-color: rgba(31, 188, 188, 0.4);
  color: #1fbcbc;
}

.qg-answer-grid button.wrong {
  background: linear-gradient(135deg, rgba(214, 87, 69, 0.2), rgba(214, 87, 69, 0.1));
  border-color: rgba(214, 87, 69, 0.55);
  color: #b63b2b;
}

.qg-score-banner {
  display: grid;
  gap: 10px;
}

.qg-score-banner strong {
  display: block;
  color: #1fbcbc;
  font-size: 24px;
}

.qg-history-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.qg-history-tabs button {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  padding: 7px 10px;
  border: 1px solid rgba(31, 188, 188, 0.15);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.85);
  color: #64748b;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  justify-content: center;
}

.qg-history-tabs button.active {
  background: rgba(31, 188, 188, 0.1);
  border-color: rgba(31, 188, 188, 0.3);
  color: #1fbcbc;
}

.qg-history-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: rgba(31, 188, 188, 0.1);
  font-size: 11px;
  font-weight: 700;
  color: #2563eb;
}

.qg-history-tabs button.active .qg-history-badge {
  background: rgba(31, 188, 188, 0.18);
}

.qg-history-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.qg-history-empty {
  text-align: center;
  color: #8fa3a0;
  padding: 30px 12px;
  font-size: 13px;
}

.qg-history-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  border: 1px solid rgba(31, 188, 188, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.75);
  cursor: pointer;
  transition: all 0.2s ease;
  color: #334155;
}

.qg-history-item:hover {
  border-color: rgba(31, 188, 188, 0.2);
  background: rgba(255, 255, 255, 0.95);
}

.qg-history-item.active {
  border-color: #1fbcbc;
  background: rgba(31, 188, 188, 0.06);
}

.qg-history-item strong {
  display: block;
  font-size: 13px;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}

.qg-history-item span {
  display: block;
  font-size: 12px;
  color: #717b83;
}

.qg-history-item small {
  display: block;
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
}

.qg-history-detail {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.qg-history-detail .qg-print-title {
  display: none;
}

.qg-history-empty-detail {
  flex: 1;
  display: grid;
  place-items: center;
  color: #94a3b8;
  font-size: 14px;
}

.qg-detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  flex-shrink: 0;
}

.qg-detail-header h3 {
  margin: 0;
  font-size: 18px;
  color: #1e293b;
}

.qg-detail-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: #717b83;
}

.qg-detail-sub strong {
  color: #1fbcbc;
  font-size: 16px;
}

.qg-detail-score-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.qg-score-bar-track {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: rgba(31, 188, 188, 0.1);
  overflow: hidden;
}

.qg-score-bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s ease;
}

.qg-score-bar-fill.level-great {
  background: linear-gradient(90deg, #1fbcbc, #1fbcbc);
}

.qg-score-bar-fill.level-good {
  background: linear-gradient(90deg, #1fbcbc, #1fbcbc);
}

.qg-score-bar-fill.level-low {
  background: linear-gradient(90deg, #e87060, #c84d3c);
}

.qg-score-bar-pct {
  font-size: 14px;
  font-weight: 800;
  color: #2563eb;
  min-width: 36px;
  text-align: right;
}

@media print {
  .qg-history-detail .qg-print-title {
    display: block;
  }
}

@media print {
  body * {
    visibility: hidden;
  }

  .qg-history-print,
  .qg-history-print * {
    visibility: visible;
  }

  .qg-history-print {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    padding: 24px;
    background: var(--surface, rgba(255, 255, 255, 0.98));
  }

  .qg-history-print h1 {
    display: block;
  }

  .no-print {
    display: none !important;
  }
}

/* ===== 閽栧嫬鎬ラ惌銉ㄧ槕閻愬綊娼伴弶?===== */

.qg-weak-panel {
  margin-top: 14px;
  padding: 16px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(255, 248, 235, 0.96), rgba(255, 255, 255, 0.96));
  border: 1px solid rgba(232, 165, 60, 0.25);
}

.qg-weak-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.qg-weak-icon {
  font-size: 18px;
  color: #d4860a;
}

.qg-weak-header strong {
  color: #8a5a00;
  font-size: 15px;
}

.qg-weak-count {
  margin-left: auto;
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(212, 134, 10, 0.12);
  color: #8a5a00;
  font-size: 12px;
  font-weight: 700;
}

.qg-weak-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.qg-weak-item {
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-weak-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.qg-weak-name {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.qg-weak-rate {
  font-size: 12px;
  font-weight: 700;
  color: #2563eb;
}

.qg-weak-rate.qg-rate-warn {
  color: #c78a00;
}

.qg-weak-rate.qg-rate-bad {
  color: #c84d3c;
}

.qg-weak-bar-track {
  height: 5px;
  border-radius: 999px;
  background: rgba(31, 188, 188, 0.1);
  overflow: hidden;
  margin-bottom: 4px;
}

.qg-weak-bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s ease;
}

.qg-weak-bar-fill.qg-bar-ok {
  background: linear-gradient(90deg, #1fbcbc, #1fbcbc);
}

.qg-weak-bar-fill.qg-bar-warn {
  background: linear-gradient(90deg, #e8a520, #c78a00);
}

.qg-weak-bar-fill.qg-bar-bad {
  background: linear-gradient(90deg, #e87060, #c84d3c);
}

.qg-weak-hint {
  font-size: 11px;
  color: #94a3b8;
}

.qg-weak-suggest {
  margin: 0;
  font-size: 12px;
  color: #717b83;
  line-height: 1.6;
  padding: 8px 10px;
  border-radius: 6px;
  background: rgba(31, 188, 188, 0.04);
  border: 1px dashed rgba(31, 188, 188, 0.15);
}

@media (max-width: 900px), (orientation: portrait) {
  .qg-page {
    height: calc(100vh - 58px) !important;
    min-height: 0 !important;
    overflow-y: auto !important;
    -webkit-overflow-scrolling: touch;
    padding: 10px 12px !important;
  }

  .qg-main-layout,
  .qg-main-layout.layout-generate,
  .qg-main-layout.layout-exam,
  .qg-main-layout.layout-history {
    display: grid !important;
    grid-template-columns: minmax(0, 1fr) !important;
    grid-template-rows: minmax(88px, 20vh) minmax(0, 1fr) !important;
    height: 100% !important;
    min-height: 0 !important;
    gap: 12px !important;
  }

  .qg-left-sidebar {
    grid-column: 1 / -1 !important;
    grid-row: 1 !important;
    height: 100% !important;
    max-height: 20vh !important;
    min-height: 88px !important;
    overflow: hidden !important;
    position: relative;
    z-index: 60;
  }

  .qg-left-sidebar.is-expanded {
    position: fixed !important;
    left: 10px !important;
    right: 10px !important;
    top: 68px !important;
    bottom: 10px !important;
    z-index: 4500 !important;
    height: auto !important;
    max-height: none !important;
    min-height: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    overflow: hidden !important;
    box-shadow: 0 18px 46px rgba(4, 18, 28, 0.22) !important;
  }

  .qg-mobile-config-toggle {
    display: flex !important;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex: 0 0 auto;
    width: 100%;
    padding: 8px 10px;
    margin: 0 0 8px;
    border: 1px solid rgba(31, 188, 188, 0.2);
    border-radius: 6px;
    background: rgba(31, 188, 188, 0.06);
    color: #2563eb;
    font-size: 14px;
    font-weight: 800;
    cursor: pointer;
  }

  .qg-mobile-config-count {
    font-size: 12px;
    color: #64748b;
    font-weight: 700;
  }

  .qg-result,
  .qg-exam-main,
  .qg-history-main,
  .qg-history-detail {
    grid-column: 1 / -1 !important;
    grid-row: 2 !important;
    min-height: 0 !important;
    overflow-y: auto !important;
    -webkit-overflow-scrolling: touch;
  }

  .qg-sidebar {
    display: none !important;
  }

  .qg-left-sidebar .qg-tabs {
    flex: 0 0 auto;
    margin-bottom: 8px !important;
  }

  .qg-left-sidebar:not(.is-expanded) .qg-sidebar-scroll {
    display: none !important;
  }

  .qg-left-sidebar.is-expanded .qg-sidebar-scroll {
    display: block !important;
    flex: 1 1 auto !important;
    min-height: 0 !important;
    max-height: none !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
    -webkit-overflow-scrolling: touch;
    touch-action: pan-y;
    padding: 4px 2px 12px !important;
  }

  .qg-left-sidebar.is-expanded .qg-panel-title,
  .qg-left-sidebar.is-expanded .qg-section,
  .qg-left-sidebar.is-expanded .qg-row,
  .qg-left-sidebar.is-expanded .qg-generate-btn,
  .qg-left-sidebar.is-expanded > .qg-sidebar-scroll > .qg-error,
  .qg-left-sidebar.is-expanded .qg-muted,
  .qg-left-sidebar.is-expanded .qg-sheet-item,
  .qg-left-sidebar.is-expanded .qg-history-tabs,
  .qg-left-sidebar.is-expanded .qg-history-list {
    width: 100% !important;
    max-width: none !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
  }

  .qg-left-sidebar.is-expanded .qg-panel-title {
    display: block !important;
    margin: 8px 0 12px !important;
  }

  .qg-left-sidebar.is-expanded .qg-row {
    display: flex !important;
    flex-direction: column !important;
    gap: 0 !important;
  }

  .qg-left-sidebar.is-expanded .qg-dropzone {
    min-height: 132px;
  }

  .qg-left-sidebar.is-expanded .qg-type-row {
    align-items: flex-start;
  }

  .qg-answer-card {
    z-index: 4700 !important;
  }

  .qg-card-handle-actions {
    pointer-events: auto !important;
    z-index: 12 !important;
  }

  .qg-card-toggle-btn {
    width: 38px !important;
    height: 38px !important;
    min-width: 38px !important;
    font-size: 18px !important;
    position: relative;
    z-index: 13;
    pointer-events: auto !important;
  }
}

/* ===== 鐢诲儚閫夋嫨鍣?===== */
.qg-profile-inline-section {
  padding: 8px 10px;
  background: linear-gradient(135deg, rgba(31, 188, 188, 0.04), rgba(31, 188, 188, 0.02));
  border: 1px solid rgba(31, 188, 188, 0.1);
  border-radius: 8px;
  margin-bottom: 16px;
}

.qg-profile-inline-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.qg-profile-select-wrap {
  flex: 1;
  min-width: 0;
}

.qg-profile-select {
  width: 100%;
  padding: 5px 8px;
  border: 1px solid rgba(31, 188, 188, 0.25);
  border-radius: 5px;
  background: var(--surface, rgba(255, 255, 255, 0.98));
  font-size: 12px;
  color: #334155;
  cursor: pointer;
  appearance: auto;
}

.qg-profile-select:focus {
  outline: none;
  border-color: rgba(31, 188, 188, 0.5);
  box-shadow: 0 0 0 2px rgba(31, 188, 188, 0.1);
}

.qg-profile-clear-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: 1px solid rgba(231, 76, 60, 0.3);
  border-radius: 4px;
  background: none;
  color: #e74c3c;
  font-size: 14px;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.15s;
}

.qg-profile-clear-btn:hover {
  background: rgba(231, 76, 60, 0.08);
  border-color: rgba(231, 76, 60, 0.5);
}

.qg-profile-inline-status {
  display: flex;
  align-items: center;
  gap: 4px;
  margin: 6px 0 0;
  font-size: 12px;
  color: #1fbcbc;
  line-height: 1.2;
  padding: 4px 8px;
  background: rgba(31, 188, 188, 0.06);
  border-radius: 6px;
  font-weight: 600;
}

.qg-profile-inline-clear {
  background: none;
  border: none;
  color: #999;
  font-size: 11px;
  cursor: pointer;
  padding: 0 2px;
}

.qg-profile-inline-clear:hover {
  color: #e74c3c;
}

.qg-profile-preview-compact {
  flex-direction: row;
  gap: 6px;
  flex-wrap: wrap;
  padding: 4px 0 0;
}

.qg-profile-dropdown-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.qg-profile-dropdown-label {
  font-size: 13px;
  color: #64748b;
  font-weight: 600;
  white-space: nowrap;
}

.qg-profile-dropdown {
  flex: 1;
  min-width: 0;
  padding: 6px 10px;
  border: 1px solid rgba(31, 188, 188, 0.2);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.88);
  font-size: 13px;
  color: #334155;
  outline: none;
  transition: border-color 0.2s;
}

.qg-profile-dropdown:focus {
  border-color: rgba(31, 188, 188, 0.45);
}

.qg-profile-goto-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: 1px solid rgba(37, 99, 235, 0.3);
  border-radius: 4px;
  background: rgba(37, 99, 235, 0.06);
  color: #2563eb;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  flex-shrink: 0;
  transition: all 0.15s;
}

.qg-profile-goto-link:hover {
  background: rgba(37, 99, 235, 0.12);
  border-color: rgba(37, 99, 235, 0.5);
}

.qg-profile-preview {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 10px;
  background: rgba(31, 188, 188, 0.04);
  border-radius: 6px;
  border: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-profile-info {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.qg-profile-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(31, 188, 188, 0.08);
  font-size: 12px;
  color: #1fbcbc;
}

/* ===== 钖勫急鐐归厤缃?===== */
.qg-import-btn-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 0;
}

/* ===== 閽栧嫬鎬ラ惌銉ㄧ槕閻愯鐖ｇ粵鎯у隘 ===== */
.qg-weak-tags-area {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.qg-weak-tags-label {
  font-size: 13px;
  color: #64748b;
  font-weight: 600;
}

.qg-weak-tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  padding: 8px;
  border: 1px solid rgba(31, 188, 188, 0.15);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.75);
  min-height: 38px;
}

.qg-weak-tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 4px;
  background: rgba(31, 188, 188, 0.1);
  border: 1px solid rgba(31, 188, 188, 0.2);
  font-size: 12px;
  color: #1fbcbc;
  font-weight: 600;
  line-height: 1.4;
}

.qg-weak-tag-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border: none;
  border-radius: 3px;
  background: rgba(220, 53, 69, 0.1);
  color: #dc3545;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s;
  line-height: 1;
}

.qg-weak-tag-remove:hover {
  background: rgba(220, 53, 69, 0.25);
}

.qg-weak-tag-input-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  min-width: 120px;
}

.qg-weak-tag-input {
  flex: 1;
  min-width: 80px;
  padding: 3px 6px;
  border: none;
  background: transparent;
  font-size: 12px;
  color: #334155;
  outline: none;
}

.qg-weak-tag-input::placeholder {
  color: #94a3b8;
}

.qg-weak-tag-add-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid rgba(31, 188, 188, 0.25);
  border-radius: 4px;
  background: rgba(31, 188, 188, 0.06);
  color: #1fbcbc;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s;
}

.qg-weak-tag-add-btn:hover {
  background: rgba(31, 188, 188, 0.15);
}

.qg-weak-tags-hint {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 6px;
  display: block;
}

.qg-weak-tags-from-profile {
  color: #1fbcbc;
  background: rgba(31, 188, 188, 0.06);
  padding: 4px 8px;
  border-radius: 4px;
  border-left: 2px solid #1fbcbc;
  font-weight: 500;
}

/* ===== Config Collapse/Expand ===== */
.qg-config-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}

.qg-config-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid rgba(31, 188, 188, 0.2);
  border-radius: 8px;
  background: rgba(31, 188, 188, 0.05);
  color: #1fbcbc;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.qg-config-toggle-btn:hover {
  background: rgba(31, 188, 188, 0.12);
  border-color: rgba(31, 188, 188, 0.35);
}

.qg-config-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 12px;
  padding: 10px 14px;
  margin-bottom: 12px;
  background: linear-gradient(135deg, rgba(31, 188, 188, 0.05), rgba(31, 188, 188, 0.03));
  border: 1px solid rgba(31, 188, 188, 0.12);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
}

.qg-config-summary:hover {
  background: linear-gradient(135deg, rgba(31, 188, 188, 0.08), rgba(31, 188, 188, 0.05));
  border-color: rgba(31, 188, 188, 0.25);
}

.qg-summary-item {
  white-space: nowrap;
}

.qg-summary-label {
  font-weight: 600;
  color: #1fbcbc;
}

.qg-summary-badge {
  display: inline-block;
  padding: 1px 8px;
  background: rgba(31, 188, 188, 0.1);
  border-radius: 10px;
  font-size: 11px;
  color: #1fbcbc;
  font-weight: 500;
}

.qg-summary-hint {
  margin-left: auto;
  font-size: 11px;
  color: #94a3b8;
  white-space: nowrap;
}

.qg-config-body {
  animation: qg-config-slide 0.25s ease;
}

@keyframes qg-config-slide {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.qg-workbench {
  display: grid;
  grid-template-columns: minmax(260px, 292px) minmax(0, 1fr);
  gap: 20px;
  width: min(1720px, calc(100vw - 40px));
  min-height: calc(100vh - 96px);
  margin: 0 auto;
  padding: 24px 0 32px;
}

.qg-module-sidebar,
.qg-glass-card,
.qg-module-panel {
  border: 1px solid rgba(31, 188, 188, 0.12);
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.06);
  backdrop-filter: blur(18px);
}

.qg-module-sidebar {
  position: sticky;
  top: 88px;
  align-self: start;
  border-radius: 18px;
  padding: 18px;
}

.qg-module-brand {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 4px 4px 18px;
  border-bottom: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-module-badge {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: linear-gradient(135deg, #1fbcbc, #1fbcbc);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  font-weight: 800;
}

.qg-module-brand h1 {
  margin: 0;
  color: #1e293b;
  font-size: 18px;
}

.qg-module-brand p {
  margin: 4px 0 0;
  color: #717b83;
  font-size: 12px;
  line-height: 1.45;
}

.qg-module-nav {
  display: grid;
  gap: 8px;
  margin-top: 16px;
}

.qg-module-nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  height: 48px;
  padding: 0 14px;
  border: 0;
  border-radius: 14px;
  background: transparent;
  color: #475569;
  font-size: 15px;
  font-weight: 650;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, color 0.18s ease;
}

.qg-module-nav-item svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.qg-module-nav-item:hover {
  transform: translateX(2px);
  background: rgba(31, 188, 188, 0.08);
}

.qg-module-nav-item.active {
  background: linear-gradient(90deg, rgba(31, 188, 188, 0.15), rgba(31, 188, 188, 0.05));
  color: #1fbcbc;
}

.qg-module-nav-item.active::before {
  content: "";
  position: absolute;
  left: 0;
  top: 11px;
  width: 4px;
  height: 26px;
  border-radius: 999px;
  background: #1fbcbc;
}

.qg-module-tip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 18px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(31, 188, 188, 0.05);
  color: #64748b;
  font-size: 12px;
}

.qg-module-tip strong {
  color: #1fbcbc;
  font-size: 20px;
}

.qg-workspace {
  min-width: 0;
}

.qg-module-panel {
  min-height: calc(100vh - 120px);
  border-radius: 18px;
  padding: 22px;
}

.qg-module-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.qg-module-head h2 {
  margin: 0;
  color: #1e293b;
  font-size: 26px;
  line-height: 1.25;
}

.qg-module-head p {
  margin: 8px 0 0;
  color: #717b83;
}

.qg-stat-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.qg-stat-card {
  min-height: 112px;
  padding: 16px;
  border: 1px solid rgba(31, 188, 188, 0.1);
  border-radius: 16px;
  background: linear-gradient(145deg, var(--surface, rgba(255, 255, 255, 0.98)), rgba(248, 250, 252, 0.9));
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.04);
}

.qg-stat-card span,
.qg-field span,
.qg-tag-editor > span {
  color: #717b83;
  font-size: 13px;
}

.qg-stat-card strong {
  display: block;
  margin-top: 10px;
  color: #1e293b;
  font-size: 28px;
}

.qg-stat-card em {
  display: block;
  margin-top: 6px;
  color: #94a3b8;
  font-style: normal;
  font-size: 12px;
}

.qg-dashboard-grid,
.qg-upload-layout,
.qg-history-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.85fr);
  gap: 16px;
}

.qg-dashboard-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.qg-glass-card {
  border-radius: 16px;
  padding: 18px;
}

.qg-card-title {
  margin-bottom: 14px;
  color: #1e293b;
  font-weight: 750;
}

.qg-trend-bars {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 12px;
  align-items: end;
  height: 190px;
}

.qg-trend-item {
  display: grid;
  gap: 8px;
  justify-items: center;
  height: 100%;
  align-content: end;
}

.qg-trend-item span {
  width: 100%;
  min-height: 28px;
  border-radius: 999px 999px 8px 8px;
  background: linear-gradient(180deg, #1fbcbc, #1fbcbc);
}

.qg-trend-item small {
  color: #717b83;
}

.qg-progress-list,
.qg-activity-list,
.qg-record-list,
.qg-preview-dist,
.qg-material-list {
  display: grid;
  gap: 10px;
}

.qg-progress-row {
  display: grid;
  grid-template-columns: 78px minmax(0, 1fr) 44px;
  align-items: center;
  gap: 10px;
  color: #475569;
}

.qg-progress-row div {
  height: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: #e2e8f0;
}

.qg-progress-row i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #1fbcbc, #1fbcbc);
}

.qg-chip-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.qg-chip-cloud span,
.qg-filter-row button,
.qg-segment-wrap button {
  border: 1px solid rgba(31, 188, 188, 0.12);
  border-radius: 999px;
  background: rgba(31, 188, 188, 0.04);
  color: #475569;
}

.qg-chip-cloud span {
  padding: 9px 12px;
  font-weight: 650;
}

.qg-activity-list button,
.qg-record-list button {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 11px 12px;
  border: 1px solid rgba(31, 188, 188, 0.1);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.9);
  color: #475569;
  text-align: left;
  cursor: pointer;
}

.qg-activity-list span {
  color: #1fbcbc;
  font-weight: 750;
}

.qg-two-col,
.qg-config-layout,
.qg-exam-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
}

.qg-two-col {
  grid-template-columns: 330px minmax(0, 1fr);
}

.qg-profile-config,
.qg-config-main {
  display: grid;
  gap: 16px;
}

.qg-option-block {
  padding: 14px;
  border: 1px solid rgba(31, 188, 188, 0.1);
  border-radius: 15px;
  background: rgba(248, 250, 252, 0.85);
}

.qg-segment-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.qg-segment-wrap button,
.qg-filter-row button {
  padding: 8px 13px;
  cursor: pointer;
}

.qg-segment-wrap button.active,
.qg-filter-row button.active {
  background: #1fbcbc;
  color: var(--surface, rgba(255, 255, 255, 0.98));
  border-color: #1fbcbc;
}

.qg-field {
  display: grid;
  gap: 8px;
}

.qg-field input,
.qg-field select,
.qg-field textarea,
.qg-type-config-row input[type="number"] {
  width: 100%;
  border: 1px solid rgba(31, 188, 188, 0.15);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.95);
  color: #1e293b;
  padding: 10px 12px;
  outline: none;
}

.qg-field input:focus,
.qg-field select:focus,
.qg-field textarea:focus {
  border-color: #1fbcbc;
  box-shadow: 0 0 0 3px rgba(31, 188, 188, 0.1);
}

.qg-field.wide {
  grid-column: 1 / -1;
}

.qg-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.qg-tag-list button,
.qg-mini-add {
  border: 0;
  border-radius: 999px;
  background: rgba(31, 188, 188, 0.08);
  color: #1fbcbc;
  padding: 7px 10px;
  cursor: pointer;
}

.qg-tag-list input {
  min-width: 160px;
  flex: 1;
  border: 1px solid rgba(31, 188, 188, 0.15);
  border-radius: 999px;
  padding: 7px 11px;
}

.qg-primary-btn,
.qg-soft-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  border-radius: 13px;
  padding: 0 16px;
  font-weight: 750;
  text-decoration: none;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

.qg-primary-btn {
  border: 0;
  background: linear-gradient(135deg, #1fbcbc, #1fbcbc);
  color: var(--surface, rgba(255, 255, 255, 0.98));
  box-shadow: 0 10px 22px rgba(31, 188, 188, 0.2);
}

.qg-soft-btn {
  border: 1px solid rgba(31, 188, 188, 0.15);
  background: rgba(31, 188, 188, 0.04);
  color: #1fbcbc;
}

.qg-primary-btn:hover:not(:disabled),
.qg-soft-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.qg-primary-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.qg-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-top: 14px;
}

.qg-type-config-list {
  display: grid;
  gap: 10px;
}

.qg-type-config-row {
  display: grid;
  grid-template-columns: minmax(150px, 1fr) 74px 22px 82px 42px;
  gap: 10px;
  align-items: center;
  padding: 12px;
  border: 1px solid rgba(31, 188, 188, 0.1);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.9);
}

.qg-type-config-row.disabled {
  opacity: 0.62;
}

.qg-type-config-row label,
.qg-check-line,
.qg-switch-grid label {
  display: flex;
  gap: 9px;
  align-items: center;
  color: #334155;
  font-weight: 650;
}

.qg-type-config-row label span {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.qg-difficulty-grid,
.qg-switch-grid,
.qg-form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.qg-difficulty-grid label {
  display: grid;
  gap: 8px;
  padding: 12px;
  border-radius: 14px;
  background: rgba(31, 188, 188, 0.04);
}

.qg-switch-grid.stacked {
  grid-template-columns: 1fr;
}

.qg-preview-card {
  align-self: start;
  position: sticky;
  top: 88px;
}

.qg-preview-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.qg-preview-metrics div {
  padding: 12px;
  border-radius: 14px;
  background: rgba(31, 188, 188, 0.04);
}

.qg-preview-metrics span,
.qg-preview-dist span {
  display: block;
  color: #717b83;
  font-size: 12px;
}

.qg-preview-metrics strong {
  color: #1e293b;
  font-size: 22px;
}

.qg-preview-dist p,
.qg-material-list div,
.qg-history-row {
  display: grid;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border: 1px solid rgba(31, 188, 188, 0.1);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.92);
}

.qg-preview-dist p {
  grid-template-columns: 1fr auto;
}

.qg-soft-btn.full {
  width: 100%;
  margin-top: 12px;
}

.qg-result-mini {
  display: grid;
  gap: 6px;
  margin-top: 14px;
  padding: 12px;
  border-radius: 14px;
  background: rgba(31, 188, 188, 0.04);
  color: #475569;
}

.qg-upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 220px;
  height: 220px;
  box-sizing: border-box;
  padding: 22px 18px 16px;
  border: 1.5px dashed rgba(31, 188, 188, 0.35);
  border-radius: 18px;
  background: linear-gradient(145deg, #f8fafc, #f1f5f9);
  color: #475569;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.18s ease, transform 0.18s ease, background 0.18s ease;
}

.qg-upload-zone.has-files {
  justify-content: stretch;
  gap: 0;
  padding: 18px 14px 14px;
}

.qg-upload-zone.active,
.qg-upload-zone:hover {
  border-color: #1fbcbc;
  transform: translateY(-1px);
  background: rgba(31, 188, 188, 0.04);
}

.qg-upload-zone svg {
  width: 44px;
  height: 44px;
  fill: none;
  stroke: #1fbcbc;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.qg-upload-progress {
  height: 8px;
  margin: 14px 0;
  overflow: hidden;
  border-radius: 999px;
  background: #e2e8f0;
}

.qg-upload-progress i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #1fbcbc, #1fbcbc);
}

.qg-material-list div {
  grid-template-columns: minmax(0, 1fr) 54px 70px auto auto auto;
}

.qg-material-list button,
.qg-history-row button {
  border: 0;
  border-radius: 10px;
  background: rgba(31, 188, 188, 0.06);
  color: #1fbcbc;
  padding: 7px 9px;
  cursor: pointer;
}

.qg-history-row button {
  padding: 7px 0;
  font-size: 12px;
}

.qg-history-row.is-running {
  align-items: start;
  border-color: rgba(31, 188, 188, 0.2);
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
}

.qg-history-status-running {
  color: #1fbcbc;
  font-weight: 800;
}

.qg-history-status-running::before {
  content: '';
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 6px;
  border-radius: 50%;
  background: #1fbcbc;
  box-shadow: 0 0 0 4px rgba(31, 188, 188, 0.1);
  vertical-align: middle;
}

.qg-history-progress {
  grid-column: 1 / -1;
  display: grid;
  gap: 7px;
  min-width: 0;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.7);
  color: #475569;
  font-size: 12px;
  line-height: 1.5;
}

.qg-history-progress-bar {
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(31, 188, 188, 0.1);
}

.qg-history-progress-bar i {
  display: block;
  height: 100%;
  min-width: 8%;
  border-radius: inherit;
  background: linear-gradient(90deg, #1fbcbc 0%, #1fbcbc 100%);
  transition: width 0.35s ease;
}

.qg-history-row button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.qg-feature-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.qg-feature-grid button {
  min-height: 72px;
  border: 1px solid rgba(31, 188, 188, 0.12);
  border-radius: 15px;
  background: linear-gradient(145deg, var(--surface, rgba(255, 255, 255, 0.98)), rgba(248, 250, 252, 0.9));
  color: #475569;
  font-weight: 750;
  cursor: pointer;
}

.qg-exam-workbench {
  grid-template-columns: minmax(0, 1.1fr) minmax(420px, 1fr);
}

.qg-exam-setup {
  grid-row: span 2;
}

.qg-exam-status {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  color: #47685e;
}

.qg-lite-question,
.qg-history-preview {
  display: grid;
  gap: 9px;
  padding: 12px;
  border: 1px solid rgba(31, 188, 188, 0.1);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
}

.qg-lite-question strong,
.qg-history-preview strong {
  color: #1e293b;
  line-height: 1.55;
}

.qg-lite-question div {
  display: grid;
  gap: 7px;
}

.qg-lite-question label {
  display: flex;
  gap: 8px;
  color: #64748b;
}

.qg-empty-state {
  display: grid;
  place-items: center;
  min-height: 160px;
  border-radius: 16px;
  background: rgba(31, 188, 188, 0.04);
  color: #94a3b8;
  text-align: center;
}

.qg-filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.qg-history-table {
  display: grid;
  gap: 10px;
}

.qg-history-row {
  grid-template-columns: minmax(135px, 1.2fr) 76px minmax(88px, 0.8fr) 44px 88px;
  gap: 7px;
}

.qg-history-row strong,
.qg-record-list strong {
  color: #1e293b;
}

.qg-history-row span {
  justify-self: start;
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(31, 188, 188, 0.08);
  color: #1fbcbc;
  font-size: 12px;
  font-weight: 700;
}

.qg-history-side {
  align-self: start;
  position: sticky;
  top: 88px;
}

.qg-history-side h3 {
  margin: 0 0 8px;
  color: #1e293b;
}

.qg-history-preview {
  margin-top: 10px;
}

.qg-history-preview span,
.qg-history-preview em {
  color: #717b83;
  font-style: normal;
  line-height: 1.55;
}

@media (max-width: 1280px) {
  .qg-stat-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .qg-dashboard-grid,
  .qg-upload-layout,
  .qg-config-layout,
  .qg-exam-workbench,
  .qg-history-workbench,
  .qg-two-col {
    grid-template-columns: 1fr;
  }

  .qg-preview-card,
  .qg-history-side,
  .qg-module-sidebar {
    position: static;
  }
}

@media (max-width: 900px) {
  .qg-workbench {
    grid-template-columns: 1fr;
    width: min(100% - 24px, 760px);
    padding-top: 14px;
  }

  .qg-module-sidebar {
    padding: 14px;
  }

  .qg-module-nav {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .qg-module-nav-item {
    justify-content: center;
    height: 46px;
    padding: 0 8px;
  }

  .qg-module-nav-item span {
    font-size: 13px;
  }

  .qg-module-nav-item.active::before {
    display: none;
  }

  .qg-module-head,
  .qg-action-row {
    align-items: stretch;
    flex-direction: column;
  }

  .qg-stat-grid,
  .qg-dashboard-grid,
  .qg-difficulty-grid,
  .qg-switch-grid,
  .qg-form-grid,
  .qg-feature-grid {
    grid-template-columns: 1fr;
  }

  .qg-type-config-row,
  .qg-material-list div,
  .qg-history-row {
    grid-template-columns: 1fr;
  }
}

/* Lightweight question-generator workbench refinement */
.qg-workbench {
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 22px;
  width: min(1480px, calc(100vw - 56px));
  padding-top: 34px;
}

.qg-module-sidebar {
  border-color: rgba(31, 188, 188, 0.1);
  background: rgba(255, 255, 255, 0.75);
  box-shadow: 0 14px 34px rgba(0, 0, 0, 0.04);
}

.qg-module-brand {
  padding: 4px 2px 16px;
}

.qg-module-brand h1 {
  font-size: 19px;
}

.qg-module-brand p {
  max-width: 210px;
}

.qg-module-nav {
  gap: 4px;
}

.qg-module-nav-item {
  height: 46px;
  border-radius: 11px;
  font-size: 14px;
}

.qg-module-tip {
  display: grid;
  gap: 5px;
  background: transparent;
  border-top: 1px solid rgba(31, 188, 188, 0.1);
  border-radius: 0;
  padding: 16px 4px 0;
}

.qg-module-tip strong {
  color: #1fbcbc;
  font-size: 14px;
}

.qg-module-panel {
  max-width: 100%;
  min-height: calc(100vh - 138px);
  border: 1px solid rgba(31, 188, 188, 0.1);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 18px 46px rgba(0, 0, 0, 0.04);
  padding: 30px 34px;
}

.qg-module-head {
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-module-head h2 {
  font-size: 28px;
  font-weight: 760;
}

.qg-module-head p {
  color: #717b83;
  font-size: 15px;
}

.qg-glass-card {
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  padding: 0;
  backdrop-filter: none;
}

.qg-dashboard-grid,
.qg-upload-layout,
.qg-history-workbench,
.qg-config-layout,
.qg-exam-workbench,
.qg-two-col {
  gap: 26px;
}

.qg-dashboard-grid {
  grid-template-columns: minmax(0, 1.1fr) minmax(330px, 0.9fr);
  padding-top: 10px;
}

.qg-dashboard-grid > .qg-glass-card,
.qg-config-layout > .qg-glass-card,
.qg-config-layout > .qg-preview-card,
.qg-upload-layout > .qg-glass-card,
.qg-exam-workbench > .qg-glass-card,
.qg-history-workbench > .qg-glass-card,
.qg-history-workbench > .qg-history-side,
.qg-two-col > .qg-glass-card {
  padding-top: 4px;
}

.qg-dashboard-grid > .qg-glass-card:nth-child(n + 3) {
  padding-top: 22px;
  border-top: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-stat-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  margin: 2px 0 24px;
  border-bottom: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-stat-card {
  min-height: auto;
  padding: 4px 28px 22px 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.qg-stat-card + .qg-stat-card {
  padding-left: 24px;
  border-left: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-stat-card strong {
  font-size: 32px;
}

.qg-card-title {
  margin-bottom: 16px;
  color: #1e293b;
  font-size: 17px;
}

.qg-trend-bars {
  height: 150px;
  padding-right: 10px;
}

.qg-trend-item span {
  max-width: 38px;
  background: linear-gradient(180deg, rgba(31, 188, 188, 0.7), rgba(31, 188, 188, 0.2));
}

.qg-progress-row {
  grid-template-columns: 82px minmax(0, 1fr) 44px;
}

.qg-chip-cloud span {
  border: 0;
  background: rgba(31, 188, 188, 0.06);
  padding: 7px 11px;
}

.qg-activity-list button,
.qg-record-list button,
.qg-preview-dist p,
.qg-material-list div,
.qg-history-row,
.qg-lite-question,
.qg-history-preview {
  border: 0;
  border-top: 1px solid rgba(31, 188, 188, 0.08);
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.qg-activity-list button,
.qg-record-list button {
  padding: 12px 0;
}

.qg-two-col {
  grid-template-columns: 280px minmax(0, 1fr);
}

.qg-option-block {
  padding: 0 0 18px;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.qg-option-block + .qg-option-block {
  padding-top: 2px;
}

.qg-segment-wrap button,
.qg-filter-row button {
  border: 0;
  background: rgba(31, 188, 188, 0.06);
  padding: 7px 13px;
}

.qg-segment-wrap button.active,
.qg-filter-row button.active {
  background: rgba(31, 188, 188, 0.12);
  color: #1fbcbc;
  box-shadow: inset 0 0 0 1px rgba(31, 188, 188, 0.2);
}

.qg-type-config-row {
  grid-template-columns: minmax(150px, 1fr) 72px 22px 78px 42px;
  border: 0;
  border-top: 1px solid rgba(31, 188, 188, 0.08);
  border-radius: 0;
  background: transparent;
  padding: 11px 0;
}

.qg-type-config-row:first-child {
  border-top: 0;
}

.qg-difficulty-grid label {
  border-radius: 0;
  background: transparent;
  padding: 6px 0;
}

.qg-switch-grid {
  padding-top: 6px;
  border-top: 1px solid rgba(31, 188, 188, 0.08);
}

.qg-form-grid {
  padding-top: 16px;
  border-top: 1px solid rgba(31, 188, 188, 0.08);
}

.qg-field input,
.qg-field select,
.qg-field textarea,
.qg-type-config-row input[type="number"] {
  border-color: rgba(31, 188, 188, 0.12);
  background: rgba(248, 250, 252, 0.85);
  box-shadow: none;
}

.qg-preview-card,
.qg-history-side {
  position: static;
  padding-left: 24px !important;
  border-left: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-preview-metrics {
  grid-template-columns: 1fr;
  gap: 0;
}

.qg-preview-metrics div {
  padding: 12px 0;
  border-radius: 0;
  background: transparent;
  border-bottom: 1px solid rgba(31, 188, 188, 0.08);
}

.qg-result-mini,
.qg-empty-state {
  background: rgba(31, 188, 188, 0.04);
  box-shadow: none;
}

.qg-upload-zone {
  min-height: 152px;
  border-color: rgba(31, 188, 188, 0.25);
  background: rgba(248, 250, 252, 0.7);
}

.qg-material-list div {
  grid-template-columns: minmax(0, 1fr) 52px 72px 44px 70px 44px;
  padding: 10px 0;
}

.qg-feature-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.qg-feature-grid button {
  min-height: 0;
  border: 0;
  border-radius: 999px;
  background: rgba(31, 188, 188, 0.06);
  color: #1fbcbc;
  padding: 8px 14px;
  font-weight: 680;
}

.qg-exam-workbench {
  grid-template-columns: minmax(0, 1fr) minmax(360px, 0.8fr);
}

.qg-exam-setup {
  grid-row: auto;
}

.qg-exam-paper-lite {
  padding-left: 24px !important;
  border-left: 1px solid rgba(31, 188, 188, 0.1);
}

.qg-history-workbench {
  grid-template-columns: minmax(0, 1fr) minmax(340px, 0.72fr);
}

.qg-history-row {
  grid-template-columns: minmax(135px, 1.2fr) 74px minmax(92px, 0.8fr) 44px 92px repeat(3, 42px);
  padding: 10px 0;
}

.qg-history-row span {
  background: rgba(31, 188, 188, 0.06);
}

.qg-material-list button,
.qg-history-row button {
  background: transparent;
  color: #1fbcbc;
  padding: 6px 0;
}

@media (max-width: 1280px) {
  .qg-workbench {
    width: min(1180px, calc(100vw - 32px));
  }

  .qg-dashboard-grid,
  .qg-upload-layout,
  .qg-config-layout,
  .qg-exam-workbench,
  .qg-history-workbench,
  .qg-two-col {
    grid-template-columns: 1fr;
  }

  .qg-preview-card,
  .qg-history-side,
  .qg-exam-paper-lite {
    padding-left: 0 !important;
    border-left: 0;
    padding-top: 22px !important;
    border-top: 1px solid rgba(31, 188, 188, 0.1);
  }
}

@media (max-width: 900px) {
  .qg-workbench {
    grid-template-columns: 1fr;
    width: min(100% - 24px, 760px);
    gap: 16px;
  }

  .qg-module-panel {
    padding: 24px 22px;
  }

  .qg-stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .qg-stat-card,
  .qg-stat-card + .qg-stat-card {
    padding: 10px 12px 16px 0;
    border-left: 0;
  }

  .qg-history-row,
  .qg-material-list div,
  .qg-type-config-row {
    grid-template-columns: 1fr;
  }
}

/* Strict three-rectangle layout: top nav + left function rail + right content panel */
.app-shell {
  background: #fff;
  height: 100vh;
  overflow: hidden;
}

.app-shell :global(.topbar) {
  box-shadow: none !important;
  border-bottom: 1px solid #e2e8f0;
}

.app-shell :global(.topbar::after) {
  left: 0 !important;
  right: 0 !important;
  height: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

:global(body:has(.qg-page) .site-record-footer) {
  display: none !important;
}

.qg-page {
  height: calc(100vh - 64px);
  padding: 0 !important;
  overflow: hidden;
  background: #fff;
}

.qg-page > *:not(.qg-exam-full-layout):not(.qg-exam-result-panel):not(.qg-exam-pre-panel) *,
.qg-page > *:not(.qg-exam-full-layout):not(.qg-exam-result-panel):not(.qg-exam-pre-panel) *::before,
.qg-page > *:not(.qg-exam-full-layout):not(.qg-exam-result-panel):not(.qg-exam-pre-panel) *::after {
  border-radius: 0 !important;
  box-shadow: none !important;
  backdrop-filter: none !important;
}

.qg-workbench {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 0 !important;
  width: 100% !important;
  height: 100%;
  min-height: 0;
  margin: 0 !important;
  padding: 0 !important;
  background: #fff;
}

.qg-module-sidebar {
  position: relative !important;
  top: auto !important;
  height: 100%;
  align-self: stretch;
  overflow: auto;
  border: 0 !important;
  border-right: 1px solid #e2e8f0 !important;
  background: #f8fafc !important;
  padding: 22px 18px !important;
}

.qg-module-brand {
  border-bottom: 1px solid #e2e8f0 !important;
  padding: 0 0 18px !important;
}

.qg-module-brand h1 {
  font-size: 19px;
  color: #1e293b;
}

.qg-module-brand p {
  color: #64748b;
}

.qg-module-nav {
  gap: 0 !important;
  margin-top: 18px;
}

.qg-module-nav-item {
  height: 48px;
  padding: 0 12px !important;
  border: 0 !important;
  border-bottom: 1px solid #f1f5f9 !important;
  background: transparent !important;
  color: #475569;
  transform: none !important;
}

.qg-module-nav-item:hover {
  background: #f1f5f9 !important;
}

.qg-module-nav-item.active {
  background: #f0fdf4 !important;
  color: #16a34a !important;
}

.qg-module-nav-item.active::before {
  left: 0;
  top: 0;
  width: 3px;
  height: 100%;
  background: #16a34a;
}

.qg-module-tip {
  margin-top: 18px !important;
  padding: 14px 4px 0 !important;
  border-top: 1px solid #e2e8f0 !important;
  background: transparent !important;
}

.qg-workspace {
  min-width: 0;
  height: 100%;
  overflow: auto;
  background: #fff;
}

.qg-module-panel {
  min-height: 100%;
  border: 0 !important;
  background: #fff !important;
  padding: 30px 36px !important;
}

.qg-module-head {
  margin: 0 0 20px !important;
  padding-bottom: 18px !important;
  border-bottom: 1px solid #e2e8f0 !important;
}

.qg-module-head h2 {
  margin: 0;
  font-size: 26px;
  color: #1e293b;
}

.qg-module-head p {
  margin-top: 8px;
  color: #6e8a81;
}

.qg-glass-card,
.qg-stat-card,
.qg-option-block,
.qg-result-mini,
.qg-empty-state,
.qg-lite-question,
.qg-history-preview {
  border: 0 !important;
  background: transparent !important;
}

.qg-dashboard-grid,
.qg-upload-layout,
.qg-history-workbench,
.qg-config-layout,
.qg-exam-workbench,
.qg-two-col {
  gap: 28px !important;
}

.qg-stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0 !important;
  margin: 0 0 24px !important;
  padding-bottom: 20px;
  border-bottom: 1px solid #e2e8f0 !important;
}

.qg-stat-card {
  min-height: auto !important;
  padding: 0 24px 0 0 !important;
}

.qg-stat-card + .qg-stat-card {
  padding-left: 24px !important;
  border-left: 1px solid #e2e8f0 !important;
}

.qg-stat-card strong {
  font-size: 30px;
  color: #1e293b;
}

.qg-dashboard-grid {
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
}

.qg-card-title {
  margin: 0 0 14px !important;
  color: #1e293b;
  font-size: 16px;
}

.qg-dashboard-grid > .qg-glass-card,
.qg-upload-layout > .qg-glass-card,
.qg-exam-workbench > .qg-glass-card,
.qg-history-workbench > .qg-glass-card,
.qg-two-col > .qg-glass-card,
.qg-config-layout > .qg-glass-card,
.qg-config-layout > .qg-preview-card {
  padding: 0 !important;
}

.qg-dashboard-grid > .qg-glass-card:nth-child(n + 3),
.qg-preview-card,
.qg-history-side,
.qg-exam-paper-lite {
  border-top: 1px solid #e2e8f0 !important;
  padding-top: 20px !important;
}

.qg-preview-card,
.qg-history-side,
.qg-exam-paper-lite {
  border-left: 1px solid #e2e8f0 !important;
  padding-left: 26px !important;
}

.qg-type-config-row,
.qg-preview-dist p,
.qg-material-list div,
.qg-history-row,
.qg-activity-list button,
.qg-record-list button,
.qg-lite-question,
.qg-history-preview {
  border: 0 !important;
  border-top: 1px solid #e2e8f0 !important;
  background: transparent !important;
}

.qg-type-config-row,
.qg-material-list div,
.qg-history-row {
  padding: 10px 0 !important;
}

.qg-segment-wrap button,
.qg-filter-row button,
.qg-feature-grid button,
.qg-tag-list button,
.qg-mini-add,
.qg-material-list button,
.qg-history-row button {
  border: 0 !important;
  background: transparent !important;
  color: #64748b !important;
}

.qg-segment-wrap button.active,
.qg-filter-row button.active,
.qg-feature-grid button:hover {
  background: #f1f5f9 !important;
}

.qg-primary-btn,
.qg-soft-btn {
  border-radius: 0 !important;
  box-shadow: none !important;
}

.qg-soft-btn {
  border: 1px solid #e2e8f0 !important;
  background: #fff !important;
}

.qg-primary-btn {
  background: #1e293b !important;
}

.qg-config-goto-btn {
  display: inline-grid !important;
  place-items: center !important;
  width: 52px !important;
  height: 52px !important;
  min-height: 52px;
  border-radius: 999px !important;
  padding: 0 !important;
  background: #1e293b !important;
  border: 1px solid #1e293b !important;
  color: #fff !important;
}

.qg-config-goto-btn svg {
  width: 25px;
  height: 25px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.qg-page.qg-page .qg-config-goto-btn,
.qg-page.qg-page .qg-lock-ratio-btn {
  border-radius: 999px !important;
}

.qg-page.qg-page .qg-config-summary-icon {
  border-radius: 16px !important;
}

.qg-generate-sheet-btn {
  min-height: 46px !important;
  border-radius: 999px !important;
  padding: 0 26px !important;
  background: #1e293b !important;
  border: 1px solid #1e293b !important;
  color: #fff !important;
  font-weight: 800 !important;
}

.qg-field input,
.qg-field select,
.qg-field textarea,
.qg-type-config-row input[type="number"] {
  border: 1px solid #e2e8f0 !important;
  background: #fff !important;
}

.qg-upload-zone {
  min-height: 142px;
  border: 1px dashed #cbd5e1 !important;
  background: #f8fafc !important;
}

.qg-upload-zone:hover,
.qg-upload-zone.active {
  background: #f1f5f9 !important;
}

.qg-history-workbench {
  grid-template-columns: minmax(0, 1fr) minmax(330px, 0.7fr);
}

.qg-history-row {
  grid-template-columns: minmax(140px, 1.2fr) 78px minmax(94px, 0.8fr) 46px 94px repeat(3, 42px);
}

.qg-history-row span,
.qg-chip-cloud span {
  background: #f1f5f9 !important;
}

@media (max-width: 900px) {
  .qg-page {
    height: calc(100vh - 64px);
  }

  .qg-workbench {
    grid-template-columns: 1fr !important;
    grid-template-rows: auto minmax(0, 1fr);
  }

  .qg-module-sidebar {
    height: auto;
    border-right: 0 !important;
    border-bottom: 1px solid #e2e8f0 !important;
    overflow: visible;
  }

  .qg-module-nav {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .qg-module-nav-item.active::before {
    display: none;
  }

  .qg-module-panel {
    padding: 24px 22px 96px !important;
  }

  .qg-stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .qg-stat-card + .qg-stat-card {
    border-left: 0 !important;
    padding-left: 0 !important;
  }

  .qg-dashboard-grid,
  .qg-upload-layout,
  .qg-history-workbench,
  .qg-config-layout,
  .qg-exam-workbench,
  .qg-two-col {
    grid-template-columns: 1fr !important;
  }

  .qg-preview-card,
  .qg-history-side,
  .qg-exam-paper-lite {
    border-left: 0 !important;
    padding-left: 0 !important;
  }

  .qg-history-row,
  .qg-material-list div,
  .qg-type-config-row {
    grid-template-columns: 1fr !important;
  }
}

/* Dashboard metric cards requested by user */
.qg-stat-grid {
  gap: 16px !important;
  border-bottom: 0 !important;
  padding-bottom: 8px !important;
}

.qg-stat-card,
.qg-stat-card + .qg-stat-card {
  display: grid !important;
  grid-template-columns: 54px minmax(0, 1fr);
  align-items: center;
  gap: 14px;
  min-height: 112px !important;
  padding: 18px 20px !important;
  border: 1px solid #e2e8f0 !important;
  border-left: 1px solid #e2e8f0 !important;
  border-radius: 18px !important;
  background: #fff !important;
}

.qg-stat-icon {
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  border-radius: 15px !important;
  background: #f1f5f9;
}

.qg-stat-icon svg {
  width: 28px;
  height: 28px;
  fill: none;
  stroke: rgba(255, 255, 255, 0.94);
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.qg-stat-copy {
  min-width: 0;
}

.qg-stat-copy span,
.qg-stat-copy strong,
.qg-stat-copy em {
  display: block;
}

.qg-stat-copy span {
  color: #4e7569;
  font-size: 13px;
}

.qg-stat-copy strong {
  margin-top: 6px;
  color: #113f34;
  font-size: 30px;
  line-height: 1.1;
}

.qg-stat-copy em {
  margin-top: 8px;
  color: #7e9990;
  font-style: normal;
  font-size: 12px;
}

.qg-dashboard-fill {
  margin-top: 26px;
  padding-top: 22px;
  border-top: 1px solid #e2e8f0;
}

.qg-suggestion-list {
  display: grid;
}

.qg-suggestion-row {
  display: grid;
  grid-template-columns: 140px minmax(0, 1fr) 94px;
  gap: 14px;
  align-items: center;
  min-height: 54px;
  border-top: 1px solid #e2e8f0;
}

.qg-suggestion-row:first-child {
  border-top: 0;
}

.qg-suggestion-row strong {
  color: #1e293b;
}

.qg-suggestion-row span {
  color: #64748b;
  line-height: 1.5;
}

.qg-suggestion-row em {
  justify-self: end;
  color: #1e293b;
  font-style: normal;
  font-weight: 650;
}

/* Dashboard spacing cleanup */
.qg-module-head {
  border-bottom: 0 !important;
}

.qg-dashboard-grid {
  align-items: stretch;
}

.qg-dashboard-grid > .qg-glass-card {
  min-height: 270px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.qg-dashboard-grid > .qg-glass-card:nth-child(n + 3) {
  border-top: 0 !important;
  padding-top: 0 !important;
}

.qg-trend-bars {
  flex: 1;
}

.qg-progress-list,
.qg-activity-list,
.qg-chip-cloud {
  flex: 1;
}

.qg-chip-cloud {
  align-content: center;
}

.qg-dashboard-fill,
.qg-suggestion-list,
.qg-suggestion-row {
  display: none !important;
}

.qg-module-head .qg-soft-btn {
  border: 0 !important;
  border-radius: 16px !important;
  background: #1e293b !important;
  color: #fff !important;
  padding: 0 18px;
}

.qg-module-head .qg-soft-btn:hover {
  background: #334155 !important;
}

@media (max-width: 900px) {
  .qg-stat-grid {
    grid-template-columns: 1fr !important;
  }

  .qg-suggestion-row {
    grid-template-columns: 1fr;
    gap: 4px;
    padding: 10px 0;
  }

  .qg-suggestion-row em {
    justify-self: start;
  }
}

/* Dashboard lower area: exact 2x2 equal blocks */
.qg-dashboard-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  grid-template-rows: repeat(2, minmax(250px, 1fr)) !important;
  align-items: stretch !important;
  min-height: calc(100vh - 390px);
}

.qg-dashboard-grid > .qg-glass-card {
  min-height: 0 !important;
  height: 100%;
  padding: 18px 20px !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 18px !important;
  background: #fff !important;
}

.qg-chip-cloud {
  display: grid !important;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  align-content: center;
}

.qg-chip-cloud span {
  display: flex;
  align-items: center;
  min-height: 44px;
}

.qg-progress-list,
.qg-activity-list {
  justify-content: start;
}

.qg-card-note {
  margin: -6px 0 16px;
  color: #64748b;
  font-size: 13px;
  line-height: 1.55;
}

.qg-card-empty {
  display: grid;
  min-height: 88px;
  margin: 0;
  place-items: center;
  color: #94a3b8;
  font-size: 13px;
  text-align: center;
}

.qg-panel-foot {
  margin-top: auto;
  padding-top: 12px;
  color: #64748b;
  font-size: 13px;
  border-top: 1px solid #e2e8f0;
}

.qg-dashboard-grid .qg-trend-bars {
  height: auto;
  min-height: 120px;
}

.qg-dashboard-grid .qg-progress-list,
.qg-dashboard-grid .qg-activity-list,
.qg-dashboard-grid .qg-chip-cloud {
  margin-bottom: 14px;
}

@media (max-width: 900px) {
  .qg-dashboard-grid {
    grid-template-columns: 1fr !important;
    grid-template-rows: none !important;
    min-height: 0;
  }
}

/* Keep dashboard fully visible without scrolling on ordinary desktop viewports */
.qg-dashboard-panel {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  height: 100%;
  overflow: hidden;
  padding-top: 24px !important;
  padding-bottom: 18px !important;
}

.qg-dashboard-panel .qg-module-head {
  margin-bottom: 12px !important;
  padding-bottom: 0 !important;
}

.qg-dashboard-panel .qg-module-head h2 {
  font-size: 24px;
}

.qg-dashboard-panel .qg-stat-grid {
  margin-bottom: 14px !important;
  padding-bottom: 0 !important;
}

.qg-dashboard-panel .qg-stat-card,
.qg-dashboard-panel .qg-stat-card + .qg-stat-card {
  min-height: 86px !important;
  grid-template-columns: 46px minmax(0, 1fr);
  gap: 12px;
  padding: 12px 16px !important;
}

.qg-dashboard-panel .qg-stat-icon {
  width: 46px;
  height: 46px;
}

.qg-dashboard-panel .qg-stat-icon svg {
  width: 24px;
  height: 24px;
}

.qg-dashboard-panel .qg-stat-copy strong {
  margin-top: 4px;
  font-size: 26px;
}

.qg-dashboard-panel .qg-stat-copy em {
  margin-top: 5px;
}

.qg-dashboard-panel .qg-dashboard-grid {
  min-height: 0 !important;
  height: 100%;
  gap: 14px !important;
  grid-template-rows: repeat(2, minmax(0, 1fr)) !important;
}

.qg-dashboard-panel .qg-dashboard-grid > .qg-glass-card {
  min-height: 0 !important;
  height: 100%;
  overflow: hidden;
  padding: 13px 16px !important;
}

.qg-dashboard-panel .qg-card-title {
  margin-bottom: 7px !important;
  font-size: 15px;
}

.qg-dashboard-panel .qg-card-note {
  margin: 0 0 8px;
  font-size: 12px;
  line-height: 1.35;
}

.qg-dashboard-panel .qg-panel-foot {
  padding-top: 7px;
  font-size: 12px;
}

.qg-dashboard-panel .qg-trend-bars {
  min-height: 72px;
  height: auto;
}

.qg-dashboard-panel .qg-trend-item span {
  max-width: 38px;
}

.qg-dashboard-panel .qg-progress-list {
  gap: 6px;
}

.qg-dashboard-panel .qg-progress-row {
  grid-template-columns: 70px minmax(0, 1fr) 40px;
  gap: 8px;
}

.qg-dashboard-panel .qg-chip-cloud {
  gap: 8px;
}

.qg-dashboard-panel .qg-chip-cloud span {
  min-height: 34px;
  padding: 6px 10px;
}

.qg-dashboard-panel .qg-activity-list {
  gap: 0;
  margin-bottom: 6px;
}

.qg-dashboard-panel .qg-activity-list button {
  grid-template-columns: 42px minmax(0, 1fr) auto;
  padding: 7px 0;
}

.qg-dashboard-panel .qg-activity-list strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 900px) {
  .qg-dashboard-panel {
    display: block;
    height: auto;
    overflow: visible;
  }
}

/* Requirement pass: merge profile into config, generate sheet preview, larger exam area */
.qg-profile-merge-section {
  padding-bottom: 12px;
  border-bottom: 1px solid #e2e8f0;
}

.qg-merged-profile-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 8px;
  align-items: start;
}

.qg-text-link {
  justify-self: start;
  color: #64748b;
  text-decoration: none;
  font-weight: 700;
  padding: 0;
  font-size: 14px;
}

.qg-inline-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.qg-inline-tags span {
  padding: 5px 10px;
  background: #f1f5f9;
  color: #475569;
}

.qg-muted-line {
  margin: 10px 0 0;
  color: #94a3b8;
}

.qg-xiaozhi-task-loading {
  min-height: min(520px, calc(100vh - 190px));
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 32px;
  border: 1px solid #d7e5df;
  border-radius: 8px;
  background: #f7fbf9;
  color: #526963;
}

.qg-xiaozhi-task-loading > div {
  display: grid;
  gap: 6px;
}

.qg-xiaozhi-task-loading strong {
  color: #183c32;
  font-size: 16px;
}

.qg-xiaozhi-task-loading span:not(.qg-xiaozhi-task-spinner) {
  font-size: 13px;
}

.qg-xiaozhi-task-spinner {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  border: 3px solid #c9ded5;
  border-top-color: #138a6a;
  border-radius: 50%;
  animation: qg-xiaozhi-task-spin 0.8s linear infinite;
}

@keyframes qg-xiaozhi-task-spin {
  to { transform: rotate(360deg); }
}

.qg-upload-layout {
  grid-template-columns: 360px minmax(0, 1fr) !important;
  height: calc(100vh - 170px);
  min-height: 0;
}

.qg-upload-layout > .qg-glass-card {
  overflow: hidden;
}

.qg-preview-title {
  margin-top: 18px !important;
}

.qg-question-preview-stage {
  display: grid;
  place-items: center;
  min-height: 280px;
  height: calc(100vh - 520px);
  border: 1px solid #e2e8f0 !important;
  border-radius: 18px !important;
  background: #f8fafc !important;
  color: #64748b;
  text-align: center;
  padding: 20px;
  overflow: auto;
}

.qg-question-preview-stage svg {
  width: 54px;
  height: 54px;
  fill: none;
  stroke: #94a3b8;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.qg-question-preview-stage strong {
  color: #1e293b;
}

.qg-question-preview-stage.generating {
  place-items: stretch;
  text-align: left;
}

.qg-ai-log-head {
  color: #64748b;
  font-weight: 800;
  margin-bottom: 10px;
}

.qg-question-preview-stage pre {
  white-space: pre-wrap;
  margin: 0;
  color: #334155;
  line-height: 1.6;
}

.qg-file-icon-grid {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  max-width: 100%;
  flex: 1;
  margin-top: 0;
  padding: 6px 4px 12px;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-color: #cbd5e1 #f1f5f9;
  scrollbar-width: thin;
}

.qg-file-icon-grid::-webkit-scrollbar {
  height: 8px;
}

.qg-file-icon-grid::-webkit-scrollbar-track {
  background: #f1f5f9;
}

.qg-file-icon-grid::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 999px;
}

.qg-file-icon-card {
  position: relative;
  display: grid;
  flex: 0 0 104px;
  justify-items: center;
  align-content: center;
  gap: 5px;
  min-height: 92px;
  padding: 8px 7px;
  border: 1px solid #e2e8f0 !important;
  border-radius: 16px !important;
  background: #fff !important;
  color: #334155 !important;
  text-align: center;
}

.qg-file-icon-card.active {
  border-color: #cbd5e1 !important;
  background: #f8fafc !important;
}

.qg-file-badge {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: #1e293b;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
}

.qg-file-icon-card strong {
  max-width: 100%;
  overflow: hidden;
  color: #334155;
  font-size: 11px;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.qg-file-remove-dot {
  position: absolute;
  top: -7px;
  right: -7px;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  background: #fff;
  color: #64748b;
  font-size: 16px;
  font-weight: 800;
  line-height: 1;
}

.qg-sheet-preview-card {
  min-height: 0;
}

.qg-sheet-complete-banner {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 10px 20px 14px;
  padding: 16px 18px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #f8fafc;
  color: #475569;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.qg-sheet-complete-icon {
  display: grid;
  flex: 0 0 42px;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 999px;
  background: #1e293b;
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.qg-sheet-complete-icon svg {
  width: 24px;
  height: 24px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.qg-sheet-complete-banner strong {
  display: block;
  margin-bottom: 4px;
  color: #1e293b;
  font-size: 18px;
  font-weight: 900;
}

.qg-sheet-complete-banner em {
  display: block;
  color: #64748b;
  font-size: 13px;
  font-style: normal;
  font-weight: 650;
}

.qg-large-preview-stage {
  min-height: 560px;
  height: calc(100vh - 250px);
}

.qg-large-preview-stage.has-file {
  place-items: stretch;
}

.qg-large-preview-stage.has-questions {
  display: block;
  place-items: initial;
  text-align: left;
  overflow-y: auto !important;
  overflow-x: hidden;
  scrollbar-color: #cbd5e1 #f1f5f9;
  scrollbar-width: thin;
}

.qg-large-preview-stage.has-questions::-webkit-scrollbar {
  width: 8px;
}

.qg-large-preview-stage.has-questions::-webkit-scrollbar-track {
  background: #f1f5f9;
}

.qg-large-preview-stage.has-questions::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 999px;
}

.qg-file-preview-panel {
  display: grid;
  justify-items: start;
  align-content: start;
  gap: 10px;
  width: 100%;
  max-width: none;
  height: 100%;
  color: #64748b;
  text-align: left;
}

.qg-file-preview-icon {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  border-radius: 16px;
  background: #1e293b;
  color: #fff;
  font-size: 16px;
  font-weight: 850;
}

.qg-file-preview-panel strong {
  color: #1e293b;
  font-size: 18px;
}

.qg-file-preview-panel em {
  color: #64748b;
  font-style: normal;
  font-weight: 700;
}

.qg-file-preview-text {
  width: 100%;
  min-height: 260px;
  max-height: calc(100vh - 430px);
  overflow: auto;
  box-sizing: border-box;
  padding: 14px 16px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #334155;
  font-size: 14px;
  line-height: 1.75;
}

.qg-preview-question-row {
  width: 100%;
  display: grid;
  gap: 6px;
  padding: 12px 0;
  border-top: 1px solid #e2e8f0;
  text-align: left;
}

.qg-preview-question-row:first-child {
  border-top: 0;
}

.qg-preview-question-row span {
  color: #64748b;
}

.qg-exam-workbench {
  grid-template-columns: 1fr !important;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 12px !important;
  height: calc(100vh - 170px);
  min-height: 0;
}

.qg-exam-setup {
  grid-column: 1;
  grid-row: 1;
  overflow: visible;
  padding-bottom: 8px !important;
  border-bottom: 1px solid #e2e8f0 !important;
}

.qg-exam-paper-lite {
  grid-column: 1;
  grid-row: 2;
  height: 100%;
  overflow: auto;
  padding-left: 0 !important;
  border-left: 0 !important;
  border-top: 0 !important;
}

.qg-exam-workbench > .qg-glass-card:last-child {
  grid-column: 1;
  grid-row: 3;
  overflow: hidden;
  max-height: 86px;
}

.qg-exam-setup .qg-feature-grid {
  display: flex;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.qg-exam-setup .qg-form-grid {
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px;
  padding-top: 8px;
}

.qg-exam-setup .qg-field input {
  padding: 8px 9px;
}

.qg-exam-setup .qg-check-line {
  align-self: end;
  min-height: 36px;
  font-size: 13px;
}

.qg-exam-workbench > .qg-glass-card:last-child .qg-card-title {
  margin-bottom: 6px !important;
}

.qg-exam-workbench > .qg-glass-card:last-child .qg-record-list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.qg-exam-paper-lite .qg-lite-question {
  padding: 14px 0;
}

.qg-history-placeholder {
  display: grid;
  place-items: center;
  gap: 10px;
  min-height: 260px;
  text-align: center;
  color: #94a3b8;
}

.qg-history-placeholder svg {
  width: 62px;
  height: 62px;
  fill: none;
  stroke: #94a3b8;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.qg-history-placeholder strong {
  color: #1e293b;
}

.qg-config-layout {
  grid-template-columns: minmax(760px, 1fr) 280px !important;
  align-items: start;
  height: calc(100vh - 150px);
  min-height: 0;
  gap: 24px !important;
}

.qg-config-main {
  overflow: auto !important;
  padding-right: 10px !important;
}

.qg-config-main .qg-card-title {
  margin-bottom: 10px !important;
}

.qg-type-config-list {
  display: grid;
  grid-template-columns: 1fr;
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
}

.qg-type-config-row {
  grid-template-columns: minmax(180px, 1fr) 68px 28px 72px 50px !important;
  min-height: 40px !important;
  padding: 6px 0 !important;
  gap: 10px !important;
  border-top: 1px solid #f1f5f9 !important;
}

.qg-type-config-row input[type="number"] {
  width: 100% !important;
  height: 34px !important;
  padding: 6px 8px !important;
}

.qg-type-config-row em {
  white-space: nowrap;
  color: #64748b;
}

.qg-type-config-row label {
  min-width: 0;
  white-space: nowrap;
}

.qg-type-config-row label input {
  flex: 0 0 auto;
}

.qg-difficulty-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
  gap: 10px !important;
  margin-top: 10px !important;
}

.qg-difficulty-grid label,
.qg-switch-grid label {
  min-height: 36px !important;
  padding: 8px 10px !important;
}

.qg-switch-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
  gap: 10px !important;
  margin-top: 10px !important;
}

.qg-form-grid {
  gap: 10px 14px !important;
  margin-top: 10px !important;
}

.qg-form-grid textarea {
  min-height: 48px;
  max-height: 56px;
}

.qg-preview-card {
  border-left-color: #e2e8f0 !important;
  overflow: hidden !important;
  padding-left: 18px !important;
}

.qg-preview-dist {
  margin-top: 10px;
}

.qg-preview-dist p {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  padding: 8px 0 !important;
}

.qg-preview-dist em {
  color: #475569;
  font-style: normal;
  font-weight: 700;
  white-space: nowrap;
}

.qg-config-main .qg-type-config-row {
  min-height: 36px !important;
  padding: 4px 0 !important;
}

.qg-config-main .qg-type-config-row input[type="number"] {
  height: 30px !important;
  padding: 4px 8px !important;
}

.qg-config-main .qg-check-line {
  min-height: 32px;
  margin: 6px 0;
}

.qg-config-main .qg-difficulty-grid {
  margin-top: 6px !important;
}

.qg-config-main .qg-difficulty-grid label {
  grid-template-columns: minmax(0, 1fr);
  gap: 4px !important;
  padding: 2px 0 !important;
}

.qg-config-main .qg-difficulty-grid input[type="range"] {
  height: 16px;
}

.qg-config-main .qg-switch-grid {
  margin-top: 6px !important;
  padding-top: 6px !important;
}

.qg-config-main .qg-switch-grid label {
  min-height: 30px !important;
  padding: 4px 8px !important;
}

.qg-config-main .qg-form-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
  margin-top: 8px !important;
  padding-top: 8px !important;
}

.qg-config-main .qg-field.wide {
  grid-column: auto !important;
}

.qg-config-main .qg-field {
  gap: 4px;
}

.qg-config-main .qg-field input,
.qg-config-main .qg-field textarea {
  min-height: 34px;
  padding: 6px 9px !important;
}

.qg-config-main .qg-form-grid textarea {
  min-height: 34px;
  max-height: 36px;
  resize: none;
}

.qg-module-panel:has(.qg-config-layout) {
  height: 100% !important;
  min-height: 0 !important;
  padding-top: 22px !important;
  padding-bottom: 18px !important;
}

.qg-module-panel:has(.qg-config-layout) .qg-module-head {
  padding-bottom: 10px !important;
  margin-bottom: 0 !important;
}

.qg-module-panel:has(.qg-config-layout) .qg-module-head h2 {
  font-size: 26px;
}

.qg-module-panel:has(.qg-config-layout) .qg-config-layout {
  height: auto !important;
}

.qg-module-panel:has(.qg-config-dashboard) {
  height: 100% !important;
  min-height: 0 !important;
  padding-top: 22px !important;
  padding-bottom: 18px !important;
}

.qg-module-panel:has(.qg-config-dashboard) .qg-module-head {
  padding-bottom: 10px !important;
}

.qg-config-dashboard {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
  height: calc(100vh - 156px);
  min-height: 0;
  font-family: "Noto Serif SC", "PingFang SC", "Microsoft YaHei", serif;
}

.qg-config-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.qg-config-summary-card {
  position: relative;
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  column-gap: 14px;
  align-content: center;
  align-items: center;
  min-height: 76px;
  padding: 12px 18px;
  border: 1px solid #e2e8f0 !important;
  border-radius: 20px !important;
  background: #fff !important;
  overflow: hidden;
}

.qg-config-summary-card::before {
  content: none !important;
}

.qg-config-summary-icon {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 16px !important;
  background: #1e293b;
  color: #fff;
  grid-row: 1 / span 3;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
}

.qg-config-summary-icon svg {
  width: 25px;
  height: 25px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.qg-config-summary-card > span,
.qg-config-summary-card > strong,
.qg-config-summary-card > em {
  grid-column: 2;
}

.qg-config-summary-card span,
.qg-config-summary-card em {
  color: #64748b;
  font-size: 13px;
  font-style: normal;
}

.qg-config-summary-card strong {
  margin: 2px 0;
  color: #1e293b;
  font-size: 26px;
  line-height: 1.1;
}

.qg-config-board-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
  grid-template-rows: repeat(2, minmax(0, 1fr));
  gap: 10px;
  min-height: 0;
}

.qg-config-board-block {
  min-height: 0;
  overflow: hidden;
  padding: 12px 16px;
  border: 1px solid #e2e8f0 !important;
  border-radius: 20px !important;
  background: #fff !important;
}

.qg-config-board-block .qg-card-title {
  margin-bottom: 7px !important;
}

.qg-config-types-block {
  grid-row: auto !important;
}

.qg-type-config-list-board {
  border-top: 1px solid #e2e8f0;
  border-bottom: 0;
}

.qg-type-config-list-board .qg-type-config-row {
  grid-template-columns: minmax(138px, 1fr) 52px 22px 56px 46px !important;
  min-height: 25px !important;
  padding: 0 !important;
  font-size: 14px;
}

.qg-type-config-list-board .qg-type-config-row input[type="number"] {
  height: 23px !important;
  padding: 2px 6px !important;
}

.qg-type-config-list-board .qg-type-config-row label {
  gap: 7px;
}

.qg-type-config-list-board .qg-type-config-row label span {
  width: 8px;
  height: 8px;
}

.qg-difficulty-grid-board {
  grid-template-columns: 1fr !important;
  gap: 5px !important;
}

.qg-difficulty-title {
  display: flex !important;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.qg-lock-ratio-btn {
  display: inline-grid !important;
  place-items: center !important;
  width: 34px !important;
  height: 34px !important;
  padding: 0 !important;
  border-radius: 999px !important;
  border: 1px solid #e2e8f0 !important;
  background: #f8fafc !important;
  color: #64748b !important;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
}

.qg-lock-ratio-btn svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.qg-lock-ratio-btn.locked {
  background: #1e293b !important;
  color: #fff !important;
  border-color: transparent !important;
}

.qg-difficulty-grid-board label {
  display: grid;
  grid-template-columns: 34px 88px minmax(0, 1fr) 48px;
  align-items: center;
  gap: 7px !important;
  padding: 1px 0 !important;
}

.qg-difficulty-grid-board label.locked {
  opacity: 0.72;
}

.qg-difficulty-grid-board label.locked input[type="range"] {
  cursor: not-allowed;
  filter: grayscale(0.35);
}

.qg-config-auto-line {
  min-height: 24px;
  margin: 0 0 5px;
  font-size: 13px;
}

.qg-switch-grid-board {
  grid-template-columns: 1fr !important;
  gap: 6px !important;
  border-top: 0 !important;
  padding-top: 0 !important;
}

.qg-switch-grid-board label {
  min-height: 28px !important;
  padding: 4px 8px !important;
  background: #f8fafc;
}

.qg-config-dist-board {
  display: none;
  gap: 0;
  margin-top: 6px;
}

.qg-config-dist-board p {
  padding: 4px 0 !important;
}

.qg-form-grid-board {
  display: grid;
  grid-template-columns: 1fr !important;
  gap: 6px !important;
  margin-top: 0 !important;
  padding-top: 0 !important;
  border-top: 0 !important;
}

.qg-form-grid-board .qg-field {
  gap: 3px;
}

.qg-form-grid-board input,
.qg-form-grid-board textarea {
  min-height: 29px !important;
  padding: 4px 8px !important;
}

.qg-form-grid-board textarea {
  max-height: 32px;
  resize: none;
}

@media (max-width: 1100px) {
  .qg-upload-layout,
  .qg-exam-workbench {
    grid-template-columns: 1fr !important;
    height: auto;
  }

  .qg-exam-paper-lite,
  .qg-exam-setup,
  .qg-exam-workbench > .qg-glass-card:last-child {
    grid-column: auto;
    grid-row: auto;
    height: auto;
  }
}

.qg-exam-panel-compact {
  display: flex !important;
  flex-direction: column !important;
  min-height: 0 !important;
}

.qg-exam-workbench-compact {
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) !important;
  grid-template-rows: auto minmax(0, 1fr) !important;
  gap: 12px !important;
  min-height: 0 !important;
  height: calc(100vh - 245px) !important;
}

.qg-exam-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 46px;
}

.qg-exam-select-btn,
.qg-exam-start-btn {
  min-height: 44px !important;
  border-radius: 999px !important;
  padding: 0 26px !important;
  font-weight: 800 !important;
}

.qg-exam-select-btn {
  border: 1px solid #e2e8f0 !important;
  background: #fff !important;
  color: #64748b !important;
}

.qg-exam-start-btn {
  border: 1px solid #1e293b !important;
  background: #1e293b !important;
  color: #fff !important;
}

.qg-exam-paper-focus {
  display: flex !important;
  flex-direction: column !important;
  grid-column: 1 / -1 !important;
  grid-row: 2 / 3 !important;
  min-height: 0 !important;
  height: 100% !important;
  block-size: 100% !important;
  min-block-size: 100% !important;
  max-block-size: 100% !important;
  overflow-y: auto !important;
  align-self: stretch !important;
}

.qg-exam-paper-focus .qg-card-title,
.qg-exam-paper-focus .qg-exam-status,
.qg-exam-paper-focus .qg-lite-question {
  flex: 0 0 auto;
}

/* ===== Inline Exam Interface ===== */
.qg-exam-inline-panel {
  display: flex !important;
  flex-direction: column !important;
  min-height: 0 !important;
  overflow: visible !important;
}

/* 鑰冭瘯妯″紡涓嬪厑璁搁〉闈㈡粴鍔?*/
/* Allow page scrolling during exam */
.qg-page.exam-mode {
  overflow-y: auto !important;
  height: auto !important;
  min-height: calc(100vh - 64px);
  padding: 0 !important;
}

/* Override app-shell overflow for exam */
.app-shell:has(.qg-page.exam-mode) {
  height: auto !important;
  overflow: visible !important;
}

.qg-page.exam-mode .qg-workbench {
  display: block !important;
  width: 100% !important;
  max-width: 100% !important;
  min-height: calc(100vh - 120px);
  padding: 0 !important;
}

.qg-page.exam-mode .qg-module-sidebar {
  display: none !important;
}

.qg-page.exam-mode .qg-module-panel {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
  min-height: auto !important;
}

.qg-page.exam-mode .qg-workspace {
  height: calc(100vh - 64px) !important;
  overflow: hidden !important;
  display: flex !important;
  flex-direction: column !important;
}

.qg-page.exam-mode .qg-module-panel {
  height: 100% !important;
  overflow: hidden !important;
  padding: 0 !important;
}

.qg-exam-full-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f8fafc;
}

.qg-exam-full-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 28px;
  background: linear-gradient(135deg, #2f5d8a 0%, #3b7dd8 100%);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 12px 12px 0 0;
  flex-shrink: 0;
}

.qg-exam-full-title h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}

.qg-exam-full-title span {
  font-size: 13px;
  opacity: 0.8;
}

.qg-exam-full-timer {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255,255,255,0.18);
  padding: 6px 18px;
  border-radius: 20px;
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.qg-timer-mode-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.25);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 12px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.qg-timer-mode-btn:hover {
  background: rgba(255,255,255,0.25);
}

.qg-timer-value {
  font-variant-numeric: tabular-nums;
}

.qg-timer-target {
  font-size: 13px;
  opacity: 0.7;
  font-variant-numeric: tabular-nums;
}

.qg-card-timer-toggle {
  background: rgba(59,125,216,0.1);
  border: 1px solid rgba(59,125,216,0.2);
  color: #2f5d8a;
  border-radius: 10px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
  padding: 0;
  flex-shrink: 0;
}

.qg-card-timer-toggle:hover {
  background: rgba(59,125,216,0.2);
}

.qg-exam-full-finish-btn {
  padding: 10px 28px;
  background: rgba(255,255,255,0.15);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.qg-exam-full-finish-btn:hover {
  background: rgba(255,255,255,0.25);
}

.qg-exam-full-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 20px;
  padding: 20px 28px;
  background: #f8fafc;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.qg-exam-full-paper {
  flex: 1;
  min-width: 0;
  min-height: 0;
  padding-bottom: 40px;
}

.qg-exam-full-question {
  background: #fff;
  border-radius: 10px;
  padding: 20px 24px;
  margin-bottom: 16px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}

.qg-exam-q-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.qg-exam-q-num {
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, #3b7dd8 0%, #2f5d8a 100%);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}

.qg-exam-q-type {
  font-size: 12px;
  color: #3b7dd8;
  background: #e8f4ff;
  padding: 2px 10px;
  border-radius: 10px;
  font-weight: 500;
}

.qg-exam-q-score {
  font-size: 12px;
  color: #8a96a8;
  margin-left: auto;
}

.qg-exam-q-stem {
  margin: 0 0 14px;
  font-size: 15px;
  line-height: 1.7;
  color: #1a2b3d;
}

.qg-exam-q-options {
  display: grid;
  gap: 10px;
}

.qg-exam-q-option {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  transition: all 0.15s;
  font-size: 14px;
  color: #334155;
}

.qg-exam-q-option:hover {
  background: #f0f5fa;
  border-color: #c5d5e5;
}

.qg-exam-q-option.selected {
  background: #e8f4ff;
  border-color: #3b7dd8;
}

.qg-exam-q-option input {
  margin-top: 2px;
  accent-color: #3b7dd8;
}

.qg-exam-q-textarea {
  width: 100%;
  border: 1px solid #dce5ea;
  border-radius: 8px;
  padding: 12px;
  font-size: 14px;
  resize: vertical;
  font-family: inherit;
}

.qg-exam-q-textarea:focus {
  outline: none;
  border-color: #3b7dd8;
  box-shadow: 0 0 0 3px rgba(59, 125, 216, 0.1);
}

/* Floating answer card - compact and clean */
.qg-exam-floating-card {
  position: sticky;
  top: 80px;
  width: 200px;
  flex-shrink: 0;
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 14px;
  border: 1px solid rgba(59,125,216,0.12);
  box-shadow: 0 2px 16px rgba(0,0,0,0.06);
  padding: 14px;
  max-height: calc(100vh - 120px);
  overflow-y: auto;
  z-index: 100;
  align-self: flex-start;
}

.qg-exam-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.qg-exam-card-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a2b3d;
}

.qg-exam-card-progress {
  font-size: 12px;
  color: #3b7dd8;
  font-weight: 600;
  background: #e8f4ff;
  padding: 2px 8px;
  border-radius: 10px;
}

.qg-exam-card-progress-bar {
  height: 4px;
  background: var(--border, rgba(31, 188, 188, 0.1));
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 12px;
}

.qg-exam-card-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b7dd8 0%, #22c55e 100%);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.qg-exam-card-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
}

.qg-exam-card-btn {
  width: 100%;
  aspect-ratio: 1;
  border: 1.5px solid #d8e2ec;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  color: #6b8299;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.15s;
}

.qg-exam-card-btn:hover {
  border-color: #3b7dd8;
  color: #3b7dd8;
  background: #f0f7ff;
}

.qg-exam-card-btn.done {
  background: #3b7dd8;
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border-color: #3b7dd8;
}

.qg-exam-card-btn.current {
  box-shadow: 0 0 0 2px #22c55e;
  border-color: #22c55e;
  position: relative;
}

.qg-exam-card-btn.current::after {
  content: '';
  position: absolute;
  top: -3px;
  right: -3px;
  width: 8px;
  height: 8px;
  background: #22c55e;
  border-radius: 50%;
}

.qg-exam-card-btn.flagged {
  background: #fef3c7;
  border-color: #f59e0b;
  color: #92400e;
  position: relative;
}

.qg-exam-card-btn.flagged::before {
  content: '';
  position: absolute;
  top: -2px;
  left: -2px;
  width: 10px;
  height: 10px;
  background: #f59e0b;
  border-radius: 50%;
}

.qg-legend-dot.flagged-dot {
  background: #f59e0b;
}

.qg-exam-card-timer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: linear-gradient(135deg, #f0f7ff 0%, #e8f4ff 100%);
  border: 1px solid #d0e4f7;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 700;
  color: #2f5d8a;
  font-variant-numeric: tabular-nums;
  margin-bottom: 12px;
  text-align: center;
}

.qg-exam-card-legend {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #edf1f4;
}

.qg-legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #8a96a8;
}

.qg-legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.qg-legend-dot.current {
  background: #22c55e;
}

.qg-legend-dot.answered {
  background: #3b7dd8;
}

.qg-legend-dot.unanswered {
  background: #d8e2ec;
}

.qg-legend-dot.wrong-dot {
  background: #ef4444;
}

/* Result answer card */
.qg-exam-result-answer-card {
  margin-top: 20px;
  padding: 16px 20px;
  background: #f0f4f8;
  border-radius: 12px;
  border: 1px solid var(--border, rgba(31, 188, 188, 0.1));
}

.qg-exam-result-answer-card h3 {
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 600;
  color: #1a2b3d;
}

.qg-result-card-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.qg-result-card-btn {
  width: 36px;
  height: 36px;
  border: 2px solid #d8e2ec;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  color: #6b8299;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.qg-result-card-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.qg-result-card-btn.correct {
  background: #22c55e;
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border-color: #22c55e;
}

.qg-result-card-btn.wrong {
  background: #ef4444;
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border-color: #ef4444;
}

.qg-result-card-legend {
  display: flex;
  gap: 16px;
  justify-content: center;
  padding-top: 10px;
  border-top: 1px solid var(--border, rgba(31, 188, 188, 0.1));
}

/* Exam result panel */
.qg-exam-result-panel {
  display: flex;
  justify-content: center;
  padding: 32px 28px;
  overflow-y: auto;
  height: 100%;
}

/* Score ring */
.qg-exam-score-ring-wrap {
  position: relative;
  width: 120px;
  height: 120px;
  margin: 0 auto 24px;
}

.qg-exam-score-ring {
  width: 100%;
  height: 100%;
}

.qg-exam-score-ring-text {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.qg-exam-score-ring-pct {
  font-size: 28px;
  font-weight: 700;
  color: #1a2b3d;
  line-height: 1;
}

.qg-exam-score-ring-label {
  font-size: 12px;
  color: #8a96a8;
  margin-top: 4px;
}

/* Wrong question header */
.qg-exam-wrong-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.qg-exam-wrong-type {
  font-size: 11px;
  color: #3b7dd8;
  background: #e8f4ff;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.qg-exam-wrong-kp {
  font-size: 11px;
  color: #8b5cf6;
  background: #f3f0ff;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.qg-exam-result-card {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 16px;
  padding: 48px 40px;
  text-align: center;
  box-shadow: 0 4px 24px rgba(0,0,0,0.06);
  max-width: 700px;
  width: 100%;
}

.qg-exam-result-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
}

.qg-exam-result-icon.pass {
  background: #e6f7ed;
  color: #22c55e;
}

.qg-exam-result-icon.fail {
  background: #fef2f2;
  color: #ef4444;
}

.qg-exam-result-card h2 {
  margin: 0 0 20px;
  font-size: 24px;
  color: #1a2b3d;
}

.qg-exam-result-score {
  margin-bottom: 32px;
}

.qg-exam-score-big {
  font-size: 56px;
  font-weight: 700;
  color: #2f5d8a;
}

.qg-exam-score-total {
  font-size: 18px;
  color: #8a96a8;
  margin-left: 8px;
}

.qg-exam-result-stats {
  display: flex;
  justify-content: center;
  gap: 40px;
  margin-bottom: 36px;
  padding: 24px 0;
  border-top: 1px solid #edf1f4;
  border-bottom: 1px solid #edf1f4;
}

.qg-exam-stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.qg-exam-stat-item strong {
  font-size: 24px;
  color: #1a2b3d;
}

.qg-exam-stat-item span {
  font-size: 13px;
  color: #8a96a8;
}

.qg-exam-wrong-review {
  text-align: left;
  margin-bottom: 32px;
  max-height: 320px;
  overflow-y: auto;
  padding-right: 4px;
}

.qg-exam-wrong-review h3 {
  font-size: 16px;
  color: #1a2b3d;
  margin: 0 0 16px;
}

.qg-exam-wrong-item {
  padding: 14px 16px;
  background: #fafbfc;
  border-radius: 8px;
  margin-bottom: 10px;
  border-left: 3px solid #ef4444;
}

.qg-exam-wrong-stem {
  margin: 0 0 8px;
  font-size: 14px;
  color: #1a2b3d;
  line-height: 1.6;
}

.qg-exam-wrong-answer {
  margin: 0 0 4px;
  font-size: 13px;
  color: #5b7a94;
}

.qg-exam-wrong-answer .wrong {
  color: #ef4444;
  font-weight: 600;
}

.qg-exam-wrong-answer .correct {
  color: #22c55e;
  font-weight: 600;
}

.qg-exam-wrong-analysis {
  margin: 6px 0 0;
  font-size: 12px;
  color: #8a96a8;
  font-style: italic;
}

.qg-exam-result-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
}

/* Mobile exam layout */
@media (max-width: 900px) {
  .qg-exam-full-body {
    flex-direction: column;
    padding: 12px;
    gap: 12px;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }

  .qg-exam-floating-card {
    position: sticky;
    top: 0;
    width: 100%;
    max-height: 200px;
    overflow-y: auto;
    border-radius: 12px;
    z-index: 50;
    order: -1;
  }

  .qg-exam-card-grid {
    grid-template-columns: repeat(8, 1fr);
  }

  .qg-exam-full-topbar {
    padding: 12px 16px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .qg-exam-full-title h2 {
    font-size: 15px;
  }

  .qg-exam-full-question {
    padding: 14px 16px;
  }

  .qg-exam-result-panel {
    padding: 16px 12px;
  }

  .qg-exam-result-card {
    padding: 20px 16px;
  }
}

.qg-exam-sync-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  margin: 20px 0 0;
  background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%);
  border: 1px solid #86efac;
  border-radius: 10px;
  color: #15803d;
  font-size: 13px;
  font-weight: 500;
}

.qg-exam-sync-hint svg {
  color: #22c55e;
  flex-shrink: 0;
}

.qg-exam-ai-score-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: center;
  margin: 20px 0 0;
  padding: 16px 18px;
  border: 1px solid #b7e6d0;
  border-radius: 18px;
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  text-align: left;
}

.qg-exam-ai-score-panel.active {
  border-color: #86efac;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
}

.qg-exam-ai-score-panel strong {
  display: block;
  margin-bottom: 4px;
  color: #14532d;
  font-size: 15px;
}

.qg-exam-ai-score-panel span {
  display: block;
  color: #166534;
  font-size: 13px;
  line-height: 1.6;
}

.qg-exam-ai-score-panel .qg-primary-btn {
  min-width: 132px;
  border-radius: 999px;
}

.qg-exam-weak-summary {
  margin: 20px 0 0;
  padding: 16px 20px;
  background: var(--surface, rgba(255, 255, 255, 0.94))7ed;
  border: 1px solid #fed7aa;
  border-radius: 10px;
}

.qg-exam-weak-summary h3 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #9a3412;
}

.qg-weak-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.qg-weak-tag {
  display: inline-block;
  padding: 4px 12px;
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  font-size: 12px;
  font-weight: 600;
  border-radius: 14px;
}

/* Pre-exam panel */
.qg-exam-pre-panel {
  display: flex;
  flex-direction: column;
}

.qg-exam-pre-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.qg-exam-pre-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
}

.qg-exam-pre-info span:first-child {
  font-weight: 600;
  color: #1a2b3d;
}

.qg-exam-pre-info span:last-child {
  font-size: 13px;
  color: #8a96a8;
}

/* Rounded filled sidebar cards and actions */
.qg-module-sidebar,
.qg-history-side,
.qg-sheet-preview-card {
  border-radius: 24px !important;
  background: linear-gradient(180deg, #f0fdf4 0%, #e4f8ec 100%) !important;
  border: 1px solid rgba(31, 188, 188, 0.16) !important;
}

.qg-module-nav-item,
.qg-module-tip,
.qg-history-preview,
.qg-file-icon-card,
.qg-record-list button,
.qg-activity-list button,
.qg-history-row button,
.qg-soft-btn,
.qg-primary-btn {
  border-radius: 999px;
}

.qg-module-nav-item {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border: 1px solid rgba(31, 188, 188, 0.14);
}

.qg-module-nav-item.active,
.qg-history-row button,
.qg-soft-btn {
  background: #dff8eb;
  border-color: rgba(31, 188, 188, 0.2);
  color: #117a51;
}

.qg-history-preview,
.qg-file-icon-card,
.qg-record-list button,
.qg-activity-list button {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border: 1px solid rgba(31, 188, 188, 0.14);
  box-shadow: 0 8px 20px rgba(31, 188, 188, 0.06);
}

.qg-page :is(
button,
.qg-primary-btn,
.qg-soft-btn,
.qg-secondary-btn,
.qg-link-btn,
.qg-generate-btn,
.qg-card-submit-btn,
.qg-card-toggle-btn,
.qg-filter-clear-btn,
.qg-inline-clear-btn,
.qg-batch-btn,
.qg-copy-btn,
.qg-similar-btn,
.qg-collapse-btn,
.qg-profile-clear-btn,
.qg-config-toggle-btn,
.qg-generate-sheet-btn,
.qg-config-goto-btn,
.qg-exam-full-finish-btn
) {
  border-radius: 999px !important;
  border: 1px solid rgba(31, 188, 188, 0.2) !important;
  background: linear-gradient(135deg, #eefbf4 0%, #dcf8ea 100%) !important;
  color: #117a51 !important;
  box-shadow: 0 8px 18px rgba(31, 188, 188, 0.1) !important;
}

.qg-page :is(
.qg-primary-btn,
.qg-generate-btn,
.qg-card-submit-btn,
.qg-generate-sheet-btn,
.qg-config-goto-btn
) {
  border-color: transparent !important;
  background: linear-gradient(135deg, #1fbcbc 0%, #1fbcbc 100%) !important;
  color: var(--surface, rgba(255, 255, 255, 0.94)) !important;
  box-shadow: 0 10px 22px rgba(31, 188, 188, 0.2) !important;
}

.qg-page :is(.qg-exam-full-finish-btn, .qg-batch-delete-btn) {
  border-color: transparent !important;
  background: linear-gradient(135deg, #ef6758 0%, #dc3f32 100%) !important;
  color: var(--surface, rgba(255, 255, 255, 0.94)) !important;
  box-shadow: 0 10px 20px rgba(220, 63, 50, 0.18) !important;
}

.qg-page :is(button, .qg-primary-btn, .qg-soft-btn, .qg-secondary-btn):hover:not(:disabled) {
  transform: translateY(-1px);
}

.qg-page button:disabled {
  background: #e8f0ec !important;
  color: #8aa099 !important;
  border-color: rgba(138, 160, 153, 0.2) !important;
  box-shadow: none !important;
}

/* Dashboard rounded filled cards and buttons */
.qg-dashboard-panel .qg-module-head .qg-soft-btn {
  min-height: 44px !important;
  padding: 0 22px !important;
  border-radius: 999px !important;
  border: 1px solid rgba(31, 188, 188, 0.2) !important;
  background: linear-gradient(135deg, #dff8eb 0%, #c9f0dc 100%) !important;
  color: #0c7a4e !important;
  box-shadow: 0 10px 22px rgba(31, 188, 188, 0.12) !important;
}

.qg-dashboard-panel .qg-stat-grid {
  gap: 14px !important;
  padding-bottom: 0 !important;
  border-bottom: 0 !important;
}

.qg-dashboard-panel .qg-stat-card,
.qg-dashboard-panel .qg-stat-card + .qg-stat-card {
  min-height: 112px !important;
  display: grid !important;
  grid-template-columns: 52px minmax(0, 1fr) !important;
  align-items: center !important;
  gap: 16px !important;
  padding: 18px 22px !important;
  border: 1px solid rgba(31, 188, 188, 0.16) !important;
  border-radius: 24px !important;
  background: linear-gradient(135deg, #effcf5 0%, #dff7eb 100%) !important;
  box-shadow: 0 14px 30px rgba(31, 188, 188, 0.1) !important;
}

.qg-dashboard-panel .qg-stat-icon {
  border-radius: 18px !important;
  background: linear-gradient(135deg, #1fbcbc 0%, #1fbcbc 100%) !important;
  color: rgba(255, 255, 255, 0.94) !important;
}

.qg-dashboard-panel .qg-dashboard-grid {
  gap: 18px !important;
}

.qg-dashboard-panel .qg-dashboard-grid > .qg-glass-card,
.qg-dashboard-panel .qg-dashboard-grid > .qg-glass-card:nth-child(n + 3) {
  min-height: 0 !important;
  height: 100% !important;
  padding: 20px 24px !important;
  border: 1px solid rgba(31, 188, 188, 0.16) !important;
  border-radius: 24px !important;
  background: linear-gradient(135deg, #f4fdf8 0%, #e8f8ef 100%) !important;
  box-shadow: 0 14px 34px rgba(31, 188, 188, 0.1) !important;
  overflow: hidden !important;
}

.qg-dashboard-panel .qg-activity-list button {
  min-height: 46px !important;
  padding: 10px 14px !important;
  border: 1px solid rgba(31, 188, 188, 0.16) !important;
  border-radius: 0 !important;
  background: linear-gradient(135deg, #eafaf2 0%, #d8f4e5 100%) !important;
  color: #117a51 !important;
  box-shadow: 0 8px 18px rgba(31, 188, 188, 0.06) !important;
}

.qg-dashboard-panel .qg-chip-cloud span,
.qg-dashboard-panel .qg-progress-row,
.qg-dashboard-panel .qg-panel-foot {
  border-radius: 999px !important;
  background: rgba(223, 248, 235, 0.78) !important;
}

.qg-dashboard-panel .qg-progress-row {
  padding: 7px 12px !important;
}

.qg-dashboard-panel .qg-panel-foot {
  padding: 8px 14px !important;
  border-top: 0 !important;
  color: #0d8b5c !important;
}

.qg-page.qg-page .qg-dashboard-panel .qg-module-head .qg-soft-btn,
.qg-page.qg-page .qg-dashboard-panel .qg-activity-list button {
  box-shadow: 0 10px 22px rgba(31, 188, 188, 0.12) !important;
}

.qg-page.qg-page .qg-dashboard-panel .qg-module-head .qg-soft-btn {
  border-radius: 999px !important;
}

.qg-page.qg-page .qg-dashboard-panel .qg-activity-list button {
  border-radius: 0 !important;
}

.qg-page.qg-page .qg-dashboard-panel .qg-stat-card,
.qg-page.qg-page .qg-dashboard-panel .qg-stat-card + .qg-stat-card,
.qg-page.qg-page .qg-dashboard-panel .qg-dashboard-grid > .qg-glass-card,
.qg-page.qg-page .qg-dashboard-panel .qg-dashboard-grid > .qg-glass-card:nth-child(n + 3) {
  border-radius: 24px !important;
  box-shadow: 0 14px 34px rgba(31, 188, 188, 0.1) !important;
}

.qg-page.qg-page.qg-page .qg-workbench.qg-workbench .qg-module-panel .qg-config-goto-btn,
.qg-page.qg-page.qg-page .qg-workbench.qg-workbench .qg-module-panel .qg-lock-ratio-btn {
  border-radius: 999px !important;
}

.qg-page.qg-page.qg-page .qg-workbench.qg-workbench .qg-module-panel .qg-config-summary-icon {
  border-radius: 16px !important;
}

/* Final question-generator dashboard refresh */
.qg-page {
  min-height: calc(100vh - 72px) !important;
  background: #f7fbfa !important;
  color: #1f3433 !important;
}

.qg-page .qg-workbench {
  display: flex !important;
  min-height: calc(100vh - 72px) !important;
  background: #f7fbfa !important;
  overflow: hidden !important;
}

.qg-page .qg-module-sidebar {
  position: relative !important;
  width: 240px !important;
  min-width: 240px !important;
  max-width: 240px !important;
  min-height: calc(100vh - 72px) !important;
  padding: 0 !important;
  border: 0 !important;
  border-right: 1px solid #e8f0ee !important;
  border-radius: 0 !important;
  background: #f3fbf7 !important;
  box-shadow: none !important;
}

.qg-page .qg-module-brand {
  margin: 32px 24px 24px !important;
  padding: 0 !important;
}

.qg-page .qg-module-brand h1 {
  margin: 0 !important;
  color: #1f3433 !important;
  font-size: 20px !important;
  line-height: 1.2 !important;
  font-weight: 700 !important;
  letter-spacing: 0 !important;
}

.qg-page .qg-module-nav {
  display: flex !important;
  flex-direction: column !important;
  gap: 0 !important;
  padding: 0 !important;
}

.qg-page.qg-page .qg-module-nav-item,
.qg-page.qg-page .qg-module-nav-item:hover {
  position: relative !important;
  height: 56px !important;
  min-height: 56px !important;
  margin: 0 24px 12px !important;
  padding: 0 18px !important;
  border: 0 !important;
  border-radius: 14px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  gap: 12px !important;
  background: transparent !important;
  color: #536b68 !important;
  box-shadow: none !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  transform: none !important;
}

.qg-page.qg-page .qg-module-nav-item.active,
.qg-page.qg-page .qg-module-nav-item.active:hover {
  background: linear-gradient(90deg, #ddf7ea, #f1fbf7) !important;
  color: #0e9f6e !important;
}

.qg-page .qg-module-nav-item.active::before {
  content: "" !important;
  position: absolute !important;
  left: 0 !important;
  top: 12px !important;
  bottom: 12px !important;
  width: 4px !important;
  border-radius: 999px !important;
  background: #10a66f !important;
}

.qg-page .qg-module-tip {
  margin: 16px 24px 0 !important;
  padding: 16px !important;
  border: 1px solid rgba(205, 239, 227, 0.78) !important;
  border-radius: 16px !important;
  background: rgba(255, 255, 255, 0.72) !important;
  box-shadow: none !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 8px !important;
}

.qg-page .qg-module-tip strong {
  color: #0e9f6e !important;
  font-size: 14px !important;
  font-weight: 700 !important;
}

.qg-page .qg-module-tip span {
  color: #667a77 !important;
  font-size: 13px !important;
}

.qg-page .qg-sidebar-deco {
  position: absolute !important;
  left: 24px !important;
  right: 24px !important;
  bottom: 28px !important;
  color: #9aaeaa !important;
  font-size: 13px !important;
  line-height: 1.7 !important;
}

.qg-page .qg-sidebar-books {
  width: 120px !important;
  height: 112px !important;
  margin-bottom: 12px !important;
  border-radius: 32px !important;
  display: grid !important;
  place-items: center !important;
  background:
    radial-gradient(circle at 68% 26%, rgba(19, 166, 111, 0.16), transparent 34%),
    linear-gradient(145deg, rgba(255, 255, 255, 0.72), rgba(221, 247, 234, 0.58)) !important;
  font-size: 58px !important;
}

.qg-page .qg-workspace {
  flex: 1 1 auto !important;
  min-width: 0 !important;
  min-height: calc(100vh - 72px) !important;
  padding: 32px 36px !important;
  background: #f7fbfa !important;
  overflow: auto !important;
}

.qg-page .qg-module-panel {
  min-height: auto !important;
  padding: 0 !important;
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}

.qg-page .qg-dashboard-panel .qg-module-head {
  min-height: 44px !important;
  margin: 0 0 24px !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 24px !important;
  border: 0 !important;
}

.qg-page .qg-dashboard-panel .qg-module-head h2 {
  margin: 0 !important;
  color: #1f3433 !important;
  font-size: 26px !important;
  line-height: 1.25 !important;
  font-weight: 700 !important;
  letter-spacing: 0 !important;
}

.qg-page.qg-page .qg-dashboard-panel .qg-refresh-btn,
.qg-page.qg-page .qg-dashboard-panel .qg-refresh-btn:hover {
  height: 44px !important;
  min-height: 44px !important;
  padding: 0 22px !important;
  border: 1px solid #cdefe3 !important;
  border-radius: 999px !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 8px !important;
  background: #f1fbf7 !important;
  color: #0e9f6e !important;
  box-shadow: none !important;
  font-size: 14px !important;
  font-weight: 700 !important;
}

.qg-page.qg-page .qg-dashboard-panel .qg-refresh-btn:hover {
  background: #e2f8ef !important;
  transform: translateY(-1px) !important;
}

.qg-page .qg-dashboard-panel .qg-stat-grid {
  display: grid !important;
  grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
  gap: 24px !important;
  margin: 0 !important;
  padding: 0 !important;
}

.qg-page.qg-page .qg-dashboard-panel .qg-stat-card,
.qg-page.qg-page .qg-dashboard-panel .qg-stat-card + .qg-stat-card {
  height: 126px !important;
  min-height: 126px !important;
  padding: 24px !important;
  border: 1px solid #e6f1ee !important;
  border-radius: 22px !important;
  display: grid !important;
  grid-template-columns: 56px minmax(0, 1fr) !important;
  align-items: center !important;
  gap: 20px !important;
  background: #ffffff !important;
  box-shadow: 0 12px 32px rgba(31, 72, 66, 0.06) !important;
}

.qg-page .qg-dashboard-panel .qg-stat-icon {
  width: 56px !important;
  height: 56px !important;
  border-radius: 14px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  background: linear-gradient(135deg, #20c997, #0e9f6e) !important;
  color: #ffffff !important;
  box-shadow: 0 12px 24px rgba(14, 159, 110, 0.18) !important;
}

.qg-page.qg-page.qg-page .qg-dashboard-panel .qg-stat-icon.qg-stat-icon--blue {
  background: #e9f1ff !important;
  color: #2563eb !important;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.12) !important;
}

.qg-page.qg-page.qg-page .qg-dashboard-panel .qg-stat-icon.qg-stat-icon--green {
  background: #e7f8f0 !important;
  color: #059669 !important;
  box-shadow: 0 8px 18px rgba(5, 150, 105, 0.12) !important;
}

.qg-page.qg-page.qg-page .qg-dashboard-panel .qg-stat-icon.qg-stat-icon--orange {
  background: #fff3df !important;
  color: #d97706 !important;
  box-shadow: 0 8px 18px rgba(217, 119, 6, 0.12) !important;
}

.qg-page.qg-page.qg-page .qg-dashboard-panel .qg-stat-icon.qg-stat-icon--purple {
  background: #f1eaff !important;
  color: #7c3aed !important;
  box-shadow: 0 8px 18px rgba(124, 58, 237, 0.12) !important;
}

.qg-page.qg-page.qg-page .qg-dashboard-panel .qg-stat-icon svg {
  fill: none !important;
  stroke: currentColor !important;
}

.qg-page .qg-stat-copy {
  display: flex !important;
  min-width: 0 !important;
  flex-direction: column !important;
  gap: 5px !important;
}

.qg-page .qg-stat-copy span {
  color: #7a8f8c !important;
  font-size: 14px !important;
}

.qg-page .qg-stat-copy strong {
  color: #1f3433 !important;
  font-size: 30px !important;
  line-height: 1 !important;
  font-weight: 700 !important;
}

.qg-page .qg-stat-copy em {
  color: #8aa09c !important;
  font-size: 14px !important;
  font-style: normal !important;
}

.qg-page .qg-dashboard-panel .qg-dashboard-grid {
  display: grid !important;
  grid-template-columns: minmax(0, 52fr) minmax(0, 48fr) !important;
  grid-template-rows: auto !important;
  grid-auto-rows: auto !important;
  gap: 24px !important;
  margin-top: 24px !important;
  height: auto !important;
  min-height: 0 !important;
  overflow: visible !important;
}

.qg-page.qg-page .qg-dashboard-panel .qg-dashboard-grid > .qg-glass-card,
.qg-page.qg-page .qg-dashboard-panel .qg-dashboard-grid > .qg-glass-card:nth-child(n + 3) {
  height: 300px !important;
  min-height: 0 !important;
  padding: 24px 28px !important;
  border: 1px solid #e6f1ee !important;
  border-radius: 22px !important;
  background: #ffffff !important;
  box-shadow: 0 12px 32px rgba(31, 72, 66, 0.06) !important;
  overflow: hidden !important;
}

.qg-page.qg-page .qg-dashboard-panel .qg-dashboard-grid-bottom > .qg-glass-card {
  height: 280px !important;
}

.qg-page .qg-dashboard-panel .qg-card-title {
  margin: 0 0 8px !important;
  color: #1f3433 !important;
  font-size: 18px !important;
  line-height: 1.25 !important;
  font-weight: 700 !important;
}

.qg-page .qg-dashboard-panel .qg-card-note {
  margin: 0 0 18px !important;
  color: #7a8f8c !important;
  font-size: 14px !important;
  line-height: 1.5 !important;
}

.qg-page .qg-line-chart {
  position: relative !important;
  height: 162px !important;
  padding-left: 34px !important;
  box-sizing: border-box !important;
}

.qg-page .qg-y-axis {
  position: absolute !important;
  left: 0 !important;
  top: 2px !important;
  bottom: 24px !important;
  display: flex !important;
  flex-direction: column !important;
  justify-content: space-between !important;
  color: #667a77 !important;
  font-size: 12px !important;
}

.qg-page .qg-trend-svg {
  width: 100% !important;
  height: 130px !important;
  display: block !important;
}

.qg-page .qg-grid-line {
  stroke: #edf2f1 !important;
  stroke-width: 1 !important;
}

.qg-page .qg-trend-line {
  fill: none !important;
  stroke: #10a66f !important;
  stroke-width: 3 !important;
  stroke-linecap: round !important;
  stroke-linejoin: round !important;
}

.qg-page .qg-trend-dot {
  fill: #10a66f !important;
  stroke: #ffffff !important;
  stroke-width: 3 !important;
}

.qg-page .qg-x-axis {
  display: grid !important;
  grid-template-columns: repeat(7, 1fr) !important;
  color: #667a77 !important;
  font-size: 12px !important;
  text-align: center !important;
}

.qg-page .qg-dashboard-panel .qg-panel-foot {
  min-height: 30px !important;
  margin-top: 8px !important;
  padding: 6px 16px !important;
  border: 0 !important;
  border-radius: 10px !important;
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  background: #eef9f4 !important;
  color: #0e9f6e !important;
  font-size: 14px !important;
  font-weight: 600 !important;
}

.qg-page .qg-progress-list {
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) !important;
  gap: 18px !important;
  margin-top: 24px !important;
  width: 100% !important;
}

.qg-page.qg-page .qg-dashboard-panel .qg-progress-row {
  display: grid !important;
  grid-template-columns: 88px minmax(0, 1fr) 48px !important;
  align-items: center !important;
  gap: 16px !important;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.qg-page .qg-progress-row span {
  color: #1f3433 !important;
  font-size: 15px !important;
  font-weight: 600 !important;
}

.qg-page .qg-progress-row div {
  height: 6px !important;
  border-radius: 999px !important;
  overflow: hidden !important;
  background: #edf2f1 !important;
}

.qg-page .qg-progress-row i {
  display: block !important;
  height: 100% !important;
  border-radius: inherit !important;
  background: linear-gradient(90deg, #0e9f6e, #83dbc0) !important;
}

.qg-page .qg-progress-row strong {
  color: #1f3433 !important;
  font-size: 15px !important;
  text-align: right !important;
}

.qg-page .qg-chip-cloud {
  display: grid !important;
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  gap: 12px !important;
  margin-top: 20px !important;
}

.qg-page.qg-page .qg-dashboard-panel .qg-chip-cloud span {
  min-height: 52px !important;
  padding: 0 18px !important;
  border: 0 !important;
  border-radius: 12px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  background: #eef9f4 !important;
  color: #1f3433 !important;
  font-size: 15px !important;
  font-weight: 700 !important;
}

.qg-page .qg-review-foot {
  margin-top: 18px !important;
  border-radius: 12px !important;
  background: #f1fbf7 !important;
}

.qg-page .qg-activity-list {
  display: grid !important;
  gap: 0 !important;
  margin-top: 14px !important;
  border: 1px solid #eef2f1 !important;
  border-radius: 12px !important;
  overflow: hidden !important;
  background: #ffffff !important;
}

.qg-page.qg-page .qg-dashboard-panel .qg-activity-list button {
  height: 52px !important;
  min-height: 52px !important;
  padding: 0 16px !important;
  border: 0 !important;
  border-bottom: 1px solid #eef2f1 !important;
  border-radius: 0 !important;
  display: grid !important;
  grid-template-columns: 32px minmax(0, 1fr) auto !important;
  align-items: center !important;
  gap: 12px !important;
  background: #ffffff !important;
  color: #1f3433 !important;
  box-shadow: none !important;
  text-align: left !important;
  transform: none !important;
}

.qg-page .qg-activity-list button:last-child {
  border-bottom: 0 !important;
}

.qg-page .qg-activity-icon {
  width: 28px !important;
  height: 28px !important;
  border-radius: 9px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}

.qg-page .qg-activity-sheet {
  background: #ddf7ea !important;
  color: #0e9f6e !important;
}

.qg-page .qg-activity-exam {
  background: #e4f0ff !important;
  color: #2f7de1 !important;
}

.qg-page .qg-activity-file {
  background: #f0e8ff !important;
  color: #7c3aed !important;
}

.qg-page .qg-activity-title-row {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  min-width: 0 !important;
}

.qg-page .qg-activity-title-row em {
  color: #0e9f6e !important;
  font-size: 13px !important;
  font-style: normal !important;
  font-weight: 700 !important;
}

.qg-page .qg-activity-title-row strong {
  min-width: 0 !important;
  color: #1f3433 !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}

.qg-page .qg-activity-title-row small {
  padding: 3px 8px !important;
  border-radius: 999px !important;
  background: #eef9f4 !important;
  color: #0e9f6e !important;
  font-size: 12px !important;
  font-weight: 600 !important;
}

.qg-page .qg-activity-list time {
  color: #7a8f8c !important;
  font-size: 13px !important;
  white-space: nowrap !important;
}

.qg-page .qg-activity-foot {
  margin-top: 12px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  color: #0e9f6e !important;
  font-size: 14px !important;
  font-weight: 600 !important;
}

.qg-page.qg-page .qg-activity-foot button,
.qg-page.qg-page .qg-activity-foot button:hover {
  height: auto !important;
  min-height: 0 !important;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  color: #0e9f6e !important;
  font-size: 14px !important;
  font-weight: 700 !important;
}

@media (max-width: 1199px) {
  .qg-page .qg-dashboard-panel .qg-stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }

  .qg-page .qg-dashboard-panel .qg-dashboard-grid {
    grid-template-columns: 1fr !important;
  }
}

@media (max-width: 768px) {
  .qg-page .qg-workbench {
    display: block !important;
  }

  .qg-page .qg-module-sidebar {
    display: none !important;
  }

  .qg-page .qg-workspace {
    padding: 16px !important;
  }

  .qg-page .qg-dashboard-panel .qg-stat-grid {
    grid-template-columns: 1fr !important;
  }

  .qg-page .qg-dashboard-panel .qg-module-head {
    align-items: flex-start !important;
    flex-direction: column !important;
  }

  .qg-page.qg-page .qg-dashboard-panel .qg-dashboard-grid > .qg-glass-card,
  .qg-page.qg-page .qg-dashboard-panel .qg-dashboard-grid-bottom > .qg-glass-card {
    height: auto !important;
    min-height: 280px !important;
  }

  .qg-page .qg-chip-cloud {
    grid-template-columns: 1fr !important;
  }
}

/* Question config: keep icons in the green education theme. */
.qg-page.qg-page .qg-module-panel:has(.qg-config-dashboard) svg {
  color: #0e9f6e !important;
  stroke: currentColor !important;
}

.qg-page.qg-page .qg-module-panel:has(.qg-config-dashboard) .qg-config-summary-icon {
  background: linear-gradient(135deg, #20c997, #0e9f6e) !important;
  color: #ffffff !important;
  box-shadow: 0 10px 22px rgba(14, 159, 110, 0.18) !important;
}

.qg-page.qg-page .qg-module-panel:has(.qg-config-dashboard) .qg-config-summary-icon svg {
  color: #ffffff !important;
  stroke: currentColor !important;
}

.qg-page.qg-page .qg-module-panel:has(.qg-config-dashboard) .qg-config-goto-btn,
.qg-page.qg-page .qg-module-panel:has(.qg-config-dashboard) .qg-lock-ratio-btn {
  border-color: #cdefe3 !important;
  background: #f1fbf7 !important;
  color: #0e9f6e !important;
}

.qg-page.qg-page .qg-module-panel:has(.qg-config-dashboard) .qg-lock-ratio-btn.locked {
  border-color: transparent !important;
  background: linear-gradient(135deg, #20c997, #0e9f6e) !important;
  color: #ffffff !important;
  box-shadow: 0 8px 18px rgba(14, 159, 110, 0.18) !important;
}

.qg-page.qg-page .qg-module-panel:has(.qg-config-dashboard) .qg-lock-ratio-btn.locked svg {
  color: #ffffff !important;
}

.qg-page.resource-tool-standalone {
  min-height: 100vh;
  padding-top: 72px;
  background: #f7fbfa;
}

.resource-return-button {
  position: fixed;
  top: 18px;
  left: 24px;
  z-index: 120;
  height: 42px;
  padding: 0 18px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #cdefe3;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #0e9f6e;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 10px 26px rgba(31, 72, 66, 0.1);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.resource-return-button:hover {
  transform: translateY(-1px);
  background: #f1fbf7;
  box-shadow: 0 14px 30px rgba(31, 72, 66, 0.14);
}

/* Resource-tool generate view: a compact input rail and a readable preview surface. */
.qg-page.resource-tool-standalone .qg-workbench {
  background: #f5f7f6 !important;
}

.qg-page.resource-tool-standalone .qg-module-sidebar {
  width: 224px !important;
  min-width: 224px !important;
  max-width: 224px !important;
  background: #ffffff !important;
  border-right-color: #e1e6e4 !important;
}

.qg-page.resource-tool-standalone .qg-module-nav-item,
.qg-page.resource-tool-standalone .qg-module-nav-item:hover {
  height: 48px !important;
  min-height: 48px !important;
  margin: 0 14px 7px !important;
  padding: 0 14px !important;
  border: 1px solid transparent !important;
  border-radius: 6px !important;
  background: transparent !important;
  color: #45514e !important;
  box-shadow: none !important;
  transform: none !important;
}

.qg-page.resource-tool-standalone .qg-module-nav-item.active,
.qg-page.resource-tool-standalone .qg-module-nav-item.active:hover {
  border-color: #d6e8df !important;
  background: #edf8f2 !important;
  color: #087451 !important;
}

.qg-page.resource-tool-standalone .qg-module-tip {
  margin: 18px 14px 0 !important;
  padding: 14px !important;
  border: 1px solid #e1e6e4 !important;
  border-radius: 6px !important;
  background: #f8faf9 !important;
}

.qg-page.resource-tool-standalone .qg-sidebar-deco {
  display: none !important;
}

.qg-page.resource-tool-standalone .qg-workspace {
  padding: 28px 36px 36px !important;
  background: #f5f7f6 !important;
}

.qg-page.resource-tool-standalone .qg-generate-panel .qg-module-head {
  min-height: 50px;
  margin: 0 0 20px !important;
  padding: 0 0 16px !important;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #dfe5e2 !important;
}

.qg-page.resource-tool-standalone .qg-generate-panel .qg-module-head h2 {
  margin: 0;
  color: #17201d;
  font-size: 25px;
  font-weight: 750;
}

.qg-page.resource-tool-standalone .qg-generate-sheet-btn,
.qg-page.resource-tool-standalone .qg-generate-sheet-btn:hover:not(:disabled) {
  min-height: 42px !important;
  padding: 0 18px !important;
  border: 1px solid #0a7654 !important;
  border-radius: 6px !important;
  background: #0b7956 !important;
  box-shadow: none !important;
  color: #ffffff !important;
  transform: none !important;
}

.qg-page.resource-tool-standalone .qg-upload-layout {
  grid-template-columns: minmax(332px, 390px) minmax(0, 1fr) !important;
  gap: 20px !important;
  height: calc(100vh - 176px) !important;
  min-height: 620px !important;
}

.qg-page.resource-tool-standalone .qg-upload-layout > .qg-glass-card,
.qg-page.resource-tool-standalone .qg-sheet-preview-card {
  border: 1px solid #dfe5e2 !important;
  border-radius: 8px !important;
  background: #ffffff !important;
  box-shadow: none !important;
}

.qg-page.resource-tool-standalone .qg-generate-input-panel {
  padding: 20px !important;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.qg-page.resource-tool-standalone .qg-profile-merge-section {
  padding: 0 0 16px !important;
  border-bottom-color: #e7ece9 !important;
}

.qg-page.resource-tool-standalone .qg-card-title {
  color: #1f2926 !important;
  font-size: 15px !important;
  font-weight: 700 !important;
}

.qg-page.resource-tool-standalone .qg-tag-editor {
  gap: 9px;
}

.qg-page.resource-tool-standalone .qg-tag-list {
  min-height: 42px;
  padding: 5px !important;
  border: 1px solid #d9e1dd !important;
  border-radius: 6px !important;
  background: #ffffff !important;
}

.qg-page.resource-tool-standalone .qg-tag-list button,
.qg-page.resource-tool-standalone .qg-mini-add {
  border-radius: 4px !important;
  box-shadow: none !important;
}

.qg-page.resource-tool-standalone .qg-upload-zone {
  min-height: 198px !important;
  padding: 20px !important;
  border: 1px dashed #9bcdbb !important;
  border-radius: 6px !important;
  background: #f7fbf9 !important;
}

.qg-page.resource-tool-standalone .qg-upload-zone:hover,
.qg-page.resource-tool-standalone .qg-upload-zone.active {
  border-color: #0b8a62 !important;
  background: #eef9f3 !important;
}

.qg-page.resource-tool-standalone .qg-upload-zone > svg {
  color: #0b8a62 !important;
}

.qg-page.resource-tool-standalone .qg-field.wide {
  margin-top: auto;
}

.qg-page.resource-tool-standalone .qg-field textarea,
.qg-page.resource-tool-standalone .qg-tag-list input {
  border-color: #d9e1dd !important;
  border-radius: 6px !important;
  background: #ffffff !important;
  box-shadow: none !important;
}

.qg-page.resource-tool-standalone .qg-field textarea {
  min-height: 132px;
  resize: vertical;
}

.qg-page.resource-tool-standalone .qg-sheet-preview-card {
  padding: 0 !important;
  display: flex;
  flex-direction: column;
  overflow: hidden !important;
}

.qg-page.resource-tool-standalone .qg-sheet-preview-card .qg-preview-title {
  min-height: 58px;
  margin: 0 !important;
  padding: 0 22px !important;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #e3e9e6;
  background: #fbfcfb;
}

.qg-page.resource-tool-standalone .qg-question-preview-stage {
  flex: 1 1 auto;
  width: auto;
  height: auto !important;
  min-height: 0 !important;
  margin: 18px !important;
  border: 0 !important;
  border-radius: 6px !important;
  background: #f7f9f8 !important;
  color: #6d7a76;
}

.qg-page.resource-tool-standalone .qg-question-preview-stage > svg {
  width: 44px;
  height: 44px;
  stroke: #8ca7a0;
}

.qg-page.resource-tool-standalone .qg-question-preview-stage strong {
  margin-top: 8px;
  color: #34403c;
}

@media (max-width: 1100px) {
  .qg-page.resource-tool-standalone .qg-upload-layout {
    grid-template-columns: 1fr !important;
    height: auto !important;
  }

  .qg-page.resource-tool-standalone .qg-generate-input-panel {
    min-height: 0;
  }

  .qg-page.resource-tool-standalone .qg-sheet-preview-card {
    min-height: 480px;
  }
}

</style>
<!-- Non-scoped: override body overflow for exam scrolling -->
<style>
body.exam-scroll-override,
body.exam-scroll-override .app-shell {
  overflow: auto !important;
  height: auto !important;
}
</style>
