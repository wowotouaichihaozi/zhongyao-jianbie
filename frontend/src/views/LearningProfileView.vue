<template>
  <div :class="['lp-page', { 'has-live-avatar': activeMenu === 'assess', 'profile-assess-mode': activeMenu === 'assess', 'profile-report-mode': activeMenu === 'report' && hasGeneratedReport, 'profile-history-mode': activeMenu === 'history' }]" @click="resumeLearningAvatarIfNeeded">
    <!-- Toast 閫氱煡 -->
    <Transition name="toast">
      <div v-if="toastMsg" class="toast-bar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
          <path d="M9 12l2 2 4-4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>{{ toastMsg }}</span>
      </div>
    </Transition>

    <aside class="lp-sidebar">
      <nav class="sidebar-nav">
        <button
          v-for="item in sidebarMenuItems"
          :key="item.key"
          :class="['nav-item', { active: activeMenu === item.key }]"
          @click="selectSidebarMenu(item.key)"
        >
          <span class="nav-icon">
            <component :is="item.icon" :size="20" :stroke-width="2" />
          </span>
          <span class="nav-label">{{ item.label }}</span>
        </button>
      </nav>
      <div
        id="learning-profile-digital-human-stage"
        class="sidebar-digital-human-stage"
        :data-digital-human-stage="activeMenu === 'assess' ? 'active' : 'standby'"
      >
        <div class="sidebar-stage-card">
          <strong>数字人舞台</strong>
          <div
            :class="[
              'sidebar-stage-frame',
              {
                'has-avatar': !learningAvatarError,
                'has-error': Boolean(learningAvatarError),
              },
            ]"
            aria-label="讯飞虚拟数字人舞台"
          >
            <DigitalHumanAvatar
              ref="digitalHumanRef"
              class="sidebar-learning-avatar"
              :show-status="false"
              :show-error="false"
              :show-resume="false"
              @status-change="handleLearningAvatarStatus"
              @error="handleLearningAvatarError"
            />
          </div>
          <span
            :class="['sidebar-stage-state', { error: learningAvatarError }]"
            aria-live="polite"
          >
            {{ learningAvatarError ? '连接异常' : avatarDisplayStatus }}
          </span>
        </div>
      </div>
    </aside>

    <!-- 右侧内容区 -->
    <main class="lp-content">
      <!-- 画像报告 -->
      <div v-if="activeMenu === 'report'" class="content-panel">
        <!-- 无数据空状态 -->
        <div v-if="!hasGeneratedReport" class="report-empty-dashboard">
          <div class="empty-report-head">
            <div>
              <h2>学习画像报告</h2>
              <p>基于多维数据生成你的个性化学习画像</p>
            </div>
          </div>

          <div class="empty-report-grid">
            <section class="empty-report-card empty-main-card">
              <div class="empty-visual">
                <div class="empty-visual-card">
                  <svg viewBox="0 0 64 64" fill="none" aria-hidden="true">
                    <rect x="14" y="8" width="36" height="48" rx="6" fill="#E7E9E8" />
                    <path d="M24 24h16M24 32h12M24 40h18" stroke="#343938" stroke-width="3" stroke-linecap="round" />
                    <circle cx="43" cy="18" r="10" fill="#D2D6D5" />
                    <path d="M39 18l3 3 6-7" stroke="#202424" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                </div>
              </div>

              <h3>画像报告尚未生成</h3>
              <p class="empty-report-desc">完成 10 个画像维度后，系统会自动生成学习画像报告</p>

              <div class="empty-progress-box">
                <div class="empty-progress-meta">
                  <strong>数据采集进度</strong>
                  <span>{{ completedCount }}/{{ profileDimensionTotal }} 个维度已完成</span>
                </div>
                <div class="empty-progress-track">
                  <div :style="{ width: reportProgressPercent + '%' }"></div>
                </div>
              </div>

              <div class="empty-collect-actions">
                <button type="button" @click="openCollectPage('scale')">
                  <ClipboardCheck :size="18" />
                  量表问卷
                </button>
                <button type="button" @click="openCollectPage('upload')">
                  <UploadCloud :size="18" />
                  上传作业完成情况
                </button>
                <button type="button" @click="openCollectPage('chat')">
                  <MessageCircle :size="18" />
                  对话
                </button>
              </div>

              <button
                :class="['empty-generate-btn', { disabled: !canUseReportAction }]"
                :disabled="!canUseReportAction"
                type="button"
                @click="handleReportAction"
              >
                <FileText :size="18" />
                {{ reportActionLabel }}
              </button>

              <div class="empty-tip-box">
                <Sparkles :size="18" />
                <div>
                  <strong>小贴士</strong>
                  <p>完成 10 个画像维度后，系统将自动调用学习画像智能体，帮助你更好地了解学习现状、规划学习路径。</p>
                </div>
              </div>
            </section>

            <div class="empty-side-stack">
              <section class="empty-report-card agent-state-card">
                <div class="agent-state-head">
                  <h3>
                    <UserRoundCheck :size="18" />
                    学习画像智能体实时状态
                  </h3>
                  <span>{{ agentRuntimeLabel }}</span>
                </div>

                <div class="agent-state-body">
                  <div class="agent-timeline">
                    <div
                      v-for="(step, index) in agentStatusSteps"
                      :key="step.title"
                      :class="['agent-time-step', { active: index === agentTimelineActiveIndex, done: index < agentTimelineActiveIndex }]"
                    >
                      <span>{{ index + 1 }}</span>
                      <div>
                        <strong>{{ step.title }}</strong>
                        <p>{{ step.desc }}</p>
                      </div>
                    </div>
                  </div>

                  <div class="agent-log-panel">
                    <div class="agent-log-head">
                      <strong>详细执行信息</strong>
                      <span>{{ agentLogLabel }}</span>
                    </div>
                    <template v-if="analysisStreamEvents.length">
                      <div class="agent-log-overview">
                        <div>
                          <span>当前智能体</span>
                          <strong>{{ analysisCurrentAgent }}</strong>
                        </div>
                        <div>
                          <span>模型</span>
                          <strong>{{ analysisRuntimeModel }}</strong>
                        </div>
                        <div>
                          <span>运行 ID</span>
                          <strong class="monospace">{{ analysisRunId || '等待分配' }}</strong>
                        </div>
                        <div>
                          <span>质量审核</span>
                          <strong>{{ analysisReviewLabel }}</strong>
                        </div>
                        <div>
                          <span>当前阶段</span>
                          <strong>{{ formatAnalysisStage(latestAnalysisEvent.stage || latestAnalysisEvent.event) }}</strong>
                        </div>
                        <div>
                          <span>累计耗时</span>
                          <strong>{{ analysisElapsedLabel }}</strong>
                        </div>
                      </div>
                      <div class="agent-log-progress" aria-label="画像分析进度">
                        <div>
                          <span>执行进度</span>
                          <strong>{{ analysisProgress }}%</strong>
                        </div>
                        <div class="agent-log-progress-track" aria-hidden="true">
                          <span :style="{ width: `${analysisProgress}%` }"></span>
                        </div>
                      </div>
                      <div ref="analysisLogRef" class="agent-log-lines" aria-live="polite">
                        <article
                        v-for="(item, index) in analysisStreamEvents"
                        :key="item.id || `${item.time}-${index}`"
                        :class="['agent-log-entry', item.status, { thinking: aiAnalyzing && index === analysisStreamEvents.length - 1 }]"
                      >
                          <header>
                            <time>{{ item.time }}</time>
                            <strong>{{ formatAnalysisStage(item.stage || item.event) }}</strong>
                            <span>{{ formatAnalysisStatus(item.status) }}</span>
                            <b v-if="Number.isFinite(Number(item.progress))">{{ Math.round(Number(item.progress)) }}%</b>
                          </header>
                          <p>{{ item.message || item.text || item.error || '' }}</p>
                          <dl v-if="item.details?.length">
                            <div v-for="detail in item.details" :key="`${item.id}-${detail.label}`">
                              <dt>{{ detail.label }}</dt>
                              <dd :class="{ monospace: detail.monospace }">{{ detail.value }}</dd>
                            </div>
                          </dl>
                        </article>
                      </div>
                    </template>
                    <div v-else class="agent-log-empty">
                      <strong>{{ allCompleted ? '智能体已就绪' : '等待数据采集完成' }}</strong>
                      <p>{{ allCompleted ? '画像维度已补齐，系统会自动启动画像分析智能体。' : '完成 10 个画像维度后，才能启动学习画像智能体。' }}</p>
                    </div>
                  </div>
                </div>
              </section>

              <section class="empty-report-card preview-state-card">
                <div class="status-explain">
                  <h3>状态说明</h3>
                  <strong>{{ agentStatusSteps[agentTimelineActiveIndex]?.title }}</strong>
                  <p>{{ agentStatusSteps[agentTimelineActiveIndex]?.detail }}</p>
                </div>
                <div class="preview-divider"></div>
                <div class="result-preview">
                  <h3>结果预览（示例）</h3>
                  <div class="report-preview-mini">
                    <div class="mini-radar">
                      <svg viewBox="0 0 120 90" fill="none">
                        <polygon points="60,10 96,34 84,76 36,76 24,34" fill="rgba(32,36,36,.08)" stroke="#8A9190" />
                        <polygon points="60,24 84,38 76,64 42,68 34,40" fill="rgba(32,36,36,.18)" stroke="#343938" />
                      </svg>
                    </div>
                    <div class="mini-score">
                      <span>85</span>
                    </div>
                  </div>
                  <p>学习画像报告包含学习风格、知识掌握、能力雷达、学习建议等多维度分析结果。</p>
                  <button type="button" @click="handleReportAction">
                    查看示例报告
                  </button>
                </div>
              </section>
            </div>
          </div>
        </div>

        <!-- 智能体分析完成后展示报告 -->
        <div v-else class="profile-dashboard-report">
          <header class="profile-dashboard-header">
            <div>
              <h2>{{ reportMainTitle }}</h2>
              <p>基于稳定学习特征的个性化学习画像报告</p>
            </div>
            <div class="profile-growth-route" aria-label="学习成长阶段">
              <div v-for="(step, index) in reportGrowthSteps" :key="step.label" class="growth-route-step">
                <span><component :is="step.icon" :size="22" :stroke-width="1.8" /></span>
                <small>{{ step.label }}</small>
                <i v-if="index < reportGrowthSteps.length - 1"></i>
              </div>
            </div>
          </header>

          <section id="profile-overview" class="profile-summary-strip">
            <article v-for="card in reportSummaryCards" :key="card.label">
              <component :is="card.icon" :size="39" :stroke-width="1.55" />
              <div>
                <span>{{ card.label }}</span>
                <strong>{{ card.title }}</strong>
                <p>{{ card.detail }}</p>
              </div>
            </article>
          </section>

          <div class="profile-dashboard-grid">
            <div class="profile-dashboard-column profile-dashboard-left">
              <section id="profile-style" class="profile-dash-card profile-ability-card">
                <h3>十维学习画像</h3>
                <div class="profile-ability-list">
                  <div v-for="row in reportAbilityRows" :key="row.label" class="profile-ability-row">
                    <span class="ability-row-icon"><component :is="row.icon" :size="15" /></span>
                    <strong>{{ row.label }}</strong>
                    <div class="ability-segments" :aria-label="`${row.label} ${row.level}`">
                      <i v-for="segment in 6" :key="segment" :class="{ filled: segment <= row.segments }"></i>
                    </div>
                    <small>{{ row.level }}</small>
                  </div>
                </div>
              </section>

              <section id="profile-evidence" class="profile-dash-card profile-evidence-matrix">
                <h3>证据与依据矩阵 <small>（画像维度与证据映射）</small></h3>
                <div class="evidence-table-wrap">
                  <table>
                    <thead><tr><th>维度</th><th>项目实践表现</th><th>代码实践风格</th><th>知识掌握广度</th><th>学习内容偏好</th></tr></thead>
                    <tbody>
                      <tr v-for="row in reportAbilityRows" :key="`evidence-${row.label}`">
                        <td>{{ row.label }}</td>
                        <td v-for="(level, index) in row.evidence" :key="index"><i :class="`evidence-${level}`"></i></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div class="evidence-legend"><span><i class="evidence-strong"></i>强相关</span><span><i class="evidence-mid"></i>中相关</span><span><i class="evidence-weak"></i>弱相关</span><span>— 关联较弱/无</span></div>
              </section>
            </div>

            <div class="profile-dashboard-column profile-dashboard-middle">
              <section id="profile-radar" class="profile-dash-card profile-radar-card">
                <h3>六维能力雷达图</h3>
                <div class="profile-radar-stage">
                  <svg viewBox="0 0 400 400" class="radar-svg" aria-label="六维能力雷达图">
                    <polygon v-for="level in 5" :key="level" :points="getPolygonPoints((radarMaxR * level) / 5)" fill="none" stroke="#d9dddc" />
                    <line v-for="(_, index) in scaleQuestions" :key="`report-axis-${index}`" :x1="radarCenter" :y1="radarCenter" :x2="getDataPoint(index, 5).x" :y2="getDataPoint(index, 5).y" stroke="#d9dddc" />
                    <polygon :points="getDataPolygonPoints()" fill="rgba(32,36,36,.22)" stroke="#343938" stroke-width="2.2" />
                    <circle v-for="(_, index) in scaleQuestions" :key="`radar-point-${index}`" :cx="getDataPoint(index).x" :cy="getDataPoint(index).y" r="4" fill="#202424" />
                    <text v-for="(item, index) in scaleQuestions" :key="item.short" :x="getLabelPos(index).x" :y="getLabelPos(index).y" :text-anchor="getLabelAnchor(index)" dominant-baseline="middle" class="radar-label">
                      {{ item.short }} {{ (reportRadarScores[index] * 2).toFixed(1) }}
                    </text>
                  </svg>
                </div>
              </section>

              <section id="profile-ai" class="profile-dash-card profile-ai-analysis-card">
                <h3>AI 画像分析（结论）</h3>
                <div class="profile-ai-conclusion">
                  <figure
                    class="profile-ai-portrait"
                    :class="`profile-portrait-${reportPortraitState}`"
                    :aria-label="reportPortraitState === 'ready' ? '报告专属学习者头像' : '默认学习者头像'"
                  >
                    <img
                      :src="reportPortraitUrl || DEFAULT_PROFILE_PORTRAIT_URL"
                      :alt="reportPortraitState === 'ready' ? '由学习画像智能体生成的学习者人像' : '默认嵌入式学习者头像'"
                    />
                    <figcaption v-if="reportPortraitState === 'loading'" class="profile-portrait-status" role="status">
                      <span class="profile-portrait-spinner" aria-hidden="true"></span>
                      <small>{{ reportPortraitLoadingLabel }}</small>
                    </figcaption>
                    <figcaption v-else-if="reportPortraitState === 'missing'" class="profile-portrait-status" role="status">
                      <small>当前为默认头像</small>
                      <button type="button" title="生成报告专属头像" @click.stop="retryReportPortrait"><Sparkles :size="13" />生成</button>
                    </figcaption>
                    <figcaption v-else-if="reportPortraitState === 'failed'" class="profile-portrait-status profile-portrait-status-error" role="alert" :title="reportPortraitError">
                      <small>专属头像生成失败</small>
                      <button type="button" title="重试生成报告专属头像" aria-label="重试生成报告专属头像" @click.stop="retryReportPortrait"><RefreshCcw :size="14" /></button>
                    </figcaption>
                  </figure>
                  <p>{{ currentReport.aiAnalysis?.summary || '已结合学习目标、知识基础、学习偏好和薄弱知识点生成当前学习画像。' }}</p>
                </div>
                <div class="profile-ai-compare">
                  <div>
                    <strong>优势（Strengths）</strong>
                    <p v-for="item in reportStrengths" :key="item"><CheckCircle2 :size="13" />{{ item }}</p>
                  </div>
                  <div>
                    <strong>待提升（Weaknesses）</strong>
                    <p v-for="item in reportWeaknesses" :key="item"><TriangleAlert :size="13" />{{ item }}</p>
                  </div>
                </div>
              </section>
            </div>

            <div class="profile-dashboard-column profile-dashboard-right">
              <section id="profile-preference" class="profile-dash-card profile-preference-card">
                <h3>学习偏好与目标</h3>
                <div v-for="item in reportPreferenceRows" :key="item.label" class="profile-preference-row">
                  <span><component :is="item.icon" :size="25" :stroke-width="1.7" /></span>
                  <strong>{{ item.label }}</strong>
                  <p>{{ item.value }}</p>
                </div>
              </section>

              <section id="profile-plan" class="profile-dash-card profile-plan-card">
                <h3>推荐学习方案（基于画像定制）</h3>
                <div v-for="(item, index) in reportPlanRows" :key="item.title" class="profile-plan-row">
                  <span><component :is="item.icon" :size="24" :stroke-width="1.8" /></span>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.text }}</p>
                  <small>{{ String(index + 1).padStart(2, '0') }}</small>
                </div>
              </section>
            </div>
          </div>
        </div>
      </div>

      <!-- 评估画像 -->
      <div v-if="activeMenu === 'assess'" class="content-panel assess-panel">
        <div class="assess-layout assess-redesign">
          <section class="assessment-chat-shell">
            <div class="chat-area portrait-chat-area">
              <div class="chat-messages portrait-chat-messages" ref="chatMessagesRef">
                <div v-for="(m, mi) in displayChatMessages" :key="m.id || mi" :class="['chat-message-row', m.role]">
                  <span :class="['message-avatar', m.role]" aria-hidden="true">
                    <img v-if="m.role === 'bot'" :src="'/botlogo.png'" alt="" />
                    <img v-else src="/userlogo.png" alt="" />
                  </span>
                  <div :class="['chat-bubble', m.role]">
                    <span>{{ m.text }}</span>
                    <div v-if="m.attachments?.length" class="profile-message-attachments">
                      <a
                        v-for="attachment in m.attachments"
                        :key="attachment.id || attachment.name"
                        :href="attachment.url || undefined"
                        target="_blank"
                        rel="noopener noreferrer"
                        :title="attachment.name"
                      >
                        <component :is="profileAttachmentIcon(attachment.kind)" :size="13" />
                        <b>{{ attachment.name }}</b>
                      </a>
                    </div>
                    <small>{{ m.time }}</small>
                  </div>
                </div>
                <div
                  v-if="chatLoading && !chatStreaming"
                  class="chat-message-row bot thinking-message-row"
                  role="status"
                  aria-label="智能体正在思考"
                >
                  <span class="message-avatar bot" aria-hidden="true">
                    <img src="/botlogo.png" alt="" />
                  </span>
                  <div class="chat-bubble bot typing-indicator" aria-hidden="true">
                    <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                  </div>
                </div>
              </div>
              <div v-if="chatMsgs.length" class="chat-reset-row">
                <button class="chat-reset-btn" @click="resetChat">
                  <RotateCcw :size="15" :stroke-width="2.2" />
                  重新开始对话
                </button>
              </div>
              <div v-if="profileChatAttachments.length" class="profile-pending-attachments">
                <span v-for="(file, index) in profileChatAttachments" :key="`${file.name}-${file.lastModified}-${index}`">
                  <component :is="profileAttachmentIcon(profileFileKind(file))" :size="14" />
                  <b>{{ file.name }}</b>
                  <button type="button" :title="`移除 ${file.name}`" @click="removeProfileAttachment(index)">×</button>
                </span>
              </div>
              <div class="chat-input-row">
                <input ref="profileImageInputRef" type="file" accept="image/*" multiple hidden @change="queueProfileAttachments" />
                <input ref="profileVideoInputRef" type="file" accept="video/*" multiple hidden @change="queueProfileAttachments" />
                <input ref="profileFileInputRef" type="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.md" multiple hidden @change="queueProfileAttachments" />
                <div class="profile-input-tools">
                  <button type="button" title="添加图片" aria-label="添加图片" @click="profileImageInputRef?.click()"><ImagePlus :size="18" /></button>
                  <button type="button" title="添加视频" aria-label="添加视频" @click="profileVideoInputRef?.click()"><Video :size="18" /></button>
                  <button type="button" title="添加文件" aria-label="添加文件" @click="profileFileInputRef?.click()"><Paperclip :size="18" /></button>
                </div>
                <input
                  v-model="chatInput"
                  class="chat-input"
                  :placeholder="chatLoading ? 'AI正在思考...' : '输入你的学习背景或问题...'"
                  :disabled="chatLoading"
                  @keydown.enter="sendChat"
                />
                <button class="chat-send" @click="sendChat" :disabled="chatLoading || (!chatInput.trim() && !profileChatAttachments.length)">
                  <SendHorizontal :size="22" :stroke-width="2.15" />
                </button>
              </div>
            </div>
          </section>

          <aside class="profile-portrait-panel">
            <div class="portrait-panel-head">
              <div>
                <p class="chat-eyebrow">学习画像</p>
                <h3>数字人脸画像</h3>
              </div>
            </div>

            <div class="portrait-summary">
              <div class="portrait-score-ring" :style="{ '--score': `${profileMatchScore}%` }">
                <strong>{{ completedProfileDimensionCount }}/{{ profileDimensionKeys.length }}</strong>
                <em>已完成维度</em>
              </div>
              <div class="portrait-summary-copy">
                <span>上次更新：{{ lastPortraitUpdate ? formatTime(lastPortraitUpdate) : '等待对话' }}</span>
              </div>
            </div>

            <div class="data-face-wrap">
              <svg class="profile-face-links" viewBox="0 0 430 430" aria-hidden="true">
                <g
                  v-for="tag in profileFaceDimensionTags"
                  :key="`${tag.name}-line`"
                  class="face-link-group"
                >
                  <polyline
                    :class="['face-link-line', { done: tag.done }]"
                    :points="tag.line.points"
                  />
                  <circle
                    :class="['face-link-anchor', { done: tag.done }]"
                    :cx="tag.line.endX"
                    :cy="tag.line.endY"
                    r="3.2"
                  />
                </g>
              </svg>
              <div
                class="profile-face-stage"
                role="img"
                aria-label="由点阵区块逐步补全的学习画像人脸"
              >
                <svg class="profile-face-vector" viewBox="0 0 218 282" aria-hidden="true">
                  <g class="profile-face-dots" :style="{ '--portrait-progress': portraitCompletionRatio }">
                    <ellipse cx="109" cy="135" rx="72" ry="112" />
                    <path d="M58 103 Q78 88 98 103 M120 103 Q140 88 160 103" />
                    <path d="M62 119 Q80 132 98 119 M120 119 Q138 132 156 119" />
                    <path d="M109 116 Q101 151 109 162 Q117 164 123 159" />
                    <path d="M83 185 Q109 201 135 185 Q109 212 83 185" />
                    <path d="M69 225 Q109 256 149 225" />
                  </g>
                </svg>
              </div>
              <button
                v-for="tag in profileFaceDimensionTags"
                :key="tag.name"
                type="button"
                :class="['face-dimension-tag', tag.side, {
                  done: tag.done,
                  selected: selectedFaceDimensionName === tag.name,
                }]"
                :style="tag.style"
                :aria-label="`查看${tag.name}详细信息`"
                :aria-pressed="selectedFaceDimensionName === tag.name"
                aria-controls="profile-face-dimension-detail"
                @click="selectFaceDimension(tag)"
              >
                <span>{{ tag.index }}</span>
                <b>{{ tag.name }}</b>
              </button>
              <section
                v-if="selectedFaceDimension"
                id="profile-face-dimension-detail"
                class="face-dimension-detail"
                role="region"
                aria-live="polite"
                :style="selectedFaceDimensionDetailStyle"
                :aria-label="`${selectedFaceDimension.name}详细信息`"
              >
                <header>
                  <span>{{ selectedFaceDimension.index }}</span>
                  <div>
                    <small :class="{ done: selectedFaceDimension.done }">
                      {{ selectedFaceDimension.done ? '已采集' : '待补充' }}
                    </small>
                    <strong>{{ selectedFaceDimension.name }}</strong>
                  </div>
                  <button type="button" title="关闭详细信息" aria-label="关闭详细信息" @click.stop="closeFaceDimension">
                    <X :size="16" />
                  </button>
                </header>
                <p>{{ selectedFaceDimension.value }}</p>
              </section>
            </div>
          </aside>
        </div>

        <!-- 量表问卷 -->
        <div v-if="false && activeOrb === 'scale'" class="assessment-modal-surface">
          <div class="form-card collect-panel-card scale-form-card">
            <div class="chat-panel-head">
              <div>
                <p class="chat-eyebrow">学习画像数据采集</p>
                <h3 class="form-title">量表问卷</h3>
              </div>
              <button class="chat-back-btn" type="button" @click="activeOrb = null">返回画像</button>
            </div>
            <div class="scale-list">
              <div v-for="(q, qi) in scaleQuestions" :key="qi" class="scale-item">
                <p class="scale-q">{{ qi + 1 }}. {{ q.text }}</p>
                <div class="scale-options">
                  <label v-for="score in 5" :key="score" class="scale-opt">
                    <input v-model.number="scaleAnswers[qi]" type="radio" :name="'scale-' + qi" :value="score" />
                    <span class="opt-dot"></span>
                    <span class="opt-text">{{ score }}</span>
                  </label>
                </div>
                <div class="scale-labels">
                  <span>较弱</span>
                  <span>较强</span>
                </div>
              </div>
            </div>
            <button class="form-submit" type="button" @click="submitScale">提交量表问卷</button>
          </div>
        </div>

        <!-- 上传作业完成情况 -->
        <div v-else-if="false && activeOrb === 'upload'" class="assessment-modal-surface">
          <div class="form-card collect-panel-card upload-panel-card">
            <div class="chat-panel-head">
              <div>
                <p class="chat-eyebrow">学习画像数据采集</p>
                <h3 class="form-title">上传作业完成情况</h3>
              </div>
              <button class="chat-back-btn" type="button" @click="activeOrb = null">返回画像</button>
            </div>
            <div
              class="upload-zone"
              @dragover.prevent
              @drop.prevent="onDrop"
              @click="triggerUpload"
            >
              <input ref="fileInput" type="file" accept="image/*,.pdf" multiple hidden @change="onFileSelect" />
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="upload-icon">
                <path d="M12 16V4m0 0L8 8m4-4l4 4M4 14v4a2 2 0 002 2h12a2 2 0 002-2v-4" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <p class="upload-text">拖拽文件至此处，或 <span class="upload-link">点击上传</span></p>
              <p class="upload-hint">支持 JPG / PNG / PDF 格式</p>
            </div>
            <div v-if="uploadFiles.length" class="file-list">
              <div v-for="(f, fi) in uploadFiles" :key="fi" class="file-item">
                <span class="file-name">{{ f.name }}</span>
                <span class="file-size">{{ formatSize(f.size) }}</span>
                <button class="file-remove" type="button" @click.stop="uploadFiles.splice(fi, 1)">×</button>
              </div>
            </div>
            <button class="form-submit" type="button" :disabled="!uploadFiles.length" @click="submitUpload">确认上传</button>
          </div>
        </div>
      </div>

      <!-- 历史报告 -->
      <div v-if="activeMenu === 'history'" class="content-panel history-panel">
        <!-- 空状态 -->
        <div v-if="!historyReports.length" class="history-shell history-empty-shell">
          <div class="history-list-head">
            <div>
              <h2>历史记录</h2>
              <p>当前画像会统一用于学习路径、资源、题库、辅导、面试和效果评估。</p>
            </div>
            <button
              class="history-create-button"
              type="button"
              :disabled="!!profileActionBusy"
              @click="createNewLearningProfile"
            >
              <Plus :size="18" />
              <span>{{ profileActionBusy === 'create' ? '正在创建' : '新建学习画像' }}</span>
            </button>
          </div>
          <div class="empty-state history-empty-state">
            <div class="empty-icon">
              <Clock3 :size="34" :stroke-width="1.8" />
            </div>
            <p class="empty-text">暂无历史报告</p>
            <p class="empty-hint">完成评估后将自动生成历史记录</p>
          </div>
        </div>

        <!-- 历史报告列表 -->
        <div v-else class="history-shell history-list">
          <div class="history-list-head">
            <div>
              <h2>历史记录</h2>
              <p>当前画像会统一用于学习路径、资源、题库、辅导、面试和效果评估。</p>
            </div>
            <button
              class="history-create-button"
              type="button"
              :disabled="!!profileActionBusy"
              @click="createNewLearningProfile"
            >
              <Plus :size="18" />
              <span>{{ profileActionBusy === 'create' ? '正在创建' : '新建学习画像' }}</span>
            </button>
          </div>
          <div class="history-items">
            <div
              v-for="report in historyReports"
              :key="report.id"
              :class="['history-item', { active: report.isActive }]"
              @click="viewHistoryReport(report)"
            >
              <div class="history-item-time">
                <span class="history-time-icon">
                  <Clock3 :size="23" :stroke-width="1.9" />
                </span>
                <div>
                  <strong>{{ report.profileName || '学习画像' }}</strong>
                  <span>{{ formatTime(report.timestamp) }}</span>
                </div>
              </div>
              <div class="history-item-summary">
                <span v-if="report.isActive" class="history-badge current">当前使用</span>
                <span class="history-badge version">v{{ report.version || 1 }}</span>
                <span class="history-badge done">画像报告已生成</span>
                <span class="history-badge done">{{ getReportDimensionCount(report) }}/10 维度</span>
                <span v-if="report.aiAnalysis?.learningStyle" class="history-badge done">{{ report.aiAnalysis.learningStyle }}</span>
                <span :class="['history-badge', 'path', { ready: report.learningPath?.hasPath }]">
                  <Map :size="14" />
                  {{ report.learningPath?.hasPath ? `${report.learningPath.weekCount || 0} 周独立路径` : '独立路径待生成' }}
                </span>
                <span v-if="report.parentReportId" class="history-parent">
                  <GitBranch :size="14" />
                  由报告 #{{ report.parentReportId }} 更新
                </span>
              </div>
              <div class="history-item-actions">
                <button
                  title="打开对应学习路径"
                  :disabled="!!profileActionBusy"
                  @click.stop="openProfilePath(report)"
                >
                  <Map :size="17" />
                </button>
                <button
                  v-if="!report.isActive"
                  title="设为当前画像"
                  :disabled="!!profileActionBusy"
                  @click.stop="activateProfileVersion(report)"
                >
                  <CheckCircle2 :size="17" />
                </button>
                <button
                  title="基于此画像更新"
                  :disabled="!!profileActionBusy"
                  @click.stop="refreshProfileVersion(report)"
                >
                  <RefreshCcw :size="17" />
                </button>
                <button
                  title="重命名画像"
                  :disabled="!!profileActionBusy"
                  @click.stop="renameProfileVersion(report)"
                >
                  <Pencil :size="16" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 数据采集表单区 -->
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Activity,
  BookOpen,
  Boxes,
  BrainCircuit,
  Bug,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  Clock4,
  Code2,
  Cpu,
  FileText,
  Flame,
  Gauge,
  GitBranch,
  Goal,
  Hand,
  ImagePlus,
  Library,
  ListChecks,
  Map,
  MessageCircle,
  Network,
  Paperclip,
  Pencil,
  Plus,
  RefreshCcw,
  Repeat2,
  RotateCcw,
  Rocket,
  Search,
  SendHorizontal,
  SlidersHorizontal,
  Sparkles,
  Target,
  TriangleAlert,
  UploadCloud,
  UserRound,
  UserRoundCheck,
  Video,
  Wrench,
  X,
} from 'lucide-vue-next'
import DigitalHumanAvatar from '../components/DigitalHumanAvatar.vue'
import {
  analyzeLearningProfileStream,
  activateLearningProfile,
  getLearningProfiles,
  getLearningProfileSession,
  getLearningProfileSessions,
  getLearningProfilePortraitFile,
  getLearningProfilePortraitStatus,
  generateLearningProfilePortrait,
  refreshLearningProfile,
  renameLearningProfile,
  resetLearningProfile,
  requestLearningProfileBackgroundChat,
  resetLearningProfileBackgroundChat,
  createLearningProfileSession,
  sendLearningProfileSessionMessage,
  streamLearningProfileBackgroundChat,
  uploadMultimodalInputs,
} from '../services/api.js'
import { useGlobalDebug } from '../stores/globalDebug.js'
import {
  buildProfileSessionChatMessages,
  INITIAL_CHAT_OPENING,
} from '../utils/learningProfileChat.js'

const LS_KEY = 'learningProfileData'
const router = useRouter()
const route = useRoute()
const { addLog, setSection } = useGlobalDebug()

// --- AI ???? ---
const chatLoading = ref(false)
const chatStreaming = ref(false)
const chatInitializing = ref(false)
const chatHistory = ref([]) // ?????????
const profileSessions = ref([])
const activeProfileSessionId = ref(null)
const CHAT_CONNECTING_TEXT = '正在连接学习背景智能体，请稍候...'
const CHAT_REPLY_PENDING_TEXT = '正在整理你的学习背景信息...'
const LLM_CHAT_TIMEOUT_MS = 90000
let initialChatRequestStarted = false
let chatMessageIdSeed = 0

function createChatMessageId(prefix = 'chat') {
  chatMessageIdSeed += 1
  return `${prefix}-${Date.now()}-${chatMessageIdSeed}`
}

function isTransientChatText(text) {
  const value = String(text || '').trim()
  return value === CHAT_CONNECTING_TEXT || value === CHAT_REPLY_PENDING_TEXT
}

function settleTransientBotMessage(botMessage, message) {
  if (!botMessage || !isTransientChatText(botMessage.text)) return false
  setChatBotMessage(botMessage, message, 'system')
  persistChatState({ chatTimestamp: Date.now() })
  return true
}

function setChatBotMessage(botMessage, text, source = 'llm') {
  const messageId = botMessage?.id
  const index = chatMsgs.value.findIndex(item => item === botMessage || (messageId && item.id === messageId))
  const targetIndex = index >= 0
    ? index
    : chatMsgs.value.map((item, itemIndex) => ({ item, itemIndex })).reverse()
      .find(({ item }) => item.role === 'bot' && (isTransientChatText(item.text) || item.source === 'llm-streaming'))?.itemIndex
  if (typeof targetIndex !== 'number' || targetIndex < 0) {
    if (botMessage) {
      botMessage.text = text
      botMessage.timestamp = botMessage.timestamp || Date.now()
      botMessage.source = source
    }
    return
  }
  const current = chatMsgs.value[targetIndex]
  Object.assign(current, {
    id: current.id || messageId || createChatMessageId('bot'),
    text,
    timestamp: current.timestamp || Date.now(),
    source: source === 'llm' ? 'llm-streaming' : source,
  })
  chatMsgs.value = chatMsgs.value.slice()
}

// --- AI 鍒嗘瀽閰嶇疆 ---
const aiAnalyzing = ref(false)
const analysisStreamEvents = ref([])
const analysisStreamMessage = ref('')
const analysisLogRef = ref(null)
const analysisStreamStartedAt = ref(0)

// --- Toast ---
const toastMsg = ref('')
let toastTimer = null
function showToast(msg) {
  toastMsg.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMsg.value = '' }, 2000)
}

