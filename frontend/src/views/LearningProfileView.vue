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

    <Teleport to="body">
      <Transition name="developer-panel">
        <div
          v-if="developerPanelOpen"
          class="profile-developer-backdrop"
          role="presentation"
          @click.self="closeDeveloperPanel"
        >
          <section
            ref="developerPanelRef"
            class="profile-developer-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="profile-developer-title"
            tabindex="-1"
          >
            <header class="profile-developer-header">
              <span class="profile-developer-icon" aria-hidden="true">
                <Wrench :size="20" />
              </span>
              <div>
                <p>仅用于本地测试</p>
                <h2 id="profile-developer-title">学习画像开发工具</h2>
              </div>
              <button type="button" title="关闭" aria-label="关闭开发工具" @click="closeDeveloperPanel">
                <X :size="19" />
              </button>
            </header>

            <div class="profile-developer-status">
              <span>当前采集进度</span>
              <strong>{{ completedProfileDimensionCount }}/{{ profileDimensionKeys.length }}</strong>
            </div>

            <div class="profile-developer-actions">
              <button
                type="button"
                class="profile-developer-action fill"
                :disabled="developerActionBusy"
                @click="fillDeveloperProfile"
              >
                <Sparkles :size="20" />
                <span>
                  <strong>{{ developerActionBusy ? '正在创建并激活画像' : '一键完成学习画像' }}</strong>
                  <small>{{ developerActionBusy ? '服务端正在保存画像并创建学习路径任务' : '写入十维测试数据，生成正式报告与学习路径' }}</small>
                </span>
              </button>

              <button
                type="button"
                :class="['profile-developer-action', 'clear', { armed: developerClearArmed }]"
                :disabled="developerActionBusy"
                @click="clearDeveloperProfile"
              >
                <Trash2 :size="20" />
                <span>
                  <strong>{{ developerClearArmed ? '再次点击确认清除' : '清除当前画像信息' }}</strong>
                  <small>{{ developerClearArmed ? '当前采集数据将被重置' : '历史画像版本仍会保留' }}</small>
                </span>
              </button>
            </div>

            <footer>
              <kbd>F4</kbd>
              <span>再次按下可关闭</span>
            </footer>
          </section>
        </div>
      </Transition>
    </Teleport>

    <Teleport to="body">
      <Transition name="profile-switch-dialog">
        <div
          v-if="profileSwitchDialog.open"
          class="profile-switch-backdrop"
          role="presentation"
          @click.self="resolveProfileSwitch(false)"
        >
          <section
            class="profile-switch-dialog"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="profile-switch-title"
            aria-describedby="profile-switch-description"
          >
            <span class="profile-switch-icon" aria-hidden="true"><Repeat2 :size="21" /></span>
            <div class="profile-switch-copy">
              <p>切换学习上下文</p>
              <h2 id="profile-switch-title">切换到“{{ profileSwitchDialog.profile?.profileName || '学习画像' }}”吗？</h2>
              <p id="profile-switch-description">
                切换后，岐小智群聊记录、学习路径和相关资源会一并切换。之后切回原画像，即可恢复原来的聊天与学习状态。
              </p>
            </div>
            <div class="profile-switch-actions">
              <button type="button" class="secondary" @click="resolveProfileSwitch(false)">取消</button>
              <button type="button" class="primary" @click="resolveProfileSwitch(true)">确认切换</button>
            </div>
          </section>
        </div>
      </Transition>
    </Teleport>

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
                      :alt="reportPortraitState === 'ready' ? '由学习画像智能体生成的学习者人像' : '默认中医学习者头像'"
                    />
                    <figcaption v-if="reportPortraitState === 'loading'" class="profile-portrait-status" role="status">
                      <span class="profile-portrait-spinner" aria-hidden="true"></span>
                      <small v-if="reportPortraitLoadingLabel">{{ reportPortraitLoadingLabel }}</small>
                    </figcaption>
                    <figcaption v-else-if="reportPortraitState === 'missing'" class="profile-portrait-status" role="status">
                      <small>当前为默认头像</small>
                      <button type="button" title="生成报告专属头像" @click.stop="retryReportPortrait"><Sparkles :size="13" />生成</button>
                    </figcaption>
                    <button
                      v-else-if="reportPortraitState === 'failed'"
                      type="button"
                      class="profile-portrait-retry"
                      title="重试生成报告专属头像"
                      aria-label="重试生成报告专属头像"
                      @click.stop="retryReportPortrait"
                    ><RefreshCcw :size="14" /></button>
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
                    <img v-if="m.role === 'bot'" :src="BOT_AVATAR_URL" alt="" />
                    <img v-else :src="USER_AVATAR_URL" alt="" />
                  </span>
                  <div :class="['chat-bubble', m.role, { 'typing-indicator': isPendingProfileReply(m) }]">
                    <template v-if="isPendingProfileReply(m)">
                      <span class="profile-typing-dots" aria-hidden="true"></span>
                    </template>
                    <span v-else>{{ m.text }}</span>
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
                    <small v-if="!isPendingProfileReply(m)">{{ m.time }}</small>
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
                    <span class="profile-typing-dots"></span>
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
                :style="profileFaceStageStyle"
              >
                <img
                  class="profile-face-base"
                  :src="profileFaceBaseSrc"
                  alt=""
                  aria-hidden="true"
                  @error="hideMissingProfileFaceAsset"
                />
                <img
                  v-for="segment in profileFaceSegments"
                  :key="segment.id"
                  class="profile-face-segment"
                  :class="{ active: segment.active }"
                  :src="segment.src"
                  alt=""
                  aria-hidden="true"
                  :style="segment.style"
                  @error="hideMissingProfileFaceAsset"
                />
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
              @click="openHistoryChat(report)"
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
                <button
                  class="history-delete-button"
                  :title="`删除${report.profileName || '学习画像'}`"
                  :aria-label="`删除${report.profileName || '学习画像'}`"
                  :disabled="!!profileActionBusy"
                  @click.stop="deleteProfileVersion(report)"
                >
                  <Trash2 :size="16" />
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
import { ref, reactive, computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, nextTick, watch } from 'vue'
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
  Trash2,
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
  deleteLearningProfile,
  getLearningProfiles,
  getLearningProfileSession,
  getLearningProfileSessions,
  getLearningProfilePortraitFile,
  getLearningProfilePortraitStatus,
  generateLearningProfilePortrait,
  refreshLearningProfile,
  renameLearningProfile,
  resetLearningProfile,
  resetLearningProfileBackgroundChat,
  createLearningProfileSession,
  streamLearningProfileSessionMessage,
  streamLearningProfileBackgroundChat,
  uploadMultimodalInputs,
} from '../services/api.js'
import { useGlobalDebug } from '../stores/globalDebug.js'
import {
  buildProfileSessionChatMessages,
  INITIAL_CHAT_OPENING,
} from '../utils/learningProfileChat.js'
import {
  createLearningProfileDeveloperFixture,
  isLearningProfileDeveloperShortcut,
} from '../utils/learningProfileDeveloperTools.js'
import { dispatchXiaoZhiWorkflowProgress } from '../utils/xiaozhiWorkflowProgress.js'
import { dispatchXiaoZhiProfileContextChanged } from '../utils/profileContextEvents.js'

