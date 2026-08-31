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
                <strong>正在打开岐小智生成的题单</strong>
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
                      <input v-model="newWeakTag" placeholder="输入后回车添加，如 八纲辨证" @keydown.enter.prevent="addWeakTag" />
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
              <div class="qg-exam-overview-layout">
                <div class="qg-glass-card qg-exam-question-card">
                  <div class="qg-card-title">当前试卷</div>
                  <div v-if="!selectedSheet" class="qg-empty-state">请先选择一份题单，然后开始考试。</div>
                  <div v-else-if="selectedQuestions.length" class="qg-exam-pre-info">
                    <div class="qg-exam-pre-summary">
                      <strong>{{ selectedSheet.title }}</strong>
                      <span>{{ selectedQuestions.length }} 题 · {{ selectedExamTotalScore }} 分</span>
                    </div>
                    <ol class="qg-exam-question-preview" aria-label="当前试卷部分题目">
                      <li v-for="(question, index) in examPreviewQuestions" :key="question.id || question._id || index">
                        <span class="qg-exam-preview-number">{{ index + 1 }}</span>
                        <div>
                          <p>{{ question.stem || '题目内容待补充' }}</p>
                          <small>{{ question.type || '题目' }} · {{ scoreForQuestion(question) }} 分</small>
                        </div>
                      </li>
                    </ol>
                    <p v-if="remainingExamPreviewCount" class="qg-exam-preview-more">
                      其余 {{ remainingExamPreviewCount }} 题将在开始考试后展开
                    </p>
                  </div>
                  <div v-else class="qg-empty-state">当前题单没有可用题目，请重新选择或生成题单。</div>
                </div>

                <aside v-if="selectedSheet && selectedQuestions.length" class="qg-exam-overview-sidebar">
                  <header>
                    <span>试卷概览</span>
                    <strong>{{ selectedSheet.target_topic || selectedSheet.course_name || selectedSheet.title }}</strong>
                  </header>
                  <div class="qg-exam-overview-stats">
                    <div>
                      <FileText aria-hidden="true" />
                      <span>总题数</span>
                      <strong>{{ selectedQuestions.length }} 题</strong>
                    </div>
                    <div>
                      <ClipboardCheck aria-hidden="true" />
                      <span>总分值</span>
                      <strong>{{ selectedExamTotalScore }} 分</strong>
                    </div>
                    <div>
                      <History aria-hidden="true" />
                      <span>建议用时</span>
                      <strong>{{ selectedExamMinutes }} 分钟</strong>
                    </div>
                  </div>
                  <section>
                    <h3>题型分布</h3>
                    <ul class="qg-exam-type-list">
                      <li v-for="item in selectedExamTypeDistribution" :key="item.type">
                        <i aria-hidden="true"></i>
                        <span>{{ item.type }}</span>
                        <strong>{{ item.count }} 题</strong>
                        <em>{{ item.score }} 分</em>
                      </li>
                    </ul>
                  </section>
                  <section v-if="selectedExamKnowledgeFocus.length">
                    <h3>知识聚焦</h3>
                    <div class="qg-exam-focus-tags">
                      <span v-for="item in selectedExamKnowledgeFocus" :key="item">{{ item }}</span>
                    </div>
                  </section>
                  <p class="qg-exam-overview-note">建议先通览题目，再按题型集中作答；提交后将自动记录错题与薄弱知识点。</p>
                </aside>
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
const examPreviewQuestions = computed(() => selectedQuestions.value.slice(0, 4))
const remainingExamPreviewCount = computed(() => Math.max(0, selectedQuestions.value.length - examPreviewQuestions.value.length))
const selectedExamTotalScore = computed(() => (
  selectedQuestions.value.reduce((sum, question) => sum + Number(scoreForQuestion(question) || 0), 0)
))
const selectedExamMinutes = computed(() => Math.max(10, Math.ceil(selectedQuestions.value.length * 2.5)))
const selectedExamTypeDistribution = computed(() => {
  const distribution = new Map()
  selectedQuestions.value.forEach((question) => {
    const type = String(question?.type || '其他题型').trim() || '其他题型'
    const current = distribution.get(type) || { type, count: 0, score: 0 }
    current.count += 1
    current.score += Number(scoreForQuestion(question) || 0)
    distribution.set(type, current)
  })
  return Array.from(distribution.values())
})
const selectedExamKnowledgeFocus = computed(() => {
  const focus = []
  selectedQuestions.value.forEach((question) => {
    const values = [
      question?.knowledge_point,
      question?.knowledgePoint,
      ...(Array.isArray(question?.tags) ? question.tags : []),
    ]
    values.forEach((value) => {
      const text = String(value || '').trim()
      if (text && !focus.includes(text)) focus.push(text)
    })
  })
  return focus.slice(0, 6)
})
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
    pastedText.value = `请围绕 ${topic} 生成中医学习小测，重点覆盖基础概念、辨证思路、常见易错点和医案应用。`
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
    title: sheet.title || '中医基础题库练习小测',
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
    title: sheet?.title || bank?.title || '中医基础题库练习小测',
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
    streamMessage.value = task.status === 'queued' ? '岐小智题库任务已排队...' : '岐小智正在生成题库...'
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
        title: [courseName.value, chapterName.value].filter(Boolean).join(' ') || '中医基础题库练习小测',
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
    pastedText.value = '快速练习模式：请针对以下中医薄弱知识点生成练习题。知识点包括：' + wpText + '。每道题需包含知识点标签和解析，贴近中医辨证与医案学习场景。'
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
        title: [courseName.value, chapterName.value].filter(Boolean).join(' ') || '中医基础题库练习小测',
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
        title: [courseName.value, chapterName.value].filter(Boolean).join(' ') || '中医基础题库练习小测',
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

<style scoped src="../styles/question-generator-view.css"></style>

<style scoped src="../styles/question-generator-workbench.css"></style>

<style scoped src="../styles/question-generator-exam.css"></style>

<style src="../styles/question-generator-view.global.css"></style>