// --- localStorage helpers ---
function loadProfile() {
  try {
    const raw = localStorage.getItem(LS_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch { return {} }
}
function saveProfile(patch) {
  const current = loadProfile()
  const merged = { ...current, ...patch }
  localStorage.setItem(LS_KEY, JSON.stringify(merged))
  profileData.value = merged
}

function replaceProfile(profile) {
  const nextProfile = profile && typeof profile === 'object' ? { ...profile } : {}
  localStorage.setItem(LS_KEY, JSON.stringify(nextProfile))
  profileData.value = nextProfile
}

function clearProfileCache() {
  localStorage.removeItem(LS_KEY)
  localStorage.removeItem('resourceEvaluations')
  localStorage.removeItem('learning-profile-switched')
  profileData.value = {}
  viewingHistory.value = null
  chatMsgs.value = []
  chatHistory.value = []
}

const profileData = ref(loadProfile())

const profileDimensionKeys = [
  '专业/课程背景',
  '学习目标',
  '当前知识基础',
  '学习进度',
  '薄弱知识点',
  '易错点类型',
  '学习风格/认知偏好',
  '资源形式偏好',
  '可投入时间',
  '难度接受程度',
]

const profileDimensionAliases = {
  '专业/课程背景': ['专业', '专业背景', '课程背景', 'courseBackground', 'major', 'course'],
  '学习目标': ['目标', 'learningGoal', 'learningGoals', 'goals'],
  '当前知识基础': ['知识基础', '当前基础', 'knowledgeBase', 'currentKnowledge'],
  '学习进度': ['进度', 'learningProgress', 'progress'],
  '薄弱知识点': ['薄弱点', '弱项', 'weakPoints', 'weaknesses'],
  '易错点类型': ['易错点', '错因类型', 'errorTypes', 'mistakeTypes'],
  '学习风格/认知偏好': ['学习风格', '认知偏好', 'learningStyle', 'learningPreference'],
  '资源形式偏好': ['资源偏好', '资源形式', 'resourcePreference', 'resourcePreferences', 'preferredResources'],
  '可投入时间': ['投入时间', '学习时间', 'availableTime', 'timeCommitment'],
  '难度接受程度': ['难度偏好', '难度', 'difficultyPreference', 'difficulty'],
}

function isProfileDimensionFilled(value) {
  if (Array.isArray(value)) return value.length > 0
  return String(value || '').trim().length > 0
}

function normalizeStudentProfileDimensions(profile) {
  const source = profile && typeof profile === 'object' && !Array.isArray(profile) ? profile : {}
  const normalized = {}
  profileDimensionKeys.forEach((key) => {
    const aliases = [key, ...(profileDimensionAliases[key] || [])]
    const alias = aliases.find(candidate => isProfileDimensionFilled(source[candidate]))
    normalized[key] = alias ? source[alias] : undefined
  })
  normalized['补充信息'] = source['补充信息'] || {}
  return normalized
}

function formatProfileValue(value) {
  if (Array.isArray(value)) {
    return value.map(item => String(item || '').trim()).filter(Boolean).join('、') || '已采集'
  }
  if (value && typeof value === 'object') {
    return Object.entries(value)
      .filter(([key, item]) => key !== '补充信息' && String(item || '').trim())
      .map(([key, item]) => `${key}：${Array.isArray(item) ? item.join('、') : item}`)
      .join('；') || '已采集'
  }
  return String(value || '').trim() || '已采集'
}

const chatStudentProfile = computed(() => (
  profileData.value.chatStudentProfile && typeof profileData.value.chatStudentProfile === 'object'
    ? normalizeStudentProfileDimensions(profileData.value.chatStudentProfile)
    : {}
))

const completedProfileDimensionCount = computed(() => (
  profileDimensionKeys.filter(key => isProfileDimensionFilled(chatStudentProfile.value[key])).length
))

function persistChatState(extra = {}) {
  saveProfile({
    chatMessages: chatMsgs.value
      .filter(item => String(item.text || '').trim() && !isTransientChatText(item.text))
      .map(item => ({
        id: item.id || createChatMessageId(item.role || 'message'),
        role: item.role,
        text: String(item.text || ''),
        time: item.time || '',
        timestamp: item.timestamp || null,
        source: item.source || '',
        attachments: Array.isArray(item.attachments) ? item.attachments : [],
      })),
    chatHistory: chatHistory.value.map(item => ({
      role: item.role,
      content: String(item.content || ''),
    })),
    ...extra,
  })
}

// --- 鍘嗗彶鎶ュ憡 ---
const historyReports = ref([])
const viewingHistory = ref(null) // ?????????
const profileActionBusy = ref('')
const profileHistoryLoaded = ref(false)

function isGeneratedProfileReport(report) {
  const analysis = report?.aiAnalysis
  if (!analysis || typeof analysis !== 'object') return false
  return Boolean(
    analysis.learningStyle
    || analysis.summary
    || (Array.isArray(analysis.strengths) && analysis.strengths.length)
    || (Array.isArray(analysis.weaknesses) && analysis.weaknesses.length)
    || (Array.isArray(analysis.recommendations) && analysis.recommendations.length),
  )
}

async function loadHistoryReports() {
  try {
    const data = await getLearningProfiles()
    historyReports.value = Array.isArray(data.profiles) ? data.profiles : []
    historyReports.value.forEach(seedReportPortraitState)
    const activeProfile = historyReports.value.find(report => report.isActive) || null
    if (activeProfile && isGeneratedProfileReport(activeProfile)) {
      const currentId = Number(profileData.value?.id || 0)
      const activeId = Number(activeProfile.id || 0)
      if (!isGeneratedProfileReport(profileData.value) || currentId !== activeId) {
        replaceProfile(activeProfile)
      }
    } else if (historyReports.value.length === 0 && isGeneratedProfileReport(profileData.value)) {
      // A reset removes database reports. Do not render a stale browser cache as a report.
      clearProfileCache()
    }
    if (route.query.menu === 'report' && historyReports.value.length) {
      viewingHistory.value = activeProfile || historyReports.value[0]
      activeMenu.value = 'report'
      activeOrb.value = null
    }
  } catch {
    historyReports.value = []
  } finally {
    profileHistoryLoaded.value = true
  }
}

function viewHistoryReport(report) {
  seedReportPortraitState(report)
  viewingHistory.value = report
  activeMenu.value = 'report'
}

async function activateProfileVersion(report) {
  if (!report?.id || profileActionBusy.value) return
  profileActionBusy.value = `activate-${report.id}`
  try {
    const data = await activateLearningProfile(report.id)
    const profile = data?.profile || report
    replaceProfile(profile)
    if (data?.pathSwitched) notifyLearningPathProfileSwitched(profile)
    await loadHistoryReports()
    viewingHistory.value = historyReports.value.find(item => item.id === profile.id) || profile
    activeMenu.value = 'report'
    showToast(`已切换到 ${profile.profileName || '学习画像'} v${profile.version || 1}`)
  } catch (error) {
    showToast(error?.response?.data?.msg || error?.message || '切换画像失败')
  } finally {
    profileActionBusy.value = ''
  }
}

async function openProfilePath(report) {
  if (!report?.id || profileActionBusy.value) return
  profileActionBusy.value = `path-${report.id}`
  try {
    let profile = report
    if (!report.isActive) {
      const data = await activateLearningProfile(report.id)
      profile = data?.profile || report
      replaceProfile(profile)
      notifyLearningPathProfileSwitched(profile)
      await loadHistoryReports()
    }
    await router.push({ name: 'learning-path-stage-detail', params: { stageId: 'overview' } })
  } catch (error) {
    showToast(error?.response?.data?.msg || error?.message || '打开对应学习路径失败')
  } finally {
    profileActionBusy.value = ''
  }
}

async function createNewLearningProfile() {
  if (profileActionBusy.value) return
  profileActionBusy.value = 'create'
  try {
    await resetLearningProfile()
    localStorage.removeItem(LS_KEY)
    localStorage.removeItem('learning-profile-switched')
    profileData.value = {}
    viewingHistory.value = null
    Object.keys(scaleAnswers).forEach(key => delete scaleAnswers[key])
    uploadFiles.value = []
    profileChatAttachments.value = []
    chatMsgs.value = []
    chatHistory.value = []
    analysisStreamEvents.value = []
    analysisStreamMessage.value = ''
    aiAnalyzing.value = false
    chatLoading.value = false
    chatStreaming.value = false
    chatInitializing.value = false
    initialChatRequestStarted = false
    autoReportStarted = false
    resetReportPortraitView()
    await startNewProfileSession()
    await loadHistoryReports()
    activeMenu.value = 'assess'
    activeOrb.value = null
    await router.replace({ name: 'learning-profile', query: { menu: 'assess' } })
    showToast('已创建新的学习画像，历史画像与独立路径均已保留')
  } catch (error) {
    showToast(error?.response?.data?.msg || error?.message || '新建学习画像失败')
  } finally {
    profileActionBusy.value = ''
  }
}

function notifyLearningPathProfileSwitched(profile) {
  try {
    window.localStorage.setItem('learning-profile-switched', JSON.stringify({
      profileId: profile?.id || '',
      profileName: profile?.profileName || '学习画像',
      version: profile?.version || 1,
      switchedAt: Date.now(),
    }))
  } catch {}
}

async function refreshProfileVersion(report) {
  if (!report?.id || profileActionBusy.value) return
  router.push({ name: 'effect-assessment', query: { profileId: report.id } })
}

async function renameProfileVersion(report) {
  if (!report?.id || profileActionBusy.value) return
  const profileName = prompt('输入新的画像名称', report.profileName || '学习画像')
  if (profileName === null || !profileName.trim()) return
  profileActionBusy.value = `rename-${report.id}`
  try {
    const data = await renameLearningProfile(report.id, profileName.trim())
    const profile = data?.profile
    await loadHistoryReports()
    if (viewingHistory.value?.id === report.id) {
      viewingHistory.value = historyReports.value.find(item => item.id === report.id) || profile
    }
    if (profile?.isActive) replaceProfile({ ...profileData.value, profileName: profile.profileName })
    showToast('画像名称已更新')
  } catch (error) {
    showToast(error?.response?.data?.msg || error?.message || '重命名失败')
  } finally {
    profileActionBusy.value = ''
  }
}

function getReportDimensionCount(report) {
  if (Array.isArray(report?.completedProfileDimensions) && report.completedProfileDimensions.length) {
    return Math.min(profileDimensionKeys.length, report.completedProfileDimensions.length)
  }
  const profile = report?.chatStudentProfile
  if (profile && typeof profile === 'object') {
    return profileDimensionKeys.filter(key => isProfileDimensionFilled(profile[key])).length
  }
  return report?.chatBackground ? profileDimensionKeys.length : 0
}

// --- Orb done indicators ---
const orbDone = computed(() => ({
  scale: completedProfileDimensionCount.value >= 4,
  upload: completedProfileDimensionCount.value >= 7,
  chat: !!profileData.value.chatBackground,
}))

// --- Completion tracking ---
const completedCount = computed(() => {
  return completedProfileDimensionCount.value
})

const profileDimensionTotal = computed(() => profileDimensionKeys.length)

const reportProgressPercent = computed(() => {
  const total = profileDimensionTotal.value || 1
  return Math.min(100, Math.round((completedCount.value / total) * 100))
})

const allCompleted = computed(() => completedProfileDimensionCount.value >= profileDimensionKeys.length)

const lastPortraitUpdate = computed(() => (
  profileData.value.chatTimestamp ||
  profileData.value.uploadTimestamp ||
  profileData.value.scaleTimestamp ||
  profileData.value.timestamp ||
  ''
))

const profileChatCompleteness = computed(() => {
  const stored = Number(profileData.value.chatCompleteness)
  const storedRatio = Number.isFinite(stored) ? Math.min(1, Math.max(0, stored / 100)) : 0
  const studentProfile = chatStudentProfile.value
  const profileKeys = studentProfile
    ? Object.keys(studentProfile).filter(key => key !== '补充信息')
    : []
  const profileFilled = profileKeys.filter((key) => {
    const value = studentProfile?.[key]
    if (Array.isArray(value)) return value.length > 0
    return String(value || '').trim().length > 0
  }).length
  const profileRatio = profileKeys.length ? profileFilled / profileKeys.length : 0
  return Math.max(storedRatio, profileRatio)
})

const profileMatchScore = computed(() => {
  if (!profileDimensionKeys.length) return 0
  return Math.round((completedProfileDimensionCount.value / profileDimensionKeys.length) * 100)
})

const displayChatMessages = computed(() => {
  return chatMsgs.value.map((item, index) => ({
    ...item,
    id: item.id || `${item.role || 'message'}-${item.timestamp || index}-${index}`,
    time: item.time || formatChatMessageTime(item.timestamp, index),
  }))
})

const avatarDisplayStatus = computed(() => {
  if (activeMenu.value !== 'assess') return '待机'
  return learningAvatarStatus.value || '连接中'
})

const portraitCompletionRatio = computed(() => profileMatchScore.value / 100)

const FACE_LINK_CANVAS = { width: 430, height: 430, faceWidth: 218, faceTop: 44 }

const profileFaceAnchors = {
  '专业/课程背景': [109, 35],
  '学习目标': [65, 78],
  '当前知识基础': [153, 78],
  '学习进度': [109, 116],
  '薄弱知识点': [76, 120],
  '易错点类型': [142, 120],
  '学习风格/认知偏好': [72, 168],
  '资源形式偏好': [109, 154],
  '可投入时间': [82, 226],
  '难度接受程度': [136, 226],
}

const profileFaceTagLayout = {
  '专业/课程背景': { side: 'top', tag: [216, 6], width: 132 },
  '学习目标': { side: 'left', tag: [4, 84], width: 112 },
  '当前知识基础': { side: 'right', tag: [430, 76], width: 124 },
  '学习进度': { side: 'right', tag: [426, 128], width: 106 },
  '薄弱知识点': { side: 'left', tag: [0, 174], width: 112 },
  '易错点类型': { side: 'right', tag: [430, 196], width: 112 },
  '学习风格/认知偏好': { side: 'left', tag: [8, 270], width: 142 },
  '资源形式偏好': { side: 'right', tag: [430, 286], width: 124 },
  '可投入时间': { side: 'bottom', tag: [120, 342], width: 112 },
  '难度接受程度': { side: 'bottom', tag: [326, 332], width: 124 },
}

const profileFaceDimensionTags = computed(() => profileDimensionKeys.map((name, index) => {
  const layout = profileFaceTagLayout[name] || { side: 'right', tag: [486, 28 + index * 24] }
  const done = isProfileDimensionFilled(chatStudentProfile.value[name])
  const raw = chatStudentProfile.value[name]
  const hintText = Array.isArray(raw) ? raw.join('、') : String(raw || '')
  const [tagX, tagY] = layout.tag
  const tagWidth = Number(layout.width) || 116
  const tagHeight = 34
  const faceWidth = FACE_LINK_CANVAS.faceWidth
  const faceLeft = (FACE_LINK_CANVAS.width - faceWidth) / 2
  const faceTop = FACE_LINK_CANVAS.faceTop
  const [localAnchorX, localAnchorY] = profileFaceAnchors[name] || [109, 141]
  const anchorX = faceLeft + localAnchorX
  const anchorY = faceTop + localAnchorY
  const tagEdgeX = layout.side === 'left'
    ? tagX + tagWidth
    : layout.side === 'right'
      ? tagX - tagWidth
      : tagX
  const tagEdgeY = layout.side === 'top'
    ? tagY + tagHeight
    : layout.side === 'bottom'
      ? tagY
      : tagY + tagHeight / 2
  const startX = Math.round(tagEdgeX)
  const startY = Math.round(tagEdgeY)
  const endX = Math.round(anchorX)
  const endY = Math.round(anchorY)
  let points = ''
  if (layout.side === 'left' || layout.side === 'right') {
    const direction = layout.side === 'left' ? 1 : -1
    const available = Math.max(8, Math.min(18, Math.abs(endX - startX) / 2))
    const corridorX = Math.round(startX + direction * available)
    points = `${startX},${startY} ${corridorX},${startY} ${corridorX},${endY} ${endX},${endY}`
  } else {
    const faceBottom = faceTop + faceHeight
    const corridorY = layout.side === 'top'
      ? Math.round(Math.min(endY - 8, startY + 18))
      : Math.round(faceBottom + 2)
    points = `${startX},${startY} ${startX},${corridorY} ${endX},${corridorY} ${endX},${endY}`
  }
  return {
    name,
    index: String(index + 1).padStart(2, '0'),
    side: layout.side,
    tagX,
    tagY,
    tagWidth,
    tagHeight,
    done,
    hint: hintText ? `${name}: ${hintText}` : `${name}: 待对话补齐`,
    value: done ? formatProfileValue(raw) : '该维度尚未采集，请继续通过对话补充相关信息。',
    style: {
      left: `${tagX}px`,
      top: `${tagY}px`,
      '--tag-width': `${tagWidth}px`,
    },
    line: {
      points,
      endX,
      endY,
    },
  }
}))

const selectedFaceDimensionName = ref('')
const selectedFaceDimension = computed(() => (
  profileFaceDimensionTags.value.find(tag => tag.name === selectedFaceDimensionName.value) || null
))

const selectedFaceDimensionDetailStyle = computed(() => {
  const tag = selectedFaceDimension.value
  if (!tag) return {}
  const cardWidth = 200
  const cardHeight = 166
  const gap = 14
  const sideGap = 10
  const canvasWidth = FACE_LINK_CANVAS.width
  const canvasHeight = FACE_LINK_CANVAS.height
  const faceWidth = FACE_LINK_CANVAS.faceWidth
  const faceHeight = 282
  const faceLeft = (canvasWidth - faceWidth) / 2
  const faceTop = FACE_LINK_CANVAS.faceTop
  const faceRect = {
    left: faceLeft,
    top: faceTop,
    right: faceLeft + faceWidth,
    bottom: faceTop + faceHeight,
  }
  const tagX = Number(tag.tagX || 0)
  const tagY = Number(tag.tagY || 0)
  const tagWidth = Number(tag.tagWidth || 116)
  const tagHeight = Number(tag.tagHeight || 34)
  const side = String(tag.side || 'right')
  const visualLeft = side === 'right'
    ? tagX - tagWidth
    : side === 'top' || side === 'bottom'
      ? tagX - tagWidth / 2
      : tagX
  const visualRight = visualLeft + tagWidth
  const visualCenterX = visualLeft + tagWidth / 2
  const visualCenterY = tagY + tagHeight / 2
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value))
  const sideY = clamp(visualCenterY - cardHeight / 2, -10, canvasHeight + 44 - cardHeight)
  const centerX = clamp(visualCenterX - cardWidth / 2, -18, canvasWidth + 18 - cardWidth)
  const belowFaceY = faceRect.bottom + gap
  const aboveFaceY = faceRect.top - cardHeight - gap
  const positionCandidates = {
    left: [
      { x: faceRect.left - cardWidth - sideGap, y: sideY, arrow: 'right' },
      { x: centerX, y: belowFaceY, arrow: 'top' },
      { x: centerX, y: aboveFaceY, arrow: 'bottom' },
    ],
    right: [
      { x: faceRect.right + sideGap, y: sideY, arrow: 'left' },
      { x: centerX, y: belowFaceY, arrow: 'top' },
      { x: centerX, y: aboveFaceY, arrow: 'bottom' },
    ],
    top: [
      { x: centerX, y: tagY - cardHeight - gap, arrow: 'bottom' },
      { x: visualCenterX < canvasWidth / 2 ? faceRect.left - cardWidth - sideGap : faceRect.right + sideGap, y: sideY, arrow: visualCenterX < canvasWidth / 2 ? 'right' : 'left' },
      { x: centerX, y: belowFaceY, arrow: 'top' },
    ],
    bottom: [
      { x: centerX, y: tagY + tagHeight + gap, arrow: 'top' },
      { x: visualCenterX < canvasWidth / 2 ? faceRect.left - cardWidth - sideGap : faceRect.right + sideGap, y: sideY, arrow: visualCenterX < canvasWidth / 2 ? 'right' : 'left' },
      { x: centerX, y: aboveFaceY, arrow: 'bottom' },
    ],
  }
  const overlapPadding = 8
  const paddedFaceRect = {
    left: faceRect.left - overlapPadding,
    top: faceRect.top - overlapPadding,
    right: faceRect.right + overlapPadding,
    bottom: faceRect.bottom + overlapPadding,
  }
  const detailBounds = {
    left: -140,
    top: -24,
    right: canvasWidth + 116,
    bottom: canvasHeight + 70,
  }
  const rectFromCandidate = candidate => ({
    left: candidate.x,
    top: candidate.y,
    right: candidate.x + cardWidth,
    bottom: candidate.y + cardHeight,
  })
  const rectsOverlap = (a, b) => (
    a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top
  )
  const outOfBoundsAmount = rect => (
    Math.max(0, detailBounds.left - rect.left) +
    Math.max(0, rect.right - detailBounds.right) +
    Math.max(0, detailBounds.top - rect.top) +
    Math.max(0, rect.bottom - detailBounds.bottom)
  )
  const distanceFromTag = rect => (
    Math.abs((rect.left + rect.right) / 2 - visualCenterX) +
    Math.abs((rect.top + rect.bottom) / 2 - visualCenterY)
  )
  const candidates = positionCandidates[side] || positionCandidates.right
  const best = candidates
    .map((candidate, index) => {
      const rect = rectFromCandidate(candidate)
      const facePenalty = rectsOverlap(rect, paddedFaceRect) ? 100000 : 0
      const boundsPenalty = outOfBoundsAmount(rect) * 120
      const distancePenalty = distanceFromTag(rect)
      return {
        ...candidate,
        score: facePenalty + boundsPenalty + distancePenalty + index * 8,
      }
    })
    .sort((a, b) => a.score - b.score)[0] || { x: centerX, y: belowFaceY, arrow: 'top' }

  return {
    '--detail-x': `${Math.round(best.x)}px`,
    '--detail-y': `${Math.round(best.y)}px`,
    '--detail-width': `${cardWidth}px`,
    '--detail-arrow': best.arrow,
  }
})

function selectFaceDimension(tag) {
  selectedFaceDimensionName.value = String(tag?.name || '')
}

function closeFaceDimension() {
  selectedFaceDimensionName.value = ''
}

const abilityMetrics = computed(() => {
  return profileDimensionKeys.map((key) => {
    const filled = isProfileDimensionFilled(chatStudentProfile.value[key])
    const raw = chatStudentProfile.value[key]
    const hint = Array.isArray(raw) ? raw.join('、') : String(raw || '待对话补齐')
    return {
      name: key,
      hint: hint.length > 18 ? `${hint.slice(0, 18)}...` : hint,
      value: filled ? 100 : 18,
      icon: filled ? Sparkles : Activity,
    }
  })
})

const profileDimensionStatus = computed(() => (
  profileDimensionKeys.map(key => ({
    name: key,
    done: isProfileDimensionFilled(chatStudentProfile.value[key]),
  }))
))

// ???????????????????????
const currentReport = computed(() => {
  if (viewingHistory.value) return viewingHistory.value
  return profileData.value
})

const hasGeneratedReport = computed(() => isGeneratedProfileReport(currentReport.value))
const hasCurrentGeneratedReport = computed(() => isGeneratedProfileReport(profileData.value))
const currentReportStudentProfile = computed(() => {
  const reportProfile = currentReport.value?.chatStudentProfile
  if (reportProfile && typeof reportProfile === 'object') return reportProfile
  return chatStudentProfile.value
})
const reportPortraitUrl = ref('')
const DEFAULT_PROFILE_PORTRAIT_URL = '/default-profile-avatar.webp'
const reportPortraitStates = reactive({})
let reportPortraitObjectUrl = ''
let reportPortraitRequestToken = 0
const PROFILE_PORTRAIT_POLL_INTERVAL_MS = 2000
const PROFILE_PORTRAIT_POLL_TIMEOUT_MS = 190000

function portraitStateKey(report = currentReport.value || {}) {
  const reportId = Number(report?.id || 0)
  return reportId > 0 ? String(reportId) : `local-${String(report?.timestamp || 'current')}`
}

function normalizedReportPortraitState(report = currentReport.value || {}) {
  const status = String(report?.portrait?.status || '').trim()
  if (status === 'ready' || status === 'generating') return 'loading'
  if (status === 'failed') return 'failed'
  if (status === 'missing') return 'missing'
  return Number(report?.id || 0) > 0 ? 'missing' : 'failed'
}

const reportPortraitState = computed(() => {
  const storedState = reportPortraitStates[portraitStateKey()]?.status
  return storedState && storedState !== 'idle'
    ? storedState
    : normalizedReportPortraitState()
})
const reportPortraitError = computed(() => (
  reportPortraitStates[portraitStateKey()]?.error
    || currentReport.value?.portrait?.error
    || '画像人像生成失败，请重试'
))
const reportPortraitLoadingLabel = computed(() => (
  currentReport.value?.portrait?.status === 'generating'
    ? 'AI 正在生成并保存'
    : '正在读取已保存头像'
))

function setReportPortraitState(key, status, error = '', requestToken = 0) {
  reportPortraitStates[key] = { status, error, requestToken }
}

function seedReportPortraitState(report) {
  if (!report || typeof report !== 'object') return
  const key = portraitStateKey(report)
  const status = normalizedReportPortraitState(report)
  setReportPortraitState(
    key,
    status,
    status === 'failed' ? String(report?.portrait?.error || '') : '',
  )
}

function releaseReportPortraitUrl() {
  if (reportPortraitObjectUrl) URL.revokeObjectURL(reportPortraitObjectUrl)
  reportPortraitObjectUrl = ''
  reportPortraitUrl.value = ''
}

function resetReportPortraitView() {
  reportPortraitRequestToken += 1
  releaseReportPortraitUrl()
}

function isCurrentPortraitRequest(key, token) {
  return token === reportPortraitRequestToken
    && key === portraitStateKey()
    && activeMenu.value === 'report'
}

async function setReportPortraitUrl(sourceUrl, key, token) {
  const source = String(sourceUrl || '').trim()
  if (!source) throw new Error('画像人像地址为空')
  if (source.startsWith('blob:') || source.startsWith('data:')) {
    if (!isCurrentPortraitRequest(key, token)) return false
    if (reportPortraitObjectUrl !== source) releaseReportPortraitUrl()
    reportPortraitUrl.value = source
    return true
  }
  const imageBlob = await getLearningProfilePortraitFile(source)
  if (!(imageBlob instanceof Blob) || imageBlob.size <= 0) {
    throw new Error('数据库中的画像头像为空，请重试生成')
  }
  if (!isCurrentPortraitRequest(key, token)) return false
  releaseReportPortraitUrl()
  reportPortraitObjectUrl = URL.createObjectURL(imageBlob)
  reportPortraitUrl.value = reportPortraitObjectUrl
  return true
}

function rememberReportPortrait(report, portrait) {
  if (!report || !portrait || typeof portrait !== 'object') return
  report.portrait = { ...portrait }
  const historyReport = historyReports.value.find(item => Number(item?.id) === Number(report?.id))
  if (historyReport && historyReport !== report) historyReport.portrait = { ...portrait }
}

async function pollReportPortrait(report, key, token) {
  const reportId = Number(report?.id || 0)
  const deadline = Date.now() + PROFILE_PORTRAIT_POLL_TIMEOUT_MS
  let recoveredInterruptedJob = false
  while (Date.now() < deadline) {
    if (!isCurrentPortraitRequest(key, token)) return null
    const data = await getLearningProfilePortraitStatus(reportId)
    const portrait = data?.portrait || {}
    rememberReportPortrait(report, portrait)
    if (portrait.status === 'ready') return portrait
    if (portrait.status === 'failed') {
      throw new Error(portrait.error || '画像人像生成失败，请重试')
    }
    if (portrait.status === 'missing' && !recoveredInterruptedJob) {
      recoveredInterruptedJob = true
      const restarted = await generateLearningProfilePortrait(reportId)
      const restartedPortrait = restarted?.portrait || portrait
      rememberReportPortrait(report, restartedPortrait)
      if (restartedPortrait.status === 'ready') return restartedPortrait
      if (restartedPortrait.status === 'failed') {
        throw new Error(restartedPortrait.error || '画像人像生成失败，请重试')
      }
    }
    await sleep(PROFILE_PORTRAIT_POLL_INTERVAL_MS)
  }
  throw new Error('画像人像仍在后台生成，请稍后重新打开本报告')
}

async function ensureReportPortrait({ force = false } = {}) {
  const report = currentReport.value || {}
  const reportId = Number(report.id || 0)
  const storedUrl = String(report?.portrait?.url || '')
  const key = portraitStateKey(report)
  if (!storedUrl && !reportId) {
    setReportPortraitState(key, 'failed', '画像报告尚未保存，暂时无法生成人像')
    return
  }

  const token = ++reportPortraitRequestToken
  releaseReportPortraitUrl()
  setReportPortraitState(key, 'loading', '', token)
  try {
    let portrait = report.portrait || {}
    if (!reportId) {
      await setReportPortraitUrl(storedUrl, key, token)
      if (isCurrentPortraitRequest(key, token)) setReportPortraitState(key, 'ready', '', token)
      return
    }
    if (reportId) {
      const statusData = await getLearningProfilePortraitStatus(reportId)
      const latestPortrait = statusData?.portrait
      if (latestPortrait && typeof latestPortrait === 'object') {
        portrait = latestPortrait
      }
      rememberReportPortrait(report, portrait)
    }
    if (portrait.status === 'failed' && !force) {
      throw new Error(portrait.error || '画像人像生成失败，请重试')
    }
    if (portrait.status === 'missing' && !force) {
      if (isCurrentPortraitRequest(key, token)) setReportPortraitState(key, 'missing', '', token)
      return
    }
    if (force || !portrait.status || portrait.status === 'missing') {
      const data = await generateLearningProfilePortrait(reportId, { force })
      portrait = data?.portrait || {}
      rememberReportPortrait(report, portrait)
    }
    if (portrait.status === 'generating') {
      portrait = await pollReportPortrait(report, key, token)
      if (!portrait) return
    }
    const readyUrl = String(portrait?.url || storedUrl || '')
    if (portrait.status !== 'ready' && reportId) {
      throw new Error('画像人像状态异常，请重试')
    }
    await setReportPortraitUrl(readyUrl, key, token)
    if (isCurrentPortraitRequest(key, token)) setReportPortraitState(key, 'ready', '', token)
  } catch (error) {
    addLog(error, 'warn', '学习画像人像')
    const message = error?.response?.data?.msg || error?.message || '画像人像生成失败，请重试'
    if (isCurrentPortraitRequest(key, token)) {
      setReportPortraitState(key, 'failed', message, token)
    }
  } finally {
    const state = reportPortraitStates[key]
    if (!isCurrentPortraitRequest(key, token) && state?.status === 'loading' && state.requestToken === token) {
      const isVisibleAgain = key === portraitStateKey() && activeMenu.value === 'report'
      seedReportPortraitState(report)
      if (isVisibleAgain) nextTick(() => ensureReportPortrait())
    }
  }
}

function retryReportPortrait() {
  const key = portraitStateKey()
  setReportPortraitState(key, 'idle')
  ensureReportPortrait({ force: true })
}
const reportProfileDimensionRows = computed(() => profileDimensionKeys.map((name, index) => {
  const value = currentReportStudentProfile.value?.[name]
  const done = isProfileDimensionFilled(value)
  return {
    index: String(index + 1).padStart(2, '0'),
    name,
    done,
    displayValue: done ? formatProfileValue(value) : '待后续对话补充',
  }
}))
const reportProfileCompletion = computed(() => {
  const total = profileDimensionKeys.length
  const completed = reportProfileDimensionRows.value.filter(item => item.done).length
  return {
    total,
    completed,
    percent: total ? Math.round((completed / total) * 100) : 0,
  }
})
const reportReadableBackground = computed(() => {
  const profile = currentReportStudentProfile.value || {}
  const highlights = ['专业/课程背景', '学习目标', '薄弱知识点', '可投入时间']
    .map(key => {
      const value = profile[key]
      return isProfileDimensionFilled(value) ? `${key}：${formatProfileValue(value)}` : ''
    })
    .filter(Boolean)
  if (highlights.length) return highlights.join('；')
  const raw = String(currentReport.value?.chatBackground || '').trim()
  if (!raw) return '已基于数字人 AI 讲师对话生成学习画像。'
  if (raw.startsWith('{') || raw.startsWith('[')) return '已基于结构化画像维度生成学习画像。'
  return raw
})
const reportEvidenceItems = computed(() => [
  { label: '画像来源', value: '数字人对话采集' },
  { label: '维度完成度', value: `${reportProfileCompletion.value.completed}/${reportProfileCompletion.value.total}` },
  { label: '分析方式', value: currentReport.value?.aiAnalysis?.source === 'llm' ? 'LLM 智能分析' : '画像智能体分析' },
])
const reportFocusTags = computed(() => {
  const weaknesses = currentReport.value?.aiAnalysis?.weaknesses
  if (Array.isArray(weaknesses) && weaknesses.length) return weaknesses.slice(0, 6)
  const profile = currentReportStudentProfile.value || {}
  const weakPoints = profile['薄弱知识点']
  if (isProfileDimensionFilled(weakPoints)) {
    return Array.isArray(weakPoints) ? weakPoints.slice(0, 6) : [String(weakPoints)]
  }
  return ['嵌入式基础巩固', '实验步骤复盘', '项目任务拆解']
})

function reportProfileField(key, fallback = '待补充') {
  const value = currentReportStudentProfile.value?.[key]
  return isProfileDimensionFilled(value) ? formatProfileValue(value) : fallback
}

function compactReportText(value, maxLength = 34) {
  const text = String(value || '').trim()
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
}

const reportDirectionLabel = computed(() => {
  const background = reportProfileField('专业/课程背景', '嵌入式方向')
  if (/STM32/i.test(background)) return 'STM32 嵌入式学习'
  if (/Linux/i.test(background)) return 'Linux 嵌入式学习'
  return compactReportText(background, 14)
})

const reportMainTitle = computed(() => {
  const direction = /STM32/i.test(reportDirectionLabel.value)
    ? 'STM32方向'
    : reportDirectionLabel.value.replace(/学习/g, '')
  return `嵌入式系统学习画像（${direction}）`
})

const reportGrowthSteps = [
  { label: '入门探索', icon: Search },
  { label: '知识构建', icon: Cpu },
  { label: '项目实践', icon: Boxes },
  { label: '能力进阶', icon: Rocket },
]

const reportSummaryCards = computed(() => {
  const style = currentReport.value?.aiAnalysis?.learningStyle || '实践导向型'
  const knowledge = reportProfileField('当前知识基础', '具备嵌入式入门基础')
  const weakPoints = reportFocusTags.value
  const timeBudget = reportProfileField('可投入时间', '每周 6-10 小时')
  const difficulty = reportProfileField('难度接受程度', '适中偏挑战')
  return [
    { label: '画像总结', title: '偏实践 · 重应用', detail: '系统思维较强 · 工程落地导向', icon: UserRound },
    { label: '学习风格', title: compactReportText(style, 11), detail: '动手实践为主 · 任务驱动学习', icon: BrainCircuit },
    { label: '当前知识基础', title: compactReportText(knowledge, 11), detail: compactReportText(knowledge, 24), icon: Cpu },
    { label: '薄弱知识点', title: compactReportText(weakPoints[0] || '待诊断', 10), detail: compactReportText(weakPoints.slice(1, 3).join('、') || '持续结合学习证据更新', 24), icon: TriangleAlert },
    { label: '每周时间预算', title: compactReportText(timeBudget, 11), detail: '按可投入时间动态安排任务密度', icon: Clock4 },
    { label: '难度偏好', title: compactReportText(difficulty, 10), detail: '在基础巩固后逐步提升挑战', icon: SlidersHorizontal },
  ]
})

const reportAbilityBlueprint = [
  { label: '动手实践能力', icon: Hand, scoreIndex: 2 },
  { label: '逻辑与抽象能力', icon: BrainCircuit, scoreIndex: 0 },
  { label: '工程解决问题能力', icon: Wrench, scoreIndex: 5 },
  { label: '新知识吸收能力', icon: BookOpen, scoreIndex: 4 },
  { label: '系统设计能力', icon: Boxes, scoreIndex: 3 },
  { label: '代码规范意识', icon: Code2, scoreIndex: 1 },
  { label: '调试与排错能力', icon: Bug, scoreIndex: 1 },
  { label: '时间管理能力', icon: CalendarClock, scoreIndex: 4 },
  { label: '学习主动性', icon: Flame, scoreIndex: 4 },
  { label: '知识迁移能力', icon: Repeat2, scoreIndex: 5 },
]

const reportAbilityRows = computed(() => reportAbilityBlueprint.map((item, rowIndex) => {
  const raw = Number(reportRadarScores.value[item.scoreIndex] || 0)
  const adjusted = Math.max(1.5, Math.min(4.8, raw + ((rowIndex % 3) - 1) * 0.15))
  const segments = Math.max(2, Math.min(6, Math.round(adjusted / 5 * 6)))
  const level = adjusted >= 4 ? '较强' : adjusted >= 3.15 ? '中等' : '待提升'
  const evidenceScale = adjusted >= 4 ? ['strong', 'strong', 'mid', 'mid'] : adjusted >= 3.15 ? ['strong', 'mid', 'mid', 'weak'] : ['mid', 'weak', 'weak', 'none']
  return { ...item, score: adjusted, segments, level, evidence: evidenceScale }
}))

const reportStrengths = computed(() => {
  const strengths = currentReport.value?.aiAnalysis?.strengths
  return Array.isArray(strengths) && strengths.length
    ? strengths.slice(0, 4)
    : ['动手能力较强，喜欢解决实际问题', '学习主动，愿意尝试新技术', '具备一定工程意识与代码规范']
})

const reportWeaknesses = computed(() => {
  const weaknesses = currentReport.value?.aiAnalysis?.weaknesses
  return Array.isArray(weaknesses) && weaknesses.length
    ? weaknesses.slice(0, 4)
    : ['中断与时序理解不够深入', '底层机制掌握仍需巩固', '性能优化与调试方法需加强']
})

const reportPreferenceRows = computed(() => [
  { label: '学习目标', value: reportProfileField('学习目标', '掌握嵌入式系统开发，具备独立完成项目的能力'), icon: Target },
  { label: '资源偏好', value: reportProfileField('资源形式偏好', '实践项目、技术文档、视频教程与图文文章'), icon: Library },
  { label: '学习风格', value: reportProfileField('学习风格/认知偏好', currentReport.value?.aiAnalysis?.learningStyle || '实践导向、案例驱动'), icon: UserRound },
])

const reportPlanRows = computed(() => {
  const recommendations = Array.isArray(currentReport.value?.aiAnalysis?.recommendations)
    ? currentReport.value.aiAnalysis.recommendations
    : []
  const fallback = [
    '以项目驱动为主线，结合原理学习与底层机制剖析，逐步构建完整知识体系。',
    '重点突破当前薄弱知识点，并通过专项练习形成可验证的掌握证据。',
    '优先选择实战项目与源码解析，辅以官方文档和手册精读，建立知识闭环。',
    '每阶段完成一个完整项目，注重代码复用与模块化设计，积累可迁移经验。',
    '掌握基础应用后，尝试进阶开发与系统实践，向复杂工程能力迈进。',
  ]
  const titles = ['学习路径建议', '重点突破方向', '资源与方法建议', '实践建议', '进阶建议']
  const icons = [Map, Goal, BookOpen, Code2, Rocket]
  return titles.map((title, index) => ({
    title,
    icon: icons[index],
    text: compactReportText(recommendations[index] || fallback[index], 62),
  }))
})
const reportActionLabel = computed(() => {
  if (aiAnalyzing.value) return 'AI分析中...'
  return hasCurrentGeneratedReport.value ? '查看报告' : '生成画像'
})
const canUseReportAction = computed(() => {
  if (aiAnalyzing.value) return false
  return hasCurrentGeneratedReport.value || allCompleted.value
})