const LS_KEY = 'learningProfileData'
const BOT_AVATAR_URL = '/botlogo.png'
const USER_AVATAR_URL = '/userlogo.png'
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
const activeChatReport = ref(null)
const CHAT_CONNECTING_TEXT = '正在连接学习背景智能体，请稍候...'
const CHAT_REPLY_PENDING_TEXT = '正在整理你的学习背景信息...'
const LLM_CHAT_TIMEOUT_MS = 90000
let initialChatRequestStarted = false
let chatMessageIdSeed = 0
const developerPanelOpen = ref(false)
const developerPanelRef = ref(null)
const developerActionBusy = ref(false)
const developerClearArmed = ref(false)
let developerClearTimer = null

function closeDeveloperPanel() {
  developerPanelOpen.value = false
  developerClearArmed.value = false
  window.clearTimeout(developerClearTimer)
}

async function toggleDeveloperPanel() {
  developerPanelOpen.value = !developerPanelOpen.value
  developerClearArmed.value = false
  window.clearTimeout(developerClearTimer)
  if (developerPanelOpen.value) {
    await nextTick()
    developerPanelRef.value?.focus()
  }
}

function handleDeveloperShortcut(event) {
  if (isLearningProfileDeveloperShortcut(event)) {
    event.preventDefault()
    void toggleDeveloperPanel()
    return
  }
  if (event.key === 'Escape' && developerPanelOpen.value) {
    event.preventDefault()
    closeDeveloperPanel()
  }
}

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
  (activeChatReport.value?.chatStudentProfile || profileData.value.chatStudentProfile) && typeof (activeChatReport.value?.chatStudentProfile || profileData.value.chatStudentProfile) === 'object'
    ? normalizeStudentProfileDimensions(activeChatReport.value?.chatStudentProfile || profileData.value.chatStudentProfile)
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
const profileSwitchDialog = reactive({ open: false, profile: null, resolve: null })