const agentStatusSteps = [
  {
    title: '未连接',
    desc: '等待任务触发',
    detail: '学习画像报告尚未开始生成，请先完成量表问卷、上传作业完成情况和学习背景对话。',
  },
  {
    title: '已就绪',
    desc: '智能体已准备就绪',
    detail: '数据采集已完成，可以调用学习画像智能体生成结构化报告。',
  },
  {
    title: '实时流式输出结果',
    desc: '正在分析并生成结果',
    detail: '智能体正在读取采集数据并实时输出学习风格、优势薄弱项和学习建议。',
  },
  {
    title: '输出结束',
    desc: '结果输出完成',
    detail: '学习画像报告已生成并输出完成，可查看生成的可视化结果。',
  },
  {
    title: '生成图片',
    desc: '生成可视化报告',
    detail: '系统将报告内容整理成可视化学习画像，便于保存、展示和复盘。',
  },
]

const agentTimelineActiveIndex = computed(() => {
  if (hasCurrentGeneratedReport.value) return 3
  if (aiAnalyzing.value) return 2
  if (allCompleted.value) return 1
  return 0
})

const agentRuntimeLabel = computed(() => {
  if (aiAnalyzing.value) return '实时监控中'
  if (hasCurrentGeneratedReport.value) return '已生成报告'
  if (allCompleted.value) return '已就绪'
  return '等待任务触发'
})

const agentLogLabel = computed(() => {
  if (aiAnalyzing.value) return '接收中'
  if (analysisStreamEvents.value.length) return '已输出'
  return '暂无日志'
})

const latestAnalysisEvent = computed(() => (
  [...analysisStreamEvents.value].reverse().find(item => item?.message || item?.stage) || {}
))

const analysisProgress = computed(() => analysisStreamEvents.value.reduce((maximum, item) => {
  const progress = Number(item?.progress)
  return Number.isFinite(progress) ? Math.max(maximum, Math.max(0, Math.min(100, progress))) : maximum
}, 0))

const analysisRunId = computed(() => {
  const event = analysisStreamEvents.value.find(item => item?.runId)
  return String(event?.runId || '')
})

const analysisCurrentAgent = computed(() => {
  const event = [...analysisStreamEvents.value].reverse().find(item => item?.agentName || item?.agentId)
  if (!event) return '等待总控调度'
  const name = String(event.agentName || event.agentId || '学习画像智能体')
  const id = event.agentId && event.agentId !== name ? ` (${event.agentId})` : ''
  return `${name}${id}`
})

const analysisRuntimeModel = computed(() => {
  const event = analysisStreamEvents.value.find(item => item?.modelRuntime?.model)
  const runtime = event?.modelRuntime || {}
  const model = String(runtime.model || '').trim()
  const protocol = String(runtime.protocol || '').trim()
  return model ? `${model}${protocol ? ` · ${protocol}` : ''}` : '等待模型连接'
})

const analysisReviewLabel = computed(() => {
  const event = [...analysisStreamEvents.value].reverse().find(item => item?.stage === 'quality_review')
  if (!event) return aiAnalyzing.value ? '等待审核' : '尚未执行'
  const review = event.payload && typeof event.payload === 'object' ? event.payload : {}
  const score = Number(review.score)
  const passed = event.status === 'complete' || review.passed === true
  return Number.isFinite(score) ? `${passed ? '已通过' : '需修订'} · ${score} 分` : (passed ? '已通过' : '需修订')
})

const analysisElapsedLabel = computed(() => {
  const elapsedMs = analysisStreamEvents.value.reduce((maximum, item) => {
    const value = Number(item?.elapsedMs)
    return Number.isFinite(value) ? Math.max(maximum, value) : maximum
  }, 0)
  return formatAnalysisDuration(elapsedMs)
})

function handleReportAction() {
  viewingHistory.value = null
  activeOrb.value = null
  if (hasCurrentGeneratedReport.value) {
    activeMenu.value = 'report'
    return
  }
  if (allCompleted.value) {
    generateReport()
    return
  }
  activeMenu.value = 'assess'
  ensureInitialChatQuestion()
}

function selectSidebarMenu(key) {
  activeOrb.value = null
  activeMenu.value = menuItems.some(item => item.key === key) ? key : 'assess'
  if (activeMenu.value === 'report' && historyReports.value.length) {
    viewingHistory.value = historyReports.value.find(report => report.isActive) || historyReports.value[0]
  } else {
    viewingHistory.value = null
  }
  if (activeMenu.value === 'assess') ensureInitialChatQuestion()
}

function formatAnalysisStage(stage) {
  const labels = {
    start: '启动分析',
    request_start: '总控接单',
    collect_data: '读取画像与学习证据',
    call_agent: '总控编排',
    supervisor_plan: '任务规划',
    load_context: '汇总学习上下文',
    knowledge_skipped: '知识检索判定',
    retrieve_knowledge: '检索课程知识库',
    specialist_start: '画像智能体生成',
    skill_resolved: 'Skill 解析',
    skill_input_validated: '输入契约校验',
    mcp_tool_start: 'MCP 工具调用',
    mcp_tool_complete: 'MCP 工具完成',
    skill_output_validated: '输出契约校验',
    specialist_complete: '结构化产物提交',
    quality_review: '质量审核',
    content_safety: '内容安全审核',
    learning_feedback: '学习反馈整理',
    supervisor_finalize: '总控结果收口',
    agent_returned: 'JSON 结果校验',
    save_report: '保存报告',
    waiting: '模型生成中',
    complete: '生成完成',
    done: '流程结束',
    error: '分析异常',
    result: '生成完成',
  }
  return labels[stage] || stage || '实时状态'
}

function formatAnalysisStatus(status) {
  const labels = {
    running: '执行中',
    complete: '已完成',
    done: '已结束',
    warning: '需关注',
    failed: '失败',
    error: '失败',
  }
  return labels[String(status || '')] || '处理中'
}

function formatAnalysisDuration(elapsedMs) {
  const value = Math.max(0, Number(elapsedMs) || 0)
  if (value < 1000) return `${Math.round(value)} ms`
  if (value < 60000) return `${(value / 1000).toFixed(value < 10000 ? 1 : 0)} 秒`
  const minutes = Math.floor(value / 60000)
  const seconds = Math.round((value % 60000) / 1000)
  return `${minutes} 分 ${seconds} 秒`
}

function buildAnalysisEventDetails(item) {
  const details = []
  const payload = item?.payload && typeof item.payload === 'object' ? item.payload : {}
  const snapshot = item?.snapshot && typeof item.snapshot === 'object'
    ? item.snapshot
    : (payload.snapshot && typeof payload.snapshot === 'object' ? payload.snapshot : {})
  const add = (label, value, monospace = false) => {
    if (value === undefined || value === null || value === '') return
    const text = Array.isArray(value) ? value.join('、') : String(value)
    if (!text.trim() || details.some(detail => detail.label === label)) return
    details.push({ label, value: text, monospace })
  }

  add('智能体', item?.agentName || item?.agentId)
  add('智能体 ID', item?.agentId, true)
  add('运行 ID', item?.runId, true)
  add('累计耗时', formatAnalysisDuration(item?.elapsedMs))
  add('Skill', item?.skillId || payload.skillId, true)
  add('MCP 调用', item?.callId || payload.callId, true)
  add('任务类型', payload.taskType)
  add('专业智能体', payload.worker, true)
  if (Array.isArray(payload.plan)) add('协作步骤', `${payload.plan.length} 个`)
  if (snapshot.completedProfileDimensionCount !== undefined) {
    add('画像维度', `${snapshot.completedProfileDimensionCount}/10 已完成`)
  }
  if (snapshot.missingProfileDimensionCount !== undefined) {
    add('缺失维度', `${snapshot.missingProfileDimensionCount} 个`)
  }
  if (snapshot.scaleScoreCount !== undefined) add('量表数据', `${snapshot.scaleScoreCount} 项`)
  if (snapshot.uploadFileCount !== undefined) add('上传材料', `${snapshot.uploadFileCount} 份`)
  if (snapshot.hasChatBackground !== undefined) add('对话背景', snapshot.hasChatBackground ? '已读取' : '未提供')
  if (snapshot.weakPointCount !== undefined || payload.weakPointCount !== undefined) {
    add('薄弱点证据', `${snapshot.weakPointCount ?? payload.weakPointCount} 项`)
  }
  if (payload.examCount !== undefined) add('答题证据', `${payload.examCount} 组`)
  if (payload.experimentCount !== undefined) add('实验记录', `${payload.experimentCount} 条`)
  if (payload.score !== undefined) add('审核得分', `${payload.score} / 100`)
  if (payload.threshold !== undefined) add('通过阈值', `${payload.threshold} 分`)
  if (payload.citationCount !== undefined) add('知识引用', `${payload.citationCount} 条`)
  add('结果来源', item?.source)
  if (Array.isArray(item?.outputKeys)) add('结构字段', item.outputKeys.slice(0, 8))
  if (item?.reportId) add('画像报告 ID', item.reportId, true)
  add('错误码', item?.errorCode, true)
  add('错误详情', item?.detail)
  return details.slice(0, 12)
}

function generateReport(options = {}) {
  if (aiAnalyzing.value) return
  if (hasCurrentGeneratedReport.value && !options.force) {
    activeMenu.value = 'report'
    return
  }
  if (!allCompleted.value) {
    showToast('请先通过对话补齐 10 个画像维度')
    return
  }
  autoReportStarted = true
  viewingHistory.value = null
  activeOrb.value = null
  activeMenu.value = 'report'
  aiAnalyzing.value = true
  if (options.auto) {
    showToast('10 个画像维度已补齐，正在自动生成画像报告')
  }
  callAIAnalysis()
    .then(report => {
      saveProfile(report)
      historyReports.value = [report, ...historyReports.value.filter(item => item.id !== report.id)]
      viewingHistory.value = null
      activeMenu.value = 'report'
      showToast(options.reassess ? '画像已重新评估' : '画像报告已生成')
    })
    .catch((error) => {
      if (options.auto) autoReportStarted = false
      saveProfile({ aiAnalysis: null })
      showToast(error?.response?.data?.msg || error?.message || '画像更新失败')
    })
    .finally(() => { aiAnalyzing.value = false })
}

async function callAIAnalysis() {
  const payload = {
    scaleScores: profileData.value.scaleScores,
    scaleTimestamp: profileData.value.scaleTimestamp,
    chatBackground: profileData.value.chatBackground,
    chatTimestamp: profileData.value.chatTimestamp,
    chatStudentProfile: chatStudentProfile.value,
    completedProfileDimensions: profileDimensionKeys.filter(key => isProfileDimensionFilled(chatStudentProfile.value[key])),
    missingProfileDimensions: profileDimensionKeys.filter(key => !isProfileDimensionFilled(chatStudentProfile.value[key])),
    uploadFiles: profileData.value.uploadFiles || [],
    uploadTimestamp: profileData.value.uploadTimestamp,
    scaleQuestions: scaleQuestions.map(q => ({ text: q.text, short: q.short })),
  }
  let report = null
  analysisStreamEvents.value = []
  analysisStreamMessage.value = '画像分析智能体启动中...'
  analysisStreamStartedAt.value = Date.now()

  await analyzeLearningProfileStream(payload, async ({ event, data }) => {
    const receivedAt = Date.now()
    const message = data?.message || data?.detail || data?.stage || event
    const elapsedMs = Number.isFinite(Number(data?.elapsedMs))
      ? Number(data.elapsedMs)
      : Math.max(0, receivedAt - analysisStreamStartedAt.value)
    const streamEvent = {
      ...(data && typeof data === 'object' ? data : {}),
      id: `${data?.runId || 'profile'}-${data?.sequence || analysisStreamEvents.value.length + 1}-${receivedAt}`,
      event,
      stage: data?.stage || '',
      status: data?.status || (event === 'error' ? 'failed' : ['result', 'done'].includes(event) ? 'complete' : 'running'),
      progress: Number.isFinite(Number(data?.progress)) ? Number(data.progress) : null,
      message,
      elapsedMs,
      time: new Date(data?.time || receivedAt).toLocaleTimeString('zh-CN', { hour12: false }),
    }
    streamEvent.details = buildAnalysisEventDetails(streamEvent)
    analysisStreamMessage.value = message
    analysisStreamEvents.value = [...analysisStreamEvents.value, streamEvent].slice(-160)
    addLog({ event, data }, event === 'error' ? 'error' : 'info', '学习画像分析')
    await nextTick()
    if (analysisLogRef.value) {
      analysisLogRef.value.scrollTop = analysisLogRef.value.scrollHeight
    }
    if (event === 'result' && data?.report) {
      report = data.report
    }
    if (event === 'error') {
      throw new Error(data?.detail || data?.message || data?.error || 'AI analysis failed')
    }
  })

  const analysis = report?.aiAnalysis
  if (!analysis || !analysis.learningStyle || !Array.isArray(analysis.strengths) || !Array.isArray(analysis.weaknesses) || !Array.isArray(analysis.recommendations)) {
    throw new Error('Agent JSON is incomplete')
  }
  return report
}

// --- Navigation ---
const activeMenu = ref('assess')
const activeOrb = ref(null)
const chatInput = ref('')
const profileChatAttachments = ref([])
const profileImageInputRef = ref(null)
const profileVideoInputRef = ref(null)
const profileFileInputRef = ref(null)
const fileInput = ref(null)
const uploadFiles = ref([])
const scaleAnswers = reactive({})
const chatMsgs = ref([])
const chatMessagesRef = ref(null)
const digitalHumanRef = ref(null)
const learningAvatarStatus = ref('')
const learningAvatarError = ref('')
let lastAvatarSpeechText = ''
let autoReportStarted = false

function handleLearningAvatarStatus(event) {
  const statusTextMap = {
    idle: '准备中',
    'loading-config': '准备中',
    ready: '准备中',
    connecting: '连接中',
    connected: '已连接',
    speaking: '运行中',
    waiting: '已连接',
    disconnected: '已断开',
    'resume-required': '点击开启声音',
    destroyed: '已关闭',
    error: '连接异常',
  }
  learningAvatarStatus.value = statusTextMap[event?.code] || event?.label || ''
  if (event?.code && event.code !== 'error') {
    learningAvatarError.value = ''
  }
}

function handleLearningAvatarError(message) {
  if (/play\(\)|NotAllowedError|not-allowed|autoplay|didn't interact|user gesture|自动播放|开启声音/i.test(String(message || ''))) {
    learningAvatarStatus.value = '点击开启声音'
    learningAvatarError.value = ''
    return
  }
  learningAvatarStatus.value = '连接异常'
  learningAvatarError.value = message || ''
}

function resumeLearningAvatarIfNeeded() {
  if (learningAvatarStatus.value !== '点击开启声音') return
  digitalHumanRef.value?.resumeAvatar?.()
}

async function startLearningAvatar(options = {}) {
  const { replayLatest = true } = options
  await nextTick()
  const avatar = digitalHumanRef.value
  if (!avatar) return

  try {
    learningAvatarError.value = ''
    await avatar.startAvatar()
    if (replayLatest && !lastAvatarSpeechText) {
      const latestBotMessage = [...chatMsgs.value]
        .reverse()
        .find(item => item.role === 'bot' && item.text?.trim() && !isTransientChatText(item.text))
      if (latestBotMessage) {
        lastAvatarSpeechText = latestBotMessage.text
        avatar.speak(latestBotMessage.text).catch(() => {})
      }
    }
  } catch (error) {
    handleLearningAvatarError(error?.message || '数字人连接失败，请稍后重试')
  }
}

const menuItems = [
  {
    key: 'assess',
    label: '学习画像',
    icon: ClipboardCheck,
  },
  {
    key: 'report',
    label: '画像报告',
    icon: FileText,
  },
  {
    key: 'history',
    label: '历史记录',
    icon: Clock3,
  },
]

const sidebarMenuItems = computed(() => {
  return menuItems
})

const scaleQuestions = [
  { text: '嵌入式基础知识掌握情况', short: '基础知识' },
  { text: '编程与调试能力', short: '编程调试' },
  { text: '实验与动手能力', short: '实验动手' },
  { text: '项目实践能力', short: '项目实践' },
  { text: '学习习惯与学习投入', short: '学习投入' },
  { text: '创新能力与工程意识', short: '创新工程' },
]

// --- Radar chart ---
const radarSize = 400
const radarCenter = radarSize / 2
const radarMaxR = 140

function getPolygonPoints(r) {
  const count = scaleQuestions.length
  return Array.from({ length: count }, (_, i) => {
    const angle = (Math.PI * 2 * i / count) - Math.PI / 2
    return `${radarCenter + r * Math.cos(angle)},${radarCenter + r * Math.sin(angle)}`
  }).join(' ')
}

const reportRadarScores = computed(() => {
  const report = currentReport.value || {}
  const structuredScores = report.effectAssessment?.radarScores
    || report.aiAnalysis?.radarScores
    || report.aiAnalysis?.scores
    || report.scaleScores
  if (Array.isArray(structuredScores) && structuredScores.some(value => Number(value) > 0)) {
    return scaleQuestions.map((_, index) => Math.max(0, Math.min(5, Number(structuredScores[index] || 0))))
  }

  const student = report.chatStudentProfile || {}
  const complete = profileDimensionKeys.filter(key => isProfileDimensionFilled(student[key])).length
  const base = 2.1 + Math.min(1.3, complete / profileDimensionKeys.length * 1.3)
  const weakText = [
    ...(Array.isArray(report.aiAnalysis?.weaknesses) ? report.aiAnalysis.weaknesses : []),
    ...(Array.isArray(student['薄弱知识点']) ? student['薄弱知识点'] : [student['薄弱知识点'] || '']),
    ...(Array.isArray(student['易错点类型']) ? student['易错点类型'] : [student['易错点类型'] || '']),
  ].join(' ').toLowerCase()
  const goalText = Array.isArray(student['学习目标']) ? student['学习目标'].join(' ') : String(student['学习目标'] || '')
  const timeText = String(student['可投入时间'] || '')
  const difficultyText = String(student['难度接受程度'] || '')
  const lower = (value) => Math.max(1.4, Math.min(4.6, Number(value.toFixed(1))))
  return [
    lower(base + (/基础|c语言|stm32|单片机/.test(String(student['当前知识基础'] || '')) ? 0.25 : 0)),
    lower(base - (/代码|调试|配置|寄存器/.test(weakText) ? 0.45 : 0) + 0.1),
    lower(base - (/实验|接线|外设/.test(weakText) ? 0.25 : 0) + (/实践|项目/.test(goalText) ? 0.2 : 0)),
    lower(base + (/项目|竞赛|课程设计/.test(goalText) ? 0.35 : 0)),
    lower(base + (/\d/.test(timeText) ? 0.35 : 0)),
    lower(base + (/挑战|进阶|竞赛/.test(difficultyText) ? 0.3 : 0)),
  ]
})

function getDataPoint(i, scoreOverride = null) {
  const score = scoreOverride === null ? reportRadarScores.value[i] : scoreOverride
  const r = (score / 5) * radarMaxR
  const angle = (Math.PI * 2 * i / scaleQuestions.length) - Math.PI / 2
  return { x: radarCenter + r * Math.cos(angle), y: radarCenter + r * Math.sin(angle) }
}

function getDataPolygonPoints() {
  return Array.from({ length: scaleQuestions.length }, (_, i) => {
    const p = getDataPoint(i)
    return `${p.x},${p.y}`
  }).join(' ')
}

function getLabelPos(i) {
  const angle = (Math.PI * 2 * i / scaleQuestions.length) - Math.PI / 2
  const r = radarMaxR + 32
  return { x: radarCenter + r * Math.cos(angle), y: radarCenter + r * Math.sin(angle) }
}

function getLabelAnchor(i) {
  const angle = (Math.PI * 2 * i / scaleQuestions.length) - Math.PI / 2
  const cos = Math.cos(angle)
  if (Math.abs(cos) < 0.1) return 'middle'
  return cos > 0 ? 'start' : 'end'
}

function getLabelBaseline(i) {
  const angle = (Math.PI * 2 * i / scaleQuestions.length) - Math.PI / 2
  const sin = Math.sin(angle)
  if (Math.abs(sin) < 0.1) return 'middle'
  return sin > 0 ? 'hanging' : 'auto'
}

// --- Actions ---
function openSubmitPage(section = 'scale') {
  router.push({ path: '/learning-profile/submit', query: { section } })
}

function openCollectPage(key) {
  viewingHistory.value = null
  activeMenu.value = 'assess'
  if (key === 'chat') {
    activeOrb.value = null
    nextTick(() => {
      if (chatMessagesRef.value) chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
    })
    return
  }
  activeOrb.value = key
}

function triggerUpload() {
  fileInput.value?.click()
}

function onFileSelect(e) {
  uploadFiles.value = Array.from(e.target.files || [])
  if (e.target) e.target.value = ''
}

function onDrop(e) {
  uploadFiles.value = Array.from(e.dataTransfer.files || [])
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

function profileFileKind(file) {
  const type = String(file?.type || '').toLowerCase()
  if (type.startsWith('image/')) return 'image'
  if (type.startsWith('video/')) return 'video'
  return 'document'
}

function profileAttachmentIcon(kind) {
  if (kind === 'image') return ImagePlus
  if (kind === 'video') return Video
  return FileText
}

function queueProfileAttachments(event) {
  const selected = Array.from(event?.target?.files || [])
  if (event?.target) event.target.value = ''
  const next = profileChatAttachments.value.slice()
  for (const file of selected) {
    if (file.size > 50 * 1024 * 1024) {
      showToast(`${file.name} 超过 50 MB`)
      continue
    }
    const duplicate = next.some(item => item.name === file.name && item.size === file.size && item.lastModified === file.lastModified)
    if (!duplicate && next.length < 4) next.push(file)
  }
  profileChatAttachments.value = next
  if (selected.length && next.length >= 4) showToast('每次最多添加 4 个附件')
}

function removeProfileAttachment(index) {
  profileChatAttachments.value.splice(index, 1)
}

function normalizeUploadFile(file) {
  return {
    name: file.name,
    size: file.size,
    type: file.type || '',
    lastModified: file.lastModified || 0,
    uploadedAt: Date.now(),
  }
}

function getCurrentChatBackground() {
  return chatMsgs.value
    .filter(m => m.role === 'user')
    .map(m => String(m.text || '').trim())
    .filter(Boolean)
    .join('，')
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function formatChatMessageTime(timestamp, index = 0) {
  const date = timestamp ? new Date(timestamp) : new Date(Date.now() + index * 1000)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function typeReply(botMessage, text) {
  for (const char of text) {
    const current = chatMsgs.value.find(item => item === botMessage) || botMessage
    setChatBotMessage(botMessage, `${current.text || ''}${char}`, current.source || 'llm')
    await nextTick()
    if (chatMessagesRef.value) chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
    await sleep(/[，。！？；、,.!?]/.test(char) ? 90 : 24)
  }
}

async function speakLearningReply(text) {
  const content = String(text || '').trim()
  if (!content) return
  await nextTick()
  if (!digitalHumanRef.value) return
  try {
    await startLearningAvatar({ replayLatest: false })
    lastAvatarSpeechText = content
    await digitalHumanRef.value?.speak?.(content)
  } catch (error) {
    handleLearningAvatarError(error?.message || '数字人播报失败')
  }
}

function setChatScrollToBottom() {
  if (chatMessagesRef.value) {
    chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
  }
}

async function scrollChatToBottom({ retry = false } = {}) {
  await nextTick()
  setChatScrollToBottom()
  if (!retry) return

  requestAnimationFrame(() => {
    setChatScrollToBottom()
    setTimeout(setChatScrollToBottom, 80)
    setTimeout(setChatScrollToBottom, 240)
  })
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function normalizeAgentResult(data) {
  return data?.data?.data || data?.data || data || null
}

function assertLlmSource(event, data) {
  const source = data?.source || data?.data?.source || data?.data?.data?.source || ''
  if (source && source !== 'llm' && source !== 'pending') {
    throw new Error('学习背景对话必须由 LLM 生成，当前接口返回非 LLM 来源')
  }
}

function syncLatestBotMessage(reply) {
  const text = String(reply || '').trim()
  if (!text) return false
  const lastBot = [...chatMsgs.value].reverse().find(item => item.role === 'bot')
  if (!lastBot || !isTransientChatText(lastBot.text)) return false
  setChatBotMessage(lastBot, text, 'llm')
  persistChatState({ chatBackground: getCurrentChatBackground() || text, chatTimestamp: Date.now() })
  return true
}

function mergeProfileValue(currentValue, nextValue) {
  const currentList = Array.isArray(currentValue)
    ? currentValue.map(item => String(item || '').trim()).filter(Boolean)
    : String(currentValue || '').trim()
      ? [String(currentValue).trim()]
      : []
  const nextList = Array.isArray(nextValue)
    ? nextValue.map(item => String(item || '').trim()).filter(Boolean)
    : String(nextValue || '').trim()
      ? [String(nextValue).trim()]
      : []
  const merged = [...new Set([...currentList, ...nextList])]
  if (Array.isArray(currentValue) || Array.isArray(nextValue)) return merged
  return merged[0] || ''
}

function mergeStudentProfiles(...profiles) {
  const normalizedProfiles = profiles.map(normalizeStudentProfileDimensions)
  const merged = {}
  profileDimensionKeys.forEach((key) => {
    normalizedProfiles.forEach((profile) => {
      if (!isPlainObject(profile)) return
      merged[key] = mergeProfileValue(merged[key], profile[key])
    })
    if (!isProfileDimensionFilled(merged[key])) {
      merged[key] = ['学习目标', '薄弱知识点', '易错点类型', '学习风格/认知偏好', '资源形式偏好'].includes(key)
        ? []
        : ''
    }
  })
  const extra = normalizedProfiles.find(profile => isPlainObject(profile?.['补充信息']))?.['补充信息'] || {}
  merged['补充信息'] = extra
  return merged
}

function updatePortraitFromAgent(agentResult, reply = '') {
  const result = isPlainObject(agentResult) ? agentResult : {}
  syncLatestBotMessage(result.reply || result.question || reply)
  const mergedStudentProfile = mergeStudentProfiles(
    profileData.value.chatStudentProfile || {},
    isPlainObject(result.studentProfile) ? result.studentProfile : {},
    isPlainObject(result.student_profile) ? result.student_profile : {},
    isPlainObject(result.profile) ? result.profile : {},
    isPlainObject(result.dimensions) ? result.dimensions : {},
    isPlainObject(result.extracted) ? result.extracted : {},
  )
  const mergedCompleteness = Math.round(
    (profileDimensionKeys.filter(key => isProfileDimensionFilled(mergedStudentProfile[key])).length / profileDimensionKeys.length) * 100,
  )
  const patch = {
    chatTimestamp: Date.now(),
    chatCompleteness: mergedCompleteness,
    chatStatus: result.status || 'collecting',
    chatMissingFields: Array.isArray(result.missingFields) ? result.missingFields : [],
    chatExtracted: isPlainObject(result.extracted) ? result.extracted : (profileData.value.chatExtracted || {}),
    chatStudentProfile: mergedStudentProfile,
    chatNeedFollowup: typeof result.needFollowup === 'boolean' ? result.needFollowup : profileData.value.chatNeedFollowup,
    chatFollowUpQuestions: Array.isArray(result.followUpQuestions) ? result.followUpQuestions : (profileData.value.chatFollowUpQuestions || []),
    chatMissingProfileDimensions: profileDimensionKeys.filter(key => !isProfileDimensionFilled(mergedStudentProfile[key])),
    chatBackground: String(result.summary || getCurrentChatBackground() || reply || '').trim(),
  }
  persistChatState(patch)
}

async function requestLlmChatTurn(messages, botMessage, attachments = []) {
  let reply = ''
  let agentResult = null
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), LLM_CHAT_TIMEOUT_MS)

  try {
    await streamLearningProfileBackgroundChat({ messages, attachments }, async ({ event, data }) => {
      assertLlmSource(event, data)
      const source = data?.source || data?.data?.source || data?.data?.data?.source || 'pending'
      addLog({ event, source, data }, event === 'error' ? 'error' : 'info', '学习背景对话')
      setSection('learning-background-dialogue-agent', {
        title: '学习背景对话智能体',
        items: [
          `event: ${event}`,
          `stage: ${data?.stage || '-'}`,
          `source: ${source}`,
          `message: ${data?.message || '-'}`,
        ],
      })

      if (event === 'delta' && data?.text) {
        reply += data.text
        setChatBotMessage(botMessage, reply, 'llm')
        persistChatState({
          chatBackground: getCurrentChatBackground() || reply,
          chatTimestamp: Date.now(),
          chatCompleteness: Math.round(profileChatCompleteness.value * 100),
        })
        await scrollChatToBottom()
        return
      }

      if (event === 'result') {
        agentResult = normalizeAgentResult(data)
        const resultReply = String(agentResult?.reply || agentResult?.question || '').trim()
        if (resultReply && (resultReply.length > reply.trim().length || !reply.trim() || isTransientChatText(botMessage.text))) {
          reply = resultReply
          setChatBotMessage(botMessage, reply, 'llm')
          await scrollChatToBottom()
        }
        updatePortraitFromAgent(agentResult, reply)
        return
      }

      if (event === 'error') {
        throw new Error(data?.message || data?.error || '学习背景对话智能体调用失败')
      }
    }, { signal: controller.signal })

    if (!reply.trim() && !agentResult) {
      agentResult = await requestLearningProfileBackgroundChat({ messages, attachments }, { signal: controller.signal })
      assertLlmSource('result', agentResult)
      reply = String(agentResult?.reply || agentResult?.question || '').trim()
      if (reply) {
        setChatBotMessage(botMessage, reply, 'llm')
        updatePortraitFromAgent(agentResult, reply)
        await scrollChatToBottom()
      }
    }
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error('LLM 响应超时，请检查后端模型服务是否正常。')
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
  }

  const finalReply = String(reply || agentResult?.reply || agentResult?.question || (isTransientChatText(botMessage.text) ? '' : botMessage.text) || '').trim()
  if (!finalReply) {
    throw new Error('LLM 未返回可显示内容')
  }
  if (isTransientChatText(botMessage.text)) {
    setChatBotMessage(botMessage, finalReply, 'llm')
  }
  return { reply: finalReply, agentResult }
}

async function ensureInitialChatQuestion() {
  if (initialChatRequestStarted || chatInitializing.value || chatLoading.value || chatMsgs.value.length || chatHistory.value.length) {
    return
  }
  initialChatRequestStarted = true
  chatInitializing.value = false
  chatLoading.value = false
  chatStreaming.value = false
  const botMessage = { id: createChatMessageId('bot'), role: 'bot', text: INITIAL_CHAT_OPENING, timestamp: Date.now(), source: 'system' }
  chatMsgs.value.push(botMessage)
  chatHistory.value.push({ role: 'assistant', content: INITIAL_CHAT_OPENING })
  persistChatState({ chatTimestamp: Date.now() })
  speakLearningReply(INITIAL_CHAT_OPENING)
  await scrollChatToBottom()
}

function applyProfileSession(session) {
  if (!session) return
  activeProfileSessionId.value = session.id
  chatMsgs.value = buildProfileSessionChatMessages(session.messages)
  chatHistory.value = chatMsgs.value.map((message) => ({
    role: message.role === 'bot' ? 'assistant' : 'user', content: message.text,
  }))
  if (!chatMsgs.value.length) {
    initialChatRequestStarted = false
    ensureInitialChatQuestion()
  } else {
    initialChatRequestStarted = true
  }
}

async function loadSelectedProfileSession() {
  if (!activeProfileSessionId.value) return
  try {
    applyProfileSession(await getLearningProfileSession(activeProfileSessionId.value))
  } catch (error) {
    addLog(error, 'error', '加载学习画像会话')
    showToast('学习画像会话加载失败')
  }
}

async function initializeProfileSessions() {
  const sessions = await getLearningProfileSessions()
  profileSessions.value = sessions
  if (!sessions.length) {
    const session = await createLearningProfileSession()
    profileSessions.value = [session]
    applyProfileSession(session)
    return
  }
  activeProfileSessionId.value = sessions[0].id
  await loadSelectedProfileSession()
}

async function startNewProfileSession() {
  if (chatLoading.value) return
  try {
    const session = await createLearningProfileSession({ title: `学习画像 ${profileSessions.value.length + 1}` })
    profileSessions.value = [session, ...profileSessions.value]
    applyProfileSession(session)
    showToast('已创建新的独立学习画像对话')
  } catch (error) {
    addLog(error, 'error', '创建学习画像会话')
    showToast('新建学习画像失败')
  }
}

async function sendChat() {
  const rawMessage = chatInput.value.trim()
  const queuedFiles = profileChatAttachments.value.slice()
  if ((!rawMessage && !queuedFiles.length) || chatLoading.value) return
  chatInput.value = ''
  profileChatAttachments.value = []
  chatLoading.value = true
  chatStreaming.value = false
  let attachments = []
  try {
    attachments = queuedFiles.length
      ? await uploadMultimodalInputs(queuedFiles, 'learning-profile', route.fullPath)
      : []
  } catch (error) {
    profileChatAttachments.value = queuedFiles
    chatLoading.value = false
    addLog(error, 'error', '学习画像多模态附件')
    showToast(error?.response?.data?.msg || error?.message || '附件上传失败')
    return
  }
  const msg = rawMessage || '请分析我上传的学习材料。'
  chatMsgs.value.push({
    id: createChatMessageId('user'),
    role: 'user',
    text: msg,
    attachments,
    timestamp: Date.now(),
  })
  viewingHistory.value = null
  persistChatState({ chatBackground: getCurrentChatBackground(), chatTimestamp: Date.now() })
  await scrollChatToBottom()

  if (activeProfileSessionId.value) {
    try {
      const result = await sendLearningProfileSessionMessage(activeProfileSessionId.value, msg, attachments)
      applyProfileSession(result?.session)
      const workflow = result?.workflow || {}
      updatePortraitFromAgent(workflow, String(workflow.reply || workflow.question || ''))
      if (result?.report) {
        await loadHistoryReports()
        const pathTaskStatus = String(result?.learningPathTask?.status || '')
        showToast(
          ['queued', 'running'].includes(pathTaskStatus)
            ? '十个画像维度已补齐，学习路径已在后台开始生成'
            : '十个画像维度已补齐，完整学习画像报告已生成',
        )
      }
      await scrollChatToBottom()
    } catch (error) {
      addLog(error, 'error', '学习画像会话对话')
      showToast(error?.response?.data?.msg || error?.message || '学习画像对话失败')
    } finally {
      chatLoading.value = false
      chatStreaming.value = false
    }
    return
  }
  chatHistory.value.push({ role: 'user', content: msg })
  const botMessage = { id: createChatMessageId('bot'), role: 'bot', text: CHAT_REPLY_PENDING_TEXT, timestamp: Date.now(), source: 'llm-streaming' }

  try {
    chatMsgs.value.push(botMessage)
    chatStreaming.value = true

    const { reply, agentResult } = await requestLlmChatTurn(chatHistory.value, botMessage, attachments)
    if (!reply?.trim() || isTransientChatText(reply)) {
      throw new Error('LLM 未返回可显示内容')
    }

    chatHistory.value.push({ role: 'assistant', content: reply })
    updatePortraitFromAgent(agentResult, reply)
    chatLoading.value = false
    chatStreaming.value = false
    speakLearningReply(reply)

    // 判断对话是否应该结束
    const isComplete = agentResult?.status === 'complete'
      || /学习背景信息已收集完毕|信息已记录|信息已经足够完整/.test(reply)
    if (isComplete) {
      // 从对话中提取结构化摘要
      const summary = agentResult?.summary || extractChatSummary(reply, msg)
      updatePortraitFromAgent({ ...agentResult, summary, status: 'complete' }, reply)
      showToast('学习背景已智能提取并保存')
    } else {
      updatePortraitFromAgent(agentResult, reply)
    }

    scrollChatToBottom()
  } catch (error) {
    addLog(error, 'error', '学习背景对话')
    const fallback = `LLM 对话接口未返回有效结果：${error?.message || '未知错误'}。请检查后端大模型配置后重试。`
    chatStreaming.value = true
    await typeReply(botMessage, fallback)
    chatHistory.value.push({ role: 'assistant', content: fallback })
    persistChatState({ chatBackground: getCurrentChatBackground(), chatTimestamp: Date.now() })
    chatLoading.value = false
    chatStreaming.value = false
    showToast('大模型对话接口未连通')

    scrollChatToBottom()
  }
  settleTransientBotMessage(botMessage, 'LLM 暂时没有返回内容，请稍后重试。')
  chatLoading.value = false
  chatStreaming.value = false
  await scrollChatToBottom()
}

function extractChatSummary(aiReply, lastUserMsg) {
  const summaryMatch = aiReply.match(/(?:总结|概括)[：:]\s*(.+)/)
  if (summaryMatch) return summaryMatch[1].trim()

  // ?????????????
  const userMsgs = chatMsgs.value.filter(m => m.role === 'user').map(m => m.text)
  return userMsgs.join('，')
}

async function resetChat() {
  if (activeProfileSessionId.value) {
    await startNewProfileSession()
    return
  }
  try {
    await resetLearningProfileBackgroundChat()
  } catch (error) {
    addLog(error, 'error', '重置学习画像对话')
    showToast('后端历史记录清理失败，请稍后重试')
    return
  }
  chatMsgs.value = []
  chatHistory.value = []
  profileChatAttachments.value = []
  chatLoading.value = false
  chatStreaming.value = false
  chatInitializing.value = false
  initialChatRequestStarted = false
  autoReportStarted = false
  persistChatState({
    chatBackground: '',
    chatTimestamp: null,
    chatCompleteness: 0,
    chatStatus: 'collecting',
    chatMissingFields: [],
    chatExtracted: {},
    chatStudentProfile: {},
    chatNeedFollowup: true,
    chatFollowUpQuestions: [],
    chatMissingProfileDimensions: [],
    aiAnalysis: null,
  })
  ensureInitialChatQuestion()
}

function submitScale() {
  const answered = Object.values(scaleAnswers).filter(v => v !== undefined).length
  if (answered < scaleQuestions.length) {
    showToast('请完成所有题目后再提交')
    return
  }
  const scores = scaleQuestions.map((_, i) => scaleAnswers[i])
  saveProfile({ scaleScores: scores, scaleTimestamp: Date.now() })
  activeMenu.value = 'assess'
  activeOrb.value = null
  showToast('问卷提交成功，已返回采集进度')
}

function submitUpload() {
  const fileRecords = uploadFiles.value.map(normalizeUploadFile)
  viewingHistory.value = null
  saveProfile({ uploadFiles: fileRecords, uploadTimestamp: Date.now(), aiAnalysis: null })
  uploadFiles.value = []
  activeMenu.value = 'assess'
  activeOrb.value = null
  showToast('作业完成情况上传成功')
}

function applyRouteQuery() {
  const targetMenu = String(route.query.menu || '')
  activeMenu.value = ['assess', 'report', 'history'].includes(targetMenu) ? targetMenu : 'assess'
  activeOrb.value = null
}

// 重新打开时恢复已保存的量表答案
onMounted(() => {
  applyRouteQuery()
  loadHistoryReports()
  initializeProfileSessions().catch((error) => addLog(error, 'error', '初始化学习画像会话'))
  const saved = profileData.value.scaleScores
  if (saved) {
    saved.forEach((v, i) => { scaleAnswers[i] = v })
  }
  // 鎭㈠鑱婂ぉ璁板綍
  if (Array.isArray(profileData.value.chatMessages) && profileData.value.chatMessages.length) {
    chatMsgs.value = profileData.value.chatMessages
      .filter(item => item && (item.role === 'user' || item.role === 'bot' || item.role === 'assistant'))
      .map(item => ({
        id: item.id || createChatMessageId(item.role === 'assistant' ? 'bot' : item.role),
        role: item.role === 'assistant' ? 'bot' : item.role,
        text: String(item.text || item.content || ''),
        time: item.time || '',
        timestamp: item.timestamp || null,
        source: item.source || '',
        attachments: Array.isArray(item.attachments) ? item.attachments : [],
      }))
      .filter(item => item.text)
  }
  if (Array.isArray(profileData.value.chatHistory) && profileData.value.chatHistory.length) {
    chatHistory.value = profileData.value.chatHistory
      .filter(item => item && (item.role === 'user' || item.role === 'assistant' || item.role === 'bot'))
      .map(item => ({
        role: item.role === 'bot' ? 'assistant' : item.role,
        content: String(item.content || item.text || ''),
      }))
      .filter(item => item.content)
  } else if (chatMsgs.value.length) {
    chatHistory.value = chatMsgs.value.map(item => ({
      role: item.role === 'user' ? 'user' : 'assistant',
      content: item.text,
    }))
  }
  startLearningAvatar({ replayLatest: activeMenu.value === 'assess' })
  if (activeMenu.value === 'assess') {
    ensureInitialChatQuestion()
    scrollChatToBottom({ retry: true })
  }
})

// ???????????????????
watch(activeMenu, (val) => {
  if (val === 'assess') {
    startLearningAvatar()
    ensureInitialChatQuestion()
    scrollChatToBottom({ retry: true })
  }
})

watch(() => [route.query.collect, route.query.menu], () => {
  applyRouteQuery()
  if (activeMenu.value === 'history' || activeMenu.value === 'report') {
    loadHistoryReports()
  }
})

watch(
  () => chatMsgs.value.length,
  () => {
    if (activeMenu.value === 'assess') {
      scrollChatToBottom({ retry: true })
    }
  },
  { flush: 'post' },
)

watch(
  () => [activeMenu.value, currentReport.value?.id],
  ([menu]) => {
    resetReportPortraitView()
    if (menu === 'report') ensureReportPortrait()
  },
  { immediate: true },
)

// Do not auto-run the profile report agent on page entry/refresh.
// Report generation remains available through explicit user actions and the effect assessment update flow.

onBeforeUnmount(() => {
  resetReportPortraitView()
  digitalHumanRef.value?.destroyAvatar?.()
})
</script>

<style scoped>
.lp-page {
  display: flex;
  height: calc(100vh - 64px);
  min-height: calc(100vh - 64px);
  background: #f4faf9;
  position: relative;
  overflow: hidden !important;
}

/* Toast */
.toast-bar {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: #10b981;
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 4px 20px rgba(16, 185, 129, 0.35);
}
.toast-enter-active { animation: toastIn 0.3s ease; }
.toast-leave-active { animation: toastOut 0.3s ease; }
@keyframes toastIn { from { opacity: 0; transform: translateX(-50%) translateY(-16px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }
@keyframes toastOut { from { opacity: 1; transform: translateX(-50%) translateY(0); } to { opacity: 0; transform: translateX(-50%) translateY(-16px); } }

/* 宸︿晶瀵艰埅鏍?*/
.lp-sidebar {
  width: 240px;
  min-width: 240px;
  height: 100%;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-right: 1px solid var(--border, rgba(31, 166, 112, 0.1));
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-title {
  padding: 24px 24px 16px;
  font-size: 18px;
  font-weight: 700;
  color: #1f3f3b;
  letter-spacing: 0.5px;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 12px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: none;
  background: transparent;
  border-radius: 10px;
  cursor: pointer;
  font-size: 15px;
  color: #475569;
  transition: all 0.2s;
  text-align: left;
  width: 100%;
  position: relative;
}

.nav-item:hover {
  background: rgba(31, 188, 191, 0.06);
  color: #117a51;
}

.nav-item.active {
  background: rgba(31, 188, 191, 0.1);
  color: #117a51;
  font-weight: 600;
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* 鍙充晶鍐呭鍖?*/
.lp-content {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: 24px 32px;
  overflow-y: auto !important;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
}

.content-panel {
  width: 100%;
  min-height: 100%;
  overflow: visible !important;
}

.assess-panel {
  height: 100%;
  min-height: 0;
  overflow: hidden !important;
}

/* 绌虹姸鎬?*/
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 360px;
  gap: 16px;
}

.empty-icon {
  width: 72px;
  height: 72px;
  background: rgba(31, 188, 191, 0.08);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #21b978;
}

.empty-icon svg {
  width: 36px;
  height: 36px;
}

.empty-text {
  font-size: 18px;
  font-weight: 600;
  color: #334155;
  margin: 0;
}

.empty-hint {
  font-size: 14px;
  color: #94a3b8;
  margin: 0;
}

.empty-cta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 12px 28px;
  border: none;
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  font-size: 15px;
  font-weight: 600;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s;
  box-shadow: 0 4px 16px rgba(31, 188, 191, 0.35);
}

.empty-cta:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(31, 188, 191, 0.45);
}

.report-progress-inline {
  width: min(520px, 100%);
  display: grid;
  gap: 10px;
  margin: 6px 0 2px;
  color: #117a51;
  font-size: 14px;
  font-weight: 700;
}

.empty-actions-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}

.empty-actions-row .empty-cta {
  margin-top: 0;
  padding: 10px 18px;
  background: #eafff8;
  color: #117a51;
  border: 1px solid #b8eadf;
  box-shadow: none;
}

.generate-empty-cta.disabled,
.generate-empty-cta:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  transform: none;
  box-shadow: none;
}

.report-empty-dashboard {
  min-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding: 6px 0 28px;
}

.empty-report-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
}

.empty-report-head h2 {
  margin: 0;
  color: #172033;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: 0;
}

.empty-report-head p {
  margin: 8px 0 0;
  color: #7a8f8c;
  font-size: 15px;
}

.empty-report-grid {
  display: grid;
  grid-template-columns: minmax(560px, 1.04fr) minmax(560px, 1.16fr);
  gap: 18px;
  align-items: stretch;
}

.empty-report-card {
  border: 1px solid rgba(205, 239, 227, 0.72);
  border-radius: 20px;
  background:
    radial-gradient(circle at 18% 8%, rgba(221, 247, 234, 0.68), transparent 30%),
    rgba(255, 255, 255, 0.94);
  box-shadow: 0 12px 34px rgba(31, 72, 66, 0.08);
}

.empty-main-card {
  min-height: 650px;
  padding: 44px 46px 36px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
}

.empty-visual {
  width: 116px;
  height: 116px;
  display: grid;
  place-items: center;
  border-radius: 30px;
  background:
    radial-gradient(circle at 80% 10%, rgba(16, 185, 129, 0.22), transparent 34%),
    linear-gradient(145deg, rgba(241, 251, 247, 0.96), rgba(255, 255, 255, 0.82));
  box-shadow: inset 0 0 0 1px rgba(16, 185, 129, 0.08), 0 16px 36px rgba(16, 185, 129, 0.12);
}

.empty-visual-card {
  width: 78px;
  height: 78px;
  display: grid;
  place-items: center;
}

.empty-main-card h3 {
  margin: 0;
  color: #172033;
  font-size: 24px;
  font-weight: 800;
}

.empty-report-desc {
  max-width: 520px;
  margin: 0;
  color: #667a77;
  font-size: 15px;
  line-height: 1.8;
  text-align: center;
}

.empty-progress-box {
  width: min(560px, 100%);
  display: grid;
  gap: 12px;
  margin-top: 4px;
}

.empty-progress-meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #213a39;
  font-size: 15px;
}

.empty-progress-meta span {
  color: #0e9f6e;
  font-weight: 800;
}

.empty-progress-track {
  height: 10px;
  overflow: visible;
  border-radius: 999px;
  background: #e9f0ee;
}

.empty-progress-track div {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #20c997, #10b981);
  box-shadow: 0 0 18px rgba(16, 185, 129, 0.26);
  transition: width 0.25s ease;
}

.empty-collect-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 14px;
  margin-top: 10px;
}

.empty-collect-actions button {
  height: 50px;
  padding: 0 22px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  border: 1px solid #bcebdd;
  border-radius: 999px;
  background: #f1fbf7;
  color: #0e9f6e;
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.empty-collect-actions button:hover {
  transform: translateY(-2px);
  background: #e3f8ef;
  box-shadow: 0 10px 22px rgba(16, 185, 129, 0.12);
}

.empty-generate-btn {
  width: min(360px, 100%);
  height: 58px;
  margin-top: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border: 0;
  border-radius: 14px;
  background: linear-gradient(135deg, #20c997, #0e9f6e);
  color: #fff;
  font-size: 16px;
  font-weight: 900;
  cursor: pointer;
  box-shadow: 0 14px 28px rgba(16, 185, 129, 0.24);
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.empty-generate-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 18px 36px rgba(16, 185, 129, 0.28);
}

.empty-generate-btn.disabled,
.empty-generate-btn:disabled {
  cursor: not-allowed;
  color: #9aaea9;
  background: linear-gradient(135deg, #eef2f1, #e5ebe9);
  box-shadow: none;
}

.empty-tip-box {
  width: min(680px, 100%);
  min-height: 96px;
  margin-top: 18px;
  padding: 18px 20px;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 14px;
  align-items: start;
  border: 1px solid rgba(16, 185, 129, 0.18);
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(241, 251, 247, 0.96), rgba(255, 255, 255, 0.78));
  color: #0e9f6e;
}

.empty-tip-box strong {
  display: block;
  margin-bottom: 6px;
  color: #0e9f6e;
  font-size: 15px;
}

.empty-tip-box p {
  margin: 0;
  color: #667a77;
  font-size: 14px;
  line-height: 1.7;
}

.empty-side-stack {
  display: grid;
  gap: 16px;
}

.agent-state-card {
  min-height: 360px;
  padding: 24px;
}

.agent-state-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 18px;
}

.agent-state-head h3,
.preview-state-card h3 {
  margin: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #172033;
  font-size: 17px;
  font-weight: 900;
}

.agent-state-head span {
  position: relative;
  color: #10b981;
  font-size: 14px;
  font-weight: 800;
}

.agent-state-head span::before {
  content: "";
  width: 7px;
  height: 7px;
  margin-right: 8px;
  display: inline-block;
  border-radius: 999px;
  background: currentColor;
}

.agent-state-body {
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr);
  gap: 22px;
  align-items: stretch;
}

.agent-timeline {
  display: grid;
  gap: 14px;
  padding: 8px 0;
}

.agent-time-step {
  position: relative;
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 12px;
  color: #98a2a0;
}

.agent-time-step:not(:last-child)::after {
  content: "";
  position: absolute;
  left: 16px;
  top: 34px;
  width: 1px;
  height: calc(100% + 2px);
  border-left: 1px dashed #cfe0dc;
}

.agent-time-step > span {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: #edf2f1;
  color: #8a9c99;
  font-size: 13px;
  font-weight: 900;
}

.agent-time-step strong {
  display: block;
  color: #536b68;
  font-size: 15px;
  font-weight: 900;
}

.agent-time-step p {
  margin: 4px 0 0;
  color: #98a2a0;
  font-size: 13px;
  line-height: 1.45;
}

.agent-time-step.done > span,
.agent-time-step.active > span {
  background: linear-gradient(135deg, #20c997, #10b981);
  color: #fff;
  box-shadow: 0 0 0 6px rgba(16, 185, 129, 0.12);
}

.agent-time-step.active strong {
  color: #0e9f6e;
}

.agent-time-step.done::after,
.agent-time-step.active::after {
  border-left-color: rgba(16, 185, 129, 0.35);
}

.agent-log-panel {
  min-height: 340px;
  padding: 20px 22px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 14px;
  background: #172033;
  color: #e7fff6;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05), 0 18px 32px rgba(15, 23, 42, 0.16);
}

.agent-log-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.09);
}

.agent-log-head strong {
  font-size: 15px;
  font-weight: 900;
}

.agent-log-head span {
  color: #34d399;
  font-size: 13px;
  font-weight: 800;
}