function requestProfileSwitchConfirmation(profile) {
  if (!profile?.id || profile.isActive) return Promise.resolve(true)
  profileSwitchDialog.profile = profile
  profileSwitchDialog.open = true
  return new Promise((resolve) => { profileSwitchDialog.resolve = resolve })
}

function isPendingProfileReply(message) {
  return message?.role === 'bot'
    && message?.source === 'llm-streaming'
    && !String(message?.text || '').trim()
}

function resolveProfileSwitch(confirmed) {
  const resolve = profileSwitchDialog.resolve
  profileSwitchDialog.open = false
  profileSwitchDialog.profile = null
  profileSwitchDialog.resolve = null
  resolve?.(Boolean(confirmed))
}

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
    if (activeProfileSessionId.value) {
      const activeSession = profileSessions.value.find(
        (session) => Number(session.id) === Number(activeProfileSessionId.value),
      )
      activeChatReport.value = historyReports.value.find(
        (report) => Number(report.id) === Number(activeSession?.reportId),
      ) || null
    }
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

async function openHistoryChat(report) {
  if (!report?.id || profileActionBusy.value) return
  const session = profileSessions.value.find((item) => Number(item.reportId) === Number(report.id))
  if (!session) {
    showToast('该画像暂无关联对话记录')
    return
  }
  activeProfileSessionId.value = session.id
  activeChatReport.value = report
  viewingHistory.value = null
  activeMenu.value = 'assess'
  await loadSelectedProfileSession()
  await nextTick()
  scrollChatToBottom({ retry: true })
}