.agent-log-overview {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 16px;
  padding: 14px 0 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.agent-log-overview > div {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.agent-log-overview span,
.agent-log-progress > div:first-child > span {
  color: #91aaa4;
  font-size: 11px;
  font-weight: 700;
}

.agent-log-overview strong {
  overflow: hidden;
  color: #f2fff9;
  font-size: 12px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-log-overview .monospace,
.agent-log-entry .monospace {
  font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
}

.agent-log-progress {
  display: grid;
  gap: 7px;
  padding: 12px 0 2px;
}

.agent-log-progress > div:first-child {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.agent-log-progress > div:first-child strong {
  color: #58e2b0;
  font-size: 12px;
}

.agent-log-progress-track {
  height: 4px;
  overflow: hidden;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
}

.agent-log-progress-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #34d399;
  transition: width 0.25s ease;
}

.agent-log-lines {
  display: grid;
  gap: 10px;
  max-height: 310px;
  margin-top: 12px;
  padding-right: 5px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(52, 211, 153, 0.48) transparent;
}

.agent-log-entry {
  position: relative;
  padding: 11px 12px 11px 30px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
}

.agent-log-entry::before {
  content: "";
  position: absolute;
  left: 12px;
  top: 16px;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #34d399;
  box-shadow: 0 0 0 5px rgba(52, 211, 153, 0.12);
}

.agent-log-entry.warning::before {
  background: #fbbf24;
  box-shadow: 0 0 0 5px rgba(251, 191, 36, 0.12);
}

.agent-log-entry.failed::before,
.agent-log-entry.error::before {
  background: #fb7185;
  box-shadow: 0 0 0 5px rgba(251, 113, 133, 0.12);
}

.agent-log-entry header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  gap: 7px;
  align-items: center;
}

.agent-log-entry time {
  color: #8ee7c3;
  font-size: 12px;
  font-weight: 800;
}

.agent-log-entry header strong {
  overflow: hidden;
  color: #e7fff6;
  font-size: 12px;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-log-entry header span,
.agent-log-entry header b {
  color: #98b9b0;
  font-size: 10px;
  font-weight: 800;
}

.agent-log-entry > p {
  margin: 7px 0 0;
  color: #f2fff9;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.55;
}

.agent-log-entry dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px 12px;
  margin: 9px 0 0;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
}

.agent-log-entry dl > div {
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 6px;
}

.agent-log-entry dt {
  color: #84a49c;
  font-size: 10px;
  white-space: nowrap;
}

.agent-log-entry dd {
  overflow: hidden;
  margin: 0;
  color: #cae9df;
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-log-entry.thinking > p {
  color: #cbd5e1;
  font-weight: 600;
}

.agent-log-empty {
  min-height: 210px;
  display: grid;
  align-content: center;
  justify-items: center;
  gap: 10px;
  text-align: center;
}

.agent-log-empty strong {
  color: #e7fff6;
  font-size: 16px;
  font-weight: 900;
}

.agent-log-empty p {
  max-width: 320px;
  margin: 0;
  color: #9fb5b1;
  font-size: 13px;
  line-height: 1.7;
}

.preview-state-card {
  min-height: 210px;
  padding: 24px;
  display: grid;
  grid-template-columns: 0.82fr 1px 1.18fr;
  gap: 22px;
  align-items: stretch;
}

.status-explain {
  display: grid;
  align-content: start;
  gap: 12px;
}

.status-explain strong {
  display: inline-flex;
  width: fit-content;
  padding: 7px 12px;
  border-radius: 999px;
  background: #ddf7ea;
  color: #0e9f6e;
  font-size: 14px;
}

.status-explain p,
.result-preview p {
  margin: 0;
  color: #667a77;
  font-size: 14px;
  line-height: 1.7;
}

.preview-divider {
  background: #eef2f1;
}

.result-preview {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 14px 18px;
  align-items: center;
}

.result-preview h3 {
  grid-column: 1 / -1;
}

.report-preview-mini {
  height: 120px;
  padding: 12px;
  display: grid;
  grid-template-columns: 1fr 60px;
  gap: 10px;
  align-items: center;
  border: 1px solid #e6f1ee;
  border-radius: 12px;
  background: #fff;
}

.mini-radar {
  min-width: 0;
}

.mini-radar svg {
  width: 100%;
  height: auto;
}

.mini-score {
  width: 54px;
  height: 54px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: conic-gradient(#10b981 85%, #e6f1ee 0);
}

.mini-score span {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: inherit;
  background: #fff;
  color: #0e9f6e;
  font-size: 18px;
  font-weight: 900;
}

.result-preview button {
  width: fit-content;
  height: 42px;
  padding: 0 18px;
  border: 1px solid #bcebdd;
  border-radius: 10px;
  background: #f1fbf7;
  color: #0e9f6e;
  font-size: 14px;
  font-weight: 900;
  cursor: pointer;
}

@media (max-width: 1500px) {
  .empty-report-grid,
  .agent-state-body,
  .preview-state-card {
    grid-template-columns: 1fr;
  }

  .preview-divider {
    height: 1px;
  }
}

@media (max-width: 900px) {
  .report-empty-dashboard {
    padding-bottom: 18px;
  }

  .empty-main-card,
  .agent-state-card,
  .preview-state-card {
    padding: 22px;
  }

  .empty-main-card {
    min-height: auto;
  }

  .result-preview {
    grid-template-columns: 1fr;
  }

  .agent-log-overview,
  .agent-log-entry dl {
    grid-template-columns: 1fr;
  }

  .agent-log-entry header {
    grid-template-columns: auto minmax(0, 1fr) auto;
  }

  .agent-log-entry header b {
    display: none;
  }
}

.analysis-stream-console {
  width: min(680px, 100%);
  margin-top: 8px;
  padding: 18px;
  border: 1px solid rgba(16, 185, 129, 0.16);
  border-radius: 18px;
  background:
    radial-gradient(circle at 18% 0%, rgba(221, 247, 234, 0.85), transparent 38%),
    rgba(255, 255, 255, 0.92);
  box-shadow: 0 16px 38px rgba(31, 72, 66, 0.08);
  backdrop-filter: blur(14px);
}

.analysis-stream-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(16, 185, 129, 0.1);
}

.analysis-stream-head > div {
  display: grid;
  gap: 4px;
}

.analysis-stream-head strong {
  color: #1f3433;
  font-size: 16px;
  font-weight: 800;
}

.analysis-stream-head span {
  color: #617875;
  font-size: 13px;
}

.analysis-stream-head button {
  height: 34px;
  padding: 0 14px;
  border: 1px solid #cdefe3;
  border-radius: 999px;
  background: #f1fbf7;
  color: #0e9f6e;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.analysis-stream-lines {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.analysis-step-item {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  align-items: start;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(238, 242, 241, 0.96);
  border-radius: 14px;
  background: rgba(248, 252, 251, 0.86);
}

.analysis-step-dot {
  width: 12px;
  height: 12px;
  margin-top: 5px;
  border-radius: 999px;
  background: #20c997;
  box-shadow: 0 0 0 5px rgba(32, 201, 151, 0.12);
}

.analysis-step-item.done .analysis-step-dot {
  background: #0e9f6e;
  box-shadow: 0 0 0 5px rgba(14, 159, 110, 0.14);
}

.analysis-step-item.error .analysis-step-dot {
  background: #ef4444;
  box-shadow: 0 0 0 5px rgba(239, 68, 68, 0.12);
}

.analysis-step-copy {
  display: grid;
  gap: 4px;
}

.analysis-step-copy strong {
  color: #213a39;
  font-size: 14px;
  font-weight: 800;
}

.analysis-step-copy span {
  color: #667a77;
  font-size: 13px;
  line-height: 1.5;
}

.analysis-step-item em {
  color: #9aaea9;
  font-size: 12px;
  font-style: normal;
  white-space: nowrap;
}

/* 鎶ュ憡鍐呭 */
.report-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
  animation: fadeIn 0.3s ease;
}

.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.report-title {
  font-size: 22px;
  font-weight: 700;
  color: #1f3f3b;
  margin: 0;
}

.report-actions {
  display: flex;
  gap: 12px;
}

.reset-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border: 1px solid #e2e8f0;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  color: #475569;
  font-size: 14px;
  font-weight: 500;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.reset-btn:hover {
  border-color: #ef4444;
  color: #ef4444;
  background: #fef2f2;
}

.report-meta {
  font-size: 14px;
  color: #117a51;
  font-weight: 500;
  background: rgba(31, 188, 191, 0.08);
  padding: 10px 16px;
  border-radius: 8px;
  margin: 0;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: #1f3f3b;
  margin: 0 0 16px;
}

.meta-text {
  font-size: 13px;
  color: #94a3b8;
  margin: 12px 0 0;
}

/* 闆疯揪鍥惧尯鍩?*/
.radar-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.radar-card {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 14px;
  padding: 28px 32px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.radar-container {
  width: 100%;
  max-width: 360px;
}

.radar-svg {
  width: 100%;
  height: auto;
}

.radar-label {
  font-size: 12px;
  fill: #475569;
  font-weight: 500;
}

.radar-score {
  font-size: 11px;
  fill: #117a51;
  font-weight: 700;
}

.report-radar-panel { margin: 18px 0; padding: 22px 26px; border-color: #dcece4; background: #ffffff; }
.report-growth-banner { position: relative; display: flex; align-items: center; min-height: 142px; overflow: hidden; margin: 16px 0; border: 1px solid #dcece4; border-radius: 8px; background: #f7fffa; }
.report-growth-banner img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center 57%; opacity: .5; }
.report-growth-banner > div { position: relative; z-index: 1; width: min(560px, 56%); margin-left: clamp(20px, 4vw, 54px); padding: 16px 20px; border-left: 4px solid #18a36a; background: rgba(255, 255, 255, .9); box-shadow: 0 5px 18px rgba(18, 110, 76, .08); }
.report-growth-banner span { display: block; color: #178458; font-size: 13px; font-weight: 700; }
.report-growth-banner strong { display: block; margin: 5px 0; color: #1b3f36; font-size: 20px; }
.report-growth-banner p { margin: 0; color: #547168; font-size: 13px; line-height: 1.6; }
.report-radar-wrap { display: grid; grid-template-columns: minmax(285px, .95fr) minmax(260px, .9fr) minmax(190px, .55fr); align-items: center; gap: 26px; min-height: 300px; }
.report-radar-visual { display: grid; place-items: center; min-width: 0; }
.report-radar-wrap .radar-svg { width: min(100%, 320px); height: auto; }
.report-radar-scores { display: grid; gap: 10px; }
.report-radar-scores div { display: grid; grid-template-columns: 76px 1fr 34px; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid #eaf1ee; color: #668078; font-size: 13px; }
.report-radar-scores i { height: 6px; overflow: hidden; border-radius: 99px; background: #e6f1eb; }
.report-radar-scores i b { display: block; height: 100%; border-radius: inherit; background: #1aac70; }
.report-radar-scores strong { color: #16865a; font-size: 15px; text-align: right; }
.report-radar-stage { align-self: stretch; display: flex; flex-direction: column; justify-content: center; padding: 20px; border-left: 1px solid #dceae4; background: #f6fffa; }
.report-radar-stage span { color: #23875d; font-size: 12px; font-weight: 700; }
.report-radar-stage strong { margin: 8px 0; color: #1a4137; font-size: 18px; line-height: 1.45; }
.report-radar-stage p { margin: 0; color: #6a8179; font-size: 13px; line-height: 1.7; }
@media (max-width: 960px) { .report-radar-wrap { grid-template-columns: minmax(260px, 1fr) minmax(240px, 1fr); } .report-radar-stage { grid-column: 1 / -1; border-top: 1px solid #dceae4; border-left: 0; } }
@media (max-width: 760px) { .report-growth-banner { min-height: 190px; align-items: flex-end; } .report-growth-banner > div { width: auto; margin: 14px; } .report-radar-wrap { grid-template-columns: 1fr; } .report-radar-scores { grid-template-columns: 1fr; } .report-radar-stage { grid-column: auto; } }

/* 寰楀垎鍒楄〃 */
.scores-card {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 14px;
  padding: 28px 32px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05);
}

.score-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.score-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.score-label {
  font-size: 13px;
  color: #475569;
  min-width: 220px;
  flex-shrink: 0;
}

.score-bar-wrap {
  flex: 1;
  height: 8px;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
}

.score-bar {
  height: 100%;
  background: linear-gradient(90deg, #21b978, #117a51);
  border-radius: 4px;
  transition: width 0.6s ease;
}

.score-val {
  font-size: 13px;
  font-weight: 600;
  color: #117a51;
  min-width: 32px;
  text-align: right;
}

/* 瀛︿範鑳屾櫙 */
.bg-card {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 14px;
  padding: 28px 32px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05);
}

.bg-text {
  font-size: 15px;
  color: #334155;
  line-height: 1.7;
  margin: 0;
  padding: 16px;
  background: #f4faf9;
  border-radius: 10px;
}

/* 涓婁紶璁板綍 */
.upload-card {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 14px;
  padding: 28px 32px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05);
}

.upload-record-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.upload-record-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #f4faf9;
  border-radius: 8px;
  font-size: 14px;
  color: #475569;
}

.upload-record-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-record-size {
  color: #94a3b8;
  font-size: 13px;
}

/* Learning report dashboard refresh */
.report-content {
  display: grid;
  gap: 14px;
  width: min(100%, 1560px);
  margin: 0 auto;
  padding: 4px 0 28px;
  color: #172033;
}

.report-content .report-card,
.report-overview-card {
  border: 1px solid #e6eeee;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.045);
}

.report-content .report-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  min-height: 42px;
}

.report-content .report-title {
  margin: 0;
  color: #111827;
  font-size: 26px;
  font-weight: 850;
  line-height: 1.2;
}

.report-content .report-meta {
  margin: 8px 0 0;
  color: #667085;
  font-size: 13px;
}

.report-content .reset-btn {
  height: 40px;
  padding: 0 16px;
  border: 1px solid rgba(16, 185, 129, 0.24);
  border-radius: 999px;
  background: #effbf6;
  color: #079669;
  font-size: 14px;
  font-weight: 800;
  box-shadow: none;
}

.report-content .reset-btn:hover {
  transform: translateY(-1px);
  background: #dcf8ec;
  color: #047857;
  box-shadow: 0 10px 20px rgba(16, 185, 129, 0.12);
}

.report-overview-card {
  display: grid;
  grid-template-columns: minmax(190px, 0.82fr) minmax(300px, 1.24fr) minmax(260px, 0.95fr) minmax(250px, 0.9fr);
  overflow: hidden;
}

.overview-block {
  min-width: 0;
  min-height: 142px;
  padding: 24px 30px;
  border-right: 1px solid #e8eeee;
}

.overview-block:last-child {
  border-right: 0;
}

.overview-label {
  display: block;
  margin-bottom: 12px;
  color: #667085;
  font-size: 13px;
  font-weight: 700;
}

.overview-block strong {
  display: block;
  color: #101828;
  font-size: 20px;
  font-weight: 850;
  line-height: 1.28;
}

.progress-block strong {
  color: #059669;
  font-size: 30px;
  letter-spacing: 0;
}

.overview-block p {
  margin: 10px 0 0;
  color: #52605d;
  font-size: 13px;
  line-height: 1.65;
}

.overview-progress-track {
  height: 9px;
  margin-top: 14px;
  overflow: hidden;
  border-radius: 999px;
  background: #edf2f1;
}

.overview-progress-track div {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #10b981, #059669);
}

.overview-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.overview-icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 999px;
  background: #dff7ec;
  color: #059669;
  font-size: 14px;
  font-weight: 900;
}

.overview-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.overview-tags span,
.tag {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.3;
}

.overview-tags span {
  background: #fff3e4;
  color: #dd7415;
}

.time-block strong {
  font-size: 19px;
}

.report-content .section-title {
  position: relative;
  margin: 0;
  padding-left: 14px;
  color: #1f2937;
  font-size: 17px;
  font-weight: 850;
}

.report-content .section-title::before {
  content: "";
  position: absolute;
  left: 0;
  top: 3px;
  width: 4px;
  height: 18px;
  border-radius: 999px;
  background: #10b981;
}

.report-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.report-card-head > span {
  color: #059669;
  font-size: 13px;
  font-weight: 850;
}

.report-dimension-evidence-panel,
.report-content .ai-analysis-section,
.report-content .ai-recommendations,
.report-content .bg-card {
  padding: 22px 30px;
}

.report-profile-dimension-list {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0;
  overflow: hidden;
  border: 1px solid #edf2f1;
  border-radius: 8px;
}

.report-profile-dimension-row {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  align-items: start;
  gap: 11px;
  min-height: 82px;
  padding: 18px 18px 14px;
  border-right: 1px solid #edf2f1;
  border-bottom: 1px solid #edf2f1;
  background: #ffffff;
}

.report-profile-dimension-row:nth-child(5n) {
  border-right: 0;
}

.report-profile-dimension-row:nth-last-child(-n + 5) {
  border-bottom: 0;
}

.report-profile-dimension-row.done {
  background: linear-gradient(180deg, #ffffff, #fbfffd);
}

.dimension-index {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 999px;
  background: #e3f8ef;
  color: #059669;
  font-size: 12px;
  font-weight: 900;
}

.report-profile-dimension-row strong {
  display: block;
  margin-bottom: 6px;
  color: #203533;
  font-size: 13px;
  font-weight: 850;
  line-height: 1.35;
}

.report-profile-dimension-row p {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: #667085;
  font-size: 12px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.dimension-status {
  display: none;
}

.report-main-grid,
.report-info-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.08fr);
  gap: 14px;
}

.report-info-grid {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

.report-content .ai-analysis-grid {
  display: grid;
  grid-template-columns: 128px 98px minmax(0, 1fr);
  gap: 20px;
  align-items: center;
}

.report-content .analysis-profile-portrait,
.report-content .profile-portrait-loader {
  width: 128px;
  height: 128px;
  margin: 0;
  overflow: hidden;
  border: 1px solid #cce9db;
  border-radius: 8px;
  background: #f2fbf6;
  box-shadow: 0 8px 20px rgba(15, 118, 86, 0.1);
}

.report-content .analysis-profile-portrait img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.report-content .profile-portrait-loader {
  display: grid;
  place-items: center;
}

.report-content .profile-portrait-loader span {
  width: 38px;
  height: 38px;
  border: 3px solid #ccebdd;
  border-top-color: #0d9b67;
  border-radius: 50%;
  animation: profile-portrait-spin .85s linear infinite;
}

@keyframes profile-portrait-spin {
  to { transform: rotate(360deg); }
}

.report-content .ai-score-circle {
  width: 98px;
  height: 98px;
  border: 8px solid #dff6eb;
  border-right-color: #10b981;
  border-bottom-color: #10b981;
  background: #ffffff;
  color: #059669;
  box-shadow: none;
}

.report-content .ai-score-num {
  color: #059669;
  font-size: 30px;
  font-weight: 900;
}

.report-content .ai-score-label {
  color: #667085;
  font-size: 12px;
}

.report-content .ai-style-tag {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.report-content .style-label {
  color: #667085;
  font-size: 13px;
  font-weight: 700;
}

.report-content .style-value {
  color: #059669;
  font-size: 20px;
  line-height: 1.25;
}

.report-content .ai-style-tag p {
  margin: 0;
  color: #52605d;
  font-size: 13px;
  line-height: 1.7;
}

.report-content .ai-compare-grid {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 0;
  margin-top: 8px;
  border-top: 1px solid #edf2f1;
}

.report-content .ai-compare-card {
  min-height: 130px;
  padding: 18px 20px 4px 0;
  border: 0;
  border-right: 1px solid #edf2f1;
  border-radius: 0;
  background: transparent;
}

.report-content .ai-compare-card:last-child {
  padding-left: 24px;
  border-right: 0;
}

.report-content .compare-title {
  margin: 0 0 12px;
  color: #1f2937;
  font-size: 14px;
  font-weight: 850;
}

.report-content .compare-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}

.report-content .strength-tag {
  background: #e5f8ef;
  color: #047857;
}

.report-content .weakness-tag {
  background: #fff3e4;
  color: #dd7415;
}

.report-content .ai-recommendations .rec-list {
  position: relative;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin-top: 34px;
}

.report-content .ai-recommendations .rec-list::before {
  content: "";
  position: absolute;
  top: 13px;
  left: 22px;
  right: 22px;
  height: 1px;
  background: #dde8e5;
}

.report-content .ai-recommendations .rec-item {
  position: relative;
  display: grid;
  align-content: start;
  gap: 16px;
  padding: 0;
  background: transparent;
}

.report-content .ai-recommendations .rec-num {
  position: relative;
  z-index: 1;
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 999px;
  background: #059669;
  color: #ffffff;
  font-size: 13px;
  font-weight: 900;
}

.report-content .ai-recommendations .rec-text {
  color: #344543;
  font-size: 13px;
  line-height: 1.75;
}

.report-evidence-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.report-evidence-item {
  display: grid;
  gap: 6px;
  min-height: 68px;
  padding: 12px 14px;
  border-radius: 8px;
  background: #f5faf8;
}

.report-evidence-item span {
  color: #667085;
  font-size: 12px;
}

.report-evidence-item strong {
  color: #059669;
  font-size: 15px;
  font-weight: 900;
}

.report-content .bg-text {
  min-height: 46px;
  padding: 0;
  background: transparent;
  color: #475467;
  font-size: 14px;
  line-height: 1.75;
}

.report-content .meta-text {
  margin-top: 14px;
  color: #8a9a97;
  font-size: 12px;
}

@media (max-width: 1380px) {
  .report-overview-card {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .overview-block:nth-child(2n) {
    border-right: 0;
  }

  .overview-block:nth-child(-n + 2) {
    border-bottom: 1px solid #e8eeee;
  }

  .report-profile-dimension-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .report-profile-dimension-row:nth-child(5n) {
    border-right: 1px solid #edf2f1;
  }

  .report-profile-dimension-row:nth-child(2n) {
    border-right: 0;
  }

  .report-profile-dimension-row:nth-last-child(-n + 5) {
    border-bottom: 1px solid #edf2f1;
  }

  .report-profile-dimension-row:nth-last-child(-n + 2) {
    border-bottom: 0;
  }
}

@media (max-width: 1100px) {
  .report-main-grid,
  .report-info-grid {
    grid-template-columns: 1fr;
  }

  .report-content .ai-recommendations .rec-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .report-content .report-header,
  .report-overview-card,
  .report-content .ai-analysis-grid,
  .report-content .ai-compare-grid,
  .report-content .ai-recommendations .rec-list,
  .report-evidence-list {
    grid-template-columns: 1fr;
  }

  .report-content .report-header {
    display: grid;
  }

  .report-content .analysis-profile-portrait,
  .report-content .profile-portrait-loader {
    width: 112px;
    height: 112px;
  }

  .overview-block,
  .overview-block:nth-child(2n),
  .overview-block:nth-child(-n + 2) {
    border-right: 0;
    border-bottom: 1px solid #e8eeee;
  }

  .overview-block:last-child {
    border-bottom: 0;
  }

  .report-profile-dimension-list {
    grid-template-columns: 1fr;
  }

  .report-profile-dimension-row,
  .report-profile-dimension-row:nth-child(2n),
  .report-profile-dimension-row:nth-child(5n),
  .report-profile-dimension-row:nth-last-child(-n + 2),
  .report-profile-dimension-row:nth-last-child(-n + 5) {
    border-right: 0;
    border-bottom: 1px solid #edf2f1;
  }

  .report-profile-dimension-row:last-child {
    border-bottom: 0;
  }

  .report-content .ai-compare-card,
  .report-content .ai-compare-card:last-child {
    padding: 16px 0 0;
    border-right: 0;
  }

  .report-content .ai-recommendations .rec-list::before {
    display: none;
  }
}

.questionnaire-card {
  padding: 18px 26px 22px;
}

.questionnaire-row {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(220px, 0.8fr) minmax(300px, 1fr);
  gap: 28px;
  align-items: center;
}

.questionnaire-main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.questionnaire-main strong {
  color: #1f3433;
  font-size: 15px;
}

.questionnaire-status {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.questionnaire-status.done {
  background: #ddf7ea;
  color: #0e9f6e;
}

.questionnaire-status.pending {
  background: #fff2df;
  color: #f97316;
}

.questionnaire-time {
  display: grid;
  gap: 4px;
}

.questionnaire-time span {
  color: #7a8f8c;
  font-size: 12px;
}

.questionnaire-time strong {
  color: #475467;
  font-size: 13px;
}

.questionnaire-progress {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  color: #475467;
  font-size: 13px;
  font-weight: 800;
}

.questionnaire-progress-track {
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: #edf2f1;
}

.questionnaire-progress-track div {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #20c997, #0e9f6e);
}

/* 璇勪及鐢诲儚甯冨眬 */
.assess-layout {
  display: grid;
  grid-template-columns: clamp(560px, 38vw, 640px) minmax(0, 1fr);
  gap: 24px;
  align-items: stretch;
  height: min(760px, calc(100vh - 150px));
  min-height: 0;
  overflow: hidden;
}

/* 鍙充晶闈㈡澘锛氳繘搴︽潯 + 鍏夌悆 */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

/* 鍙充晶閲囬泦浠诲姟鍒楄〃 */
.collect-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  justify-content: center;
  flex: 1;
  min-height: 0;
}

/* 鏁板瓧浜鸿垶鍙?*/
.digital-human-stage {
  position: relative;
  border: 2px dashed #c5d8d8;
  border-radius: 20px;
  background: linear-gradient(145deg, #f0fdfa 0%, #e6f7f5 40%, #f5fffe 100%);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 0;
  box-shadow: 0 2px 16px rgba(31,188,191,0.06);
}

/* 鐢佃矾鏉胯儗鏅汗鐞?*/
.stage-circuit-bg {
  position: absolute;
  inset: 0;
  opacity: 0.06;
  background-image:
    linear-gradient(rgba(31,188,191,1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(31,188,191,1) 1px, transparent 1px),
    radial-gradient(circle, rgba(31,188,191,0.6) 1.5px, transparent 1.5px);
  background-size: 40px 40px, 40px 40px, 80px 80px;
  background-position: 0 0, 0 0, 20px 20px;
}

/* 鑸炲彴鍏夌悆瑁呴グ */
.stage-orb-deco {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(31,188,191,0.2), transparent 70%);
  animation: orbFloat 4s ease-in-out infinite;
}

.orb-deco-1 {
  width: 80px;
  height: 80px;
  top: 20px;
  right: 30px;
  animation-delay: 0s;
}

.orb-deco-2 {
  width: 56px;
  height: 56px;
  bottom: 30px;
  left: 24px;
  animation-delay: 1.3s;
}

.orb-deco-3 {
  width: 44px;
  height: 44px;
  top: 40%;
  right: 12%;
  animation-delay: 2.6s;
}

@keyframes orbFloat {
  0%, 100% { transform: translateY(0) scale(1); opacity: 0.7; }
  50% { transform: translateY(-12px) scale(1.1); opacity: 1; }
}

/* 鑸炲彴鍐呮暟瀛椾汉鏍峰紡瑕嗙洊 */
.digital-human-stage :deep(.avatar-panel) {
  position: relative;
  z-index: 1;
  width: 100%;
  min-height: 0;
  height: 100%;
  border: none;
  border-radius: 0;
  background: transparent;
}

.digital-human-stage :deep(.avatar-stage) {
  inset: 0;
}

.digital-human-stage :deep(.avatar-status) {
  top: 10px;
  left: 10px;
  font-size: 12px;
  padding: 5px 8px;
}

.digital-human-stage :deep(.avatar-placeholder strong) {
  font-size: 18px;
}

.digital-human-stage :deep(.avatar-placeholder span) {
  font-size: 12px;
}

@media (max-width: 1180px) {
  .assess-layout {
    grid-template-columns: 1fr;
  }

  .digital-human-stage {
    min-height: 520px;
  }
}

/* 鑸炲彴涓績鍐呭 */
.stage-center {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
  padding: 32px;
}

.stage-icon-wrap {
  width: 100px;
  height: 100px;
  border-radius: 24px;
  background: rgba(31,188,191,0.08);
  border: 1.5px solid rgba(31,188,191,0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: chipPulse 3s ease-in-out infinite;
}

@keyframes chipPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(31,188,191,0.1); }
  50% { box-shadow: 0 0 24px 4px rgba(31,188,191,0.12); }
}

.stage-chip-icon {
  width: 56px;
  height: 56px;
  color: #21b978;
}

.stage-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #1a2e35;
}

.stage-desc {
  margin: 0;
  font-size: 14px;
  color: #7a9a9e;
  line-height: 1.5;
}

/* 瀹屾垚搴﹁繘搴︽潯 */
.progress-section {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 14px;
  padding: 20px 24px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.progress-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f3f3b;
}

.progress-count {
  margin-left: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #117a51;
}

.progress-bar-wrap {
  width: 100%;
  height: 8px;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #21b978, #117a51);
  border-radius: 4px;
  transition: width 0.6s ease;
}

.progress-hint {
  font-size: 13px;
  color: #94a3b8;
  margin: 10px 0 0;
}

/* 閲囬泦浠诲姟琛?*/
.collect-item {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  min-height: 96px;
  padding: 16px 18px;
  border: 1px solid rgba(33, 185, 120, 0.18);
  background: linear-gradient(135deg, rgba(236, 255, 245, 0.96), rgba(245, 255, 253, 0.96));
  cursor: pointer;
  border-radius: 8px;
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
  position: relative;
  text-align: left;
}

.collect-item:hover {
  border-color: rgba(33, 185, 120, 0.42);
  box-shadow: 0 10px 24px rgba(17, 122, 81, 0.1);
  transform: translateY(-1px);
}

.collect-item.done {
  border-color: rgba(33, 185, 120, 0.38);
  background: linear-gradient(135deg, rgba(224, 255, 239, 0.98), rgba(244, 255, 250, 0.98));
}

.collect-icon {
  width: 52px;
  height: 52px;
  flex: 0 0 52px;
  border-radius: 50%;
  background: linear-gradient(145deg, #21b978, #117a51);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--surface, rgba(255, 255, 255, 0.94));
  box-shadow: 0 8px 20px rgba(31, 188, 191, 0.24);
}

.collect-copy {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.collect-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.collect-title {
  font-size: 16px;
  font-weight: 800;
  color: #1f3f3b;
}

.collect-state {
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(33, 185, 120, 0.12);
  color: #117a51;
  font-size: 12px;
  font-weight: 800;
}

.collect-desc {
  color: #6b7f86;
  font-size: 13px;
  line-height: 1.45;
  white-space: normal;
}

.collect-action {
  flex: 0 0 auto;
  min-width: 56px;
  padding: 8px 12px;
  border-radius: 8px;
  background: #ffffff;
  color: #117a51;
  border: 1px solid rgba(33, 185, 120, 0.24);
  font-size: 13px;
  font-weight: 800;
  text-align: center;
}

/* 琛ㄥ崟鍖?*/
.form-area {
  width: 100%;
}

.form-card {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 14px;
  padding: 28px 32px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05);
  animation: fadeIn 0.25s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.form-title {
  font-size: 17px;
  font-weight: 700;
  color: #1f3f3b;
  margin: 0 0 20px;
}

.form-placeholder {
  text-align: center;
  padding: 32px;
  color: #94a3b8;
  font-size: 14px;
}

.completed-placeholder {
  padding: 40px 32px;
}

.completed-icon {
  margin-bottom: 12px;
  animation: completedPulse 2s ease-in-out infinite;
}

.completed-text {
  color: #10b981;
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 4px;
}

.completed-hint {
  color: #10b981;
  font-size: 13px;
  margin: 0;
  opacity: 0.8;
}

@keyframes completedPulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.08); opacity: 0.85; }
}

/* 閲忚〃 */
.scale-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.scale-item {
  padding-bottom: 20px;
  border-bottom: 1px solid #f1f5f9;
}

.scale-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.scale-q {
  font-size: 15px;
  color: #334155;
  margin: 0 0 12px;
  line-height: 1.5;
}

.scale-options {
  display: flex;
  gap: 12px;
  margin-bottom: 6px;
}

.scale-opt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  flex: 1;
  max-width: 56px;
}

.scale-opt input {
  display: none;
}

.opt-dot {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid #d1d5db;
  background: var(--surface, rgba(255, 255, 255, 0.94));
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.scale-opt input:checked + .opt-dot {
  border-color: #21b978;
  background: #21b978;
  box-shadow: 0 2px 8px rgba(31, 188, 191, 0.35);
}

.scale-opt input:checked + .opt-dot::after {
  content: '\2713';
  color: var(--surface, rgba(255, 255, 255, 0.94));
  font-size: 16px;
  font-weight: 700;
}

.scale-opt:hover .opt-dot {
  border-color: #21b978;
}

.opt-text {
  font-size: 12px;
  color: #64748b;
}

.scale-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #94a3b8;
}

/* 涓婁紶鍖哄煙 */
.upload-zone {
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-zone:hover {
  border-color: #21b978;
  background: rgba(31, 188, 191, 0.03);
}

.upload-icon {
  width: 40px;
  height: 40px;
  color: #94a3b8;
}

.upload-text {
  font-size: 15px;
  color: #475569;
  margin: 0;
}

.upload-link {
  color: #21b978;
  font-weight: 600;
}

.upload-hint {
  font-size: 13px;
  color: #94a3b8;
  margin: 0;
}

.file-list {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #f4faf9;
  border-radius: 8px;
  font-size: 14px;
}

.file-name {
  flex: 1;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  color: #94a3b8;
  font-size: 13px;
}

.file-remove {
  background: none;
  border: none;
  color: #ef4444;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

/* 瀵硅瘽 */
.chat-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.chat-panel-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  box-sizing: border-box;
  overflow: hidden;
}

.collect-panel-card {
  flex: 1;
  min-height: 0;
  box-sizing: border-box;
  overflow-y: auto;
}

.collect-panel-card.scale-form-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.scale-form-card .chat-panel-head {
  flex: 0 0 auto;
  margin-bottom: 14px;
}

.scale-form-card .scale-list {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 14px 4px 0;
  margin-right: -6px;
  scrollbar-width: thin;
  scrollbar-color: rgba(16, 185, 129, 0.45) rgba(232, 240, 238, 0.85);
}

.scale-form-card .scale-list::-webkit-scrollbar {
  width: 8px;
}

.scale-form-card .scale-list::-webkit-scrollbar-track {
  border-radius: 999px;
  background: rgba(232, 240, 238, 0.85);
}

.scale-form-card .scale-list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: linear-gradient(180deg, #20c997, #10b981);
}

.scale-form-card .form-submit {
  flex: 0 0 auto;
  align-self: center;
  margin-top: 16px;
}

.chat-panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  margin-bottom: 16px;
}

.chat-eyebrow {
  margin: 0 0 8px;
  color: #0f8f64;
  font-size: 13px;
  font-weight: 800;
}

.chat-back-btn {
  border: 1px solid #bdebd6;
  background: #ecfff5;
  color: #117a51;
  border-radius: 8px;
  padding: 9px 16px;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
}

.chat-back-btn:hover {
  border-color: #21b978;
  background: #dffff0;
}

.chat-messages {
  flex: 1;
  max-height: none;
  min-height: 360px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-bubble {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.6;
}

.chat-bubble.bot {
  background: #f1f5f9;
  color: #475569;
  align-self: flex-start;
  border-bottom-left-radius: 4px;
}

.chat-bubble.user {
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  align-self: flex-end;
  border-bottom-right-radius: 4px;
}

.chat-input-row {
  display: flex;
  gap: 10px;
}

.chat-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.chat-input:focus {
  border-color: #21b978;
}

.chat-input:disabled {
  background: #f4faf9;
  color: #94a3b8;
  cursor: not-allowed;
}

.chat-send {
  width: 44px;
  height: 44px;
  border: none;
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s;
  flex-shrink: 0;
}

.chat-send:hover:not(:disabled) {
  transform: scale(1.05);
}

.chat-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

/* 閲嶆柊寮€濮嬪璇濇寜閽?*/
.chat-reset-row {
  display: flex;
  justify-content: center;
  padding: 4px 0;
}

.chat-reset-btn {
  background: none;
  border: 1px solid #e2e8f0;
  color: #94a3b8;
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.chat-reset-btn:hover {
  border-color: #21b978;
  color: #21b978;
}

/* 鎵撳瓧鍔ㄧ敾 */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 14px 18px;
}

/* 鐢熸垚鐢诲儚鎸夐挳鍖哄煙 */
.generate-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
}

.generate-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 36px;
  border: none;
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  font-size: 16px;
  font-weight: 600;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 16px rgba(31, 188, 191, 0.35);
}

.generate-btn.compact {
  flex-shrink: 0;
  min-height: 42px;
  padding: 0 20px;
  border-radius: 10px;
  font-size: 14px;
}

.generate-btn:hover:not(.disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(31, 188, 191, 0.45);
}

.generate-btn.disabled {
  background: #cbd5e1;
  cursor: not-allowed;
  box-shadow: none;
}

.generate-hint {
  font-size: 13px;
  color: #94a3b8;
  margin: 0;
}

/* 鍘嗗彶鎶ュ憡鍒楄〃 */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.history-list-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.history-list-head p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 13px;
}

.history-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 12px;
  padding: 20px 24px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 16px;
}

.history-item:hover {
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.1);
  transform: translateY(-2px);
}

.history-item.active {
  border: 1px solid rgba(16, 185, 129, 0.42);
  box-shadow: 0 4px 18px rgba(16, 185, 129, 0.12);
}

.history-item-time {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1f3f3b;
  min-width: 160px;
}

.history-item-time > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.history-item-time strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item-time span {
  color: #64748b;
  font-size: 12px;
  font-weight: 500;
}

.history-item-summary {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.history-badge {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 6px;
  font-weight: 500;
}

.history-badge.done {
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
}

.history-badge.pending {
  background: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
}

.history-badge.current {
  background: #059669;
  color: #fff;
}

.history-badge.version {
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
}

.history-parent {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #64748b;
  font-size: 12px;
}

.history-item-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.history-item-actions button {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(15, 118, 110, 0.16);
  border-radius: 6px;
  background: #fff;
  color: #0f766e;
  cursor: pointer;
}

.history-item-actions button:hover:not(:disabled) {
  background: rgba(16, 185, 129, 0.08);
  border-color: rgba(16, 185, 129, 0.38);
}

.history-item-actions button:disabled,
.profile-action-btn:disabled,
.reset-btn:disabled {
  cursor: wait;
  opacity: 0.55;
}

.current-profile-chip,
.profile-action-btn {
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: 6px;
  padding: 0 12px;
  font-weight: 500;
  white-space: nowrap;
}

.current-profile-chip {
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
}

.profile-action-btn {
  border: 1px solid rgba(15, 118, 110, 0.18);
  background: #fff;
  color: #0f766e;
  cursor: pointer;
}

.profile-action-btn:hover:not(:disabled) {
  background: rgba(16, 185, 129, 0.08);
}

@media (max-width: 820px) {
  .history-list-head,
  .history-item {
    align-items: stretch;
    flex-direction: column;
  }

  .history-item-time {
    min-width: 0;
  }

  .history-item-actions {
    justify-content: flex-end;
  }

  .report-actions {
    flex-wrap: wrap;
  }
}

.typing-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
  animation: typingBounce 1.4s infinite ease-in-out;
}

.typing-indicator .dot:nth-child(1) { animation-delay: 0s; }
.typing-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* 鎻愪氦鎸夐挳 */
.form-submit {
  margin-top: 24px;
  padding: 12px 32px;
  border: none;
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  font-size: 15px;
  font-weight: 600;
  border-radius: 10px;
  cursor: pointer;
  transition: transform 0.15s;
}

.form-submit:hover {
  transform: translateY(-1px);
}

.form-submit:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
}

/* AI鍒嗘瀽缁撴灉 */
.ai-analysis-section {
  background: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 14px;
  padding: 28px 32px;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05);
  animation: fadeIn 0.3s ease;
}

.ai-score-row {
  display: flex;
  align-items: center;
  gap: 32px;
  margin-bottom: 24px;
}

.ai-score-circle {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: linear-gradient(135deg, #21b978, #117a51);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 16px rgba(31, 188, 191, 0.3);
}

.ai-score-num {
  font-size: 28px;
  font-weight: 700;
  color: var(--surface, rgba(255, 255, 255, 0.94));
  line-height: 1;
}

.ai-score-label {
  font-size: 11px;
  color: rgba(255,255,255,0.85);
  margin-top: 4px;
}

.ai-style-tag {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.style-label {
  font-size: 13px;
  color: #94a3b8;
}

.style-value {
  font-size: 18px;
  font-weight: 600;
  color: #117a51;
}

.ai-compare-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.ai-compare-card {
  padding: 20px;
  border-radius: 12px;
}

.ai-compare-card.strengths {
  background: rgba(16, 185, 129, 0.06);
  border: 1px solid rgba(16, 185, 129, 0.15);
}

.ai-compare-card.weaknesses {
  background: rgba(245, 158, 11, 0.06);
  border: 1px solid rgba(245, 158, 11, 0.15);
}

.compare-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px;
}

.strengths .compare-title { color: #059669; }
.weaknesses .compare-title { color: #d97706; }

.compare-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  font-size: 13px;
  padding: 6px 14px;
  border-radius: 20px;
  font-weight: 500;
}

.strength-tag {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
}

.weakness-tag {
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
}

.ai-recommendations {
  background: #f4faf9;
  border-radius: 12px;
  padding: 20px 24px;
}

.rec-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f3f3b;
  margin: 0 0 16px;
}

.rec-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rec-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.rec-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: linear-gradient(135deg, #21b978, #117a51);
  color: var(--surface, rgba(255, 255, 255, 0.94));
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

.rec-text {
  font-size: 14px;
  color: #475569;
  line-height: 1.6;
}

/* 鍔犺浇鎸夐挳 spinner */
.btn-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: var(--surface, rgba(255, 255, 255, 0.94));
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Learning profile visual refresh */
.lp-page {
  height: calc(100vh - 72px);
  min-height: calc(100vh - 72px);
  background: #f7fbfa;
  overflow: hidden !important;
}

.lp-sidebar {
  width: 240px;
  min-width: 240px;
  height: calc(100vh - 72px);
  padding: 24px 28px;
  box-sizing: border-box;
  background: #f3fbf7;
  border-right: 1px solid #e8f0ee;
  overflow: hidden;
}

.sidebar-nav {
  gap: 0;
  padding: 0;
}

.sidebar-digital-human-stage {
  position: relative;
  width: 100%;
  min-height: 220px;
  flex: 1 1 auto;
  margin-top: 12px;
  overflow: hidden;
  contain: layout paint;
}

.nav-item {
  height: 56px;
  margin-bottom: 12px;
  padding: 0 16px;
  border-radius: 14px;
  color: #48615e;
  font-size: 15px;
  font-weight: 600;
}

.nav-item:hover {
  background: rgba(221, 247, 234, 0.55);
  color: #0e9f6e;
}

.nav-item.active {
  background: linear-gradient(90deg, #ddf7ea, #effbf6);
  color: #0e9f6e;
  font-weight: 600;
}

.nav-icon {
  width: 24px;
  color: currentColor;
}

.sidebar-deco {
  position: absolute;
  left: 28px;
  bottom: 28px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  color: #9aaeaa;
  text-align: left;
}

.book-stack {
  position: relative;
  z-index: 1;
  width: 138px;
  height: auto;
  display: block;
  object-fit: contain;
  filter: drop-shadow(0 14px 24px rgba(31, 72, 66, 0.1));
}

.plant-orb {
  position: absolute;
  top: 8px;
  right: 36px;
  width: 58px;
  height: 58px;
  border-radius: 50%;
  background: rgba(19, 166, 111, 0.14);
  filter: blur(2px);
}

.sidebar-deco p {
  margin: 0;
  font-size: 13px;
  color: #9aaeaa;
}

.lp-content {
  height: calc(100vh - 72px);
  padding: 24px;
  box-sizing: border-box;
  overflow-y: auto !important;
  background: #f7fbfa;
}

.content-panel {
  min-height: 100%;
}

.assess-panel {
  height: auto;
  min-height: 100%;
  overflow: visible !important;
}

.assess-layout {
  display: flex;
  grid-template-columns: none;
  gap: 24px;
  align-items: stretch;
  height: auto;
  min-height: 640px;
  overflow: visible;
}

.digital-human-stage,
.progress-section,
.collect-item {
  border-radius: 24px;
  box-shadow: 0 12px 40px rgba(31, 72, 66, 0.08);
}

.digital-human-stage {
  position: relative;
  flex: 0 1 60%;
  min-width: 620px;
  height: calc(100vh - 120px);
  min-height: 640px;
  padding: 32px;
  box-sizing: border-box;
  border: 0;
  background:
    url("/shuzirenbg.png") center bottom / cover no-repeat,
    radial-gradient(circle at 76% 25%, rgba(214, 246, 232, 0.84), transparent 28%),
    radial-gradient(circle at 18% 62%, rgba(224, 245, 235, 0.72), transparent 26%),
    linear-gradient(180deg, #ffffff 0%, #fbfefd 100%);
  overflow: hidden;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.stage-copy {
  position: absolute;
  z-index: 4;
  top: 32px;
  left: 32px;
  right: 24px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.stage-copy h1 {
  margin: 0 0 12px;
  color: #1f3433;
  font-size: 30px;
  line-height: 1.15;
  font-weight: 700;
  letter-spacing: 0;
}

.stage-copy p {
  margin: 0;
  color: #38514e;
  font-size: 17px;
  line-height: 1.5;
}

.stage-status {
  height: 40px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  border: 1px solid #e5f1ee;
  border-radius: 20px;
  background: #ffffff;
  color: #269f70;
  box-shadow: 0 8px 22px rgba(31, 72, 66, 0.08);
  font-size: 14px;
  font-weight: 700;
  white-space: nowrap;
}

.stage-glow {
  position: absolute;
  z-index: 1;
  border-radius: 50%;
  pointer-events: none;
}

.glow-a {
  width: 320px;
  height: 320px;
  right: 18px;
  bottom: 68px;
  background: rgba(177, 231, 205, 0.4);
  filter: blur(38px);
}

.glow-b {
  width: 220px;
  height: 220px;
  left: 52px;
  bottom: 210px;
  background: rgba(197, 226, 213, 0.48);
  filter: blur(24px);
}

.glow-c {
  width: 150px;
  height: 150px;
  right: 210px;
  top: 150px;
  background: rgba(231, 248, 240, 0.9);
  filter: blur(16px);
}

.stage-circuit-bg,
.stage-orb-deco {
  display: none;
}

.digital-human-stage :deep(.avatar-panel) {
  position: absolute;
  left: 56%;
  bottom: 28px;
  z-index: 2;
  width: 760px;
  max-width: min(760px, calc(100% - 40px));
  height: min(700px, calc(100% - 96px));
  min-height: 0;
  transform: translateX(-50%);
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  overflow: hidden;
}

.digital-human-stage :deep(.avatar-stage) {
  inset: 0;
  width: 100%;
  height: 100%;
  background: transparent !important;
  overflow: hidden;
}

.digital-human-stage :deep(> .avatar-panel > .avatar-stage > #xvideo),
.digital-human-stage :deep(> .avatar-panel > .avatar-stage > [id*="xvideo"]),
.digital-human-stage :deep(> .avatar-panel > .avatar-stage > iframe) {
  display: block !important;
  width: 100% !important;
  height: 100% !important;
  max-width: 100% !important;
  max-height: 100% !important;
  background: transparent !important;
  border: 0 !important;
  overflow: hidden !important;
}

.digital-human-stage :deep(> .avatar-panel > .avatar-stage > iframe) {
  background: #ffffff !important;
}

.digital-human-stage :deep(.avatar-status) {
  display: none;
}

.assistant-tip {
  position: absolute;
  z-index: 3;
  left: 32px;
  bottom: 170px;
  width: 280px;
  height: 96px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 7px;
  padding: 0 20px;
  box-sizing: border-box;
  border: 1px solid rgba(255, 255, 255, 0.75);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
  color: #38514e;
  backdrop-filter: blur(16px);
  box-shadow: 0 16px 38px rgba(31, 72, 66, 0.1);
}

.assistant-tip strong {
  color: #1f3433;
  font-size: 15px;
  font-weight: 700;
}

.assistant-tip span {
  font-size: 14px;
  line-height: 1.08;
}

.right-panel {
  flex: 0 1 40%;
  min-width: 480px;
  height: auto;
  gap: 18px;
  overflow: visible;
}

.progress-section {
  height: 300px;
  padding: 28px 32px 26px;
  box-sizing: border-box;
  background: #ffffff;
  display: flex;
  flex-direction: column;
}

.progress-title {
  display: block;
  margin: 0;
  color: #213a39;
  font-size: 18px;
  font-weight: 700;
}

.progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.progress-generate-btn {
  height: 40px;
  min-width: 112px;
  padding: 0 18px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(135deg, #20c997 0%, #0e9f6e 100%);
  color: #ffffff;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(16, 166, 111, 0.22);
  transition: transform 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
  white-space: nowrap;
}

.progress-generate-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 16px 30px rgba(16, 166, 111, 0.28);
}

.progress-generate-btn:disabled {
  cursor: not-allowed;
  opacity: 0.52;
  box-shadow: none;
}

.progress-body {
  display: flex;
  align-items: center;
  gap: 44px;
}

.progress-ring {
  --progress: 0%;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: conic-gradient(#13a66f var(--progress), #edf2f2 0);
  display: grid;
  place-items: center;
  flex: 0 0 auto;
}

.progress-ring::before {
  content: "";
  width: 94px;
  height: 94px;
  grid-area: 1 / 1;
  border-radius: 50%;
  background: #ffffff;
}

.progress-ring span {
  position: relative;
  z-index: 1;
  grid-area: 1 / 1;
  color: #213a39;
  font-size: 28px;
  font-weight: 700;
}

.progress-summary strong {
  display: block;
  margin-bottom: 14px;
  color: #10a66f;
  font-size: 24px;
  font-weight: 800;
}

.progress-summary p {
  margin: 0;
  color: #617875;
  font-size: 15px;
  line-height: 1.55;
}

.progress-steps {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-top: auto;
  padding: 0 10px;
}

.progress-steps::before {
  content: "";
  position: absolute;
  left: 88px;
  right: 88px;
  top: 18px;
  height: 2px;
  background: #e6eceb;
}

.progress-step {
  position: relative;
  z-index: 1;
  min-width: 92px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #48615e;
}

.step-icon {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #ddf7ea;
  color: #13a66f;
}

.step-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  line-height: 1.1;
}

.step-text strong {
  color: #48615e;
  font-weight: 700;
}

.step-text em {
  color: #7d908c;
  font-style: normal;
}

.collect-list {
  gap: 18px;
  justify-content: flex-start;
  flex: none;
}

.collect-item {
  min-height: 104px;
  height: 104px;
  margin-top: 0;
  padding: 22px 24px;
  border: 0;
  border-radius: 24px;
  background: linear-gradient(90deg, #ecfff4, #f7fffb);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  box-shadow: 0 12px 40px rgba(31, 72, 66, 0.08);
}

.collect-upload {
  background: linear-gradient(90deg, #eef6ff, #f8fbff);
}

.collect-chat {
  background: linear-gradient(90deg, #f5f0ff, #fbf9ff);
}

.collect-item:hover {
  border-color: transparent;
  box-shadow: 0 18px 38px rgba(31, 72, 66, 0.12);
  transform: translateY(-2px);
}

.collect-item.done {
  border-color: transparent;
}

.collect-icon {
  width: 48px;
  height: 48px;
  flex: 0 0 48px;
  border-radius: 14px;
  background: color-mix(in srgb, var(--card-color) 15%, transparent);
  color: var(--card-color);
  box-shadow: none;
}

.collect-copy {
  gap: 7px;
}

.collect-title {
  color: #213a39;
  font-size: 18px;
  font-weight: 700;
}

.collect-title-row {
  gap: 10px;
}

.collect-state {
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--card-soft);
  color: var(--card-color);
  font-size: 12px;
  font-weight: 700;
}

.collect-desc {
  color: #667a77;
  font-size: 14px;
  line-height: 1.35;
}

.collect-action {
  width: 76px;
  height: 40px;
  min-width: 76px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(135deg, var(--card-color), color-mix(in srgb, var(--card-color) 82%, #083f2d));
  color: #ffffff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 22px color-mix(in srgb, var(--card-color) 28%, transparent);
  font-size: 14px;
  font-weight: 600;
}

@media (max-width: 1200px) {
  .assess-layout {
    flex-direction: column;
  }

  .digital-human-stage,
  .right-panel {
    width: 100%;
    min-width: 0;
    flex-basis: auto;
  }

  .right-panel {
    min-width: 0;
  }
}

@media (max-width: 768px) {
  .lp-page {
    flex-direction: column;
    overflow-y: auto !important;
  }

  .lp-sidebar {
    width: 100%;
    min-width: 0;
    height: auto;
    padding: 12px 16px;
    overflow-x: auto;
  }

  .sidebar-nav {
    flex-direction: row;
    gap: 10px;
  }

  .nav-item {
    min-width: 128px;
    margin-bottom: 0;
  }

  .sidebar-deco {
    display: none;
  }

  .sidebar-digital-human-stage {
    display: none;
  }

  .lp-content {
    height: auto;
    padding: 16px;
  }

  .digital-human-stage {
    min-height: 640px;
    padding: 24px;
  }

  .stage-copy {
    left: 24px;
    right: 24px;
    flex-direction: column;
  }

  .digital-human-stage :deep(.avatar-panel) {
    width: min(520px, calc(100% - 32px));
    height: min(520px, calc(100% - 120px));
    min-height: 360px;
  }

  .assistant-tip {
    left: 24px;
    bottom: 70px;
    width: min(280px, calc(100% - 48px));
  }

  .progress-section {
    height: auto;
  }

  .progress-body,
  .collect-item {
    gap: 16px;
  }

  .progress-body {
    flex-wrap: wrap;
  }

  .progress-steps::before {
    display: none;
  }

  .collect-item {
    height: auto;
    min-height: 116px;
    align-items: flex-start;
  }
}
</style>

<style>
.lp-page {
  display: flex !important;
  grid-template-columns: none !important;
  height: calc(100vh - 72px) !important;
  min-height: calc(100vh - 72px) !important;
  max-height: calc(100vh - 72px) !important;
  background: #f7fbfa !important;
  border-top: 0 !important;
}

.lp-page .lp-sidebar {
  width: 240px !important;
  min-width: 240px !important;
  max-width: 240px !important;
  height: calc(100vh - 72px) !important;
  min-height: calc(100vh - 72px) !important;
  padding: 24px 28px !important;
  border-right: 1px solid #e8f0ee !important;
  background: #f3fbf7 !important;
}

.lp-page .lp-content {
  height: calc(100vh - 72px) !important;
  padding: 24px !important;
  background: #f7fbfa !important;
}

.lp-page .nav-item,
.lp-page .nav-item:hover {
  border: 0 !important;
  box-shadow: none !important;
}

.lp-page .nav-item {
  border-radius: 14px !important;
  background: transparent !important;
  color: #48615e !important;
}

.lp-page .nav-item.active,
.lp-page .nav-item.active:hover {
  background: linear-gradient(90deg, #ddf7ea, #effbf6) !important;
  color: #0e9f6e !important;
}

.lp-page .collect-item,
.lp-page .collect-item:hover {
  border: 0 !important;
  border-radius: 24px !important;
  box-shadow: 0 12px 40px rgba(31, 72, 66, 0.08) !important;
  color: inherit !important;
}

.lp-page .collect-item:hover {
  box-shadow: 0 18px 38px rgba(31, 72, 66, 0.12) !important;
}

.lp-page .collect-scale,
.lp-page .collect-scale:hover {
  background: linear-gradient(90deg, #ecfff4, #f7fffb) !important;
}

.lp-page .collect-upload,
.lp-page .collect-upload:hover {
  background: linear-gradient(90deg, #eef6ff, #f8fbff) !important;
}

.lp-page .collect-chat,
.lp-page .collect-chat:hover {
  background: linear-gradient(90deg, #f5f0ff, #fbf9ff) !important;
}

.lp-page .assess-panel:has(.scale-form-card) {
  height: 100% !important;
  min-height: 0 !important;
  overflow: hidden !important;
}

.lp-page .assess-layout:has(.scale-form-card) {
  height: 100% !important;
  min-height: 0 !important;
  overflow: hidden !important;
  align-items: stretch !important;
}

.lp-page .right-panel:has(.scale-form-card) {
  height: 100% !important;
  min-height: 0 !important;
  overflow: hidden !important;
}

.lp-page .scale-form-card {
  height: calc(100vh - 120px) !important;
  max-height: calc(100vh - 120px) !important;
  min-height: 0 !important;
  overflow: hidden !important;
}

.lp-page .scale-form-card .scale-list {
  flex: 1 1 auto !important;
  min-height: 0 !important;
  overflow-y: auto !important;
  overscroll-behavior: contain !important;
}

.lp-page .scale-form-card .form-submit {
  flex: 0 0 auto !important;
}

@media (max-width: 768px) and (orientation: portrait) {
  .lp-page.lp-page {
    flex-direction: column !important;
    width: 100% !important;
    height: auto !important;
    min-height: calc(100vh - 88px) !important;
    max-height: none !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
  }

  .lp-page.lp-page > .lp-sidebar.lp-sidebar {
    width: 100% !important;
    min-width: 0 !important;
    max-width: none !important;
    height: auto !important;
    min-height: 0 !important;
    padding: 12px 16px 8px !important;
    border-right: 0 !important;
    border-bottom: 1px solid #e8f0ee !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
  }

  .lp-page.lp-page .sidebar-nav.sidebar-nav {
    display: flex !important;
    flex-direction: row !important;
    gap: 10px !important;
    min-width: max-content !important;
    padding: 0 !important;
  }

  .lp-page.lp-page .nav-item.nav-item {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 112px !important;
    height: 48px !important;
    margin-bottom: 0 !important;
    padding: 0 14px !important;
    justify-content: center !important;
    font-size: 14px !important;
  }

  .lp-page.lp-page .sidebar-deco.sidebar-deco {
    display: none !important;
  }

  .lp-page.lp-page > .lp-content.lp-content {
    width: 100% !important;
    height: auto !important;
    min-height: 0 !important;
    padding: 14px 14px calc(120px + env(safe-area-inset-bottom)) !important;
    overflow: visible !important;
    box-sizing: border-box !important;
  }

  .lp-page.lp-page .assess-layout.assess-layout,
  .lp-page.lp-page .empty-report-grid.empty-report-grid,
  .lp-page.lp-page .report-grid.report-grid,
  .lp-page.lp-page .report-bottom-grid.report-bottom-grid {
    display: flex !important;
    flex-direction: column !important;
    grid-template-columns: none !important;
    width: 100% !important;
    min-height: 0 !important;
  }

  .lp-page.lp-page .digital-human-stage.digital-human-stage,
  .lp-page.lp-page .right-panel.right-panel,
  .lp-page.lp-page .empty-report-card.empty-report-card,
  .lp-page.lp-page .report-card.report-card {
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
  }

  .lp-page.lp-page .digital-human-stage.digital-human-stage {
    height: 560px !important;
    min-height: 560px !important;
    padding: 24px !important;
  }

  .lp-page.lp-page .right-panel.right-panel {
    min-height: 0 !important;
  }

  .lp-page.lp-page .empty-main-card.empty-main-card {
    min-height: 520px !important;
    padding: 28px 20px 24px !important;
  }

  .lp-page.lp-page .empty-side-stack.empty-side-stack,
  .lp-page.lp-page .agent-status-card.agent-status-card,
  .lp-page.lp-page .agent-preview-card.agent-preview-card {
    width: 100% !important;
    min-width: 0 !important;
  }

  .lp-page.lp-page .scale-form-card.scale-form-card {
    height: min(680px, calc(100vh - 180px)) !important;
    max-height: min(680px, calc(100vh - 180px)) !important;
  }

  .lp-page.lp-page .collect-list,
  .lp-page.lp-page .report-empty-dashboard,
  .lp-page.lp-page .content-panel {
    padding-bottom: calc(104px + env(safe-area-inset-bottom)) !important;
    box-sizing: border-box !important;
  }

  .lp-page.lp-page .collect-item {
    scroll-margin-bottom: calc(104px + env(safe-area-inset-bottom)) !important;
  }
}

/* Assessment portrait redesign */
.lp-page.lp-page .content-panel.assess-panel {
  padding: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.lp-page.lp-page .assess-layout.assess-redesign {
  display: grid !important;
  grid-template-columns: minmax(520px, 1fr) clamp(460px, 35vw, 640px) !important;
  gap: 28px !important;
  align-items: stretch !important;
  width: 100% !important;
  height: calc(100vh - 132px) !important;
  min-height: 620px !important;
  max-height: 760px !important;
}

.lp-page.lp-page .assessment-chat-shell {
  position: relative;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  padding: 30px 34px 24px;
  border: 1px solid rgba(226, 232, 240, 0.88);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.94) !important;
  box-shadow: 0 20px 52px rgba(15, 23, 42, 0.055);
}

.lp-page.lp-page .assessment-chat-shell::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.78), rgba(247, 253, 251, 0.52)) !important;
  pointer-events: none;
}

.lp-page.lp-page .chat-avatar-background {
  position: fixed;
  z-index: 1200;
  left: 34px;
  top: auto;
  bottom: 34px;
  width: 190px;
  height: clamp(270px, calc(100vh - 360px), 350px);
  overflow: hidden;
  opacity: 1;
  filter: saturate(0.82) contrast(0.98) brightness(1.04);
  pointer-events: none;
}

.lp-page.lp-page .chat-avatar-background::before {
  content: none;
  display: none;
}

.lp-page.lp-page .chat-avatar-background .learning-avatar,
.lp-page.lp-page .chat-avatar-background .avatar-panel,
.lp-page.lp-page .chat-avatar-background .avatar-stage {
  position: relative;
  z-index: 1;
  width: 100% !important;
  height: 100% !important;
  max-width: none !important;
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}

.lp-page.lp-page .chat-avatar-background canvas,
.lp-page.lp-page .chat-avatar-background video {
  object-fit: contain !important;
  object-position: center bottom !important;
}

.lp-page.lp-page .chat-avatar-background .avatar-placeholder,
.lp-page.lp-page .chat-avatar-background .avatar-error {
  display: none;
}

.lp-page.lp-page .chat-avatar-background .avatar-error {
  left: 8px;
  right: 8px;
  bottom: 58px;
  z-index: 5;
  display: block;
  padding: 8px 9px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.45;
  text-align: center;
  color: #9f1239;
  background: rgba(255, 241, 242, 0.9);
  border-color: rgba(244, 63, 94, 0.26);
  backdrop-filter: blur(10px);
}

.lp-page.lp-page .chat-avatar-background .avatar-status {
  top: auto;
  left: 50%;
  bottom: 14px;
  transform: translateX(-50%);
  z-index: 4;
  display: block;
  white-space: nowrap;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(12px);
}

.lp-page.lp-page .chat-avatar-background .resume-button {
  top: auto;
  right: auto;
  left: 50%;
  bottom: 50px;
  z-index: 5;
  display: block;
  transform: translateX(-50%);
  pointer-events: auto;
  white-space: nowrap;
  box-shadow: 0 12px 24px rgba(15, 118, 110, 0.18);
}

.lp-page.lp-page .chat-avatar-background .avatar-stage {
  transform: scale(0.96) translateY(0);
  transform-origin: center bottom;
}

.lp-page.lp-page .chat-avatar-background::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 2;
  background: transparent !important;
  pointer-events: none;
}

.lp-page.lp-page .chat-hero-head,
.lp-page.lp-page .portrait-chat-area {
  position: relative;
  z-index: 3;
}

.lp-page.lp-page .chat-hero-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  margin-bottom: 14px;
}

.lp-page.lp-page .chat-hero-head h2 {
  margin: 5px 0 10px;
  color: #1f2937;
  font-size: clamp(30px, 2.35vw, 38px);
  line-height: 1.1;
  letter-spacing: 0;
  white-space: nowrap;
}

.lp-page.lp-page .chat-hero-head p {
  margin: 0;
  color: #64748b;
  font-size: 15px;
  line-height: 1.7;
}


.lp-page.lp-page .stage-status.compact {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  flex: 0 0 auto;
  padding: 11px 18px;
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  color: #0f766e;
  font-size: 13px;
  font-weight: 700;
  backdrop-filter: blur(16px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.045);
}

.lp-page.lp-page .stage-status.compact svg {
  display: none;
}

.lp-page.lp-page .stage-status.compact::before {
  content: "";
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #12b69a;
  box-shadow: 0 0 0 4px rgba(20, 184, 166, 0.1);
}

.lp-page.lp-page .portrait-chat-area.chat-area {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  flex-direction: column;
  gap: 12px;
  padding: 0;
  background: transparent;
}

.lp-page.lp-page .portrait-chat-messages.chat-messages {
  flex: 1 1 auto;
  min-height: 0;
  max-height: none;
  padding: 4px 10px 6px 0;
  overflow-y: auto;
  scrollbar-width: none;
}

.lp-page.lp-page .portrait-chat-messages.chat-messages::-webkit-scrollbar {
  display: none;
}

.lp-page.lp-page .chat-message-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
  width: 100%;
}

.lp-page.lp-page .chat-message-row.bot {
  justify-content: flex-start;
}

.lp-page.lp-page .chat-message-row.user {
  justify-content: flex-end;
}

.lp-page.lp-page .chat-message-row.user .message-avatar {
  order: 2;
}

.lp-page.lp-page .message-avatar {
  display: grid;
  place-items: center;
  flex: 0 0 30px;
  width: 30px;
  height: 30px;
  overflow: hidden;
  border-radius: 50%;
  background: transparent;
  color: #21b978;
  box-shadow: none;
}

.lp-page.lp-page .message-avatar.bot {
  flex-basis: 30px;
  width: 30px;
  height: 30px;
  background: transparent;
}

.lp-page.lp-page .message-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.lp-page.lp-page .portrait-chat-messages .chat-bubble {
  display: flex;
  flex-direction: column;
  gap: 5px;
  max-width: min(500px, 80%);
  padding: 13px 18px 14px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 18px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(16px) saturate(1.18);
  -webkit-backdrop-filter: blur(16px) saturate(1.18);
  font-size: 13px;
  line-height: 1.56;
}

.lp-page.lp-page .portrait-chat-messages .chat-bubble small {
  color: #8a9aaf;
  font-size: 11px;
  line-height: 1;
}

.lp-page.lp-page .portrait-chat-messages .chat-bubble.bot {
  margin-right: auto;
  background: rgba(255, 255, 255, 0.9) !important;
  color: #263b38;
}

.lp-page.lp-page .portrait-chat-messages .chat-bubble.user {
  margin-left: auto;
  background: rgba(234, 251, 247, 0.92) !important;
  border-color: rgba(126, 226, 187, 0.48);
  color: #143c32;
}

.lp-page.lp-page .portrait-chat-area .chat-input-row {
  min-height: 62px;
  border: 1px solid rgba(203, 213, 225, 0.82);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.055);
  backdrop-filter: blur(18px);
}

.lp-page.lp-page .portrait-chat-area .chat-input {
  border: 0;
  background: transparent;
  box-shadow: none;
}

.lp-page.lp-page .portrait-chat-area .chat-send {
  width: 52px;
  height: 52px;
  margin-right: 4px;
  border-radius: 50%;
  background: linear-gradient(135deg, #14b8a6, #079579);
  box-shadow: 0 12px 24px rgba(20, 184, 166, 0.22);
}

.lp-page.lp-page .profile-portrait-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
  min-height: 0;
  overflow: visible;
  padding: 26px 28px 18px;
  border: 1px solid rgba(226, 232, 240, 0.88);
  border-radius: 26px;
  background: #ffffff;
  box-shadow: 0 20px 52px rgba(15, 23, 42, 0.055);
}

.lp-page.lp-page .portrait-panel-head,
.lp-page.lp-page .portrait-summary {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.lp-page.lp-page .portrait-panel-head h3 {
  margin: 6px 0 0;
  color: #1f2937;
  font-size: 22px;
  letter-spacing: 0;
}

.lp-page.lp-page .learn-more-btn {
  border: 1px solid rgba(33, 185, 120, 0.22);
  border-radius: 999px;
  background: #ffffff;
  color: #21b978;
  font-size: 13px;
  font-weight: 700;
  padding: 9px 14px;
  cursor: pointer;
}

.lp-page.lp-page .portrait-summary {
  margin-top: 14px;
  align-items: center;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(232, 239, 237, 0.86);
}

.lp-page.lp-page .portrait-score-ring {
  --score: 78%;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 0 0 96px;
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background:
    radial-gradient(circle, #ffffff 58%, transparent 59%),
    conic-gradient(#21b978 var(--score), #eaf1ef 0);
  color: #17324d;
}

.lp-page.lp-page .portrait-score-ring::after {
  content: "";
  position: absolute;
  inset: 8px;
  border: 1px dashed rgba(33, 185, 120, 0.28);
  border-radius: 50%;
}

.lp-page.lp-page .portrait-score-ring strong {
  margin: 2px 0 0;
  font-size: 24px;
  line-height: 1;
}

.lp-page.lp-page .portrait-score-ring em {
  margin-top: 7px;
  color: #5f6f85;
  font-size: 12px;
  font-style: normal;
}

.lp-page.lp-page .portrait-summary-copy {
  padding-top: 2px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.lp-page.lp-page .portrait-summary-copy span {
  color: #8390a3;
  font-size: 13px;
}

.lp-page.lp-page .portrait-summary-copy p {
  display: none;
}

.lp-page.lp-page .portrait-summary-copy button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  margin-top: 8px;
  padding: 0 16px;
  border: 1px solid rgba(33, 185, 120, 0.28);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  color: #21b978;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.lp-page.lp-page .portrait-summary-copy button::after {
  content: "→";
  margin-left: 8px;
  font-size: 14px;
}

.lp-page.lp-page .data-face-wrap {
  position: relative;
  display: block;
  gap: 10px;
  flex: 0 0 448px;
  width: 430px;
  min-height: 448px;
  margin: 0 0 4px;
  align-self: center;
}

.lp-page.lp-page .profile-face-stage {
  --face-ratio: 832 / 1078;
  position: absolute;
  z-index: 2;
  left: 50%;
  top: 44px;
  width: 218px;
  aspect-ratio: var(--face-ratio);
  overflow: visible;
  isolation: isolate;
  transform: translateX(-50%);
  filter: drop-shadow(0 18px 30px rgba(18, 156, 164, 0.08));
}

.lp-page.lp-page .profile-face-links {
  position: absolute;
  z-index: 1;
  inset: 0 0 auto 0;
  width: 100%;
  height: 430px;
  pointer-events: none;
  overflow: visible;
}

.lp-page.lp-page .face-link-line {
  fill: none;
  stroke: rgba(118, 138, 153, 0.22);
  stroke-width: 1;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: none;
  transition: stroke 0.75s ease, stroke-width 0.75s ease, opacity 0.75s ease;
  opacity: 0.76;
}

.lp-page.lp-page .face-link-line.done {
  stroke: rgba(20, 184, 166, 0.58);
  stroke-width: 1.35;
  opacity: 1;
}

.lp-page.lp-page .profile-face-base,
.lp-page.lp-page .profile-face-segment {
  position: absolute;
  display: block;
  pointer-events: none;
  user-select: none;
}

.lp-page.lp-page .profile-face-vector {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.lp-page.lp-page .profile-face-dots {
  fill: none;
  stroke: #0b9965;
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 0.1 7.2;
  filter: drop-shadow(0 0 5px rgba(11, 153, 101, 0.22));
  opacity: calc(0.58 + var(--portrait-progress) * 0.38);
}

.lp-page.lp-page .profile-face-base {
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  opacity: 0.46;
  filter: saturate(0.9) contrast(1.12);
  mix-blend-mode: multiply;
}

.lp-page.lp-page .profile-face-segment {
  transform-origin: center;
  object-fit: contain;
  animation: profileFaceAppear 0.58s ease-out both;
  animation-delay: var(--segment-delay, 0ms);
  mix-blend-mode: screen;
  transition:
    opacity 1.15s ease,
    filter 1.15s ease,
    transform 1.15s cubic-bezier(0.22, 1, 0.36, 1);
  z-index: 1;
}

.lp-page.lp-page .profile-face-segment.active {
  mix-blend-mode: normal;
  z-index: 2;
}

.lp-page.lp-page .face-dimension-tag {
  position: absolute;
  z-index: 3;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  align-items: center;
  width: var(--tag-width, 116px);
  min-height: 34px;
  padding: 4px 8px 4px 5px;
  border: 1px solid rgba(20, 184, 166, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  color: #6c7d8f;
  box-shadow: 0 8px 18px rgba(15, 118, 110, 0.035);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  cursor: default;
  transition:
    border-color 0.75s ease,
    background 0.75s ease,
    color 0.75s ease,
    box-shadow 0.75s ease,
    transform 0.75s ease;
}

.lp-page.lp-page .face-dimension-tag.right {
  transform: translateX(-100%);
  grid-template-columns: minmax(0, 1fr) 22px;
  padding: 4px 5px 4px 8px;
}

.lp-page.lp-page .face-dimension-tag.top,
.lp-page.lp-page .face-dimension-tag.bottom {
  transform: translateX(-50%);
}

.lp-page.lp-page .face-dimension-tag.bottom {
  width: var(--tag-width, 122px);
}

.lp-page.lp-page .face-dimension-tag span {
  display: grid;
  place-items: center;
  width: 19px;
  height: 19px;
  border-radius: 50%;
  background: rgba(20, 184, 166, 0.1);
  color: #6b8790;
  font-size: 9.5px;
  font-weight: 800;
  line-height: 1;
}

.lp-page.lp-page .face-dimension-tag.right span {
  grid-column: 2;
  grid-row: 1;
}

.lp-page.lp-page .face-dimension-tag b {
  min-width: 0;
  overflow: hidden;
  color: inherit;
  font-size: 10.5px;
  font-weight: 700;
  line-height: 1.12;
  overflow-wrap: anywhere;
}

.lp-page.lp-page .face-dimension-tag.done {
  border-color: rgba(20, 184, 166, 0.36);
  background: rgba(237, 253, 248, 0.9);
  color: #0f766e;
  box-shadow: 0 10px 24px rgba(20, 184, 166, 0.09);
}

.lp-page.lp-page .face-dimension-tag.done span {
  background: linear-gradient(135deg, #34d399, #0f9f6e);
  color: #ffffff;
}

.lp-page.lp-page .face-brief {
  position: absolute;
  left: 50%;
  bottom: 0;
  width: min(280px, 100%);
  margin: 0;
  color: #8a9aaf;
  font-size: 11px;
  line-height: 1.35;
  text-align: center;
  transform: translateX(-50%);
}

@keyframes profileFaceAppear {
  from {
    opacity: 0;
  }
  to {
    opacity: var(--target-opacity, 1);
  }
}

.lp-page.lp-page .ability-metrics {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 0 0 auto;
  min-height: 0;
  padding-top: 4px;
}

.lp-page.lp-page .ability-row {
  display: grid;
  grid-template-columns: 23px minmax(0, 1fr) auto;
  gap: 2px 9px;
  align-items: center;
  padding: 5px 0;
  border-bottom: 1px solid rgba(236, 242, 240, 0.88);
}

.lp-page.lp-page .ability-row:last-child {
  border-bottom: 0;
}

.lp-page.lp-page .metric-icon {
  display: grid;
  place-items: center;
  width: 23px;
  height: 23px;
  border-radius: 50%;
  background: #eefbf5;
  color: #21b978;
}

.lp-page.lp-page .metric-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0;
}

.lp-page.lp-page .metric-copy strong {
  color: #253449;
  font-size: 12px;
}

.lp-page.lp-page .metric-copy small {
  color: #8a9aaf;
  font-size: 10px;
  line-height: 1.2;
}

.lp-page.lp-page .metric-score {
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
}

.lp-page.lp-page .metric-bar {
  grid-column: 2 / 4;
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: #edf2f4;
}

.lp-page.lp-page .metric-bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #58d89c, #21b978);
}

.lp-page.lp-page .portrait-tags {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  margin-top: 8px;
  padding: 8px;
  border-radius: 16px;
  background: #f6f8fa;
}

.lp-page.lp-page .portrait-tags span {
  display: grid;
  min-height: 30px;
  place-items: center;
  border-radius: 12px;
  background: #ffffff;
  color: #718096;
  font-size: 12px;
  font-weight: 700;
}

.lp-page.lp-page .portrait-tags span:first-child {
  color: #21b978;
}

.lp-page.lp-page .portrait-dimension-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.lp-page.lp-page .dimension-chip {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 4px 9px;
  border: 1px solid rgba(148, 163, 184, 0.36);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #64748b;
  font-size: 12px;
  line-height: 1.2;
}

.lp-page.lp-page .dimension-chip.done {
  border-color: rgba(20, 184, 166, 0.36);
  background: rgba(20, 184, 166, 0.12);
  color: #0f766e;
}

.lp-page.lp-page.has-live-avatar .sidebar-deco {
  display: none !important;
}

.lp-page.lp-page.has-live-avatar .chat-avatar-background {
  z-index: 1200;
}

.lp-page.lp-page.has-live-avatar .chat-avatar-background .avatar-stage {
  transform: scale(0.96) translateY(0);
  transform-origin: center bottom;
}

.lp-page.lp-page.has-live-avatar .chat-avatar-background canvas,
.lp-page.lp-page.has-live-avatar .chat-avatar-background video {
  display: block !important;
  width: 100% !important;
  height: 100% !important;
  max-width: 100% !important;
  max-height: 100% !important;
  opacity: 1 !important;
}

.lp-page.lp-page.has-live-avatar .chat-avatar-background .avatar-stage.has-avatar-canvas video {
  position: absolute !important;
  width: 0 !important;
  height: 0 !important;
  max-width: 0 !important;
  max-height: 0 !important;
  opacity: 0 !important;
  pointer-events: none !important;
}

.lp-page.lp-page.has-live-avatar .message-avatar {
  isolation: isolate;
}

.lp-page.lp-page.has-live-avatar .message-avatar img {
  display: block;
  max-width: 100%;
  max-height: 100%;
  transform: none !important;
}

.lp-page.lp-page .assessment-modal-surface {
  position: fixed;
  z-index: 80;
  inset: 92px 32px 32px 260px;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(248, 251, 250, 0.68);
  backdrop-filter: blur(14px);
}

.lp-page.lp-page .assessment-modal-surface .collect-panel-card {
  width: min(760px, 100%);
  max-height: min(760px, calc(100vh - 164px));
  overflow: auto;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(228, 236, 234, 0.95);
  box-shadow: 0 24px 70px rgba(31, 41, 55, 0.16);
}

@media (max-width: 1400px) {
  .lp-page.lp-page .assess-layout.assess-redesign {
    grid-template-columns: minmax(500px, 1fr) 460px !important;
    gap: 18px !important;
  }

  .lp-page.lp-page .assessment-chat-shell {
    padding: 26px 30px 22px;
  }

  .lp-page.lp-page .profile-portrait-panel {
    padding: 24px 20px 18px;
  }
}

@media (max-width: 1180px) {
  .lp-page.lp-page .assess-layout.assess-redesign {
    grid-template-columns: 1fr !important;
  }

  .lp-page.lp-page .assessment-chat-shell,
  .lp-page.lp-page .profile-portrait-panel {
    min-height: 620px;
  }

  .lp-page.lp-page .assessment-modal-surface {
    inset: 88px 18px 24px 18px;
  }
}

@media (max-width: 768px) {
  .lp-page.lp-page .assessment-chat-shell,
  .lp-page.lp-page .profile-portrait-panel {
    padding: 22px 18px;
    border-radius: 20px;
  }

  .lp-page.lp-page .chat-hero-head,
  .lp-page.lp-page .portrait-summary,
  .lp-page.lp-page .portrait-panel-head {
    flex-direction: column;
  }

  .lp-page.lp-page .portrait-tags {
    grid-template-columns: 1fr;
  }

  .lp-page.lp-page .portrait-chat-messages .chat-bubble {
    max-width: 86%;
  }
}

/* Less-card assessment workspace */
.lp-page.lp-page .content-panel.assess-panel {
  min-height: calc(100vh - 92px) !important;
  padding: 0 !important;
  background:
    linear-gradient(90deg, rgba(236, 252, 248, 0.34), rgba(255, 255, 255, 0.72) 22%, rgba(255, 255, 255, 0.78) 70%, rgba(241, 250, 248, 0.5)) !important;
}

.lp-page.lp-page .assess-layout.assess-redesign {
  grid-template-columns: minmax(590px, 1fr) clamp(520px, 38vw, 660px) !important;
  gap: 0 !important;
  width: 100% !important;
  height: calc(100vh - 92px) !important;
  min-height: 680px !important;
  max-height: none !important;
  overflow: hidden !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.lp-page.lp-page .assessment-chat-shell,
.lp-page.lp-page .profile-portrait-panel {
  height: 100% !important;
  border: 0 !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  background: transparent !important;
}

.lp-page.lp-page .assessment-chat-shell {
  padding: 38px clamp(34px, 4vw, 64px) 28px !important;
}

.lp-page.lp-page .assessment-chat-shell::before {
  inset: 0 0 0 auto !important;
  width: 1px !important;
  background: linear-gradient(180deg, transparent, rgba(203, 213, 225, 0.72) 14%, rgba(203, 213, 225, 0.72) 86%, transparent) !important;
}

.lp-page.lp-page .profile-portrait-panel {
  position: relative !important;
  padding: 38px clamp(34px, 3.2vw, 56px) 24px !important;
  border-left: 1px solid rgba(203, 213, 225, 0.64) !important;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.58), rgba(248, 253, 252, 0.42)) !important;
}

.lp-page.lp-page .chat-hero-head {
  margin-bottom: 26px !important;
}

.lp-page.lp-page .chat-hero-head h2 {
  margin-top: 8px !important;
  font-size: clamp(34px, 2.5vw, 44px) !important;
  color: #172033 !important;
}

.lp-page.lp-page .chat-hero-head p {
  max-width: 640px !important;
  color: #667085 !important;
}

.lp-page.lp-page .chat-eyebrow {
  color: #059669 !important;
  font-weight: 800 !important;
}

.lp-page.lp-page .stage-status.compact {
  border-color: rgba(20, 184, 166, 0.18) !important;
  background: rgba(255, 255, 255, 0.58) !important;
  box-shadow: none !important;
}

.lp-page.lp-page .portrait-chat-area.chat-area {
  gap: 14px !important;
}

.lp-page.lp-page .portrait-chat-messages.chat-messages {
  padding: 0 16px 6px 0 !important;
}

.lp-page.lp-page .chat-message-row {
  margin-bottom: 24px !important;
}

.lp-page.lp-page .portrait-chat-messages .chat-bubble {
  max-width: min(560px, 78%) !important;
  border-color: rgba(203, 213, 225, 0.6) !important;
  border-radius: 18px !important;
  box-shadow: none !important;
}

.lp-page.lp-page .portrait-chat-messages .chat-bubble.bot {
  background: rgba(255, 255, 255, 0.66) !important;
}

.lp-page.lp-page .portrait-chat-messages .chat-bubble.user {
  background: rgba(228, 250, 244, 0.72) !important;
  border-color: rgba(45, 212, 191, 0.34) !important;
}

.lp-page.lp-page .message-avatar {
  box-shadow: none !important;
}

.lp-page.lp-page .portrait-chat-area .chat-input-row {
  min-height: 66px !important;
  border-color: rgba(203, 213, 225, 0.72) !important;
  border-radius: 999px !important;
  background: rgba(255, 255, 255, 0.72) !important;
  box-shadow: none !important;
}

.lp-page.lp-page .portrait-chat-area .chat-send {
  background: rgba(220, 252, 241, 0.96) !important;
  color: #059669 !important;
  border: 1px solid rgba(16, 185, 129, 0.18) !important;
  box-shadow: none !important;
}

.lp-page.lp-page .chat-reset-btn,
.lp-page.lp-page .learn-more-btn,
.lp-page.lp-page .portrait-summary-copy button {
  box-shadow: none !important;
}

.lp-page.lp-page .portrait-chat-area .chat-reset-row {
  position: relative !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  margin: 0 0 6px !important;
  min-height: 42px !important;
}

.lp-page.lp-page .portrait-chat-area .chat-reset-row::before,
.lp-page.lp-page .portrait-chat-area .chat-reset-row::after {
  content: "";
  display: block;
  width: clamp(42px, 9vw, 112px);
  height: 1px;
  background:
    radial-gradient(circle, rgba(20, 184, 166, 0.78) 0 3px, transparent 3.5px) center / 8px 8px no-repeat,
    linear-gradient(90deg, transparent, rgba(34, 211, 238, 0.36));
}

.lp-page.lp-page .portrait-chat-area .chat-reset-row::after {
  transform: scaleX(-1);
}

.lp-page.lp-page .portrait-chat-area .chat-reset-btn {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
  min-height: 36px !important;
  padding: 0 22px !important;
  border: 1px solid rgba(20, 184, 166, 0.32) !important;
  border-radius: 0 !important;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.82), rgba(236, 253, 245, 0.64)),
    repeating-linear-gradient(90deg, rgba(20, 184, 166, 0.08) 0 1px, transparent 1px 10px) !important;
  color: #05816f !important;
  clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px) !important;
  font-size: 14px !important;
  font-weight: 800 !important;
  letter-spacing: 0 !important;
  backdrop-filter: blur(14px) !important;
  -webkit-backdrop-filter: blur(14px) !important;
}

.lp-page.lp-page .portrait-chat-area .chat-reset-btn:hover {
  border-color: rgba(20, 184, 166, 0.58) !important;
  background:
    linear-gradient(135deg, rgba(236, 253, 245, 0.94), rgba(204, 251, 241, 0.72)),
    repeating-linear-gradient(90deg, rgba(20, 184, 166, 0.11) 0 1px, transparent 1px 10px) !important;
  transform: translateY(-1px) !important;
}

.lp-page.lp-page .portrait-chat-area .chat-input-row {
  position: relative !important;
  min-height: 64px !important;
  padding: 6px 7px 6px 54px !important;
  border: 1px solid rgba(34, 211, 238, 0.36) !important;
  border-radius: 26px !important;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(247, 253, 252, 0.68)),
    repeating-linear-gradient(90deg, rgba(34, 211, 238, 0.05) 0 1px, transparent 1px 14px) !important;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.78),
    0 0 0 1px rgba(15, 118, 110, 0.02) !important;
  overflow: hidden !important;
}

.lp-page.lp-page .portrait-chat-area .chat-input-row::before {
  content: "";
  position: absolute;
  left: 20px;
  top: 50%;
  width: 18px;
  height: 38px;
  border-left: 1px solid rgba(34, 211, 238, 0.42);
  border-top: 1px solid rgba(34, 211, 238, 0.26);
  border-bottom: 1px solid rgba(34, 211, 238, 0.26);
  clip-path: polygon(0 0, 100% 12px, 100% calc(100% - 12px), 0 100%);
  transform: translateY(-50%);
}

.lp-page.lp-page .portrait-chat-area .chat-input-row::after {
  content: "";
  position: absolute;
  left: 21px;
  top: 50%;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #12c7aa;
  box-shadow: 0 0 0 4px rgba(20, 184, 166, 0.12), 0 0 14px rgba(20, 184, 166, 0.38);
  transform: translateY(-50%);
}

.lp-page.lp-page .portrait-chat-area .chat-input {
  height: 100% !important;
  min-height: 50px !important;
  padding: 0 16px !important;
  color: #263446 !important;
  font-size: 15px !important;
}

.lp-page.lp-page .portrait-chat-area .chat-input::placeholder {
  color: #8b95a5 !important;
}

.lp-page.lp-page .portrait-chat-area .chat-send {
  position: relative !important;
  width: 64px !important;
  height: 52px !important;
  margin-right: 0 !important;
  border-radius: 0 !important;
  border-color: rgba(20, 184, 166, 0.38) !important;
  background: linear-gradient(135deg, #36e1c0, #10b981 56%, #0d9488) !important;
  color: #ffffff !important;
  clip-path: polygon(14px 0, 100% 0, 100% calc(100% - 14px), calc(100% - 14px) 100%, 0 100%, 0 14px) !important;
  box-shadow: 0 10px 22px rgba(20, 184, 166, 0.2) !important;
}

.lp-page.lp-page .portrait-chat-area .chat-send:hover:not(:disabled) {
  transform: translateY(-1px) !important;
  box-shadow: 0 14px 28px rgba(20, 184, 166, 0.26) !important;
}

.lp-page.lp-page .portrait-chat-area .chat-send:disabled {
  clip-path: polygon(14px 0, 100% 0, 100% calc(100% - 14px), calc(100% - 14px) 100%, 0 100%, 0 14px) !important;
}

/* Compact chat composer refinement */
.lp-page.lp-page .portrait-chat-area .chat-reset-row {
  min-height: 28px !important;
  margin: 0 0 4px !important;
}

.lp-page.lp-page .portrait-chat-area .chat-reset-row::before,
.lp-page.lp-page .portrait-chat-area .chat-reset-row::after {
  display: none !important;
}

.lp-page.lp-page .portrait-chat-area .chat-reset-btn {
  min-height: 28px !important;
  padding: 0 12px !important;
  gap: 6px !important;
  border: 0 !important;
  border-radius: 999px !important;
  background: rgba(236, 253, 245, 0.7) !important;
  color: #0f766e !important;
  clip-path: none !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  backdrop-filter: blur(10px) !important;
  -webkit-backdrop-filter: blur(10px) !important;
}

.lp-page.lp-page .portrait-chat-area .chat-reset-btn:hover {
  background: rgba(209, 250, 229, 0.86) !important;
  transform: none !important;
}

.lp-page.lp-page .portrait-chat-area .chat-input-row {
  min-height: 54px !important;
  padding: 5px 5px 5px 18px !important;
  border: 1px solid rgba(203, 213, 225, 0.72) !important;
  border-radius: 18px !important;
  background: rgba(255, 255, 255, 0.78) !important;
  box-shadow: none !important;
  overflow: visible !important;
}

.lp-page.lp-page .portrait-chat-area .chat-input-row::before,
.lp-page.lp-page .portrait-chat-area .chat-input-row::after {
  display: none !important;
}

.lp-page.lp-page .portrait-chat-area .chat-input {
  min-height: 42px !important;
  padding: 0 12px 0 0 !important;
  color: #273444 !important;
  font-size: 14px !important;
}

.lp-page.lp-page .portrait-chat-area .chat-input::placeholder {
  color: #98a2b3 !important;
}

.lp-page.lp-page .portrait-chat-area .chat-send {
  width: 44px !important;
  height: 44px !important;
  border: 0 !important;
  border-radius: 14px !important;
  background: #10b981 !important;
  color: #ffffff !important;
  clip-path: none !important;
  box-shadow: 0 8px 18px rgba(16, 185, 129, 0.18) !important;
}

.lp-page.lp-page .portrait-chat-area .chat-send:hover:not(:disabled) {
  transform: translateY(-1px) !important;
  background: #059669 !important;
  box-shadow: 0 10px 20px rgba(5, 150, 105, 0.2) !important;
}

.lp-page.lp-page .portrait-chat-area .chat-send:disabled {
  clip-path: none !important;
  opacity: 0.5 !important;
}

.lp-page.lp-page .portrait-panel-head {
  align-items: center !important;
}

.lp-page.lp-page .portrait-panel-head h3 {
  margin-top: 8px !important;
  font-size: 24px !important;
  color: #172033 !important;
}

.lp-page.lp-page .portrait-summary {
  margin-top: 18px !important;
  padding-bottom: 16px !important;
  border-bottom-color: rgba(203, 213, 225, 0.58) !important;
}

.lp-page.lp-page .portrait-score-ring {
  box-shadow: none !important;
}

.lp-page.lp-page .portrait-summary-copy p {
  display: none !important;
  max-width: 270px !important;
  margin: 8px 0 0 !important;
  color: #8290a3 !important;
}

.lp-page.lp-page .data-face-wrap {
  margin-top: 18px !important;
}

.lp-page.lp-page .face-link-line {
  stroke: rgba(34, 211, 238, 0.34) !important;
  stroke-width: 0.8 !important;
  stroke-dasharray: 6 5 !important;
  filter: drop-shadow(0 0 2px rgba(34, 211, 238, 0.16)) !important;
}

.lp-page.lp-page .face-link-line.done {
  stroke: rgba(20, 184, 166, 0.76) !important;
  stroke-width: 1.05 !important;
  stroke-dasharray: 9 4 !important;
  filter: drop-shadow(0 0 4px rgba(20, 184, 166, 0.28)) !important;
}

.lp-page.lp-page .face-dimension-tag {
  position: absolute !important;
  isolation: isolate !important;
  grid-template-columns: 25px minmax(0, 1fr) !important;
  min-height: 34px !important;
  padding: 5px 11px 5px 6px !important;
  border: 1px solid rgba(34, 211, 238, 0.34) !important;
  border-radius: 0 !important;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.76), rgba(240, 253, 250, 0.48)),
    repeating-linear-gradient(90deg, rgba(34, 211, 238, 0.08) 0 1px, transparent 1px 9px) !important;
  color: #31445a !important;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.58),
    0 0 0 1px rgba(15, 23, 42, 0.02) !important;
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px) !important;
  letter-spacing: 0 !important;
}

.lp-page.lp-page .face-dimension-tag::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  background:
    linear-gradient(90deg, transparent, rgba(34, 211, 238, 0.16), transparent),
    radial-gradient(circle at 0 0, rgba(34, 211, 238, 0.24), transparent 32%);
  opacity: 0.7;
}

.lp-page.lp-page .face-dimension-tag::after {
  content: "";
  position: absolute;
  right: 7px;
  bottom: 6px;
  width: 8px;
  height: 8px;
  border-right: 1px solid rgba(34, 211, 238, 0.7);
  border-bottom: 1px solid rgba(34, 211, 238, 0.7);
  opacity: 0.8;
}

.lp-page.lp-page .face-dimension-tag.right {
  grid-template-columns: minmax(0, 1fr) 25px !important;
  padding: 5px 6px 5px 11px !important;
}

.lp-page.lp-page .face-dimension-tag.right::after {
  right: auto;
  left: 7px;
  border-right: 0;
  border-left: 1px solid rgba(34, 211, 238, 0.7);
}

.lp-page.lp-page .face-dimension-tag span {
  width: 21px !important;
  height: 21px !important;
  border-radius: 0 !important;
  background: linear-gradient(135deg, rgba(8, 145, 178, 0.18), rgba(20, 184, 166, 0.1)) !important;
  color: #067a72 !important;
  box-shadow: inset 0 0 0 1px rgba(34, 211, 238, 0.35) !important;
  clip-path: polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px) !important;
  font-size: 10px !important;
}

.lp-page.lp-page .face-dimension-tag b {
  color: inherit !important;
  font-size: 11px !important;
  font-weight: 800 !important;
  text-shadow: 0 0 10px rgba(34, 211, 238, 0.12) !important;
}

.lp-page.lp-page .face-dimension-tag.done {
  border-color: rgba(20, 184, 166, 0.72) !important;
  background:
    linear-gradient(135deg, rgba(220, 252, 241, 0.88), rgba(204, 251, 241, 0.54)),
    repeating-linear-gradient(90deg, rgba(20, 184, 166, 0.12) 0 1px, transparent 1px 9px) !important;
  color: #035f56 !important;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.72),
    0 0 18px rgba(20, 184, 166, 0.12) !important;
}

.lp-page.lp-page .face-dimension-tag.done span {
  background: linear-gradient(135deg, #22d3ee, #10b981) !important;
  color: #ffffff !important;
  box-shadow: 0 0 14px rgba(20, 184, 166, 0.35) !important;
}

.lp-page.lp-page .face-brief {
  display: none !important;
}

/* img2 reference pass: compact card layout for the learning-profile dialogue page. */
.lp-page.lp-page:not(.profile-report-mode) {
  background:
    radial-gradient(circle at 22% 8%, rgba(209, 250, 229, 0.42), transparent 28%),
    radial-gradient(circle at 82% 16%, rgba(224, 242, 254, 0.32), transparent 30%),
    linear-gradient(180deg, #f7fcfa 0%, #f3faf7 100%) !important;
}

.lp-page.lp-page:not(.profile-report-mode) .lp-sidebar {
  display: flex !important;
  flex-direction: column !important;
  gap: 20px !important;
  padding: 28px 26px 22px !important;
  background:
    linear-gradient(180deg, rgba(235, 252, 245, 0.78), rgba(246, 253, 250, 0.92)) !important;
  border-right: 1px solid rgba(209, 227, 219, 0.72) !important;
}

.lp-page.lp-page:not(.profile-report-mode) .nav-item {
  height: 58px !important;
  margin-bottom: 12px !important;
  border: 1px solid transparent !important;
  border-radius: 14px !important;
  background: transparent !important;
}

.lp-page.lp-page:not(.profile-report-mode) .nav-item.active {
  border-color: rgba(93, 211, 162, 0.28) !important;
  background: linear-gradient(135deg, rgba(220, 252, 241, 0.92), rgba(236, 253, 245, 0.62)) !important;
  box-shadow: 0 12px 26px rgba(16, 185, 129, 0.08) !important;
}

.lp-page.lp-page:not(.profile-report-mode) .sidebar-digital-human-stage {
  display: flex !important;
  min-height: 0 !important;
  flex: 1 1 auto !important;
  align-items: flex-end !important;
  margin-top: 0 !important;
  overflow: visible !important;
}

.lp-page.lp-page:not(.profile-report-mode) .sidebar-stage-card {
  width: 100%;
  padding: 22px 18px 20px;
  border: 1px solid rgba(212, 226, 220, 0.9);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 18px 42px rgba(23, 72, 55, 0.08);
}

.lp-page.lp-page:not(.profile-report-mode) .sidebar-stage-card strong {
  display: block;
  margin-bottom: 14px;
  color: #22352f;
  font-size: 14px;
  font-weight: 850;
}

.lp-page.lp-page:not(.profile-report-mode) .sidebar-stage-frame {
  position: relative;
  display: grid;
  height: 162px;
  place-items: center;
  border: 1px dashed rgba(148, 163, 184, 0.58);
  border-radius: 10px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(248, 252, 250, 0.82));
}

.lp-page.lp-page:not(.profile-report-mode) .sidebar-stage-frame::before {
  content: "";
  width: 72px;
  height: 58px;
  opacity: 0.3;
  background:
    linear-gradient(#cbd5e1, #cbd5e1) 50% 100% / 72px 2px no-repeat,
    linear-gradient(#cbd5e1, #cbd5e1) 50% 78% / 54px 2px no-repeat,
    linear-gradient(135deg, transparent 18px, #e5e7eb 0 22px, transparent 0) 50% 30% / 58px 48px no-repeat;
}

.lp-page.lp-page:not(.profile-report-mode) .sidebar-stage-state {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-top: 14px;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(236, 253, 245, 0.82);
  color: #047857;
  font-size: 12px;
  font-weight: 800;
}

.lp-page.lp-page:not(.profile-report-mode) .sidebar-stage-state::before {
  content: "";
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.12);
}

.lp-page.lp-page:not(.profile-report-mode) .sidebar-stage-state.error {
  background: #fff1f2;
  color: #e11d48;
}

.lp-page.lp-page:not(.profile-report-mode) .sidebar-stage-card small {
  display: block;
  margin-top: 9px;
  color: #7b8b85;
  font-size: 12px;
}

.lp-page.lp-page:not(.profile-report-mode) .lp-content {
  padding: 30px 34px !important;
  background: transparent !important;
}

.lp-page.lp-page .assess-layout.assess-redesign {
  grid-template-columns: minmax(560px, 0.98fr) minmax(520px, 1.02fr) !important;
  gap: 24px !important;
  height: calc(100vh - 132px) !important;
  min-height: 650px !important;
  padding: 0 !important;
  overflow: visible !important;
}

.lp-page.lp-page .assessment-chat-shell,
.lp-page.lp-page .profile-portrait-panel {
  border: 1px solid rgba(216, 229, 224, 0.9) !important;
  border-radius: 10px !important;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(253, 255, 254, 0.86)) !important;
  box-shadow: 0 20px 48px rgba(31, 72, 66, 0.09) !important;
}

.lp-page.lp-page .assessment-chat-shell {
  padding: 34px clamp(28px, 3.1vw, 46px) 24px !important;
}

.lp-page.lp-page .assessment-chat-shell::before {
  display: none !important;
}

.lp-page.lp-page .profile-portrait-panel {
  padding: 34px clamp(26px, 3vw, 44px) 24px !important;
  border-left: 1px solid rgba(216, 229, 224, 0.9) !important;
}

.lp-page.lp-page .chat-hero-head {
  margin-bottom: 22px !important;
}

.lp-page.lp-page .chat-hero-head h2 {
  margin: 8px 0 12px !important;
  font-size: clamp(36px, 3vw, 48px) !important;
  line-height: 1.08 !important;
  color: #172033 !important;
}

.lp-page.lp-page .chat-hero-head p {
  max-width: 620px !important;
  color: #728093 !important;
}

.lp-page.lp-page .stage-status.compact {
  padding: 10px 17px !important;
  border-color: rgba(125, 214, 183, 0.38) !important;
  background: rgba(248, 255, 252, 0.88) !important;
  color: #0f766e !important;
}

.lp-page.lp-page .portrait-chat-messages.chat-messages {
  padding: 6px 8px 4px 0 !important;
}

.lp-page.lp-page .chat-message-row {
  margin-bottom: 18px !important;
}

.lp-page.lp-page .message-avatar {
  flex: 0 0 36px !important;
  width: 36px !important;
  height: 36px !important;
  border: 1px solid rgba(16, 185, 129, 0.25) !important;
  background: #f0fdf4 !important;
}

.lp-page.lp-page .portrait-chat-messages .chat-bubble {
  max-width: min(560px, 82%) !important;
  padding: 16px 20px !important;
  border-radius: 14px !important;
  border-color: rgba(203, 213, 225, 0.75) !important;
  background: rgba(255, 255, 255, 0.82) !important;
  box-shadow: 0 14px 32px rgba(31, 72, 66, 0.06) !important;
  font-size: 14px !important;
  line-height: 1.72 !important;
}

.lp-page.lp-page .portrait-chat-area .chat-reset-row {
  min-height: 34px !important;
  margin: 0 0 8px !important;
}

.lp-page.lp-page .portrait-chat-area .chat-reset-btn {
  min-height: 32px !important;
  padding: 0 16px !important;
  border: 1px solid rgba(16, 185, 129, 0.16) !important;
  background: rgba(236, 253, 245, 0.72) !important;
}

.lp-page.lp-page .portrait-chat-area .chat-input-row {
  min-height: 64px !important;
  padding: 6px 7px 6px 20px !important;
  border-radius: 16px !important;
  border-color: rgba(203, 213, 225, 0.82) !important;
  background: rgba(255, 255, 255, 0.92) !important;
  box-shadow: 0 12px 30px rgba(31, 72, 66, 0.07) !important;
}

.lp-page.lp-page .portrait-chat-area .chat-input {
  min-height: 50px !important;
  font-size: 15px !important;
}

.lp-page.lp-page .portrait-chat-area .chat-send {
  width: 52px !important;
  height: 52px !important;
  border-radius: 14px !important;
  background: linear-gradient(135deg, #15c99c, #08a978) !important;
  box-shadow: 0 12px 22px rgba(8, 169, 120, 0.24) !important;
}

.lp-page.lp-page .portrait-panel-head h3 {
  font-size: 27px !important;
  line-height: 1.2 !important;
}

.lp-page.lp-page .portrait-summary {
  margin-top: 18px !important;
  padding-bottom: 18px !important;
}

.lp-page.lp-page .portrait-score-ring {
  flex-basis: 104px !important;
  width: 104px !important;
  height: 104px !important;
  box-shadow: 0 13px 28px rgba(16, 185, 129, 0.12) !important;
}

.lp-page.lp-page .data-face-wrap {
  flex: 1 1 auto !important;
  width: 430px !important;
  max-width: 100% !important;
  min-height: 448px !important;
  margin: 14px auto 0 !important;
  transform: none !important;
}

.lp-page.lp-page .profile-face-links {
  left: 0 !important;
  width: 100% !important;
  height: 430px !important;
  transform: none !important;
}

.lp-page.lp-page .profile-face-stage {
  top: 44px !important;
  width: 218px !important;
}

.lp-page.lp-page .face-dimension-tag {
  min-height: 36px !important;
  border-radius: 7px !important;
  clip-path: none !important;
  background:
    linear-gradient(180deg, rgba(240, 253, 250, 0.92), rgba(226, 252, 245, 0.78)) !important;
  box-shadow: 0 8px 18px rgba(20, 184, 166, 0.08) !important;
}

.lp-page.lp-page .face-dimension-tag span {
  border-radius: 6px !important;
  clip-path: none !important;
}

.lp-page.lp-page .face-dimension-tag::after {
  display: none !important;
}

@media (max-width: 1400px) {
  .lp-page.lp-page .assess-layout.assess-redesign {
    grid-template-columns: minmax(520px, 1fr) 500px !important;
  }

  .lp-page.lp-page .assessment-chat-shell {
    padding-left: 34px !important;
    padding-right: 34px !important;
  }

  .lp-page.lp-page .profile-portrait-panel {
    padding-left: 28px !important;
    padding-right: 28px !important;
  }
}

@media (max-width: 1180px) {
  .lp-page.lp-page .assess-layout.assess-redesign {
    grid-template-columns: 1fr !important;
    height: auto !important;
    overflow: visible !important;
  }

  .lp-page.lp-page .assessment-chat-shell::before,
  .lp-page.lp-page .profile-portrait-panel {
    border-left: 0 !important;
  }

  .lp-page.lp-page .profile-portrait-panel {
    border-top: 1px solid rgba(203, 213, 225, 0.64) !important;
  }
}
</style>

<style>
/* Learning profile report: layout follows the compact three-column reference dashboard. */
.lp-page.profile-report-mode {
  height: calc(100vh - 72px) !important;
  min-height: calc(100vh - 72px) !important;
  background: #f5faf7 !important;
  color: #17231d;
}

.lp-page.profile-report-mode > .profile-report-sidebar {
  position: relative;
  width: 194px !important;
  min-width: 194px !important;
  padding: 14px 13px 16px !important;
  overflow: hidden !important;
  border-right: 1px solid #e1ebe5 !important;
  background: #f8fcfa !important;
}

.profile-report-sidebar .profile-identity-card {
  display: grid;
  min-height: 98px;
  place-items: center;
  align-content: center;
  gap: 5px;
  border-radius: 8px;
  background: linear-gradient(145deg, #70bd98, #86cbaa);
  color: #ffffff;
}

.profile-report-sidebar .profile-identity-card strong {
  font-size: 17px;
  font-weight: 800;
}

.profile-report-sidebar .profile-identity-card span {
  font-size: 12px;
  opacity: 0.94;
}

.profile-report-sidebar .profile-section-nav {
  display: grid;
  gap: 3px;
  margin-top: 13px;
}

.profile-report-sidebar .profile-section-nav a {
  display: flex;
  min-height: 42px;
  align-items: center;
  gap: 11px;
  padding: 0 14px;
  border-left: 3px solid transparent;
  color: #466456;
  font-size: 13px;
  font-weight: 650;
  text-decoration: none;
  transition: background-color 160ms ease, color 160ms ease;
}

.profile-report-sidebar .profile-section-nav a:first-child,
.profile-report-sidebar .profile-section-nav a:hover {
  border-left-color: #69b58e;
  background: #edf7f1;
  color: #339267;
}

.profile-report-sidebar .profile-report-note {
  position: absolute;
  right: 13px;
  bottom: 142px;
  left: 13px;
  padding: 13px 11px;
  border: 1px solid #dbe9e1;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.78);
}

.profile-report-sidebar .profile-report-note strong {
  color: #344a40;
  font-size: 12px;
}

.profile-report-sidebar .profile-report-note p {
  margin: 7px 0 0;
  color: #718078;
  font-size: 10px;
  line-height: 1.75;
}

.profile-report-sidebar .profile-sidebar-actions {
  position: absolute;
  right: 13px;
  bottom: 93px;
  left: 13px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.profile-report-sidebar .profile-sidebar-actions button {
  display: flex;
  min-width: 0;
  height: 34px;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border: 1px solid #d8e8df;
  border-radius: 6px;
  background: #ffffff;
  color: #4b685a;
  font-size: 11px;
  cursor: pointer;
}

.profile-report-sidebar .profile-sidebar-actions button:hover {
  border-color: #84c7a6;
  color: #25865b;
}

.profile-report-sidebar .profile-sidebar-chip {
  position: absolute;
  bottom: 9px;
  left: 46px;
  width: 102px;
  height: 75px;
  object-fit: contain;
  opacity: 0.82;
}

.lp-page.profile-report-mode > .lp-content {
  padding: 14px 15px 24px !important;
  background: #f7fbf8 !important;
  scroll-behavior: smooth;
}

.lp-page.profile-report-mode > .lp-content > .content-panel {
  min-height: auto !important;
}

.profile-dashboard-report {
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
}

.profile-dashboard-header {
  position: relative;
  display: grid;
  min-height: 90px;
  grid-template-columns: minmax(320px, 0.86fr) minmax(470px, 1.14fr);
  align-items: start;
  gap: 18px;
  padding: 8px 8px 10px 14px;
}

.profile-dashboard-header h2 {
  margin: 0;
  color: #101915;
  font-size: 27px;
  font-weight: 850;
  line-height: 1.3;
  letter-spacing: 0;
}

.profile-dashboard-header > div:first-child > p {
  margin: 7px 0 0;
  color: #52625a;
  font-size: 13px;
}

.profile-growth-route {
  display: grid;
  grid-template-columns: repeat(4, minmax(90px, 1fr));
  align-items: start;
  padding-top: 4px;
}

.growth-route-step {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 5px;
  color: #4ea078;
}

.growth-route-step > span {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 6px;
  background: #eaf5ef;
}

.growth-route-step small {
  color: #273a30;
  font-size: 11px;
  white-space: nowrap;
}

.growth-route-step i {
  position: absolute;
  z-index: 0;
  top: 17px;
  left: calc(50% + 24px);
  width: calc(100% - 48px);
  border-top: 1px dashed #75b897;
}

.growth-route-step i::after {
  content: "";
  position: absolute;
  top: -3px;
  right: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #6eaf8d;
}

.profile-summary-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 9px;
  margin-bottom: 11px;
}

.profile-summary-strip article {
  display: grid;
  min-height: 132px;
  grid-template-columns: 53px minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  padding: 15px 13px;
  overflow: hidden;
  border: 1px solid #e0e9e4;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 3px 11px rgba(42, 86, 65, 0.07);
}

.profile-summary-strip article > svg {
  color: #68b38d;
}

.profile-summary-strip article > div {
  min-width: 0;
}

.profile-summary-strip article span {
  display: block;
  margin-bottom: 9px;
  color: #293b31;
  font-size: 12px;
}

.profile-summary-strip article strong {
  display: block;
  overflow: hidden;
  color: #1a261f;
  font-size: 13px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-summary-strip article p {
  display: -webkit-box;
  margin: 5px 0 0;
  overflow: hidden;
  color: #65746c;
  font-size: 10px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.profile-dashboard-grid {
  display: grid;
  grid-template-columns: minmax(340px, 0.94fr) minmax(370px, 1.02fr) minmax(410px, 1.12fr);
  align-items: start;
  gap: 10px;
}

.profile-dashboard-column {
  display: grid;
  gap: 10px;
}

.profile-dash-card {
  overflow: hidden;
  border: 1px solid #e0e9e4;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 3px 11px rgba(42, 86, 65, 0.07);
}

.profile-dash-card > h3 {
  margin: 0;
  padding: 13px 16px 10px;
  color: #1f2c25;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0;
}

.profile-dash-card > h3 small {
  color: #77857d;
  font-size: 9px;
  font-weight: 500;
}

.profile-ability-card,
.profile-radar-card,
.profile-preference-card {
  height: 360px;
}

.profile-evidence-matrix,
.profile-ai-analysis-card,
.profile-plan-card {
  height: 336px;
}

.profile-ability-list {
  display: grid;
  gap: 5px;
  padding: 4px 16px 13px;
}

.profile-ability-row {
  display: grid;
  min-height: 25px;
  grid-template-columns: 22px 116px minmax(96px, 1fr) 35px;
  align-items: center;
  gap: 7px;
}

.ability-row-icon {
  display: grid;
  place-items: center;
  color: #5eae85;
}

.profile-ability-row > strong {
  overflow: hidden;
  color: #34463c;
  font-size: 11px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ability-segments {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 2px;
}

.ability-segments i {
  height: 14px;
  background: #eef1ef;
}

.ability-segments i:first-child { border-radius: 4px 0 0 4px; }
.ability-segments i:last-child { border-radius: 0 4px 4px 0; }
.ability-segments i.filled { background: linear-gradient(90deg, #68b58f, #a8d4bd); }

.profile-ability-row > small {
  color: #66756d;
  font-size: 10px;
  text-align: right;
}

.evidence-table-wrap {
  padding: 0 15px;
}

.profile-evidence-matrix table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.profile-evidence-matrix th,
.profile-evidence-matrix td {
  height: 22px;
  padding: 0 3px;
  border: 1px solid #e8eeea;
  color: #58675f;
  font-size: 8px;
  text-align: center;
}

.profile-evidence-matrix th:first-child,
.profile-evidence-matrix td:first-child {
  width: 31%;
  text-align: left;
}

.profile-evidence-matrix thead th {
  background: #f4f8f5;
  color: #384b40;
  font-weight: 700;
}

.profile-evidence-matrix td i,
.evidence-legend i {
  display: inline-block;
  width: 9px;
  height: 9px;
  border: 1px solid #79b999;
  border-radius: 50%;
}

.profile-evidence-matrix .evidence-strong,
.evidence-legend .evidence-strong { background: #5caf83; }
.profile-evidence-matrix .evidence-mid,
.evidence-legend .evidence-mid { background: linear-gradient(90deg, #79bd9c 50%, #ffffff 50%); }
.profile-evidence-matrix .evidence-weak,
.evidence-legend .evidence-weak { background: #ffffff; }
.profile-evidence-matrix .evidence-none { border-color: transparent; }

.evidence-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 8px 16px;
  color: #6e7c74;
  font-size: 8px;
}

.evidence-legend span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.profile-radar-stage {
  display: grid;
  height: 315px;
  place-items: center;
  padding: 0 10px 10px;
}

.profile-radar-stage .radar-svg {
  width: min(100%, 330px);
  height: 300px;
  overflow: visible;
}

.profile-radar-stage .radar-label {
  fill: #263c31;
  font-size: 12px;
  font-weight: 600;
}

.profile-ai-conclusion {
  display: grid;
  min-height: 126px;
  grid-template-columns: 116px minmax(0, 1fr);
  align-items: center;
  gap: 15px;
  margin: 0 16px 12px;
  padding: 10px;
  border: 1px solid #d6e8de;
  border-radius: 8px;
  background: #fbfefc;
}

.profile-ai-portrait {
  position: relative;
  display: grid;
  width: 106px;
  height: 106px;
  margin: 0;
  overflow: hidden;
  place-items: center;
  border: 0;
  border-radius: 24px;
  background: transparent;
}

.profile-ai-portrait img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: inherit;
}

.profile-portrait-status {
  position: absolute;
  right: 5px;
  bottom: 5px;
  left: 5px;
  display: flex;
  min-height: 27px;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 4px 6px;
  border: 1px solid rgba(212, 231, 220, 0.96);
  border-radius: 6px;
  background: rgba(246, 252, 249, 0.94);
  color: #426d57;
  backdrop-filter: blur(5px);
}

.profile-portrait-spinner {
  width: 13px;
  height: 13px;
  flex: 0 0 auto;
  border: 2px solid #cce6d8;
  border-top-color: #58a97f;
  border-radius: 50%;
  animation: profile-dashboard-spin 0.85s linear infinite;
}

.profile-portrait-status small {
  min-width: 0;
  color: inherit;
  font-size: 9px;
  font-weight: 700;
  line-height: 1.2;
  text-align: center;
}

.profile-portrait-status button {
  display: inline-flex;
  min-height: 21px;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border: 1px solid #a8d2bb;
  border-radius: 5px;
  background: #fff;
  color: #357b59;
  cursor: pointer;
  font-size: 9px;
  font-weight: 700;
}

.profile-portrait-status button:hover {
  border-color: #65ad86;
  color: #246443;
}

.profile-portrait-status-error {
  border: 1px solid #ead7d1;
  background: rgba(255, 248, 245, 0.94);
  color: #875246;
}

.profile-portrait-status-error button {
  display: grid;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid #d9bcb3;
  border-radius: 5px;
  background: #fff;
  color: #875246;
  cursor: pointer;
  place-items: center;
}

.profile-portrait-status-error button:hover {
  border-color: #b88576;
  color: #6e4035;
}

@keyframes profile-dashboard-spin { to { transform: rotate(360deg); } }

.profile-ai-conclusion > p {
  margin: 0;
  color: #43554b;
  font-size: 11px;
  line-height: 1.75;
}

.profile-ai-compare {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 0 16px 14px;
}

.profile-ai-compare > div {
  min-height: 127px;
  padding: 12px;
  border-radius: 7px;
  background: #f1f8f4;
}

.profile-ai-compare > div:last-child {
  background: #fff8f0;
}

.profile-ai-compare strong {
  display: block;
  margin-bottom: 8px;
  color: #2f4639;
  font-size: 11px;
}

.profile-ai-compare p {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  margin: 5px 0;
  color: #596a61;
  font-size: 9px;
  line-height: 1.45;
}

.profile-ai-compare p svg {
  flex: 0 0 auto;
  margin-top: 1px;
  color: #51aa7c;
}

.profile-ai-compare > div:last-child p svg { color: #df8a42; }

.profile-preference-card {
  padding-bottom: 6px;
}

.profile-preference-row {
  display: grid;
  min-height: 92px;
  grid-template-columns: 55px 73px minmax(0, 1fr);
  align-items: center;
  margin: 0 16px;
  border-bottom: 1px solid #edf1ee;
}

.profile-preference-row:last-child { border-bottom: 0; }

.profile-preference-row > span {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  color: #5eb087;
  background: #f1f8f4;
}

.profile-preference-row > strong {
  color: #273a30;
  font-size: 11px;
}

.profile-preference-row > p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: #4f6057;
  font-size: 10px;
  line-height: 1.7;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.profile-plan-card {
  padding-bottom: 8px;
}

.profile-plan-row {
  position: relative;
  display: grid;
  min-height: 54px;
  grid-template-columns: 43px 91px minmax(0, 1fr);
  align-items: center;
  margin: 0 15px;
  border-bottom: 1px solid #edf1ee;
}

.profile-plan-row:last-child { border-bottom: 0; }

.profile-plan-row > span {
  color: #58aa80;
}

.profile-plan-row > strong {
  color: #2d4036;
  font-size: 10px;
}

.profile-plan-row > p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: #4f6057;
  font-size: 9px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.profile-plan-row > small {
  position: absolute;
  right: 0;
  color: #dfeae4;
  font-size: 20px;
  font-weight: 800;
  pointer-events: none;
}

@media (max-width: 1380px) {
  .profile-summary-strip { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .profile-dashboard-grid { grid-template-columns: minmax(330px, 0.9fr) minmax(360px, 1fr); }
  .profile-dashboard-right { grid-column: 1 / -1; grid-template-columns: 1fr 1fr; }
}

@media (max-width: 980px) {
  .lp-page.profile-report-mode > .profile-report-sidebar { display: none !important; }
  .profile-dashboard-header { grid-template-columns: 1fr; }
  .profile-growth-route { display: none; }
  .profile-summary-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .profile-dashboard-grid { grid-template-columns: 1fr; }
  .profile-dashboard-right { grid-column: auto; grid-template-columns: 1fr; }
  .profile-ability-card,
  .profile-radar-card,
  .profile-preference-card,
  .profile-evidence-matrix,
  .profile-ai-analysis-card,
  .profile-plan-card { height: auto; min-height: 330px; }
}

@media (max-width: 620px) {
  .lp-page.profile-report-mode > .lp-content { padding: 12px !important; }
  .profile-dashboard-header { padding-top: 62px; }
  .profile-dashboard-header h2 { font-size: 21px; }
  .profile-summary-strip { grid-template-columns: 1fr; }
  .profile-summary-strip article { min-height: 105px; }
  .profile-ai-conclusion { grid-template-columns: 1fr; }
  .profile-ai-compare { grid-template-columns: 1fr; }
  .profile-ability-row { grid-template-columns: 22px 104px minmax(75px, 1fr) 34px; }
  .profile-preference-row { grid-template-columns: 48px 65px minmax(0, 1fr); }
  .profile-plan-row { grid-template-columns: 36px 82px minmax(0, 1fr); }
}

.lp-page.lp-page .profile-input-tools {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 3px;
}

.lp-page.lp-page .profile-input-tools button {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 7px;
  background: transparent;
  color: #60766f;
}

.lp-page.lp-page .profile-input-tools button:hover {
  border-color: rgba(16, 185, 129, 0.24);
  background: rgba(236, 253, 245, 0.9);
  color: #059669;
}

.lp-page.lp-page .portrait-chat-area .chat-input {
  min-width: 0;
}

.lp-page.lp-page .profile-pending-attachments,
.lp-page.lp-page .profile-message-attachments {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.lp-page.lp-page .profile-pending-attachments {
  padding: 8px 10px;
  border: 1px solid rgba(16, 185, 129, 0.14);
  border-radius: 8px;
  background: rgba(240, 253, 244, 0.72);
}

.lp-page.lp-page .profile-pending-attachments > span,
.lp-page.lp-page .profile-message-attachments a {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: min(220px, 100%);
  padding: 5px 7px;
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.86);
  color: #176a50;
  font-size: 11px;
}

.lp-page.lp-page .profile-message-attachments {
  margin-top: 3px;
}

.lp-page.lp-page .profile-pending-attachments b,
.lp-page.lp-page .profile-message-attachments b {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lp-page.lp-page .profile-pending-attachments button {
  width: 18px;
  height: 18px;
  padding: 0;
  border-radius: 50%;
  background: transparent;
  color: #647c74;
  line-height: 1;
}

@media (max-width: 620px) {
  .lp-page.lp-page .profile-input-tools button {
    width: 30px;
    height: 30px;
  }
}

/* Final monochrome profile system. Generated portrait bitmaps keep their native colors. */
#app .lp-page.lp-page {
  --profile-ink: #191c1c;
  --profile-muted: #737a79;
  --profile-line: #e1e4e3;
  --profile-soft: #f7f8f7;
  color: var(--profile-ink) !important;
  background: #fbfbfb !important;
}

#app .lp-page.lp-page > .lp-sidebar {
  border-right: 1px solid var(--profile-line) !important;
  background: #ffffff !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .sidebar-nav {
  gap: 2px !important;
  padding: 24px 18px !important;
}

#app .lp-page.lp-page .nav-item,
#app .lp-page.lp-page .nav-item:hover,
#app .lp-page.lp-page .nav-item.active,
#app .lp-page.lp-page .nav-item.active:hover {
  min-height: 44px !important;
  padding: 0 12px !important;
  border: 0 !important;
  border-radius: 5px !important;
  background: transparent !important;
  color: #525958 !important;
  box-shadow: none !important;
  transform: none !important;
}

#app .lp-page.lp-page .nav-item:hover,
#app .lp-page.lp-page .nav-item.active,
#app .lp-page.lp-page .nav-item.active:hover {
  background: #eff1f0 !important;
  color: #151818 !important;
}

#app .lp-page.lp-page .nav-icon,
#app .lp-page.lp-page .nav-item.active .nav-icon {
  color: currentColor !important;
  background: transparent !important;
}

#app .lp-page.lp-page .sidebar-digital-human-stage {
  padding: 0 18px 20px !important;
}

#app .lp-page.lp-page .sidebar-stage-card,
#app .lp-page.lp-page:not(.profile-report-mode) .sidebar-stage-card {
  padding: 16px 0 0 !important;
  border: 0 !important;
  border-top: 1px solid var(--profile-line) !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .sidebar-stage-frame,
#app .lp-page.lp-page:not(.profile-report-mode) .sidebar-stage-frame {
  border-color: #d7dbda !important;
  border-radius: 6px !important;
  background: #fafafa !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .sidebar-stage-frame::before,
#app .lp-page.lp-page:not(.profile-report-mode) .sidebar-stage-frame::before {
  border-color: #d7dbda !important;
  color: #a1a6a5 !important;
  filter: none !important;
}

#app .lp-page.lp-page .sidebar-stage-state,
#app .lp-page.lp-page .sidebar-stage-state.error,
#app .lp-page.lp-page:not(.profile-report-mode) .sidebar-stage-state,
#app .lp-page.lp-page:not(.profile-report-mode) .sidebar-stage-state.error {
  border-color: #dadddc !important;
  background: #f1f2f2 !important;
  color: #4f5655 !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .sidebar-stage-state::before,
#app .lp-page.lp-page:not(.profile-report-mode) .sidebar-stage-state::before {
  background: #717877 !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page > .lp-content,
#app .lp-page.lp-page .content-panel {
  background: #fbfbfb !important;
}

#app .lp-page.lp-page .content-panel {
  border: 0 !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page.profile-assess-mode > .lp-content.lp-content {
  padding: 0 !important;
  overflow: hidden !important;
  background: #ffffff !important;
}

#app .lp-page.lp-page.profile-assess-mode .content-panel.assess-panel {
  width: 100% !important;
  height: 100% !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}

#app .lp-page.lp-page .assess-layout.assess-redesign {
  gap: 0 !important;
  overflow: hidden !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: #ffffff !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page.profile-assess-mode .assess-layout.assess-redesign {
  width: 100% !important;
  height: calc(100vh - 72px) !important;
  min-height: calc(100vh - 72px) !important;
  max-height: none !important;
  margin: 0 !important;
  padding: 0 !important;
}

@media (min-width: 1181px) {
  #app .lp-page.lp-page.profile-assess-mode .assess-layout.assess-redesign {
    grid-template-columns: minmax(0, 1fr) clamp(460px, 36%, 640px) !important;
  }

  #app .lp-page.lp-page.profile-assess-mode .assessment-chat-shell {
    padding-inline: clamp(36px, 3vw, 56px) !important;
  }

  #app .lp-page.lp-page.profile-assess-mode .profile-portrait-panel {
    padding-inline: clamp(22px, 2vw, 32px) !important;
  }

  #app .lp-page.lp-page.profile-assess-mode .portrait-chat-messages .chat-bubble {
    max-width: min(720px, 84%) !important;
  }
}

#app .lp-page.lp-page .assessment-chat-shell,
#app .lp-page.lp-page .profile-portrait-panel {
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .chat-avatar-background .avatar-error,
#app .lp-page.lp-page .chat-avatar-background .avatar-status,
#app .lp-page.lp-page .chat-avatar-background .resume-button {
  display: none !important;
}

#app .lp-page.lp-page .profile-portrait-panel {
  border-left: 1px solid var(--profile-line) !important;
}

#app .lp-page.lp-page .assessment-chat-shell::before,
#app .lp-page.lp-page .portrait-chat-area .chat-input-row::before,
#app .lp-page.lp-page .portrait-chat-area .chat-input-row::after,
#app .lp-page.lp-page .portrait-chat-area .chat-reset-row::before,
#app .lp-page.lp-page .portrait-chat-area .chat-reset-row::after,
#app .lp-page.lp-page .face-dimension-tag::before,
#app .lp-page.lp-page .face-dimension-tag::after {
  content: none !important;
}

#app .lp-page.lp-page .portrait-panel-head {
  border: 0 !important;
  border-bottom: 1px solid var(--profile-line) !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .portrait-panel-head h3,
#app .lp-page.lp-page .chat-eyebrow,
#app .lp-page.lp-page .portrait-meta strong {
  color: var(--profile-ink) !important;
}

#app .lp-page.lp-page .portrait-score-ring {
  background:
    radial-gradient(circle at center, #ffffff 0 60%, transparent 61%),
    conic-gradient(#0b9965 0 var(--score), #e4eee9 var(--score) 100%) !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .profile-face-stage {
  z-index: 2 !important;
  border: 0 !important;
  background: #ffffff !important;
  box-shadow: none !important;
  filter: none !important;
}

#app .lp-page.lp-page .profile-face-links {
  z-index: 3 !important;
}

#app .lp-page.lp-page .face-link-line {
  stroke: #b8c8c1 !important;
  stroke-width: 1.15 !important;
  stroke-dasharray: none !important;
  opacity: 0.9 !important;
  filter: drop-shadow(0 0 1.5px rgba(255, 255, 255, 0.95)) !important;
  vector-effect: non-scaling-stroke;
}

#app .lp-page.lp-page .face-link-line.done {
  stroke: #0b9965 !important;
  stroke-width: 1.7 !important;
  stroke-dasharray: none !important;
  opacity: 1 !important;
  filter: drop-shadow(0 0 3px rgba(11, 153, 101, 0.38)) !important;
  animation: none !important;
}

#app .lp-page.lp-page .face-link-anchor {
  fill: #ffffff !important;
  stroke: #8fa99e !important;
  stroke-width: 1.5 !important;
  opacity: 0.96 !important;
  vector-effect: non-scaling-stroke;
}

#app .lp-page.lp-page .face-link-anchor.done {
  fill: #0b9965 !important;
  stroke: #ffffff !important;
  stroke-width: 1.8 !important;
  filter: drop-shadow(0 0 3px rgba(11, 153, 101, 0.42)) !important;
}

#app .lp-page.lp-page .profile-face-base {
  opacity: 0.24 !important;
  filter: grayscale(0.42) saturate(0.42) contrast(0.94) brightness(1.16) !important;
}

#app .lp-page.lp-page .profile-face-segment {
  filter: grayscale(0.78) saturate(0.36) contrast(0.96) brightness(1.14) opacity(0.26) !important;
}

#app .lp-page.lp-page .profile-face-segment.active {
  mix-blend-mode: normal !important;
  filter: saturate(1.55) contrast(1.16) brightness(1.03) drop-shadow(0 0 8px rgba(11, 153, 101, 0.42)) !important;
  animation: profileDimensionActivate 0.72s cubic-bezier(0.22, 1, 0.36, 1) both;
}

#app .lp-page.lp-page .face-dimension-tag {
  --tag-shift-x: 0%;
  z-index: 4 !important;
  border: 1px solid #d2d9d6 !important;
  border-radius: 5px !important;
  background: #ffffff !important;
  color: #252c29 !important;
  box-shadow: none !important;
  transform: translateX(var(--tag-shift-x)) translateY(0) scale(1) !important;
  transform-origin: center !important;
  transition:
    transform 0.22s cubic-bezier(0.22, 1, 0.36, 1),
    border-color 0.22s ease,
    background-color 0.22s ease,
    box-shadow 0.22s ease !important;
  cursor: pointer;
}