async function activateProfileVersion(report) {
  if (!report?.id || profileActionBusy.value) return
  if (!await requestProfileSwitchConfirmation(report)) return
  profileActionBusy.value = `activate-${report.id}`
  try {
    const data = await activateLearningProfile(report.id)
    const profile = data?.profile || report
    replaceProfile(profile)
    notifyLearningPathProfileSwitched(profile)
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
  if (!report.isActive && !await requestProfileSwitchConfirmation(report)) return
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
    dispatchXiaoZhiProfileContextChanged({ id: 0, profileName: '待创建画像', version: 1 })
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
  dispatchXiaoZhiProfileContextChanged(profile)
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

async function deleteProfileVersion(report) {
  if (!report?.id || profileActionBusy.value) return
  const profileName = report.profileName || '学习画像'
  const activeNotice = report.isActive
    ? '删除后将自动切换到最近一份剩余画像。'
    : ''
  const confirmed = window.confirm(
    `确定删除“${profileName}”吗？${activeNotice}\n该画像的专属路径、效果评估和智能体协作记录也会删除，已生成的学习资源仍会保留。`,
  )
  if (!confirmed) return

  profileActionBusy.value = `delete-${report.id}`
  try {
    const data = await deleteLearningProfile(report.id)
    resetReportPortraitView()
    if (viewingHistory.value?.id === report.id) viewingHistory.value = null
    if (activeChatReport.value?.id === report.id) activeChatReport.value = null
    profileSessions.value = profileSessions.value.map(session => (
      Number(session.reportId) === Number(report.id)
        ? { ...session, reportId: null }
        : session
    ))
    if (data?.activeProfile) {
      replaceProfile(data.activeProfile)
      if (report.isActive) notifyLearningPathProfileSwitched(data.activeProfile)
    } else if (report.isActive) {
      clearProfileCache()
      dispatchXiaoZhiProfileContextChanged({ id: 0, profileName: '待创建画像', version: 1 })
    }
    await loadHistoryReports()
    showToast(data?.activeProfile
      ? `已删除 ${profileName}，当前切换为 ${data.activeProfile.profileName || '学习画像'}`
      : `已删除 ${profileName}`)
  } catch (error) {
    showToast(error?.response?.data?.msg || error?.message || '删除画像失败')
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

const portraitBuildProgress = computed(() => {
  const result = {}
  profileDimensionKeys.forEach((key) => {
    result[key] = isProfileDimensionFilled(chatStudentProfile.value[key]) ? 1 : 0
  })
  return result
})

function portraitStrength(group) {
  return portraitBuildProgress.value[group] ?? 0.12
}

const FACE_ASSET_BASE = '/learning-face-cropped-split'
// Bust stale browser caches after replacing a previously incomplete static asset set.
const FACE_ASSET_VERSION = '20260825'
const FACE_CANVAS_FALLBACK = { width: 832, height: 1078 }
const profileFaceManifest = ref(null)
const profileFaceBaseSrc = `${FACE_ASSET_BASE}/face-cropped-dots-transparent.png?v=${FACE_ASSET_VERSION}`

function hideMissingProfileFaceAsset(event) {
  event.currentTarget.hidden = true
}

const faceBlockGroups = {
  forehead_top: '专业/课程背景',
  forehead_left: '学习目标',
  forehead_right: '当前知识基础',
  forehead_center: '学习进度',
  left_brow: '薄弱知识点',
  right_brow: '易错点类型',
  left_eye: '薄弱知识点',
  right_eye: '易错点类型',
  nose_bridge: '资源形式偏好',
  nose_tip: '资源形式偏好',
  left_ear: '学习风格/认知偏好',
  right_ear: '难度接受程度',
  left_cheek: '学习风格/认知偏好',
  right_cheek: '难度接受程度',
  mouth: '学习风格/认知偏好',
  left_jaw: '可投入时间',
  right_jaw: '可投入时间',
  chin: '难度接受程度',
}

const faceDimensionPrimaryBlocks = {
  '专业/课程背景': 'forehead_top',
  '学习目标': 'forehead_left',
  '当前知识基础': 'forehead_right',
  '学习进度': 'forehead_center',
  '薄弱知识点': 'left_eye',
  '易错点类型': 'right_eye',
  '学习风格/认知偏好': 'left_cheek',
  '资源形式偏好': 'nose_bridge',
  '可投入时间': 'left_jaw',
  '难度接受程度': 'right_cheek',
}

async function loadProfileFaceManifest() {
  try {
    const response = await fetch(`${FACE_ASSET_BASE}/manifest.json?v=${FACE_ASSET_VERSION}`, { cache: 'no-store' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const manifest = await response.json()
    if (!manifest?.crop?.width || !manifest?.crop?.height || !Array.isArray(manifest.blocks)) {
      throw new Error('invalid face manifest')
    }
    profileFaceManifest.value = manifest
  } catch (error) {
    profileFaceManifest.value = null
    addLog({ error: String(error) }, 'warn', '学习画像点阵人脸')
  }
}

const profileFaceCanvas = computed(() => ({
  width: Number(profileFaceManifest.value?.crop?.width) || FACE_CANVAS_FALLBACK.width,
  height: Number(profileFaceManifest.value?.crop?.height) || FACE_CANVAS_FALLBACK.height,
}))

const profileFaceStageStyle = computed(() => ({
  '--face-ratio': `${profileFaceCanvas.value.width} / ${profileFaceCanvas.value.height}`,
}))

const profileFaceSegments = computed(() => {
  const blocks = Array.isArray(profileFaceManifest.value?.blocks) ? profileFaceManifest.value.blocks : []
  const { width, height } = profileFaceCanvas.value
  return blocks.map((block) => {
    const group = faceBlockGroups[block.id] || 'chat'
    const strength = portraitStrength(group)
    const active = strength > 0.82
    const opacity = active ? 0.92 : 0.18 + strength * 0.5
    const scale = 0.985 + strength * 0.015
    const filter = active
      ? `drop-shadow(0 0 ${5 + strength * 6}px rgba(32, 36, 36, ${0.08 + strength * 0.12}))`
      : 'drop-shadow(0 0 4px rgba(32, 36, 36, 0.08))'
    return {
      id: block.id,
      src: `${FACE_ASSET_BASE}/${block.file}?v=${FACE_ASSET_VERSION}`,
      active,
      style: {
        left: `${(Number(block.x) || 0) / width * 100}%`,
        top: `${(Number(block.y) || 0) / height * 100}%`,
        width: `${(Number(block.width) || 1) / width * 100}%`,
        height: `${(Number(block.height) || 1) / height * 100}%`,
        opacity,
        transform: `scale(${scale})`,
        filter,
        '--segment-delay': `${Math.max(0, (Number(block.index) || 1) - 1) * 28}ms`,
        '--target-opacity': opacity,
        '--segment-progress': strength,
      },
    }
  })
})

const FACE_LINK_CANVAS = { width: 430, height: 430, faceWidth: 218, faceTop: 44 }

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
  const blocks = Array.isArray(profileFaceManifest.value?.blocks) ? profileFaceManifest.value.blocks : []
  const primaryBlock = blocks.find(block => block.id === faceDimensionPrimaryBlocks[name])
  const faceWidth = FACE_LINK_CANVAS.faceWidth
  const faceHeight = faceWidth * profileFaceCanvas.value.height / profileFaceCanvas.value.width
  const faceLeft = (FACE_LINK_CANVAS.width - faceWidth) / 2
  const faceTop = FACE_LINK_CANVAS.faceTop
  const centroid = primaryBlock?.centroid || {
    x: profileFaceCanvas.value.width / 2,
    y: profileFaceCanvas.value.height / 2,
  }
  const anchorX = faceLeft + Number(centroid.x || 0) / profileFaceCanvas.value.width * faceWidth
  const anchorY = faceTop + Number(centroid.y || 0) / profileFaceCanvas.value.height * faceHeight
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
  const faceHeight = faceWidth * profileFaceCanvas.value.height / profileFaceCanvas.value.width
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
const reportPortraitLoadingLabel = computed(() => (
  currentReport.value?.portrait?.status === 'generating'
    ? ''
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
  return ['中医基础巩固', '辨证思路复盘', '医案任务拆解']
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
  const background = reportProfileField('专业/课程背景', '中医方向')
  if (/诊断|四诊|辨证/.test(background)) return '中医诊断学习'
  if (/中药|方剂/.test(background)) return '中药方剂学习'
  return compactReportText(background, 14)
})

const reportMainTitle = computed(() => {
  const direction = /诊断/.test(reportDirectionLabel.value)
    ? '中医诊断方向'
    : reportDirectionLabel.value.replace(/学习/g, '')
  return `中医学习画像（${direction}）`
})

const reportGrowthSteps = [
  { label: '入门探索', icon: Search },
  { label: '知识构建', icon: Cpu },
  { label: '项目实践', icon: Boxes },
  { label: '能力进阶', icon: Rocket },
]

const reportSummaryCards = computed(() => {
  const style = currentReport.value?.aiAnalysis?.learningStyle || '实践导向型'
  const knowledge = reportProfileField('当前知识基础', '具备中医入门基础')
  const weakPoints = reportFocusTags.value
  const timeBudget = reportProfileField('可投入时间', '每周 6-10 小时')
  const difficulty = reportProfileField('难度接受程度', '适中偏挑战')
  return [
    { label: '画像总结', title: '重辨证 · 强关联', detail: '整体思维导向 · 注重医案应用', icon: UserRound },
    { label: '学习风格', title: compactReportText(style, 11), detail: '案例辨析为主 · 任务驱动学习', icon: BrainCircuit },
    { label: '当前知识基础', title: compactReportText(knowledge, 11), detail: compactReportText(knowledge, 24), icon: Cpu },
    { label: '薄弱知识点', title: compactReportText(weakPoints[0] || '待诊断', 10), detail: compactReportText(weakPoints.slice(1, 3).join('、') || '持续结合学习证据更新', 24), icon: TriangleAlert },
    { label: '每周时间预算', title: compactReportText(timeBudget, 11), detail: '按可投入时间动态安排任务密度', icon: Clock4 },
    { label: '难度偏好', title: compactReportText(difficulty, 10), detail: '在基础巩固后逐步提升挑战', icon: SlidersHorizontal },
  ]
})

const reportAbilityBlueprint = [
  { label: '方药应用能力', icon: Hand, scoreIndex: 2 },
  { label: '辨证思维能力', icon: BrainCircuit, scoreIndex: 0 },
  { label: '医案分析能力', icon: Wrench, scoreIndex: 5 },
  { label: '新知识吸收能力', icon: BookOpen, scoreIndex: 4 },
  { label: '整体观念能力', icon: Boxes, scoreIndex: 3 },
  { label: '四诊信息归纳', icon: Code2, scoreIndex: 1 },
  { label: '证候鉴别能力', icon: Bug, scoreIndex: 1 },
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
    : ['基础概念关联较好，愿意结合医案理解', '学习主动，愿意查阅教材与经典', '具备一定整体观念与辨证意识']
})

const reportWeaknesses = computed(() => {
  const weaknesses = currentReport.value?.aiAnalysis?.weaknesses
  return Array.isArray(weaknesses) && weaknesses.length
    ? weaknesses.slice(0, 4)
    : ['四诊信息归纳还不够完整', '相似证候鉴别仍需巩固', '方药配伍与医案迁移需加强']
})

const reportPreferenceRows = computed(() => [
  { label: '学习目标', value: reportProfileField('学习目标', '掌握中医基础理论，形成完整的辨证论治思路'), icon: Target },
  { label: '资源偏好', value: reportProfileField('资源形式偏好', '医案解析、课程讲义、视频教程与方药对比表'), icon: Library },
  { label: '学习风格', value: reportProfileField('学习风格/认知偏好', currentReport.value?.aiAnalysis?.learningStyle || '辨证导向、案例驱动'), icon: UserRound },
])

const reportPlanRows = computed(() => {
  const recommendations = Array.isArray(currentReport.value?.aiAnalysis?.recommendations)
    ? currentReport.value.aiAnalysis.recommendations
    : []
  const fallback = [
    '以医案为主线，结合基础理论与经典条文，逐步构建完整的辨证知识体系。',
    '重点突破当前薄弱知识点，并通过专项练习形成可验证的掌握证据。',
    '优先选择典型医案与方药对比，辅以教材和经典医籍精读，建立知识闭环。',
    '每阶段完成一个完整医案辨析，注重证据链与鉴别要点，积累可迁移经验。',
    '掌握基础辨证后，尝试复杂证候与多病机医案，逐步提升临床思维。',
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

async function callAIAnalysis(profileOverride = null) {
  const override = profileOverride && typeof profileOverride === 'object' ? profileOverride : null
  const studentProfile = override?.dimensions || chatStudentProfile.value
  const payload = {
    scaleScores: override?.scaleScores || profileData.value.scaleScores,
    scaleTimestamp: override ? Date.now() : profileData.value.scaleTimestamp,
    chatBackground: override?.summary || profileData.value.chatBackground,
    chatTimestamp: override ? Date.now() : profileData.value.chatTimestamp,
    chatStudentProfile: studentProfile,
    completedProfileDimensions: profileDimensionKeys.filter(key => isProfileDimensionFilled(studentProfile[key])),
    missingProfileDimensions: profileDimensionKeys.filter(key => !isProfileDimensionFilled(studentProfile[key])),
    uploadFiles: profileData.value.uploadFiles || [],
    uploadTimestamp: profileData.value.uploadTimestamp,
    scaleQuestions: scaleQuestions.map(q => ({ text: q.text, short: q.short })),
  }
  let report = null
  const workflowId = `learning-profile-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  analysisStreamEvents.value = []
  analysisStreamMessage.value = '画像分析智能体启动中...'
  analysisStreamStartedAt.value = Date.now()
  dispatchXiaoZhiWorkflowProgress({
    workflow: 'learning-profile',
    workflowId,
    stage: 'load_context',
    status: 'running',
    message: '学情诊断 Agent 正在汇总十维画像证据',
  })

  try {
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
      dispatchXiaoZhiWorkflowProgress({
        workflow: 'learning-profile',
        workflowId,
        stage: streamEvent.stage || event,
        status: streamEvent.status,
        progress: streamEvent.progress,
        message: streamEvent.message,
        task: data?.learningPathTask || null,
      })
      addLog({ event, data }, event === 'error' ? 'error' : 'info', '学习画像分析')
      await nextTick()
      if (analysisLogRef.value) {
        analysisLogRef.value.scrollTop = analysisLogRef.value.scrollHeight
      }
      if (event === 'result' && data?.report) {
        report = data?.learningPathTask
          ? { ...data.report, learningPathTask: data.learningPathTask }
          : data.report
      }
      if (event === 'error') {
        throw new Error(data?.detail || data?.message || data?.error || 'AI analysis failed')
      }
    })
  } catch (error) {
    dispatchXiaoZhiWorkflowProgress({
      workflow: 'learning-profile',
      workflowId,
      stage: 'error',
      status: 'failed',
      progress: 100,
      message: error?.message || '学习画像多智能体分析失败',
    })
    throw error
  }

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
  { text: '中医基础知识掌握情况', short: '基础知识' },
  { text: '辨证与临床思维能力', short: '辨证思维' },
  { text: '中药与方剂应用能力', short: '方药应用' },
  { text: '医案实践能力', short: '医案实践' },
  { text: '学习习惯与学习投入', short: '学习投入' },
  { text: '综合应用与人文素养', short: '综合素养' },
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
    lower(base + (/基础|阴阳|藏象|经络/.test(String(student['当前知识基础'] || '')) ? 0.25 : 0)),
    lower(base - (/辨证|四诊|舌象|脉象/.test(weakText) ? 0.45 : 0) + 0.1),
    lower(base - (/中药|方剂|配伍/.test(weakText) ? 0.25 : 0) + (/医案|实践/.test(goalText) ? 0.2 : 0)),
    lower(base + (/医案|竞赛|课程学习/.test(goalText) ? 0.35 : 0)),
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

    if (!reply.trim() && !agentResult) throw new Error('学习背景对话流未返回可显示内容')
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
  activeChatReport.value = historyReports.value.find((report) => Number(report.id) === Number(session.reportId)) || null
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
    const botMessage = {
      id: createChatMessageId('bot'),
      role: 'bot',
      text: '',
      timestamp: Date.now(),
      source: 'llm-streaming',
    }
    try {
      chatMsgs.value.push(botMessage)
      chatStreaming.value = true
      let result = null
      let reply = ''
      const controller = new AbortController()
      const timeoutId = window.setTimeout(() => controller.abort(), LLM_CHAT_TIMEOUT_MS)
      try {
        await streamLearningProfileSessionMessage(activeProfileSessionId.value, msg, attachments, async ({ event, data }) => {
          const source = data?.source || data?.data?.workflow?.source || 'pending'
          addLog({ event, source, data }, event === 'error' ? 'error' : 'info', '学习画像会话')
          if (event === 'delta' && data?.text) {
            reply += String(data.text)
            setChatBotMessage(botMessage, reply, 'llm')
            await scrollChatToBottom()
            return
          }
          if (event === 'result') {
            result = data?.data || data || {}
            const workflowReply = String(result?.workflow?.reply || result?.workflow?.question || '').trim()
            if (workflowReply && !reply.trim()) {
              reply = workflowReply
              setChatBotMessage(botMessage, reply, 'llm')
              await scrollChatToBottom()
            }
            return
          }
          if (event === 'error') {
            throw new Error(data?.message || data?.error || '学习画像智能体调用失败')
          }
        }, { signal: controller.signal })
      } finally {
        window.clearTimeout(timeoutId)
      }
      if (!result) throw new Error('学习画像会话流未返回结果')
      const workflow = result?.workflow || {}
      updatePortraitFromAgent(workflow, String(workflow.reply || workflow.question || ''))
      if (result?.report) {
        await loadHistoryReports()
        if (result?.learningPathTask?.taskId) {
          dispatchXiaoZhiWorkflowProgress({
            workflow: 'learning-path',
            workflowId: `learning-profile-session-${activeProfileSessionId.value || Date.now()}`,
            task: result.learningPathTask,
          })
        }
        const pathTaskStatus = String(result?.learningPathTask?.status || '')
        showToast(
          ['queued', 'running'].includes(pathTaskStatus)
            ? '十个画像维度已补齐，学习路径已在后台开始生成'
            : '十个画像维度已补齐，完整学习画像报告已生成',
        )
      }
      if (result?.session) applyProfileSession(result.session)
      await scrollChatToBottom()
    } catch (error) {
      addLog(error, 'error', '学习画像会话对话')
      const modelUnavailable = error?.response?.data?.errorCode === 'MODEL_UNAVAILABLE' || /大模型不可用|MODEL_UNAVAILABLE/.test(String(error?.message || ''))
      const errorText = modelUnavailable
        ? '学习画像大模型不可用，请稍后重试。'
        : (error?.response?.data?.msg || error?.message || '学习画像对话失败')
      setChatBotMessage(botMessage, errorText, 'error')
      showToast(errorText)
      await scrollChatToBottom()
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
    const errorText = `学习画像智能体调用失败：${error?.message || '未知错误'}`
    setChatBotMessage(botMessage, errorText, 'error')
    persistChatState({ chatBackground: getCurrentChatBackground(), chatTimestamp: Date.now() })
    chatLoading.value = false
    chatStreaming.value = false
    showToast('学习画像智能体调用失败')

    scrollChatToBottom()
  }
  settleTransientBotMessage(botMessage, '学习画像智能体未返回内容，请稍后重试。')
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

async function fillDeveloperProfile() {
  if (developerActionBusy.value) return
  const fixture = createLearningProfileDeveloperFixture()
  developerActionBusy.value = true
  aiAnalyzing.value = true
  try {
    const report = await callAIAnalysis(fixture)
    activeChatReport.value = null
    viewingHistory.value = null
    chatMsgs.value = fixture.messages
    chatHistory.value = fixture.chatHistory
    profileChatAttachments.value = []
    replaceProfile({
      ...report,
      chatMessages: fixture.messages,
      chatHistory: fixture.chatHistory,
    })
    historyReports.value = [report, ...historyReports.value.filter(item => item.id !== report.id)]
    activeMenu.value = 'assess'
    activeOrb.value = null
    closeDeveloperPanel()
    const pathPending = ['queued', 'running'].includes(String(report?.learningPathTask?.status || ''))
    showToast(pathPending ? '学习画像已激活，学习路径正在生成' : '学习画像已写入并激活')
    nextTick(() => scrollChatToBottom({ retry: true }))
  } catch (error) {
    showToast(error?.response?.data?.msg || error?.message || '测试画像写入失败')
  } finally {
    aiAnalyzing.value = false
    developerActionBusy.value = false
  }
}

async function clearDeveloperProfile() {
  if (developerActionBusy.value) return
  if (!developerClearArmed.value) {
    developerClearArmed.value = true
    window.clearTimeout(developerClearTimer)
    developerClearTimer = window.setTimeout(() => {
      developerClearArmed.value = false
    }, 4000)
    return
  }

  developerActionBusy.value = true
  window.clearTimeout(developerClearTimer)
  try {
    await resetLearningProfile()
    try {
      await resetLearningProfileBackgroundChat()
    } catch (error) {
      addLog(error, 'error', '开发工具清理学习画像对话')
    }
    clearProfileCache()
    activeChatReport.value = null
    Object.keys(scaleAnswers).forEach(key => delete scaleAnswers[key])
    uploadFiles.value = []
    profileChatAttachments.value = []
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
    closeDeveloperPanel()
    showToast('当前学习画像信息已清除')
  } catch (error) {
    developerClearArmed.value = false
    showToast(error?.response?.data?.msg || error?.message || '学习画像清除失败')
  } finally {
    developerActionBusy.value = false
  }
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

let learningProfileActivatedOnce = false

// 重新打开时恢复已保存的量表答案
onMounted(() => {
  window.addEventListener('keydown', handleDeveloperShortcut)
  applyRouteQuery()
  loadHistoryReports()
  initializeProfileSessions().catch((error) => addLog(error, 'error', '初始化学习画像会话'))
  loadProfileFaceManifest()
  const saved = profileData.value.scaleScores
  if (saved) {
    saved.forEach((v, i) => { scaleAnswers[i] = v })
  }
  startLearningAvatar({ replayLatest: activeMenu.value === 'assess' })
  if (activeMenu.value === 'assess') {
    ensureInitialChatQuestion()
    scrollChatToBottom({ retry: true })
  }
})

onActivated(() => {
  window.addEventListener('keydown', handleDeveloperShortcut)
  if (learningProfileActivatedOnce) {
    startLearningAvatar({ replayLatest: false })
    if (activeMenu.value === 'assess') scrollChatToBottom({ retry: true })
  }
  learningProfileActivatedOnce = true
})

onDeactivated(() => {
  window.removeEventListener('keydown', handleDeveloperShortcut)
  digitalHumanRef.value?.destroyAvatar?.()
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
  window.removeEventListener('keydown', handleDeveloperShortcut)
  window.clearTimeout(developerClearTimer)
  resetReportPortraitView()
  digitalHumanRef.value?.destroyAvatar?.()
})
</script>

<style scoped src="../styles/learning-profile-view.css"></style>

<style src="../styles/learning-profile-view.global.css"></style>