#app .lp-page.lp-page .face-dimension-tag.right {
  --tag-shift-x: -100%;
}

#app .lp-page.lp-page .face-dimension-tag.top,
#app .lp-page.lp-page .face-dimension-tag.bottom {
  --tag-shift-x: -50%;
}

#app .lp-page.lp-page .face-dimension-tag:hover,
#app .lp-page.lp-page .face-dimension-tag:focus-visible {
  border-color: #78aa94 !important;
  background: #f6fbf8 !important;
  box-shadow: 0 10px 24px rgba(17, 92, 62, 0.15) !important;
  transform: translateX(var(--tag-shift-x)) translateY(-5px) scale(1.045) !important;
}

#app .lp-page.lp-page .face-dimension-tag:focus-visible {
  outline: 2px solid rgba(11, 153, 101, 0.28) !important;
  outline-offset: 3px !important;
}

#app .lp-page.lp-page .face-dimension-tag:active {
  transform: translateX(var(--tag-shift-x)) translateY(-1px) scale(0.99) !important;
}

#app .lp-page.lp-page .face-dimension-tag.done {
  border-color: #0b9965 !important;
  background: #eaf8f1 !important;
  color: #075c3e !important;
  box-shadow: 0 0 0 2px rgba(11, 153, 101, 0.08), 0 8px 20px rgba(11, 98, 67, 0.12) !important;
  animation: profileDimensionActivate 0.72s cubic-bezier(0.22, 1, 0.36, 1) both;
}

#app .lp-page.lp-page .face-dimension-tag.done:hover,
#app .lp-page.lp-page .face-dimension-tag.done:focus-visible {
  border-color: #087b52 !important;
  background: #def4e8 !important;
  box-shadow: 0 0 0 3px rgba(11, 153, 101, 0.13), 0 14px 30px rgba(11, 98, 67, 0.2) !important;
}

#app .lp-page.lp-page .face-dimension-tag span {
  border-color: #cbd3d0 !important;
  border-radius: 4px !important;
  background: #eef2f0 !important;
  color: #242b28 !important;
  transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1) !important;
}

#app .lp-page.lp-page .face-dimension-tag:hover span,
#app .lp-page.lp-page .face-dimension-tag:focus-visible span {
  transform: scale(1.09) !important;
}

#app .lp-page.lp-page .face-dimension-tag.done span {
  border-color: #087b52 !important;
  background: #087b52 !important;
  color: #ffffff !important;
  box-shadow: 0 0 0 3px rgba(11, 153, 101, 0.12) !important;
}

#app .lp-page.lp-page .face-dimension-tag b {
  color: inherit !important;
}

#app .lp-page.lp-page .face-dimension-tag.selected,
#app .lp-page.lp-page .face-dimension-tag.selected:hover,
#app .lp-page.lp-page .face-dimension-tag.selected:focus-visible {
  z-index: 7 !important;
  border-color: #075c3e !important;
  background: #dff4e9 !important;
  color: #064d35 !important;
  box-shadow: 0 0 0 3px rgba(11, 153, 101, 0.14), 0 14px 30px rgba(11, 98, 67, 0.18) !important;
  transform: translateX(var(--tag-shift-x)) translateY(-3px) scale(1.035) !important;
}

#app .lp-page.lp-page .face-dimension-detail {
  position: absolute;
  /* The selected node is z-index 7; keep its detail panel above every node. */
  z-index: 10;
  top: var(--detail-y, 124px);
  left: var(--detail-x, 50%);
  width: var(--detail-width, 200px);
  max-height: 166px;
  padding: 13px;
  overflow: visible;
  border: 1px solid #9bc8b2;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 18px 42px rgba(17, 92, 62, 0.2);
  color: #1c2d25;
  transform: none;
}

#app .lp-page.lp-page .face-dimension-detail::before {
  content: "";
  position: absolute;
  width: 12px;
  height: 12px;
  border: inherit;
  background: inherit;
  box-shadow: inherit;
  transform: rotate(45deg);
}

#app .lp-page.lp-page .face-dimension-detail[style*="--detail-arrow: left"]::before {
  left: -7px;
  top: 50%;
  border-top: 0;
  border-right: 0;
  transform: translateY(-50%) rotate(45deg);
}

#app .lp-page.lp-page .face-dimension-detail[style*="--detail-arrow: right"]::before {
  right: -7px;
  top: 50%;
  border-bottom: 0;
  border-left: 0;
  transform: translateY(-50%) rotate(45deg);
}

#app .lp-page.lp-page .face-dimension-detail[style*="--detail-arrow: top"]::before {
  top: -7px;
  left: 50%;
  border-right: 0;
  border-bottom: 0;
  transform: translateX(-50%) rotate(45deg);
}

#app .lp-page.lp-page .face-dimension-detail[style*="--detail-arrow: bottom"]::before {
  bottom: -7px;
  left: 50%;
  border-top: 0;
  border-left: 0;
  transform: translateX(-50%) rotate(45deg);
}

#app .lp-page.lp-page .face-dimension-detail header {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) 28px;
  align-items: center;
  gap: 9px;
}

#app .lp-page.lp-page .face-dimension-detail header > span {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border-radius: 5px;
  background: #087b52;
  color: #ffffff;
  font-size: 11px;
  font-weight: 800;
}

#app .lp-page.lp-page .face-dimension-detail header > div {
  display: grid;
  min-width: 0;
  gap: 2px;
}

#app .lp-page.lp-page .face-dimension-detail small {
  color: #7a8580;
  font-size: 9px;
  font-weight: 700;
}

#app .lp-page.lp-page .face-dimension-detail small.done {
  color: #087b52;
}

#app .lp-page.lp-page .face-dimension-detail strong {
  overflow: hidden;
  color: #13251d;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

#app .lp-page.lp-page .face-dimension-detail header > button {
  display: grid;
  width: 28px;
  height: 28px;
  padding: 0;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: #f0f4f2;
  color: #52615a;
  cursor: pointer;
}

#app .lp-page.lp-page .face-dimension-detail header > button:hover,
#app .lp-page.lp-page .face-dimension-detail header > button:focus-visible {
  background: #dff1e8;
  color: #075c3e;
}

#app .lp-page.lp-page .face-dimension-detail p {
  max-height: 85px;
  margin: 10px 0 0;
  padding-top: 9px;
  overflow-y: auto;
  border-top: 1px solid #e2ebe6;
  color: #34483e;
  font-size: 11px;
  line-height: 1.65;
  overflow-wrap: anywhere;
}

#app .lp-page.lp-page.profile-assess-mode .profile-portrait-panel,
#app .lp-page.lp-page.profile-assess-mode .data-face-wrap {
  overflow: visible !important;
}

@media (max-width: 480px) {
  #app .lp-page.lp-page .face-dimension-detail {
    top: 76px;
    left: 50%;
    width: min(300px, calc(100% - 28px));
    max-height: 176px;
    transform: translateX(-50%);
  }
}

@keyframes profileDataFlow {
  to { stroke-dashoffset: -28; }
}

@keyframes profileDimensionActivate {
  from { opacity: 0.45; }
  55% { opacity: 1; }
  to { opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  #app .lp-page.lp-page .face-link-line.done,
  #app .lp-page.lp-page .profile-face-segment.active,
  #app .lp-page.lp-page .face-dimension-tag.done {
    animation: none !important;
  }
}

#app .lp-page.lp-page .chat-bubble,
#app .lp-page.lp-page .portrait-chat-area .chat-bubble {
  border-color: #e3e8e6 !important;
  border-radius: 20px !important;
  background: #ffffff !important;
  color: #252b29 !important;
  box-shadow: 0 8px 24px rgba(23, 39, 33, 0.045) !important;
}

#app .lp-page.lp-page .chat-bubble.user,
#app .lp-page.lp-page .portrait-chat-area .chat-bubble.user {
  border-color: #d4e5dc !important;
  background: #f0f8f4 !important;
  color: #1f3028 !important;
}

#app .lp-page.lp-page .portrait-chat-messages .thinking-message-row {
  align-items: center !important;
}

#app .lp-page.lp-page .portrait-chat-messages .thinking-message-row .typing-indicator {
  display: inline-flex !important;
  flex: 0 0 auto !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 7px !important;
  width: auto !important;
  min-width: 76px !important;
  max-width: none !important;
  min-height: 52px !important;
  margin: 0 auto 0 0 !important;
  padding: 15px 20px !important;
}

#app .lp-page.lp-page .portrait-chat-messages .typing-indicator .dot {
  flex: 0 0 7px !important;
  width: 7px !important;
  height: 7px !important;
  background: #176f4b !important;
  will-change: transform, opacity;
  animation: agentThinkingJump 1.08s infinite ease-in-out both !important;
}

#app .lp-page.lp-page .portrait-chat-messages .typing-indicator .dot:nth-child(1) {
  animation-delay: 0s !important;
}

#app .lp-page.lp-page .portrait-chat-messages .typing-indicator .dot:nth-child(2) {
  animation-delay: 0.16s !important;
}

#app .lp-page.lp-page .portrait-chat-messages .typing-indicator .dot:nth-child(3) {
  animation-delay: 0.32s !important;
}

@keyframes agentThinkingJump {
  0%, 60%, 100% {
    transform: translateY(0) scale(0.76);
    opacity: 0.35;
  }
  30% {
    transform: translateY(-6px) scale(1);
    opacity: 1;
  }
}

#app .lp-page.lp-page .profile-pending-attachments,
#app .lp-page.lp-page .profile-pending-attachments > span,
#app .lp-page.lp-page .profile-message-attachments a {
  border-color: #dfe3e2 !important;
  border-radius: 6px !important;
  background: #ffffff !important;
  color: #4a5150 !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .portrait-chat-area .chat-input-row {
  min-height: 64px !important;
  padding: 6px 8px 6px 18px !important;
  border: 0 !important;
  border-radius: 24px !important;
  background: #ffffff !important;
  box-shadow: 0 10px 30px rgba(23, 39, 33, 0.075) !important;
  overflow: hidden !important;
  transition: box-shadow 0.2s ease !important;
}

#app .lp-page.lp-page .portrait-chat-area .chat-input-row:focus-within {
  box-shadow: 0 14px 36px rgba(23, 111, 75, 0.11) !important;
}

#app .lp-page.lp-page .portrait-chat-area .chat-input {
  color: #242827 !important;
  border: 0 !important;
  outline: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .profile-input-tools button,
#app .lp-page.lp-page .chat-reset-btn {
  border: 0 !important;
  border-radius: 10px !important;
  background: transparent !important;
  color: #176f4b !important;
}

#app .lp-page.lp-page .profile-input-tools button:hover,
#app .lp-page.lp-page .chat-reset-btn:hover {
  border-color: #dadddc !important;
  background: #eff1f0 !important;
  color: #171919 !important;
}

#app .lp-page.lp-page .portrait-chat-area .chat-send,
#app .lp-page.lp-page .portrait-chat-area .chat-send:hover:not(:disabled) {
  width: 50px !important;
  height: 50px !important;
  border: 0 !important;
  border-radius: 50% !important;
  background: #176f4b !important;
  color: #ffffff !important;
  box-shadow: 0 8px 20px rgba(23, 111, 75, 0.18) !important;
  transform: none !important;
}

#app .lp-page.lp-page .portrait-chat-area .chat-send:hover:not(:disabled) {
  background: #0f5f3f !important;
  box-shadow: 0 10px 24px rgba(15, 95, 63, 0.24) !important;
}

#app .lp-page.lp-page .toast-bar {
  border-color: #176f4b !important;
  border-radius: 6px !important;
  background: #176f4b !important;
  color: #ffffff !important;
  box-shadow: 0 6px 18px rgba(20, 24, 23, 0.16) !important;
}

#app .lp-page.lp-page .report-empty-dashboard,
#app .lp-page.lp-page .profile-dashboard-report {
  background: transparent !important;
}

#app .lp-page.lp-page .empty-report-card,
#app .lp-page.lp-page .profile-summary-strip article,
#app .lp-page.lp-page .profile-dash-card,
#app .lp-page.lp-page .history-item {
  border: 1px solid var(--profile-line) !important;
  border-radius: 6px !important;
  background: #ffffff !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .empty-visual-card,
#app .lp-page.lp-page .empty-progress-box,
#app .lp-page.lp-page .empty-tip-box,
#app .lp-page.lp-page .status-explain,
#app .lp-page.lp-page .result-preview {
  border-color: #e1e4e3 !important;
  border-radius: 6px !important;
  background: #f5f6f6 !important;
  color: #4f5655 !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .empty-progress-track,
#app .lp-page.lp-page .ability-segments i,
#app .lp-page.lp-page .agent-log-progress-track {
  background: #e4e7e6 !important;
}

#app .lp-page.lp-page .empty-progress-track > div,
#app .lp-page.lp-page .agent-log-progress-track span {
  background: #176f4b !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .empty-collect-actions button,
#app .lp-page.lp-page .history-item-actions button,
#app .lp-page.lp-page .result-preview button,
#app .lp-page.lp-page .profile-ai-portrait button {
  border-color: #d9dddc !important;
  border-radius: 6px !important;
  background: #ffffff !important;
  color: #3f4645 !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .empty-generate-btn,
#app .lp-page.lp-page .empty-generate-btn:hover:not(:disabled) {
  border-color: #176f4b !important;
  border-radius: 6px !important;
  background: #176f4b !important;
  color: #ffffff !important;
  box-shadow: none !important;
  transform: none !important;
}

#app .lp-page.lp-page .agent-time-step > span,
#app .lp-page.lp-page .agent-time-step.done > span,
#app .lp-page.lp-page .agent-time-step.active > span {
  background: #e7e9e8 !important;
  color: #303534 !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .agent-time-step.active > span,
#app .lp-page.lp-page .agent-time-step.done > span {
  background: #176f4b !important;
  color: #ffffff !important;
}

#app .lp-page.lp-page .agent-time-step::after,
#app .lp-page.lp-page .agent-time-step.done::after,
#app .lp-page.lp-page .agent-time-step.active::after {
  border-left-color: #cfd4d3 !important;
}

#app .lp-page.lp-page .agent-log-panel {
  border-color: #303534 !important;
  border-radius: 6px !important;
  background: #202323 !important;
  color: #f3f4f4 !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .agent-log-panel :is(strong, dd, p) {
  color: #eef0ef !important;
}

#app .lp-page.lp-page .agent-log-panel :is(span, time, dt) {
  color: #aeb4b3 !important;
}

#app .lp-page.lp-page .agent-log-entry::before,
#app .lp-page.lp-page .agent-log-entry.warning::before,
#app .lp-page.lp-page .agent-log-entry.failed::before,
#app .lp-page.lp-page .agent-log-entry.error::before {
  background: #c8cccb !important;
  box-shadow: none !important;
}

#app .lp-page.lp-page .profile-dashboard-header,
#app .lp-page.lp-page .profile-dash-card > h3 {
  border-color: var(--profile-line) !important;
  background: transparent !important;
}

#app .lp-page.lp-page .profile-summary-strip article > svg,
#app .lp-page.lp-page .ability-row-icon,
#app .lp-page.lp-page .profile-preference-row > span,
#app .lp-page.lp-page .profile-plan-row > span,
#app .lp-page.lp-page .profile-ai-compare p svg {
  color: #555c5b !important;
}

#app .lp-page.lp-page .profile-preference-row > span,
#app .lp-page.lp-page .profile-ai-compare > div,
#app .lp-page.lp-page .profile-ai-compare > div:last-child {
  background: #f2f3f3 !important;
}

#app .lp-page.lp-page .profile-evidence-matrix :is(.evidence-strong, .evidence-mid, .evidence-weak),
#app .lp-page.lp-page .evidence-legend :is(.evidence-strong, .evidence-mid, .evidence-weak) {
  border-color: #6d7473 !important;
  background: #6d7473 !important;
}

#app .lp-page.lp-page .profile-evidence-matrix .evidence-mid,
#app .lp-page.lp-page .evidence-legend .evidence-mid {
  background: linear-gradient(90deg, #8b9190 50%, #ffffff 50%) !important;
}

#app .lp-page.lp-page .profile-evidence-matrix .evidence-weak,
#app .lp-page.lp-page .evidence-legend .evidence-weak {
  background: #ffffff !important;
}

#app .lp-page.lp-page .profile-radar-stage polygon[fill='none'],
#app .lp-page.lp-page .profile-radar-stage line {
  stroke: #d9dddc !important;
}

#app .lp-page.lp-page .profile-radar-stage polygon:not([fill='none']) {
  fill: rgba(32, 36, 36, 0.2) !important;
  stroke: #343938 !important;
}

#app .lp-page.lp-page .profile-radar-stage circle {
  fill: #202424 !important;
}

#app .lp-page.lp-page .profile-portrait-status {
  border-color: #d9dddc !important;
  background: #f3f4f4 !important;
  color: #555c5b !important;
}

#app .lp-page.lp-page .profile-portrait-spinner {
  border-color: #d5d9d8 !important;
  border-top-color: #303534 !important;
}

#app .lp-page.lp-page .history-item.active,
#app .lp-page.lp-page .history-item:hover {
  border-color: #aeb5b4 !important;
  background: #fafafa !important;
  box-shadow: none !important;
  transform: none !important;
}

#app .lp-page.lp-page .history-badge,
#app .lp-page.lp-page .history-badge.done,
#app .lp-page.lp-page .history-badge.pending,
#app .lp-page.lp-page .history-badge.current,
#app .lp-page.lp-page .history-badge.version {
  border-color: #d9dddc !important;
  border-radius: 4px !important;
  background: #f1f2f2 !important;
  color: #4f5655 !important;
}

#app .lp-page.lp-page .empty-state .empty-icon,
#app .lp-page.lp-page .empty-state svg {
  color: #646b6a !important;
  background: #f0f1f1 !important;
  box-shadow: none !important;
}

/* Restore the report's green data-visualization accents without affecting profile state. */
#app .lp-page.lp-page.profile-report-mode {
  background: #f5faf7 !important;
}

#app .lp-page.lp-page.profile-report-mode > .profile-report-sidebar {
  border-right-color: #e1ebe5 !important;
  background: #f8fcfa !important;
}

#app .lp-page.lp-page.profile-report-mode > .lp-content,
#app .lp-page.lp-page.profile-report-mode .content-panel {
  background: #f7fbf8 !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-section-nav a:first-child,
#app .lp-page.lp-page.profile-report-mode .profile-section-nav a:hover {
  border-left-color: #69b58e !important;
  background: #edf7f1 !important;
  color: #2d8b61 !important;
}

#app .lp-page.lp-page.profile-report-mode .growth-route-step {
  color: #4ea078 !important;
}

#app .lp-page.lp-page.profile-report-mode .growth-route-step > span {
  background: #eaf5ef !important;
}

#app .lp-page.lp-page.profile-report-mode .growth-route-step i {
  border-top-color: #75b897 !important;
}

#app .lp-page.lp-page.profile-report-mode .growth-route-step i::after {
  background: #6eaf8d !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-summary-strip article,
#app .lp-page.lp-page.profile-report-mode .profile-dash-card {
  border-color: #dfe9e3 !important;
  background: #ffffff !important;
  box-shadow: 0 3px 11px rgba(42, 86, 65, 0.07) !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-summary-strip article > svg {
  color: #68b38d !important;
}

#app .lp-page.lp-page.profile-report-mode .ability-row-icon {
  color: #5eae85 !important;
}

#app .lp-page.lp-page.profile-report-mode .ability-segments i {
  background: #e8eeea !important;
}

#app .lp-page.lp-page.profile-report-mode .ability-segments i.filled {
  background: linear-gradient(90deg, #68b58f, #a8d4bd) !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-evidence-matrix td i,
#app .lp-page.lp-page.profile-report-mode .evidence-legend i {
  border-color: #79b999 !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-evidence-matrix .evidence-strong,
#app .lp-page.lp-page.profile-report-mode .evidence-legend .evidence-strong {
  background: #5caf83 !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-evidence-matrix .evidence-mid,
#app .lp-page.lp-page.profile-report-mode .evidence-legend .evidence-mid {
  background: linear-gradient(90deg, #79bd9c 50%, #ffffff 50%) !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-evidence-matrix .evidence-weak,
#app .lp-page.lp-page.profile-report-mode .evidence-legend .evidence-weak {
  background: #ffffff !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-radar-stage polygon[fill='none'],
#app .lp-page.lp-page.profile-report-mode .profile-radar-stage line {
  stroke: #d4e5dc !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-radar-stage polygon:not([fill='none']) {
  fill: rgba(92, 175, 131, 0.22) !important;
  stroke: #4f9f76 !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-radar-stage circle {
  fill: #3f9469 !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-preference-row > span {
  background: #f1f8f4 !important;
  color: #5eb087 !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-plan-row > span {
  color: #58aa80 !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-ai-compare > div {
  background: #f1f8f4 !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-ai-compare > div:last-child {
  background: #fff8f0 !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-ai-compare p svg {
  color: #51aa7c !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-ai-compare > div:last-child p svg {
  color: #df8a42 !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-portrait-status {
  border-color: #d4e7dc !important;
  background: #eaf5ef !important;
  color: #668475 !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-portrait-spinner {
  border-color: #cce6d8 !important;
  border-top-color: #58a97f !important;
}

#app .lp-page.lp-page.profile-report-mode .profile-portrait-status-error {
  border-color: #ead7d1 !important;
  background: #fff8f5 !important;
  color: #875246 !important;
}

@media (max-width: 480px) {
  #app .lp-page.lp-page .profile-portrait-panel {
    overflow: hidden !important;
  }

  #app .lp-page.lp-page .data-face-wrap {
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    gap: 8px !important;
    width: 100% !important;
    max-width: 100% !important;
    min-height: 0 !important;
    padding-top: 282px !important;
    margin: 12px auto 0 !important;
    box-sizing: border-box !important;
  }

  #app .lp-page.lp-page .profile-face-links {
    display: none !important;
  }

  #app .lp-page.lp-page .profile-face-stage {
    top: 12px !important;
    width: 190px !important;
  }

  #app .lp-page.lp-page .face-dimension-tag,
  #app .lp-page.lp-page .face-dimension-tag.right,
  #app .lp-page.lp-page .face-dimension-tag.top,
  #app .lp-page.lp-page .face-dimension-tag.bottom {
    position: relative !important;
    inset: auto !important;
    left: auto !important;
    top: auto !important;
    width: 100% !important;
    min-height: 40px !important;
    padding: 5px 7px !important;
    grid-template-columns: 22px minmax(0, 1fr) !important;
    transform: none !important;
    box-sizing: border-box !important;
  }

  #app .lp-page.lp-page .face-dimension-tag.right span {
    grid-column: 1 !important;
    grid-row: 1 !important;
  }

  #app .lp-page.lp-page .face-dimension-tag b {
    font-size: 10px !important;
    line-height: 1.25 !important;
  }
}

@media (max-width: 1180px) {
  #app .lp-page.lp-page.profile-assess-mode > .lp-content.lp-content {
    overflow-y: auto !important;
  }

  #app .lp-page.lp-page.profile-assess-mode .content-panel.assess-panel,
  #app .lp-page.lp-page.profile-assess-mode .assess-layout.assess-redesign {
    height: auto !important;
    overflow: visible !important;
  }

  #app .lp-page.lp-page .assess-layout.assess-redesign {
    gap: 0 !important;
  }

  #app .lp-page.lp-page .profile-portrait-panel {
    border-left: 0 !important;
    border-top: 1px solid var(--profile-line) !important;
  }
}

@media (max-width: 768px) and (orientation: portrait) {
  #app .lp-page.lp-page.profile-assess-mode > .lp-content.lp-content {
    padding-bottom: calc(88px + env(safe-area-inset-bottom)) !important;
    overflow: visible !important;
  }

  #app .lp-page.lp-page.profile-assess-mode .portrait-chat-area .chat-input-row {
    margin-bottom: calc(96px + env(safe-area-inset-bottom)) !important;
  }

  #app .lp-page.lp-page.profile-assess-mode .content-panel.assess-panel,
  #app .lp-page.lp-page.profile-assess-mode .assess-layout.assess-redesign {
    height: auto !important;
    overflow: visible !important;
  }
}

/* Keep profile content scrollable without showing page-level scrollbars. */
.lp-page,
.lp-page * {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.lp-page::-webkit-scrollbar,
.lp-page *::-webkit-scrollbar {
  width: 0;
  height: 0;
  display: none;
}

/* Learning profile history: match the quiet white reference dashboard. */
#app .lp-page.lp-page.profile-history-mode {
  background: #f7f8f7 !important;
}

#app .lp-page.lp-page.profile-history-mode > .lp-sidebar {
  width: 276px !important;
  min-width: 276px !important;
  padding: 64px 24px 28px !important;
  border-right: 1px solid #edf0ee !important;
  background: rgba(255, 255, 255, 0.86) !important;
  box-shadow: 12px 0 34px rgba(31, 72, 66, 0.035) !important;
}

#app .lp-page.lp-page.profile-history-mode .sidebar-nav {
  gap: 14px !important;
  padding: 0 !important;
}

#app .lp-page.lp-page.profile-history-mode .nav-item,
#app .lp-page.lp-page.profile-history-mode .nav-item:hover,
#app .lp-page.lp-page.profile-history-mode .nav-item.active,
#app .lp-page.lp-page.profile-history-mode .nav-item.active:hover {
  min-height: 62px !important;
  padding: 0 24px !important;
  border-radius: 7px !important;
  color: #2d3533 !important;
  font-size: 16px !important;
  font-weight: 800 !important;
}

#app .lp-page.lp-page.profile-history-mode .nav-item:hover,
#app .lp-page.lp-page.profile-history-mode .nav-item.active,
#app .lp-page.lp-page.profile-history-mode .nav-item.active:hover {
  background: linear-gradient(105deg, rgba(213, 248, 232, 0.9), rgba(230, 246, 238, 0.72)) !important;
  color: #0f6f56 !important;
}

#app .lp-page.lp-page.profile-history-mode .nav-icon {
  color: currentColor !important;
}

#app .lp-page.lp-page.profile-history-mode .sidebar-digital-human-stage {
  flex: 1 1 auto !important;
  align-items: flex-end !important;
  padding: 0 !important;
}

#app .lp-page.lp-page.profile-history-mode .sidebar-stage-card,
#app .lp-page.lp-page.profile-history-mode:not(.profile-report-mode) .sidebar-stage-card {
  padding: 28px 24px 18px !important;
  border-top: 1px solid #e2e8e5 !important;
}

#app .lp-page.lp-page.profile-history-mode .sidebar-stage-card strong {
  margin-bottom: 16px !important;
  color: #1f2926 !important;
  font-size: 15px !important;
  font-weight: 850 !important;
}

#app .lp-page.lp-page.profile-history-mode .sidebar-stage-frame {
  height: 172px !important;
  border: 1px dashed #d6ddda !important;
  border-radius: 6px !important;
  background: rgba(255, 255, 255, 0.62) !important;
}

#app .lp-page.lp-page.profile-history-mode .sidebar-stage-state {
  margin-top: 18px !important;
  border: 0 !important;
  border-radius: 999px !important;
  background: #f1f5f3 !important;
  color: #1f3a34 !important;
}

#app .lp-page.lp-page.profile-history-mode .sidebar-stage-state::before {
  background: #4dbf91 !important;
}

#app .lp-page.lp-page.profile-history-mode .sidebar-stage-card small {
  margin-top: 10px !important;
  color: #75837e !important;
}

#app .lp-page.lp-page.profile-history-mode > .lp-content.lp-content {
  padding: 26px 24px 32px !important;
  background: transparent !important;
}

#app .lp-page.lp-page.profile-history-mode .history-panel {
  min-height: calc(100vh - 124px) !important;
  border: 0 !important;
  border-radius: 11px !important;
  background: #ffffff !important;
  box-shadow: 0 16px 42px rgba(27, 46, 41, 0.055) !important;
}

#app .lp-page.lp-page.profile-history-mode .history-shell {
  min-height: calc(100vh - 124px);
  padding: 46px 34px;
}

#app .lp-page.lp-page.profile-history-mode .history-list {
  gap: 34px !important;
}

#app .lp-page.lp-page.profile-history-mode .history-list-head {
  display: flex !important;
  align-items: flex-start !important;
  justify-content: space-between !important;
  gap: 24px !important;
}

#app .lp-page.lp-page.profile-history-mode .history-create-button,
#app .lp-page.lp-page.profile-history-mode .history-create-button:hover:not(:disabled) {
  min-width: 152px !important;
  min-height: 44px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
  flex: 0 0 auto !important;
  border: 1px solid #0e8062 !important;
  border-radius: 7px !important;
  padding: 0 18px !important;
  background: #0e8062 !important;
  color: #ffffff !important;
  font-size: 14px !important;
  font-weight: 800 !important;
  line-height: 1 !important;
  box-shadow: 0 7px 18px rgba(14, 128, 98, 0.16) !important;
  transform: none !important;
}

#app .lp-page.lp-page.profile-history-mode .history-create-button:hover:not(:disabled) {
  border-color: #0a6f55 !important;
  background: #0a6f55 !important;
}

#app .lp-page.lp-page.profile-history-mode .history-create-button:disabled {
  cursor: wait !important;
  opacity: 0.62 !important;
}

#app .lp-page.lp-page.profile-history-mode .history-list-head h2 {
  margin: 0 !important;
  color: #1f2926 !important;
  font-size: 21px !important;
  line-height: 1.25 !important;
  font-weight: 900 !important;
  letter-spacing: 0 !important;
}

#app .lp-page.lp-page.profile-history-mode .history-list-head p {
  margin: 14px 0 0 !important;
  color: #4f5d59 !important;
  font-size: 16px !important;
  line-height: 1.7 !important;
}

#app .lp-page.lp-page.profile-history-mode .history-items {
  gap: 14px !important;
}

#app .lp-page.lp-page.profile-history-mode .history-item {
  min-height: 116px !important;
  padding: 24px 18px 24px 24px !important;
  gap: 22px !important;
  border: 1px solid #e3e7e5 !important;
  border-radius: 8px !important;
  background: #ffffff !important;
  box-shadow: 0 3px 11px rgba(30, 46, 42, 0.035) !important;
  transform: none !important;
}

#app .lp-page.lp-page.profile-history-mode .history-item:hover,
#app .lp-page.lp-page.profile-history-mode .history-item.active {
  border-color: #dce3df !important;
  box-shadow: 0 8px 22px rgba(30, 46, 42, 0.07) !important;
  transform: none !important;
}

#app .lp-page.lp-page.profile-history-mode .history-item-time {
  min-width: 250px !important;
  gap: 16px !important;
}

#app .lp-page.lp-page.profile-history-mode .history-time-icon {
  width: 46px;
  height: 46px;
  display: grid;
  flex: 0 0 46px;
  place-items: center;
  border: 3px solid rgba(21, 126, 98, 0.16);
  border-radius: 50%;
  background: #e8fbf2;
  color: #13775c;
}

#app .lp-page.lp-page.profile-history-mode .history-item-time strong {
  color: #1b2421 !important;
  font-size: 18px !important;
  line-height: 1.35 !important;
  font-weight: 900 !important;
}

#app .lp-page.lp-page.profile-history-mode .history-item-time span {
  color: #63716d !important;
  font-size: 15px !important;
  line-height: 1.35 !important;
  font-weight: 500 !important;
}

#app .lp-page.lp-page.profile-history-mode .history-item-summary {
  align-items: center !important;
  gap: 14px !important;
}

#app .lp-page.lp-page.profile-history-mode .history-badge,
#app .lp-page.lp-page.profile-history-mode .history-badge.done,
#app .lp-page.lp-page.profile-history-mode .history-badge.pending,
#app .lp-page.lp-page.profile-history-mode .history-badge.current,
#app .lp-page.lp-page.profile-history-mode .history-badge.version {
  min-height: 34px !important;
  display: inline-flex !important;
  align-items: center !important;
  border: 0 !important;
  border-radius: 7px !important;
  padding: 0 15px !important;
  background: #f3f5f4 !important;
  color: #293330 !important;
  font-size: 14px !important;
  font-weight: 700 !important;
  line-height: 1 !important;
  white-space: nowrap !important;
}

#app .lp-page.lp-page.profile-history-mode .history-badge.current {
  background: #e1f3ea !important;
  color: #0e7056 !important;
}

#app .lp-page.lp-page.profile-history-mode .history-badge.path {
  gap: 6px !important;
  background: #eef4fb !important;
  color: #315f87 !important;
}

#app .lp-page.lp-page.profile-history-mode .history-badge.path.ready {
  background: #e5f5ee !important;
  color: #0d7558 !important;
}

#app .lp-page.lp-page.profile-history-mode .history-parent {
  min-height: 34px !important;
  align-items: center !important;
  color: #64706c !important;
  font-size: 13px !important;
}

#app .lp-page.lp-page.profile-history-mode .history-item-actions {
  gap: 8px !important;
  margin-left: auto !important;
}

#app .lp-page.lp-page.profile-history-mode .history-item-actions button,
#app .lp-page.lp-page.profile-history-mode .history-item-actions button:hover:not(:disabled) {
  width: 44px !important;
  height: 44px !important;
  border: 1px solid #dfe5e2 !important;
  border-radius: 8px !important;
  background: #ffffff !important;
  color: #26302d !important;
  box-shadow: none !important;
  transform: none !important;
}

#app .lp-page.lp-page.profile-history-mode .history-item-actions button:hover:not(:disabled) {
  border-color: #b9d8cc !important;
  background: #f5fbf8 !important;
  color: #0f6f56 !important;
}

#app .lp-page.lp-page.profile-history-mode .history-empty-state {
  min-height: 360px !important;
}

#app .lp-page.lp-page.profile-history-mode .history-empty-state .empty-icon {
  background: #e8fbf2 !important;
  color: #13775c !important;
}

@media (max-width: 1120px) {
  #app .lp-page.lp-page.profile-history-mode .history-item {
    align-items: flex-start !important;
    flex-direction: column !important;
  }

  #app .lp-page.lp-page.profile-history-mode .history-item-time {
    min-width: 0 !important;
  }

  #app .lp-page.lp-page.profile-history-mode .history-item-actions {
    width: 100% !important;
    justify-content: flex-end !important;
  }
}

@media (max-width: 760px) {
  #app .lp-page.lp-page.profile-history-mode {
    flex-direction: column !important;
  }

  #app .lp-page.lp-page.profile-history-mode > .lp-sidebar {
    width: 100% !important;
    min-width: 0 !important;
    height: auto !important;
    padding: 14px !important;
  }

  #app .lp-page.lp-page.profile-history-mode .sidebar-digital-human-stage {
    display: none !important;
  }

  #app .lp-page.lp-page.profile-history-mode > .lp-content.lp-content {
    padding: 14px !important;
  }

  #app .lp-page.lp-page.profile-history-mode .history-list-head {
    align-items: stretch !important;
    flex-direction: column !important;
  }

  #app .lp-page.lp-page.profile-history-mode .history-create-button {
    width: 100% !important;
  }

  #app .lp-page.lp-page.profile-history-mode .history-shell {
    min-height: 560px;
    padding: 28px 18px;
  }

  #app .lp-page.lp-page.profile-history-mode .history-list-head p {
    font-size: 14px !important;
  }

  #app .lp-page.lp-page.profile-history-mode .history-item-time strong {
    font-size: 16px !important;
  }

  #app .lp-page.lp-page.profile-history-mode .history-badge,
  #app .lp-page.lp-page.profile-history-mode .history-badge.done,
  #app .lp-page.lp-page.profile-history-mode .history-badge.current,
  #app .lp-page.lp-page.profile-history-mode .history-badge.version {
    min-height: 30px !important;
    padding: 0 10px !important;
    font-size: 12px !important;
  }
}

/* Keep the three learning-profile modes aligned on one stable desktop rail. */
@media (min-width: 761px) {
  #app .lp-page.lp-page {
    --learning-profile-sidebar-width: 276px;
  }

  #app .lp-page.lp-page > .lp-sidebar.lp-sidebar {
    box-sizing: border-box !important;
    flex: 0 0 var(--learning-profile-sidebar-width) !important;
    width: var(--learning-profile-sidebar-width) !important;
    min-width: var(--learning-profile-sidebar-width) !important;
    max-width: var(--learning-profile-sidebar-width) !important;
  }

  /* All three profile tabs share one rail geometry. History used to enlarge its
     navigation independently, which made the same sidebar look wider. */
  #app .lp-page.lp-page > .lp-sidebar.lp-sidebar,
  #app .lp-page.lp-page.profile-history-mode > .lp-sidebar.lp-sidebar {
    padding: 28px 26px 22px !important;
  }

  #app .lp-page.lp-page .sidebar-nav,
  #app .lp-page.lp-page.profile-history-mode .sidebar-nav {
    gap: 2px !important;
    padding: 0 !important;
  }

  #app .lp-page.lp-page .nav-item,
  #app .lp-page.lp-page .nav-item:hover,
  #app .lp-page.lp-page .nav-item.active,
  #app .lp-page.lp-page .nav-item.active:hover,
  #app .lp-page.lp-page.profile-history-mode .nav-item,
  #app .lp-page.lp-page.profile-history-mode .nav-item:hover,
  #app .lp-page.lp-page.profile-history-mode .nav-item.active,
  #app .lp-page.lp-page.profile-history-mode .nav-item.active:hover {
    box-sizing: border-box !important;
    height: 58px !important;
    min-height: 58px !important;
    margin-bottom: 12px !important;
    padding: 0 16px !important;
    font-family: inherit !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    line-height: 1.25 !important;
    letter-spacing: 0 !important;
  }

  #app .lp-page.lp-page .nav-label,
  #app .lp-page.lp-page.profile-history-mode .nav-label {
    display: block !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    line-height: 20px !important;
    letter-spacing: 0 !important;
    white-space: nowrap !important;
  }

  #app .lp-page.lp-page .sidebar-digital-human-stage,
  #app .lp-page.lp-page.profile-history-mode .sidebar-digital-human-stage {
    padding: 0 !important;
  }

  #app .lp-page.lp-page .sidebar-stage-card,
  #app .lp-page.lp-page.profile-history-mode .sidebar-stage-card,
  #app .lp-page.lp-page.profile-history-mode:not(.profile-report-mode) .sidebar-stage-card {
    box-sizing: border-box !important;
    padding: 16px 0 0 !important;
    border-top: 1px solid var(--profile-line) !important;
  }

  /* Keep the shared rail out of mode-specific flex sizing entirely. */
  #app .lp-page.lp-page {
    box-sizing: border-box !important;
    padding-left: var(--learning-profile-sidebar-width) !important;
    position: relative !important;
  }

  #app .lp-page.lp-page > .lp-sidebar.lp-sidebar {
    position: absolute !important;
    inset: 0 auto 0 0 !important;
    z-index: 2 !important;
    height: auto !important;
    display: flex !important;
    flex-direction: column !important;
    overflow: hidden !important;
  }

  #app .lp-page.lp-page > .lp-content.lp-content {
    box-sizing: border-box !important;
    flex: 1 1 100% !important;
    width: 100% !important;
    min-width: 0 !important;
  }

  #app .lp-page.lp-page .sidebar-nav {
    flex: 0 0 auto !important;
  }

  #app .lp-page.lp-page .sidebar-digital-human-stage,
  #app .lp-page.lp-page.profile-history-mode .sidebar-digital-human-stage {
    display: flex !important;
    flex-direction: column !important;
    flex: 1 1 auto !important;
    min-height: 0 !important;
    align-items: stretch !important;
    justify-content: flex-end !important;
    margin-top: 0 !important;
    overflow: hidden !important;
  }

  #app .lp-page.lp-page .sidebar-stage-card,
  #app .lp-page.lp-page.profile-history-mode .sidebar-stage-card,
  #app .lp-page.lp-page.profile-history-mode:not(.profile-report-mode) .sidebar-stage-card {
    width: 100% !important;
    height: 290px !important;
    min-height: 290px !important;
    max-height: 290px !important;
    flex: 0 0 290px !important;
  }

  #app .lp-page.lp-page .sidebar-stage-frame,
  #app .lp-page.lp-page.profile-history-mode .sidebar-stage-frame,
  #app .lp-page.lp-page.profile-assess-mode .sidebar-stage-frame {
    height: 200px !important;
    min-height: 200px !important;
    max-height: 200px !important;
  }

  #app .lp-page.lp-page .sidebar-stage-card > strong,
  #app .lp-page.lp-page.profile-history-mode .sidebar-stage-card > strong {
    margin: 0 0 12px !important;
    font-size: 14px !important;
    line-height: 20px !important;
  }

  #app .lp-page.lp-page .sidebar-stage-state,
  #app .lp-page.lp-page.profile-history-mode .sidebar-stage-state {
    min-height: 28px !important;
    margin-top: 12px !important;
    box-sizing: border-box !important;
  }
}

/* Keep the shared SDK player inside the sidebar stage instead of floating over it. */
#app .lp-page.lp-page .sidebar-stage-frame {
  position: relative !important;
  overflow: hidden !important;
  isolation: isolate;
}

#app .lp-page.lp-page .sidebar-stage-frame.has-avatar::before {
  display: none !important;
}

#app .lp-page.lp-page .sidebar-learning-avatar {
  position: absolute !important;
  inset: 0 !important;
  z-index: 1 !important;
  width: 100% !important;
  height: 100% !important;
  min-height: 0 !important;
  opacity: 1;
  pointer-events: auto;
  transition: opacity 0.18s ease;
}

#app .lp-page.lp-page .sidebar-stage-frame.has-error .sidebar-learning-avatar {
  opacity: 0;
  pointer-events: none;
}

#app .lp-page.lp-page .sidebar-learning-avatar .avatar-stage {
  position: absolute !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  transform: none !important;
}

#app .lp-page.lp-page .sidebar-learning-avatar .avatar-status,
#app .lp-page.lp-page .sidebar-learning-avatar .avatar-error,
#app .lp-page.lp-page .sidebar-learning-avatar .resume-button {
  display: none !important;
}

#app .lp-page.lp-page .sidebar-learning-avatar canvas,
#app .lp-page.lp-page .sidebar-learning-avatar video,
#app .lp-page.lp-page .sidebar-learning-avatar iframe {
  width: 100% !important;
  height: 100% !important;
  object-fit: contain !important;
  object-position: center bottom !important;
}

@media (max-width: 760px) {
  #app .lp-page.lp-page .sidebar-digital-human-stage,
  #app .lp-page.lp-page.profile-history-mode .sidebar-digital-human-stage {
    display: flex !important;
    width: 100% !important;
    min-height: 190px !important;
    flex: 0 0 auto !important;
    align-items: stretch !important;
    padding: 0 14px 14px !important;
    overflow: hidden !important;
  }

  #app .lp-page.lp-page .sidebar-stage-card,
  #app .lp-page.lp-page.profile-history-mode .sidebar-stage-card {
    width: 100% !important;
    padding-top: 12px !important;
  }

  #app .lp-page.lp-page .sidebar-stage-frame,
  #app .lp-page.lp-page.profile-history-mode .sidebar-stage-frame {
    height: 150px !important;
  }
}

</style>


