<template>
  <main class="auth-landing-page">
    <div class="auth-scroll-progress" :style="{ transform: `scaleX(${scrollProgress})` }" aria-hidden="true"></div>

    <header class="auth-landing-nav">
      <a class="auth-landing-brand" href="#top" aria-label="嵌智学航首页">
        <img src="/logo.png" alt="嵌智学航" />
      </a>

      <nav class="auth-landing-links" aria-label="产品能力">
        <a href="#capabilities">核心能力</a>
        <a href="#model-capabilities">模型能力</a>
        <a href="#innovation">创新展示</a>
        <a href="#workflow">学习闭环</a>
        <a href="#resources-capability">多模态资源</a>
        <a href="#assessment-capability">效果评估</a>
      </nav>

      <div class="auth-landing-actions">
        <button type="button" class="auth-login-link" @click="openAuth('login')">登录</button>
        <button type="button" class="auth-register-button" @click="openAuth('register')">注册</button>
      </div>
    </header>

    <section id="top" class="auth-landing-hero">
      <div class="auth-hero-copy">
        <span class="auth-hero-kicker">
          <Cpu :size="15" :stroke-width="2" />
          Agent Harness 架构 · 22 个已实现角色
        </span>
        <h1>
          <strong>嵌智学航</strong>
          <span>让每一步学习都有依据</span>
        </h1>
        <p>从学习画像到周路径、资源、实验与效果评估，让智能体围绕真实学习证据持续编排。</p>

        <ul class="auth-hero-points" aria-label="平台特点">
          <li><CheckCircle2 :size="16" />画像驱动</li>
          <li><CheckCircle2 :size="16" />智能编排</li>
          <li><CheckCircle2 :size="16" />多模态资源</li>
        </ul>

        <div class="auth-hero-actions">
          <button type="button" class="auth-start-button" @click="openAuth('login')">
            开始学习
            <ArrowRight :size="17" />
          </button>
          <a href="#capabilities" class="auth-outline-link">查看能力</a>
        </div>
      </div>

      <div class="auth-hero-gallery" aria-label="嵌入式学习场景">
        <figure class="auth-gallery-main" :style="heroVisualStyle">
          <picture>
            <source srcset="/auth-hero-embedded-collage.webp" type="image/webp" />
            <img src="/auth-hero-embedded-collage.png" alt="示波器、开发板、机器人与数字人组成的嵌入式学习场景" decoding="async" fetchpriority="high" />
          </picture>
        </figure>
        <figure class="auth-gallery-crop crop-scope" aria-hidden="true">
          <picture>
            <source srcset="/auth-capability-assessment.webp" type="image/webp" />
            <img src="/auth-capability-assessment.png" alt="" decoding="async" />
          </picture>
        </figure>
        <figure class="auth-gallery-crop crop-face" aria-hidden="true">
          <picture>
            <source srcset="/auth-capability-profile.webp" type="image/webp" />
            <img src="/auth-capability-profile.png" alt="" decoding="async" />
          </picture>
        </figure>
        <span class="auth-gallery-label label-live"><Activity :size="14" />实时学习证据</span>
        <span class="auth-gallery-label label-profile"><Network :size="14" />动态画像</span>
      </div>
    </section>

    <section class="auth-skill-band auth-reveal auth-stagger" aria-label="平台能力">
      <div><Network :size="23" /><span>动态学习画像</span></div>
      <div><Route :size="23" /><span>个性化周路径</span></div>
      <div><BookOpenCheck :size="23" /><span>多模态资源</span></div>
      <div><FlaskConical :size="23" /><span>嵌入式实验</span></div>
      <div><Gauge :size="23" /><span>学习效果评估</span></div>
    </section>

    <section id="model-capabilities" class="auth-model-section auth-reveal" aria-labelledby="model-capabilities-title">
      <div class="auth-section">
        <header class="auth-section-head compact">
          <div>
            <span class="auth-section-kicker">真实模型能力</span>
            <h2 id="model-capabilities-title">从主控推理到多模态生成</h2>
          </div>
        </header>

        <div class="auth-harness-architecture" aria-label="Agent Harness 多模型封装架构">
          <div class="auth-harness-title">
            <span><Cpu :size="18" />Agent Harness 多模型封装架构</span>
            <code>agent-harness-supervisor-blackboard</code>
          </div>
          <ol>
            <li>
              <span class="auth-harness-step-icon"><BrainCircuit :size="20" /></span>
              <div><b>Supervisor + 共享黑板</b><small>统一接收画像、任务与学习证据</small></div>
            </li>
            <li>
              <span class="auth-harness-step-icon"><Route :size="20" /></span>
              <div><b>模态感知模型路由</b><small>文本、图片、文档与生成任务按能力分流</small></div>
            </li>
            <li>
              <span class="auth-harness-step-icon"><PlugZap :size="20" /></span>
              <div><b>Skill + MCP + Handler</b><small>专业能力通过版本化契约调用真实执行器</small></div>
            </li>
            <li>
              <span class="auth-harness-step-icon"><ShieldCheck :size="20" /></span>
              <div><b>契约校验与审核回写</b><small>校验结构化输出，完成质量、安全与证据记录</small></div>
            </li>
          </ol>
        </div>

        <div class="auth-model-grid auth-stagger">
          <article style="--reveal-delay: 0ms; --model-accent: #087c60; --model-soft: #e7f5f0">
            <div class="auth-model-card-head">
              <span class="auth-model-icon"><BrainCircuit :size="22" /></span>
              <small class="auth-model-tag core">讯飞核心 · 主控</small>
            </div>
            <h3>讯飞星火 Spark X2 Agent</h3>
            <code>xsparkx2agent</code>
            <p>驱动 Supervisor、学习规划、资源编排、问答与评估等 Harness 推理链路。</p>
          </article>

          <article style="--reveal-delay: 70ms; --model-accent: #2563eb; --model-soft: #eaf1ff">
            <div class="auth-model-card-head">
              <span class="auth-model-icon"><Eye :size="22" /></span>
              <small class="auth-model-tag domestic">国产模型 · 视觉</small>
            </div>
            <h3>Kimi K2.6</h3>
            <code>xopkimik26</code>
            <p>解析图片和视觉证据，再把结构化结果交回 Spark X2 Agent 继续编排。</p>
          </article>

          <article style="--reveal-delay: 140ms; --model-accent: #7c3aed; --model-soft: #f2ebff">
            <div class="auth-model-card-head">
              <span class="auth-model-icon"><ImageIcon :size="22" /></span>
              <small class="auth-model-tag adapter">可插拔适配器 · 生图</small>
            </div>
            <h3>Image2 兼容图像模型</h3>
            <code>gpt-image-2 / gpt-image-2-ext</code>
            <p>学习画像插画与 AI 视频首帧复用同一类生成接口；模型 ID 由服务端配置，可替换为兼容图像模型。</p>
          </article>

          <article style="--reveal-delay: 210ms; --model-accent: #c2415d; --model-soft: #fbecef">
            <div class="auth-model-card-head">
              <span class="auth-model-icon"><Clapperboard :size="22" /></span>
              <small class="auth-model-tag domestic">国产模型 · 视频</small>
            </div>
            <h3>Seedance 视频模型</h3>
            <code>1.5 默认 · 2 Mini / 2 可选</code>
            <p>默认经 Coze 工作流调用 Seedance 1.5，也支持豆包 Seedance 2.0 Mini 与 2.0。</p>
          </article>

          <article style="--reveal-delay: 280ms; --model-accent: #a15c08; --model-soft: #fff3df">
            <div class="auth-model-card-head">
              <span class="auth-model-icon"><AudioLines :size="22" /></span>
              <small class="auth-model-tag adapter">讯飞 SDK + 音频适配器</small>
            </div>
            <h3>视频旁白与讯飞数字人 TTS</h3>
            <code>讯飞超拟人语音合成 · x4_yezi</code>
            <p>数字人播报由讯飞 SDK 提供；视频旁白通过可替换 TTS 适配器生成，x4_yezi 仅为配置音色。</p>
          </article>
        </div>
      </div>
    </section>

    <section id="capabilities" class="auth-section auth-capabilities-section auth-reveal">
      <header class="auth-section-head">
        <div>
          <span class="auth-section-kicker">核心能力</span>
          <h2>由学习画像驱动的学习工作台</h2>
          <p>每个模块共享当前画像、学习证据和任务状态，形成连续的个性化学习体验。</p>
        </div>
        <div class="auth-section-switch" aria-label="能力类别">
          <span class="active">学习规划</span>
          <span>资源生成</span>
          <span>实验评估</span>
        </div>
      </header>

      <div class="auth-capability-grid auth-stagger">
        <article id="profile-capability" class="auth-capability-card" style="--reveal-delay: 0ms">
          <figure class="auth-capability-media media-profile">
            <picture>
              <source srcset="/auth-capability-profile.webp" type="image/webp" />
              <img src="/auth-capability-profile.png" alt="点云数字人学习画像" loading="lazy" decoding="async" />
            </picture>
          </figure>
          <div class="auth-capability-copy">
            <span><Network :size="18" />学习画像</span>
            <h3>从对话和学习行为中持续更新</h3>
            <p>汇总聊天、做题、实验、资源访问和路径完成情况，形成可追溯的十维画像。</p>
          </div>
        </article>

        <article class="auth-capability-card" style="--reveal-delay: 90ms">
          <figure class="auth-capability-media media-path">
            <picture>
              <source srcset="/auth-capability-path.webp" type="image/webp" />
              <img src="/auth-capability-path.png" alt="嵌入式开发板与学习路径" loading="lazy" decoding="async" />
            </picture>
          </figure>
          <div class="auth-capability-copy">
            <span><Route :size="18" />学习路径</span>
            <h3>把目标拆成每周可执行任务</h3>
            <p>结合薄弱点、目标和可投入时间，编排周次地图；每周提供可验收任务与六类资源入口。</p>
          </div>
        </article>

        <article id="resources-capability" class="auth-capability-card" style="--reveal-delay: 180ms">
          <figure class="auth-capability-media media-resource">
            <picture>
              <source srcset="/auth-capability-resources.webp" type="image/webp" />
              <img src="/auth-capability-resources.png" alt="多模态学习资源生成工作台" loading="lazy" decoding="async" />
            </picture>
          </figure>
          <div class="auth-capability-copy">
            <span><BookOpenCheck :size="18" />个性化资源</span>
            <h3>任务参数直接进入生成工具</h3>
            <p>提供题库、PPT、思维导图、视频查找、单片机实验与 AI 视频讲解；AI 视频仅在用户确认后生成。</p>
          </div>
        </article>

        <article id="assessment-capability" class="auth-capability-card" style="--reveal-delay: 270ms">
          <figure class="auth-capability-media media-assessment">
            <picture>
              <source srcset="/auth-capability-assessment.webp" type="image/webp" />
              <img src="/auth-capability-assessment.png" alt="嵌入式实验与学习效果评估" loading="lazy" decoding="async" />
            </picture>
          </figure>
          <div class="auth-capability-copy">
            <span><Gauge :size="18" />效果评估</span>
            <h3>看见进步、薄弱点与下一步</h3>
            <p>用学习时长、资源轨迹、任务证据和雷达变化解释本轮学习效果。</p>
          </div>
        </article>
      </div>
    </section>

    <section id="innovation" class="auth-innovation-section auth-reveal">
      <header class="auth-section-head compact">
        <div>
          <span class="auth-section-kicker">创新可视化</span>
          <h2>看见知识关联与持续演化</h2>
        </div>
        <p>展示数据来自课程知识索引、真实引用记录与审核反哺过程。</p>
      </header>
      <div class="auth-innovation-grid auth-stagger">
        <article style="--reveal-delay: 0ms">
          <div class="innovation-preview knowledge-preview">
            <img src="/auth-knowledge-network.jpg" alt="嵌智学航真实知识网络页面" loading="lazy" decoding="async" />
            <span class="knowledge-preview-badge">真实知识网络</span>
          </div>
          <div class="innovation-copy">
            <span><Network :size="17" />可审计知识网络</span>
            <h3>Obsidian 风格浏览来源、引用和审核反哺</h3>
            <button type="button" @click="openAuthForRoute('/knowledge-network')">进入知识网络<ArrowRight :size="16" /></button>
          </div>
        </article>
      </div>
    </section>

    <section id="workflow" class="auth-flow-section auth-reveal">
      <div class="auth-section auth-flow-inner">
        <header class="auth-section-head compact">
          <div>
            <span class="auth-section-kicker">学习闭环</span>
            <h2>从一次对话，到持续更新</h2>
          </div>
          <p>嵌小智统一编排画像、路径、资源与评估，任务执行状态全程可见。</p>
        </header>

        <div class="auth-flow-track auth-stagger">
          <article style="--reveal-delay: 0ms; --flow-color: #147a78; --flow-soft: #e6f4f2">
            <div class="auth-flow-step-head">
              <span class="auth-flow-icon"><BrainCircuit :size="24" /></span>
              <b>01</b>
            </div>
            <h3>理解学习者</h3>
            <p>对话与多模态材料进入学习画像。</p>
            <ArrowRight class="auth-flow-arrow" :size="18" aria-hidden="true" />
          </article>
          <article style="--reveal-delay: 100ms; --flow-color: #2563eb; --flow-soft: #eaf1ff">
            <div class="auth-flow-step-head">
              <span class="auth-flow-icon"><Route :size="24" /></span>
              <b>02</b>
            </div>
            <h3>编排周路径</h3>
            <p>目标、时间和薄弱点转为每周任务。</p>
            <ArrowRight class="auth-flow-arrow" :size="18" aria-hidden="true" />
          </article>
          <article style="--reveal-delay: 200ms; --flow-color: #7c3aed; --flow-soft: #f1eaff">
            <div class="auth-flow-step-head">
              <span class="auth-flow-icon"><Layers3 :size="24" /></span>
              <b>03</b>
            </div>
            <h3>生成与实践</h3>
            <p>资源和实验按任务状态准备，AI 视频在用户确认后进入后台生成。</p>
            <ArrowRight class="auth-flow-arrow" :size="18" aria-hidden="true" />
          </article>
          <article style="--reveal-delay: 300ms; --flow-color: #c2415d; --flow-soft: #fbecef">
            <div class="auth-flow-step-head">
              <span class="auth-flow-icon"><BarChart3 :size="24" /></span>
              <b>04</b>
            </div>
            <h3>评估再更新</h3>
            <p>学习证据反馈到画像和下一阶段。</p>
          </article>
        </div>
      </div>
    </section>

    <section class="auth-bonus-section auth-reveal" aria-labelledby="bonus-capabilities-title">
      <header class="auth-section-head compact">
        <div>
          <span class="auth-section-kicker">赛题加分能力</span>
          <h2 id="bonus-capabilities-title">从生成到验证的 AI 学习工程</h2>
        </div>
        <p>以可追溯的学习证据连接知识、智能体、资源与实验。</p>
      </header>
      <div class="auth-bonus-grid auth-stagger">
        <article style="--reveal-delay: 0ms">
          <Cpu :size="20" :stroke-width="2" />
          <div><strong>讯飞能力适配</strong><span>模型、语音与数字人能力接口</span></div>
        </article>
        <article style="--reveal-delay: 70ms">
          <Clapperboard :size="20" :stroke-width="2" />
          <div><strong>多模态资源生成</strong><span>题单、PPT、导图、视频与实验</span></div>
        </article>
        <article style="--reveal-delay: 140ms">
          <Database :size="20" :stroke-width="2" />
          <div><strong>私有知识库</strong><span>课程检索、引用溯源与待验证标记</span></div>
        </article>
        <article style="--reveal-delay: 210ms">
          <ShieldCheck :size="20" :stroke-width="2" />
          <div><strong>防幻觉与安全</strong><span>结构校验、内容审核与账户隔离</span></div>
        </article>
        <article style="--reveal-delay: 280ms">
          <Bot :size="20" :stroke-width="2" />
          <div><strong>可编排智能体</strong><span>Harness、Skill 与 MCP 协同调度</span></div>
        </article>
        <article style="--reveal-delay: 350ms">
          <PlugZap :size="20" :stroke-width="2" />
          <div><strong>开放调用接口</strong><span>资源任务支持智能体与页面复用</span></div>
        </article>
        <article style="--reveal-delay: 420ms">
          <Cable :size="20" :stroke-width="2" />
          <div><strong>软硬件融合实验</strong><span>Arduino、8051 仿真与实操证据</span></div>
        </article>
        <article style="--reveal-delay: 490ms">
          <BrainCircuit :size="20" :stroke-width="2" />
          <div><strong>辅导与动态评估</strong><span>学习辅导、画像更新与路径调整</span></div>
        </article>
        <article style="--reveal-delay: 560ms">
          <FileCode2 :size="20" :stroke-width="2" />
          <div><strong>AI Coding 工程化</strong><span>需求、测试与可复现构建记录</span></div>
        </article>
        <article style="--reveal-delay: 630ms">
          <ServerCog :size="20" :stroke-width="2" />
          <div><strong>国产化能力适配</strong><span>国产模型路由与本地数据持久化</span></div>
        </article>
      </div>
    </section>

    <section class="auth-proof-section auth-reveal auth-stagger" aria-label="平台实证数据">
      <div>
        <strong>6,223</strong>
        <span>私有知识文档</span>
        <small>覆盖嵌入式课程与实践</small>
      </div>
      <div>
        <strong>22</strong>
        <span>Harness 已实现角色</span>
        <small>1 总控 + 18 专业 + 3 运行时</small>
      </div>
      <div>
        <strong>18</strong>
        <span>可调用 Harness Skill</span>
        <small>以 Manifest 实际注册为准</small>
      </div>
      <div>
        <strong>10</strong>
        <span>动态画像维度</span>
        <small>学习证据持续更新</small>
      </div>
    </section>

    <section class="auth-final-section auth-reveal auth-stagger">
      <div>
        <span class="auth-section-kicker">开始学习</span>
        <h2>建立属于你的嵌入式学习闭环</h2>
        <p>登录后，嵌小智会从当前画像继续，而不是从头开始。</p>
      </div>
      <div class="auth-final-actions">
        <button type="button" class="auth-start-button" @click="openAuth('login')">
          登录平台
          <ArrowRight :size="17" />
        </button>
        <button type="button" class="auth-register-secondary" @click="openAuth('register')">创建账号</button>
      </div>
    </section>

    <footer class="auth-landing-footer">
      <div class="auth-footer-brand">
        <img src="/logo.png" alt="嵌智学航" />
        <span>嵌入式学习智能体平台</span>
      </div>
      <div class="auth-open-source" aria-label="开源项目与框架">
        <span>开源项目与框架</span>
        <div>
          <a href="https://vuejs.org/" target="_blank" rel="noreferrer">Vue 3</a>
          <a href="https://vite.dev/" target="_blank" rel="noreferrer">Vite</a>
          <a href="https://flask.palletsprojects.com/" target="_blank" rel="noreferrer">Flask</a>
          <a href="https://echarts.apache.org/" target="_blank" rel="noreferrer">ECharts</a>
          <a href="https://mermaid.js.org/" target="_blank" rel="noreferrer">Mermaid</a>
          <a href="https://lucide.dev/" target="_blank" rel="noreferrer">Lucide</a>
          <a href="https://github.com/wokwi/wokwi-elements" target="_blank" rel="noreferrer">Wokwi Elements</a>
          <a href="https://ffmpeg.org/" target="_blank" rel="noreferrer">FFmpeg</a>
          <a href="https://github.com/LianjiaTech/oh-my-ppt" target="_blank" rel="noreferrer">OhMyPPT</a>
        </div>
      </div>
      <div class="auth-data-security">
        <ShieldCheck :size="15" :stroke-width="2" aria-hidden="true" />
        <span>数据安全：密码采用 bcrypt 单向哈希，会话凭据仅保存哈希；学习数据和文件按账户鉴权隔离。</span>
        <a class="auth-icp-record" href="https://beian.miit.gov.cn/" target="_blank" rel="noreferrer">赣ICP备2026009448号-1</a>
      </div>
    </footer>

  </main>

  <main
    v-if="authModalOpen"
    class="auth-page auth-modal-backdrop relative flex min-h-screen items-center justify-center overflow-x-hidden overflow-y-auto px-4 py-3 font-sans text-slate-800 sm:py-4"
    role="dialog"
    aria-modal="true"
    aria-label="登录或注册"
    @click.self="closeAuth"
  >
    <div class="pointer-events-none absolute inset-0 auth-page-gradient" aria-hidden="true"></div>
    <div class="pointer-events-none absolute left-0 top-0 h-full w-full opacity-75" aria-hidden="true">
      <svg class="absolute inset-0 h-full w-full" viewBox="0 0 1440 820" preserveAspectRatio="none">
        <g fill="none" stroke="rgba(20,184,166,0.16)" stroke-width="1.2">
          <path d="M0 170 120 222 246 128 432 228 612 178 748 312" />
          <path d="M42 555 216 490 318 640 468 575 616 690" />
          <path d="M1015 390 1128 455 1260 360 1394 440 1440 428" />
          <path d="M1078 690 1210 620 1324 720 1440 665" />
        </g>
        <g fill="rgba(16,185,129,0.24)">
          <circle cx="120" cy="222" r="5" />
          <circle cx="246" cy="128" r="6" />
          <circle cx="432" cy="228" r="4" />
          <circle cx="612" cy="178" r="8" />
          <circle cx="216" cy="490" r="6" />
          <circle cx="468" cy="575" r="5" />
          <circle cx="1128" cy="455" r="5" />
          <circle cx="1260" cy="360" r="4" />
          <circle cx="1394" cy="440" r="7" />
          <circle cx="1324" cy="720" r="5" />
        </g>
      </svg>
    </div>

    <div class="pointer-events-none absolute right-[11%] top-[44%] hidden -translate-y-1/2 opacity-70 lg:block" aria-hidden="true">
      <div class="relative h-72 w-72">
        <div class="absolute left-1/2 top-7 h-12 w-12 -translate-x-1/2 rounded-full bg-gradient-to-br from-brand-300 to-cyan-300 shadow-[0_20px_50px_rgba(16,185,129,0.25)]"></div>
        <div class="absolute left-1/2 top-28 h-28 w-36 -translate-x-1/2 rounded-b-[32px] rounded-t-md bg-gradient-to-br from-brand-200/85 via-brand-400/55 to-sky-300/75 shadow-[0_28px_70px_rgba(14,165,233,0.18)]"></div>
        <div class="absolute left-[84px] top-28 h-28 w-20 origin-bottom-right -skew-y-12 rounded-bl-[28px] rounded-tl-md bg-white/62 ring-1 ring-white/60"></div>
        <div class="absolute right-[84px] top-28 h-28 w-20 origin-bottom-left skew-y-12 rounded-br-[28px] rounded-tr-md bg-white/52 ring-1 ring-white/60"></div>
        <div class="absolute left-8 top-24 h-36 w-56 rounded-[50%] border border-brand-300/45"></div>
      </div>
    </div>

    <section
      class="auth-modal-panel relative z-10 w-full max-w-[540px] rounded-[24px] border border-white/70 bg-white/70 px-6 shadow-auth backdrop-blur-2xl sm:px-7"
      :class="activeTab === 'register' ? 'auth-card-register py-3' : 'py-7'"
    >
      <button type="button" class="auth-modal-close" aria-label="关闭登录窗口" @click="closeAuth">
        <X :size="20" />
      </button>
      <header class="text-center" :class="activeTab === 'register' ? 'mb-2' : 'mb-6'">
        <div class="mx-auto mb-1.5 flex items-center justify-center gap-3">
          <div class="relative grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-brand-50 to-white text-brand-600 shadow-[0_14px_30px_rgba(16,185,129,0.14)] ring-1 ring-brand-100">
            <Cpu class="absolute -right-1.5 -top-1.5 text-brand-400" :size="18" />
            <GraduationCap :size="28" stroke-width="1.9" />
          </div>
          <div class="text-left">
            <h1 class="text-[28px] font-extrabold leading-tight tracking-[0] text-brand-600">嵌智学航</h1>
            <p class="mt-0.5 text-xs font-medium tracking-[0.12em] text-slate-400">智能学习 · 智慧未来</p>
          </div>
        </div>
      </header>

      <RoleSelector v-model="role" :class="activeTab === 'register' ? 'mb-2.5' : 'mb-6'" />
      <TabSwitch v-model="activeTab" :class="activeTab === 'register' ? 'mb-2.5' : 'mb-5'" />

      <Transition name="auth-panel" mode="out-in">
        <LoginForm
          v-if="activeTab === 'login'"
          key="login"
          :form="loginForm"
          :loading="authLoading"
          :message="authMessage"
          :error="authError"
          :captcha-required="captchaRequired"
          :captcha-question="captchaQuestion"
          @submit="submitLogin"
        />
        <RegisterForm
          v-else
          key="register"
          :form="registerForm"
          :loading="authLoading"
          :message="authMessage"
          :error="authError"
          :email-valid="isRegisterEmailValid"
          :email-code-sending="emailCodeSending"
          :email-code-countdown="emailCodeCountdown"
          :password-strength="passwordStrength"
          @submit="submitRegister"
          @send-email-code="sendEmailCode"
        />
      </Transition>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Activity,
  AudioLines,
  ArrowRight,
  BarChart3,
  Bot,
  BookOpenCheck,
  BrainCircuit,
  Cable,
  CheckCircle2,
  Clapperboard,
  Cpu,
  Database,
  Eye,
  FileCode2,
  FlaskConical,
  Gauge,
  GraduationCap,
  Image as ImageIcon,
  Layers3,
  Network,
  PlugZap,
  Route,
  ServerCog,
  ShieldCheck,
  X,
} from 'lucide-vue-next'
import LoginForm from '../components/auth/LoginForm.vue'
import RegisterForm from '../components/auth/RegisterForm.vue'
import RoleSelector from '../components/auth/RoleSelector.vue'
import TabSwitch from '../components/auth/TabSwitch.vue'
import { getLoginCaptcha, loginAdminUser, loginUser, registerUser, sendRegisterEmailCode } from '../services/api.js'
import { readRememberedLoginAccount, rememberLoginAccount, setAuthSession } from '../stores/auth.js'
import { DEFAULT_AUTHENTICATED_PATH, safeInternalRedirect } from '../utils/authRedirect.js'

const router = useRouter()
const route = useRoute()

const activeTab = ref('login')
const authModalOpen = ref(false)
const role = ref(route.query.role === 'admin' ? 'admin' : 'user')
const authLoading = ref(false)
const authMessage = ref('')
const authError = ref(false)
const scrollProgress = ref(0)
const heroShift = ref(0)
const captchaRequired = ref(false)
const captchaId = ref('')
const captchaQuestion = ref('')
const pendingRoute = ref(safeInternalRedirect(route.query.redirect))
const emailCodeSending = ref(false)
const emailCodeCountdown = ref(0)
let emailCodeTimer = null
let landingScrollFrame = null
let revealObserver = null

const heroVisualStyle = computed(() => ({
  transform: `translate3d(0, ${heroShift.value}px, 0)`,
}))

const loginForm = reactive({
  username: readRememberedLoginAccount(),
  password: '',
  captchaAnswer: '',
})

const registerForm = reactive({
  username: '',
  displayName: '',
  email: '',
  emailCode: '',
  password: '',
  confirmPassword: '',
  acceptTerms: false,
})

const emailPattern = /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$/

const isRegisterEmailValid = computed(() => emailPattern.test(registerForm.email.trim()))

const passwordStrength = computed(() => {
  const password = registerForm.password || ''
  let score = 0
  if (password.length >= 8) score += 1
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1
  if (/\d/.test(password)) score += 1
  if (/[^A-Za-z0-9]/.test(password)) score += 1
  if (score >= 4) return { label: '强', level: 'strong' }
  if (score >= 2) return { label: '中', level: 'medium' }
  return { label: '弱', level: 'weak' }
})

watch([activeTab, role], () => {
  resetFeedback()
})

watch(authModalOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
})

function openAuth(tab = 'login') {
  activeTab.value = tab === 'register' ? 'register' : 'login'
  if (activeTab.value === 'login' && !loginForm.username) {
    loginForm.username = readRememberedLoginAccount()
  }
  authModalOpen.value = true
}

function openAuthForRoute(target) {
  pendingRoute.value = safeInternalRedirect(target)
  openAuth('login')
}

function closeAuth() {
  if (authLoading.value) return
  authModalOpen.value = false
}

function handleAuthKeydown(event) {
  if (event.key === 'Escape' && authModalOpen.value) closeAuth()
}

function updateLandingScrollState() {
  if (landingScrollFrame) cancelAnimationFrame(landingScrollFrame)
  landingScrollFrame = requestAnimationFrame(() => {
    const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight)
    scrollProgress.value = Math.min(1, Math.max(0, window.scrollY / maxScroll))
    heroShift.value = Math.min(48, window.scrollY * 0.08)
    landingScrollFrame = null
  })
}

function setupLandingReveals() {
  const elements = document.querySelectorAll('.auth-reveal')
  if (!('IntersectionObserver' in window)) {
    elements.forEach(element => element.classList.add('is-visible'))
    return
  }

  revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return
      entry.target.classList.add('is-visible')
      revealObserver?.unobserve(entry.target)
    })
  }, {
    threshold: 0.12,
    rootMargin: '0px 0px -8% 0px',
  })

  elements.forEach(element => revealObserver.observe(element))
}

onMounted(() => {
  document.documentElement.classList.add('auth-landing-scroll')
  document.body.classList.add('auth-landing-scroll')
  window.addEventListener('keydown', handleAuthKeydown)
  window.addEventListener('scroll', updateLandingScrollState, { passive: true })
  updateLandingScrollState()
  requestAnimationFrame(setupLandingReveals)
  if (pendingRoute.value) openAuth('login')
})

function getAdminBaseUrl() {
  if (import.meta.env.DEV) {
    const hostname = window.location.hostname || '127.0.0.1'
    return `${window.location.protocol}//${hostname}:9527`
  }
  return `${window.location.origin}/admin`
}

function getAdminHomeUrl(loginToken) {
  const token = loginToken?.token || ''
  const refreshToken = loginToken?.refreshToken || token
  if (!token) return `${getAdminBaseUrl()}/login`

  const params = new URLSearchParams({
    auth_token: token,
    refresh_token: refreshToken,
    redirect: '/dashboard',
  })

  return `${getAdminBaseUrl()}/dashboard#${params.toString()}`
}

function resetFeedback() {
  authMessage.value = ''
  authError.value = false
  captchaRequired.value = false
  captchaId.value = ''
  captchaQuestion.value = ''
  loginForm.captchaAnswer = ''
}

function setMessage(message, isError = true) {
  authMessage.value = message
  authError.value = isError
}

function validateAccount(value) {
  const account = value.trim()
  if (!account) return '请输入账号'
  if (account.includes('@')) {
    return emailPattern.test(account) ? '' : '请输入正确的邮箱地址'
  }
  if (!/^[A-Za-z0-9_@.\-\u4e00-\u9fa5]{3,32}$/.test(account)) {
    return '账号长度需为 3-32 位，可包含中文、字母、数字、下划线、点、@ 或短横线'
  }
  return ''
}

function validateLogin() {
  const accountError = validateAccount(loginForm.username)
  if (accountError) return accountError
  if (!loginForm.password || loginForm.password.length < 8) return '密码至少 8 位'
  if (captchaRequired.value && !loginForm.captchaAnswer) return '请输入验证码'
  return ''
}

function validateRegister() {
  const accountError = validateAccount(registerForm.username)
  if (accountError) return accountError
  if (!registerForm.displayName.trim()) return '请输入昵称'
  if (!isRegisterEmailValid.value) return '请输入正确的邮箱地址'
  if (!registerForm.emailCode.trim()) return '请输入邮箱验证码'
  if (!registerForm.password || registerForm.password.length < 8) return '密码至少 8 位'
  if (passwordStrength.value.level === 'weak') return '密码强度过弱，请增加数字、大小写字母或符号'
  if (registerForm.password !== registerForm.confirmPassword) return '两次输入的密码不一致'
  if (!registerForm.acceptTerms) return '注册前请先同意用户协议与隐私政策'
  return ''
}

function persistUser(user) {
  setAuthSession({ ...user, avatarUrl: user.avatarUrl || '/userlogo.png' })
}

async function refreshCaptcha(payload = {}) {
  captchaRequired.value = true
  captchaId.value = payload.captchaId || ''
  captchaQuestion.value = payload.question || ''
  if (!captchaId.value || !captchaQuestion.value) {
    const captcha = await getLoginCaptcha()
    captchaId.value = captcha.captchaId
    captchaQuestion.value = captcha.question
  }
  loginForm.captchaAnswer = ''
}

function startEmailCodeCountdown(seconds = 60) {
  emailCodeCountdown.value = seconds
  if (emailCodeTimer) clearInterval(emailCodeTimer)
  emailCodeTimer = setInterval(() => {
    emailCodeCountdown.value = Math.max(0, emailCodeCountdown.value - 1)
    if (emailCodeCountdown.value === 0 && emailCodeTimer) {
      clearInterval(emailCodeTimer)
      emailCodeTimer = null
    }
  }, 1000)
}

onUnmounted(() => {
  if (emailCodeTimer) clearInterval(emailCodeTimer)
  if (landingScrollFrame) cancelAnimationFrame(landingScrollFrame)
  revealObserver?.disconnect()
  document.documentElement.classList.remove('auth-landing-scroll')
  document.body.classList.remove('auth-landing-scroll')
  window.removeEventListener('keydown', handleAuthKeydown)
  window.removeEventListener('scroll', updateLandingScrollState)
  document.body.style.overflow = ''
})

async function sendEmailCode() {
  if (!isRegisterEmailValid.value) {
    setMessage('请输入正确的邮箱地址')
    return
  }

  emailCodeSending.value = true
  setMessage('', false)
  try {
    const result = await sendRegisterEmailCode({ email: registerForm.email.trim() })
    setMessage(result.msg || '验证码已发送，请查收邮箱', false)
    startEmailCodeCountdown(60)
  } catch (error) {
    const data = error.response?.data || {}
    setMessage(data.msg || data.message || '验证码发送失败，请稍后再试')
  } finally {
    emailCodeSending.value = false
  }
}

async function submitLogin() {
  const validation = validateLogin()
  if (validation) {
    setMessage(validation)
    return
  }

  authLoading.value = true
  setMessage('', false)
  try {
    const credentials = {
      username: loginForm.username.trim(),
      password: loginForm.password,
    }

    if (role.value === 'admin') {
      const loginToken = await loginAdminUser(credentials)
      rememberLoginAccount(credentials.username)
      setMessage('正在进入后台管理...', false)
      window.location.href = getAdminHomeUrl(loginToken)
      return
    }

    const user = await loginUser({
      ...credentials,
      captchaId: captchaId.value,
      captchaAnswer: loginForm.captchaAnswer,
    })
    rememberLoginAccount(credentials.username)
    persistUser(user)
    localStorage.setItem('appMode', role.value)
    if (role.value === 'admin') {
      if (user.role !== 'admin') {
        setMessage('当前账号不是管理员，请切换管理员账号登录')
        return
      }
      localStorage.setItem('SOY_token', JSON.stringify(user.token))
      localStorage.setItem('SOY_refreshToken', JSON.stringify(user.token))
      localStorage.setItem('SOY_lastLoginUserId', JSON.stringify(String(user.id)))
      setMessage('正在进入后台管理...', false)
      window.location.href = getAdminHomeUrl()
      return
    }
    setMessage('登录成功，正在进入系统...', false)
    await router.replace(pendingRoute.value || DEFAULT_AUTHENTICATED_PATH)
  } catch (error) {
    const data = error.response?.data || {}
    if (data.captchaRequired) await refreshCaptcha(data)
    setMessage(data.msg || data.message || '认证失败，请稍后再试')
  } finally {
    authLoading.value = false
  }
}

async function submitRegister() {
  const validation = validateRegister()
  if (validation) {
    setMessage(validation)
    return
  }

  authLoading.value = true
  setMessage('', false)
  try {
    const user = await registerUser({
      username: registerForm.username.trim(),
      displayName: registerForm.displayName.trim(),
      email: registerForm.email.trim(),
      emailCode: registerForm.emailCode.trim(),
      password: registerForm.password,
    })
    rememberLoginAccount(registerForm.username)
    persistUser(user)
    localStorage.setItem('appMode', 'user')
    setMessage('注册成功，正在进入系统...', false)
    await router.replace(pendingRoute.value || DEFAULT_AUTHENTICATED_PATH)
  } catch (error) {
    const data = error.response?.data || {}
    setMessage(data.msg || data.message || '注册失败，请稍后再试')
  } finally {
    authLoading.value = false
  }
}
</script>

<style scoped>
.auth-page-gradient {
  background:
    radial-gradient(circle at 16% 16%, rgba(52, 211, 153, 0.18), transparent 28%),
    radial-gradient(circle at 88% 20%, rgba(125, 211, 252, 0.22), transparent 30%),
    radial-gradient(circle at 18% 86%, rgba(16, 185, 129, 0.18), transparent 32%),
    linear-gradient(135deg, #f8fffd 0%, #eefaf7 42%, #f8fbff 100%);
}

.auth-page::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(16, 185, 129, 0.18) 1px, transparent 1px);
  background-size: 18px 18px;
  mask-image: radial-gradient(circle at 86% 44%, black 0 18%, transparent 34%);
  pointer-events: none;
}

.auth-page::after {
  content: "";
  position: absolute;
  left: 18%;
  top: 24%;
  width: 620px;
  height: 620px;
  border-radius: 999px;
  border: 1px solid rgba(16, 185, 129, 0.16);
  transform: rotate(-18deg);
  pointer-events: none;
}

.auth-panel-enter-active,
.auth-panel-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.auth-panel-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.auth-panel-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.auth-landing-page {
  min-height: 100vh;
  overflow-x: hidden;
  color: #1c2020;
  background: #ffffff;
}

.auth-landing-nav {
  width: min(1460px, calc(100% - 64px));
  height: 76px;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 260px;
  align-items: center;
  margin: 0 auto;
  border-bottom: 1px solid #eceeed;
}

.auth-landing-brand {
  width: fit-content;
  display: inline-flex;
  align-items: center;
}

.auth-landing-brand img {
  width: 146px;
  height: auto;
  display: block;
  filter: none;
  opacity: 1;
}

.auth-landing-links {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 38px;
}

.auth-landing-links a,
.auth-login-link {
  border: 0 !important;
  background: transparent !important;
  color: #6d7372 !important;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
}

.auth-landing-links a:hover,
.auth-login-link:hover {
  color: #1d2120 !important;
}

.auth-landing-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
}

.auth-register-button,
.auth-start-button {
  border: 1px solid #176f4b !important;
  border-radius: 6px !important;
  background: #176f4b !important;
  color: #ffffff !important;
  box-shadow: none !important;
}

.auth-register-button {
  min-width: 66px;
  height: 38px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 650;
}

.auth-start-button {
  min-width: 132px;
  height: 46px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 0 20px;
  font-size: 15px;
  font-weight: 650;
}

.auth-register-button:hover,
.auth-start-button:hover {
  border-color: #10583b !important;
  background: #10583b !important;
  color: #ffffff !important;
  transform: none !important;
}

.auth-landing-hero {
  width: min(1460px, calc(100% - 64px));
  min-height: calc(100vh - 134px);
  display: flex;
  align-items: center;
  justify-content: flex-start;
  margin: 0 auto;
  padding: 54px 0 46px;
  box-sizing: border-box;
}

.auth-hero-copy {
  max-width: 760px;
}

.auth-hero-kicker {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 11px;
  border: 1px solid #e3e6e5;
  border-radius: 999px;
  color: #6b7271;
  background: #ffffff;
  font-size: 12px;
  font-weight: 550;
}

.auth-hero-kicker svg {
  color: #176f4b;
}

.auth-hero-copy h1 {
  margin: 30px 0 22px;
  letter-spacing: 0;
}

.auth-hero-copy h1 strong,
.auth-hero-copy h1 span {
  display: block;
  letter-spacing: 0;
}

.auth-hero-copy h1 strong {
  color: #111414;
  font-size: 66px;
  font-weight: 820;
  line-height: 1.05;
}

.auth-hero-copy h1 span {
  margin-top: 10px;
  color: #176f4b;
  font-size: 44px;
  font-weight: 780;
  line-height: 1.16;
}

.auth-hero-copy > p {
  max-width: 570px;
  margin: 0;
  color: #69706f;
  font-size: 17px;
  line-height: 1.85;
}

.auth-hero-points {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin: 26px 0 0;
  padding: 0;
  list-style: none;
}

.auth-hero-points li {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #2e3433;
  font-size: 14px;
  font-weight: 600;
}

.auth-hero-points svg {
  color: #176f4b;
}

.auth-hero-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 34px;
}

.auth-outline-link {
  min-width: 112px;
  height: 46px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #dfe3e2;
  border-radius: 6px;
  color: #303534;
  background: #ffffff;
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
}

.auth-outline-link:hover {
  border-color: #b7bfbd;
  background: #fafbfa;
}

.auth-capability-strip {
  width: min(1460px, calc(100% - 64px));
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 0 auto;
  border-top: 1px solid #e8eae9;
  border-bottom: 1px solid #e8eae9;
}

.auth-capability-strip > div {
  min-height: 94px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 28px;
  border-right: 1px solid #e8eae9;
}

.auth-capability-strip > div:last-child {
  border-right: 0;
}

.auth-capability-strip strong {
  color: #1a1e1d;
  font-size: 20px;
  font-weight: 750;
}

.auth-capability-strip span {
  margin-top: 5px;
  color: #787f7e;
  font-size: 13px;
}

.auth-modal-backdrop {
  position: fixed !important;
  inset: 0;
  z-index: 2000;
  min-height: 100vh;
  background: rgba(20, 24, 23, 0.36) !important;
  backdrop-filter: blur(2px);
}

.auth-modal-backdrop > .pointer-events-none {
  display: none !important;
}

.auth-modal-backdrop::before,
.auth-modal-backdrop::after {
  content: none !important;
}

.auth-modal-panel {
  position: relative;
  max-height: calc(100vh - 40px);
  overflow-x: hidden;
  overflow-y: auto;
  border: 1px solid #dfe3e2 !important;
  border-radius: 8px !important;
  background: #ffffff !important;
  box-shadow: 0 24px 70px rgba(20, 24, 23, 0.22) !important;
  backdrop-filter: none !important;
  scrollbar-color: #c5cac9 transparent;
}

.auth-modal-close {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 4;
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  padding: 0 !important;
  border: 1px solid #dfe3e2 !important;
  border-radius: 6px !important;
  background: #ffffff !important;
  color: #525958 !important;
  box-shadow: none !important;
}

.auth-modal-close:hover {
  border-color: #b7bfbd !important;
  background: #f7f8f7 !important;
  color: #171919 !important;
}

.auth-modal-panel header h1 {
  color: #1a1e1d !important;
  font-size: 24px !important;
  letter-spacing: 0 !important;
}

.auth-modal-panel header p {
  color: #747b7a !important;
  letter-spacing: 0 !important;
}

.auth-modal-panel header > div > div:first-child {
  border-radius: 6px !important;
  background: #edf5f1 !important;
  color: #176f4b !important;
  box-shadow: none !important;
}

.auth-modal-panel :deep(input) {
  border-color: #dfe3e2 !important;
  border-radius: 6px !important;
  background: #ffffff !important;
  box-shadow: none !important;
}

.auth-modal-panel :deep(input:focus) {
  border-color: #176f4b !important;
  box-shadow: 0 0 0 3px rgba(23, 111, 75, 0.1) !important;
}

.auth-modal-panel :deep(.auth-role-option) {
  border-color: #dfe3e2 !important;
  border-radius: 6px !important;
  background: #ffffff !important;
  box-shadow: none !important;
  transform: none !important;
}

.auth-modal-panel :deep(.auth-role-option-active) {
  border-color: #9ab8aa !important;
  background: #f2f7f4 !important;
  color: #176f4b !important;
}

.auth-modal-panel :deep(.auth-role-option span:first-child) {
  border-radius: 5px !important;
  background: #f2f4f3 !important;
  color: #525958 !important;
  box-shadow: none !important;
}

.auth-modal-panel :deep(.auth-tab-action-active) {
  color: #176f4b !important;
}

.auth-modal-panel :deep(.auth-primary-action),
.auth-modal-panel :deep(.auth-primary-action:hover:not(:disabled)) {
  border-radius: 6px !important;
  background: #176f4b !important;
  color: #ffffff !important;
  box-shadow: none !important;
  transform: none !important;
}

@media (max-width: 1120px) {
  .auth-landing-nav,
  .auth-landing-hero,
  .auth-capability-strip {
    width: min(980px, calc(100% - 40px));
  }

  .auth-landing-nav {
    grid-template-columns: 190px minmax(0, 1fr) 190px;
  }

  .auth-landing-links {
    gap: 20px;
  }

  .auth-hero-copy h1 strong {
    font-size: 54px;
  }

  .auth-hero-copy h1 span {
    font-size: 36px;
  }

}

@media (max-width: 860px) {
  .auth-landing-nav {
    width: calc(100% - 32px);
    grid-template-columns: 1fr auto;
  }

  .auth-landing-links {
    display: none;
  }

  .auth-landing-hero {
    width: calc(100% - 32px);
    min-height: 0;
    padding: 54px 0 38px;
  }

  .auth-hero-copy {
    max-width: 680px;
  }

  .auth-capability-strip {
    width: calc(100% - 32px);
    grid-template-columns: 1fr 1fr;
  }

  .auth-capability-strip > div:nth-child(2) {
    border-right: 0;
  }

  .auth-capability-strip > div:nth-child(-n + 2) {
    border-bottom: 1px solid #e8eae9;
  }
}

@media (max-width: 560px) {
  .auth-landing-nav {
    height: 68px;
  }

  .auth-landing-brand img {
    width: 116px;
  }

  .auth-landing-actions {
    gap: 6px;
  }

  .auth-login-link {
    padding: 0 8px !important;
  }

  .auth-register-button {
    min-width: 58px;
    height: 34px;
    padding: 0 12px;
  }

  .auth-landing-hero {
    padding-top: 40px;
  }

  .auth-hero-copy h1 {
    margin-top: 24px;
  }

  .auth-hero-copy h1 strong {
    font-size: 42px;
  }

  .auth-hero-copy h1 span {
    font-size: 28px;
  }

  .auth-hero-copy > p {
    font-size: 15px;
  }

  .auth-hero-points {
    gap: 10px 16px;
  }

  .auth-capability-strip > div {
    min-height: 82px;
    padding: 0 14px;
  }

  .auth-capability-strip strong {
    font-size: 17px;
  }

  .auth-modal-backdrop {
    padding: 10px !important;
  }

  .auth-modal-panel {
    max-height: calc(100vh - 20px);
    padding-left: 18px !important;
    padding-right: 18px !important;
  }
}

/* Long-form public entry page */
.auth-landing-page {
  --landing-width: min(1460px, calc(100% - 64px));
  position: relative;
  min-height: 100vh;
  overflow-x: hidden;
  background: #ffffff;
  scroll-behavior: smooth;
}

:global(html.auth-landing-scroll),
:global(body.auth-landing-scroll),
:global(body.auth-landing-scroll #app) {
  height: auto;
  min-height: 100%;
}

:global(html.auth-landing-scroll),
:global(body.auth-landing-scroll) {
  overflow-x: hidden;
  overflow-y: auto;
}

.auth-scroll-progress {
  position: fixed;
  z-index: 180;
  top: 0;
  right: 0;
  left: 0;
  height: 2px;
  background: #176f4b;
  transform: scaleX(0);
  transform-origin: left center;
  pointer-events: none;
}

.auth-landing-nav {
  position: sticky;
  z-index: 140;
  top: 0;
  width: var(--landing-width);
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

.auth-landing-hero {
  width: var(--landing-width);
  min-height: calc(100vh - 126px);
  display: grid;
  grid-template-columns: minmax(430px, 0.86fr) minmax(560px, 1.14fr);
  align-items: center;
  gap: 64px;
  padding: 58px 0 68px;
}

.auth-hero-copy {
  max-width: 640px;
}

.auth-hero-copy h1 strong {
  font-size: 64px;
}

.auth-hero-copy h1 span {
  color: #147a78;
  font-size: 45px;
}

.auth-hero-copy > p {
  max-width: 610px;
  color: #454d4b;
}

.auth-hero-gallery {
  position: relative;
  height: 620px;
  min-width: 0;
}

.auth-gallery-main,
.auth-gallery-crop {
  margin: 0;
  overflow: hidden;
  border: 1px solid #e2e5e4;
  border-radius: 3px;
  background: #f7f8f8;
}

.auth-gallery-main {
  position: absolute;
  inset: 42px 0 30px 72px;
  will-change: transform;
}

.auth-gallery-main picture,
.auth-gallery-crop picture,
.auth-capability-media picture {
  width: 100%;
  height: 100%;
  display: block;
}

.auth-gallery-main img,
.auth-gallery-crop img,
.auth-capability-media img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.auth-gallery-crop {
  position: absolute;
  z-index: 2;
  border: 10px solid #ffffff;
  box-shadow: 0 14px 34px rgba(21, 30, 28, 0.12);
}

.auth-gallery-crop.crop-scope {
  top: 78px;
  left: 0;
  width: 235px;
  height: 198px;
}

.auth-gallery-crop.crop-scope img {
  object-position: center;
}

.auth-gallery-crop.crop-face {
  right: -14px;
  bottom: 0;
  width: 220px;
  height: 235px;
}

.auth-gallery-crop.crop-face img {
  object-position: center 46%;
}

.auth-gallery-label {
  position: absolute;
  z-index: 3;
  min-height: 32px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 11px;
  border: 1px solid #dfe4e2;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.94);
  color: #28302e;
  font-size: 12px;
  font-weight: 650;
  box-shadow: 0 8px 22px rgba(21, 30, 28, 0.08);
}

.auth-gallery-label svg {
  color: #147a78;
}

.auth-gallery-label.label-live {
  top: 30px;
  right: 24px;
}

.auth-gallery-label.label-profile {
  bottom: 34px;
  left: 38px;
}

.auth-skill-band {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  border-top: 1px solid #e7e9e8;
  border-bottom: 1px solid #e7e9e8;
  background: #ffffff;
}

.auth-skill-band > div {
  min-height: 94px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 11px;
  border-right: 1px solid #e7e9e8;
  color: #555d5a;
  font-size: 14px;
  font-weight: 600;
}

.auth-skill-band > div:last-child {
  border-right: 0;
}

.auth-skill-band > div:nth-child(1) svg { color: #0f8f8a; }
.auth-skill-band > div:nth-child(2) svg { color: #2563eb; }
.auth-skill-band > div:nth-child(3) svg { color: #7c3aed; }
.auth-skill-band > div:nth-child(4) svg { color: #d66a08; }
.auth-skill-band > div:nth-child(5) svg { color: #c2415d; }

.auth-model-section {
  padding: 88px 0 94px;
  background: #f5f8f7;
  scroll-margin-top: 92px;
}

.auth-model-section .auth-section-head {
  align-items: flex-end;
  margin-bottom: 34px;
}

.auth-harness-architecture {
  margin-bottom: 18px;
  overflow: hidden;
  border: 1px solid #cfdad6;
  border-radius: 8px;
  background: #ffffff;
}

.auth-harness-title {
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 10px 18px;
  border-bottom: 1px solid #e0e7e4;
  background: #eef5f2;
}

.auth-harness-title > span {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: #173d32;
  font-size: 14px;
  font-weight: 780;
}

.auth-harness-title > span svg {
  color: #087c60;
}

.auth-harness-title code {
  overflow-wrap: anywhere;
  color: #426057;
  font-family: "Cascadia Code", "SFMono-Regular", Consolas, monospace;
  font-size: 11px;
  text-align: right;
}

.auth-harness-architecture ol {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  padding: 0;
  margin: 0;
  list-style: none;
}

.auth-harness-architecture li {
  position: relative;
  min-width: 0;
  min-height: 102px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 17px;
  border-right: 1px solid #e2e8e5;
}

.auth-harness-architecture li:last-child {
  border-right: 0;
}

.auth-harness-architecture li:not(:last-child)::after {
  content: "";
  position: absolute;
  z-index: 2;
  top: 50%;
  right: -5px;
  width: 9px;
  height: 9px;
  border-top: 2px solid #9aaca5;
  border-right: 2px solid #9aaca5;
  background: #ffffff;
  transform: translateY(-50%) rotate(45deg);
}

.auth-harness-step-icon {
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border-radius: 7px;
  color: #087c60;
  background: #e7f5f0;
}

.auth-harness-architecture li > div {
  min-width: 0;
  display: grid;
  gap: 6px;
}

.auth-harness-architecture b {
  color: #26312e;
  font-size: 13px;
  line-height: 1.4;
}

.auth-harness-architecture small {
  color: #69746f;
  font-size: 11px;
  line-height: 1.55;
}

.auth-model-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.auth-model-grid article {
  min-width: 0;
  min-height: 278px;
  padding: 22px 20px;
  border: 1px solid #dce4e1;
  border-top: 3px solid var(--model-accent);
  border-radius: 8px;
  background: #ffffff;
  transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
}

.auth-model-grid article:hover {
  border-color: color-mix(in srgb, var(--model-accent) 36%, #dce4e1);
  box-shadow: 0 14px 32px rgba(27, 43, 38, 0.09);
  transform: translateY(-3px);
}

.auth-model-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.auth-model-icon {
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: var(--model-accent);
  background: var(--model-soft);
}

.auth-model-card-head small {
  color: var(--model-accent);
  font-size: 11px;
  font-weight: 750;
  line-height: 1.45;
  text-align: right;
}

.auth-model-tag {
  max-width: calc(100% - 54px);
  padding: 4px 7px;
  border: 1px solid currentColor;
  border-radius: 5px;
  background: #ffffff;
}

.auth-model-tag.core {
  color: #087c60;
  background: #eef9f5;
}

.auth-model-tag.domestic {
  color: #2563eb;
  background: #f1f5ff;
}

.auth-model-tag.adapter {
  color: #6a5a73;
  background: #f7f4f8;
}

.auth-model-grid h3 {
  margin: 20px 0 0;
  color: #19201e;
  font-size: 17px;
  line-height: 1.45;
  letter-spacing: 0;
}

.auth-model-grid code {
  min-height: 44px;
  display: flex;
  align-items: center;
  margin-top: 12px;
  padding: 8px 10px;
  overflow-wrap: anywhere;
  border: 1px solid #e2e7e5;
  border-radius: 5px;
  background: #f7f9f8;
  color: #35413d;
  font-family: "Cascadia Code", "SFMono-Regular", Consolas, monospace;
  font-size: 11px;
  line-height: 1.45;
}

.auth-model-grid p {
  margin: 13px 0 0;
  color: #5c6763;
  font-size: 12px;
  line-height: 1.7;
}

.auth-section {
  width: var(--landing-width);
  margin: 0 auto;
}

.auth-capabilities-section {
  padding: 112px 0 124px;
  scroll-margin-top: 92px;
}

.auth-section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 40px;
  margin-bottom: 44px;
}

.auth-section-head.compact {
  align-items: flex-start;
}

.auth-section-head > div:first-child {
  max-width: 760px;
}

.auth-section-kicker {
  display: inline-flex;
  align-items: center;
  color: #147a78;
  font-size: 13px;
  font-weight: 750;
}

.auth-section-head h2,
.auth-final-section h2 {
  margin: 12px 0 0;
  color: #151918;
  font-size: 40px;
  font-weight: 780;
  line-height: 1.25;
  letter-spacing: 0;
}

.auth-section-head p,
.auth-final-section p {
  margin: 13px 0 0;
  color: #555d5a;
  font-size: 15px;
  line-height: 1.75;
}

.auth-section-head.compact > p {
  max-width: 460px;
  margin: 7px 0 0;
}

.auth-section-switch {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 4px;
  border-radius: 8px;
  background: #f2f4f3;
}

.auth-section-switch span {
  min-width: 78px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: #69716f;
  font-size: 13px;
}

.auth-section-switch span.active {
  background: #ffffff;
  color: #1b211f;
  box-shadow: 0 2px 8px rgba(20, 26, 24, 0.08);
}

.auth-capability-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.auth-capability-card {
  min-width: 0;
  overflow: hidden;
  border: 1px solid #e0e4e2;
  border-radius: 6px;
  background: #ffffff;
  transition: border-color 180ms ease, transform 180ms ease, box-shadow 180ms ease;
  scroll-margin-top: 100px;
}

.auth-capability-card:hover {
  border-color: #bcc7c3;
  transform: translateY(-4px);
  box-shadow: 0 14px 34px rgba(22, 31, 28, 0.08);
}

.auth-capability-media {
  aspect-ratio: 4 / 3;
  margin: 0;
  overflow: hidden;
  border-bottom: 1px solid #e7e9e8;
  background: #f6f7f7;
}

.auth-capability-media img {
  transition: transform 420ms ease;
}

.auth-capability-card:hover .auth-capability-media img {
  transform: scale(1.035);
}

.auth-capability-media.media-profile img { object-position: center 46%; }
.auth-capability-media.media-path img { object-position: center center; }
.auth-capability-media.media-resource img { object-position: center 48%; }
.auth-capability-media.media-assessment img { object-position: center center; }

.auth-capability-copy {
  padding: 20px 20px 22px;
}

.auth-capability-copy > span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #147a78;
  font-size: 13px;
  font-weight: 750;
}

.auth-capability-card:nth-child(2) .auth-capability-copy > span { color: #2563eb; }
.auth-capability-card:nth-child(3) .auth-capability-copy > span { color: #7c3aed; }
.auth-capability-card:nth-child(4) .auth-capability-copy > span { color: #c2415d; }

.auth-capability-copy h3 {
  margin: 14px 0 0;
  color: #1a1f1e;
  font-size: 18px;
  line-height: 1.45;
  letter-spacing: 0;
}

.auth-capability-copy p {
  margin: 10px 0 0;
  color: #5b6361;
  font-size: 13px;
  line-height: 1.7;
}

.auth-innovation-section {
  width: min(1180px, calc(100% - 48px));
  margin: 0 auto;
  padding: 82px 0 88px;
  scroll-margin-top: 76px;
}

.auth-innovation-section > .auth-section-head { margin-bottom: 30px; }

.auth-innovation-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 18px;
}

.auth-innovation-grid > article {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(250px, 1.1fr) minmax(220px, .9fr);
  min-height: 290px;
  overflow: hidden;
  border: 1px solid #d9e1de;
  border-radius: 6px;
  background: #ffffff;
}

.innovation-preview {
  position: relative;
  min-height: 290px;
  overflow: hidden;
  background: #070b12;
}

.knowledge-preview img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
  object-position: center;
}

.knowledge-preview::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(180deg, transparent 62%, rgba(3, 8, 15, .5));
}

.knowledge-preview-badge {
  position: absolute;
  right: 14px;
  bottom: 14px;
  z-index: 2;
  padding: 5px 9px;
  border: 1px solid rgba(92, 225, 193, .42);
  border-radius: 3px;
  background: rgba(4, 12, 20, .78);
  color: #87ead2;
  font-size: 10px;
  font-weight: 800;
  line-height: 1;
}

.innovation-copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 24px;
}

.innovation-copy > span { display: flex; align-items: center; gap: 7px; color: #147a68; font-size: 12px; font-weight: 800; }
.innovation-copy h3 { margin: 13px 0 24px; color: #19211f; font-size: 17px; line-height: 1.5; }
.innovation-copy button { min-height: 40px; display: flex; align-items: center; justify-content: center; gap: 7px; border: 1px solid #1b5849; border-radius: 4px; background: #1b5849; color: #ffffff; font: inherit; font-size: 11px; font-weight: 800; cursor: pointer; }

.auth-flow-section {
  background: #f4f7f6;
  scroll-margin-top: 76px;
}

.auth-flow-inner {
  padding: 82px 0 88px;
}

.auth-flow-inner .auth-section-head {
  align-items: flex-end;
  margin-bottom: 36px;
}

.auth-flow-track {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 24px;
}

.auth-flow-track article {
  position: relative;
  display: flex;
  min-height: 184px;
  min-width: 0;
  flex-direction: column;
  padding: 24px;
  border: 1px solid #dfe7e4;
  border-top: 3px solid var(--flow-color);
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 10px 26px rgba(33, 54, 49, 0.06);
  transition: border-color 180ms ease, box-shadow 180ms ease, transform 180ms ease;
}

.auth-flow-track article:hover {
  border-color: color-mix(in srgb, var(--flow-color) 34%, #dfe7e4);
  box-shadow: 0 16px 34px rgba(33, 54, 49, 0.1);
  transform: translateY(-3px);
}

.auth-flow-step-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.auth-flow-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: var(--flow-color);
  background: var(--flow-soft);
}

.auth-flow-track article b {
  color: var(--flow-color);
  font-size: 13px;
  font-weight: 780;
  font-variant-numeric: tabular-nums;
}

.auth-flow-track h3 {
  margin: 22px 0 0;
  color: #1b201f;
  font-size: 19px;
  line-height: 1.35;
  letter-spacing: 0;
}

.auth-flow-track p {
  margin: 10px 0 0;
  color: #606865;
  font-size: 13px;
  line-height: 1.7;
}

.auth-flow-arrow {
  position: absolute;
  z-index: 2;
  top: 50%;
  right: -22px;
  padding: 3px;
  border-radius: 50%;
  color: #77817e;
  background: #f4f7f6;
  transform: translateY(-50%);
  box-sizing: content-box;
}

.auth-bonus-section {
  width: var(--landing-width);
  padding: 96px 0;
  margin: 0 auto;
}

.auth-bonus-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 1px;
  margin-top: 34px;
  border: 1px solid #dfe4e2;
  border-radius: 8px;
  overflow: hidden;
  background: #dfe4e2;
}

.auth-bonus-grid article {
  min-width: 0;
  min-height: 118px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 20px 18px;
  background: #ffffff;
}

.auth-bonus-grid article > svg {
  flex: 0 0 auto;
  margin-top: 2px;
  color: #087c60;
}

.auth-bonus-grid article:nth-child(2) > svg,
.auth-bonus-grid article:nth-child(6) > svg { color: #2563eb; }
.auth-bonus-grid article:nth-child(3) > svg,
.auth-bonus-grid article:nth-child(7) > svg { color: #7c3aed; }
.auth-bonus-grid article:nth-child(4) > svg,
.auth-bonus-grid article:nth-child(8) > svg { color: #c2415d; }
.auth-bonus-grid article:nth-child(9) > svg { color: #b45309; }
.auth-bonus-grid article:nth-child(10) > svg { color: #2563eb; }

.auth-bonus-grid article > div {
  min-width: 0;
  display: grid;
  gap: 7px;
}

.auth-bonus-grid strong {
  color: #1a2220;
  font-size: 15px;
  line-height: 1.35;
}

.auth-bonus-grid span {
  color: #66716d;
  font-size: 12px;
  line-height: 1.6;
}

.auth-proof-section {
  width: var(--landing-width);
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 0 auto;
  border-top: 1px solid #e2e5e4;
  border-bottom: 1px solid #e2e5e4;
  background: #f7faf9;
}

.auth-proof-section > div {
  --proof-accent: #087c60;
  min-height: 156px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 32px;
  border-right: 1px solid #e2e5e4;
  box-shadow: inset 0 3px 0 var(--proof-accent);
  background: #ffffff;
}

.auth-proof-section > div:nth-child(2) {
  --proof-accent: #2563eb;
}

.auth-proof-section > div:nth-child(3) {
  --proof-accent: #a63b62;
}

.auth-proof-section > div:nth-child(4) {
  --proof-accent: #a15c08;
}

.auth-proof-section > div:last-child {
  border-right: 0;
}

.auth-proof-section strong {
  color: var(--proof-accent);
  font-size: 42px;
  font-variant-numeric: tabular-nums;
  font-weight: 800;
  line-height: 1;
  letter-spacing: 0;
  white-space: nowrap;
}

.auth-proof-section span {
  margin-top: 14px;
  color: #28312f;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.35;
}

.auth-proof-section small {
  margin-top: 5px;
  color: #76807c;
  font-size: 11px;
  line-height: 1.45;
  letter-spacing: 0;
}

.auth-final-section {
  width: var(--landing-width);
  min-height: 390px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 48px;
  margin: 0 auto;
  border-bottom: 1px solid #e4e7e6;
}

.auth-final-section > div:first-child {
  max-width: 760px;
}

.auth-final-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.auth-register-secondary {
  min-width: 112px;
  height: 46px;
  padding: 0 18px;
  border: 1px solid #d8dddb !important;
  border-radius: 6px !important;
  background: #ffffff !important;
  color: #29312f !important;
  font-size: 14px;
  font-weight: 650;
}

.auth-register-secondary:hover {
  border-color: #aeb9b5 !important;
  background: #f7f8f8 !important;
}

.auth-landing-footer {
  width: var(--landing-width);
  min-height: 148px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 28px;
  margin: 0 auto;
  color: #737b78;
  font-size: 12px;
}

.auth-footer-brand {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 16px;
}

.auth-footer-brand img {
  width: 118px;
  height: auto;
}

.auth-open-source {
  min-width: 0;
  display: grid;
  justify-items: end;
  gap: 8px;
  color: #818986;
  font-size: 11px;
}

.auth-open-source > span {
  color: #59635f;
  font-weight: 700;
}

.auth-open-source > div {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 7px 14px;
}

.auth-open-source a {
  color: #68736f;
  text-decoration: none;
  transition: color 0.2s ease;
}

.auth-open-source a:hover,
.auth-open-source a:focus-visible {
  color: #087451;
  outline: none;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.auth-data-security {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 7px;
  padding-top: 12px;
  border-top: 1px solid #e6e9e7;
  color: #65706c;
  font-size: 11px;
  line-height: 1.5;
}

.auth-data-security svg {
  flex: 0 0 auto;
  color: #087451;
}

.auth-icp-record {
  flex: 0 0 auto;
  margin-left: auto;
  color: #65706c;
  text-decoration: none;
  white-space: nowrap;
}

.auth-icp-record:hover,
.auth-icp-record:focus-visible {
  color: #087451;
  outline: none;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.auth-reveal {
  opacity: 0;
  transform: translateY(44px) scale(0.985);
  transform-origin: center bottom;
  transition:
    opacity 560ms ease,
    transform 760ms cubic-bezier(0.16, 1, 0.3, 1);
  will-change: opacity, transform;
}

.auth-reveal.is-visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.auth-stagger > * {
  opacity: 0;
  transform: translateY(42px) scale(0.92);
  transform-origin: center bottom;
  will-change: opacity, transform;
}

.auth-reveal.is-visible.auth-stagger > *,
.auth-reveal.is-visible .auth-stagger > * {
  animation: auth-pop-in 760ms cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: var(--reveal-delay, 0ms);
}

.auth-skill-band > div:nth-child(1),
.auth-proof-section > div:nth-child(1),
.auth-final-section > div:nth-child(1) { --reveal-delay: 40ms; }

.auth-skill-band > div:nth-child(2),
.auth-proof-section > div:nth-child(2),
.auth-final-section > div:nth-child(2) { --reveal-delay: 130ms; }

.auth-skill-band > div:nth-child(3),
.auth-proof-section > div:nth-child(3) { --reveal-delay: 220ms; }

.auth-skill-band > div:nth-child(4),
.auth-proof-section > div:nth-child(4) { --reveal-delay: 310ms; }

.auth-skill-band > div:nth-child(5) { --reveal-delay: 400ms; }

.auth-reveal .auth-section-head {
  opacity: 0;
  transform: translateY(32px) scale(0.96);
  transform-origin: left bottom;
  will-change: opacity, transform;
}

.auth-reveal.is-visible .auth-section-head {
  animation: auth-pop-in 720ms cubic-bezier(0.16, 1, 0.3, 1) 40ms both;
}

@keyframes auth-pop-in {
  0% {
    opacity: 0;
    transform: translateY(42px) scale(0.92);
  }

  68% {
    opacity: 1;
    transform: translateY(-7px) scale(1.012);
  }

  84% {
    opacity: 1;
    transform: translateY(2px) scale(0.997);
  }

  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (max-width: 1200px) {
  .auth-landing-page {
    --landing-width: min(1060px, calc(100% - 40px));
  }

  .auth-landing-hero {
    grid-template-columns: minmax(380px, 0.9fr) minmax(460px, 1.1fr);
    gap: 36px;
  }

  .auth-hero-copy h1 strong { font-size: 54px; }
  .auth-hero-copy h1 span { font-size: 36px; }
  .auth-hero-gallery { height: 530px; }

  .auth-capability-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .auth-model-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .auth-harness-architecture ol {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .auth-harness-architecture li:nth-child(2) {
    border-right: 0;
  }

  .auth-harness-architecture li:nth-child(-n + 2) {
    border-bottom: 1px solid #e2e8e5;
  }

  .auth-harness-architecture li:nth-child(2)::after {
    display: none;
  }

  .auth-bonus-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .auth-innovation-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .auth-landing-page {
    --landing-width: calc(100% - 32px);
  }

  .auth-landing-hero {
    min-height: 0;
    grid-template-columns: 1fr;
    gap: 42px;
    padding: 60px 0 72px;
  }

  .auth-hero-copy {
    max-width: 700px;
  }

  .auth-hero-gallery {
    width: 100%;
    height: 500px;
  }

  .auth-skill-band {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .auth-skill-band > div:nth-child(3) {
    border-right: 0;
  }

  .auth-skill-band > div:nth-child(-n + 3) {
    border-bottom: 1px solid #e7e9e8;
  }

  .auth-section-head,
  .auth-final-section {
    align-items: flex-start;
    flex-direction: column;
  }

  .auth-section-head.compact > p {
    max-width: 700px;
  }

  .auth-model-section .auth-section-head {
    align-items: flex-start;
  }

  .auth-model-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .auth-flow-track {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .auth-flow-inner .auth-section-head {
    align-items: flex-start;
  }

  .auth-flow-arrow {
    display: none;
  }

  .auth-bonus-section {
    padding: 76px 0;
  }

  .auth-innovation-grid > article {
    grid-template-columns: 1fr;
  }

  .innovation-preview {
    min-height: 240px;
  }

}

@media (max-width: 560px) {
  .auth-landing-hero {
    padding: 44px 0 58px;
  }

  .auth-innovation-section {
    width: calc(100% - 32px);
    padding: 60px 0 68px;
  }

  .auth-innovation-grid {
    gap: 14px;
  }

  .innovation-preview {
    min-height: 220px;
  }

  .innovation-copy {
    padding: 20px;
  }

  .auth-hero-copy h1 strong { font-size: 42px; }
  .auth-hero-copy h1 span { font-size: 29px; }

  .auth-hero-gallery {
    height: 350px;
  }

  .auth-gallery-main {
    inset: 28px 0 20px 28px;
  }

  .auth-gallery-crop {
    border-width: 6px;
  }

  .auth-gallery-crop.crop-scope {
    top: 48px;
    width: 128px;
    height: 112px;
  }

  .auth-gallery-crop.crop-face {
    right: -6px;
    width: 126px;
    height: 132px;
  }

  .auth-gallery-label {
    display: none;
  }

  .auth-skill-band {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .auth-bonus-section {
    padding: 58px 0;
  }

  .auth-bonus-grid {
    grid-template-columns: 1fr;
    margin-top: 26px;
  }

  .auth-bonus-grid article {
    min-height: 0;
    padding: 18px;
  }

  .auth-model-section {
    padding: 60px 0 64px;
  }

  .auth-model-grid {
    grid-template-columns: 1fr;
  }

  .auth-harness-title {
    align-items: flex-start;
    flex-direction: column;
    gap: 5px;
    padding: 14px 16px;
  }

  .auth-harness-title code {
    text-align: left;
  }

  .auth-harness-architecture ol {
    grid-template-columns: 1fr;
  }

  .auth-harness-architecture li,
  .auth-harness-architecture li:nth-child(2) {
    min-height: 0;
    border-right: 0;
    border-bottom: 1px solid #e2e8e5;
  }

  .auth-harness-architecture li:last-child {
    border-bottom: 0;
  }

  .auth-harness-architecture li::after {
    display: none;
  }

  .auth-model-grid article {
    min-height: 0;
  }

  .auth-skill-band > div {
    min-height: 78px;
    justify-content: flex-start;
    padding: 0 18px;
  }

  .auth-skill-band > div:nth-child(2n) {
    border-right: 0;
  }

  .auth-skill-band > div:nth-child(3) {
    border-right: 1px solid #e7e9e8;
  }

  .auth-skill-band > div:nth-child(4) {
    border-bottom: 1px solid #e7e9e8;
  }

  .auth-skill-band > div:last-child {
    grid-column: 1 / -1;
    border-top: 1px solid #e7e9e8;
  }

  .auth-capabilities-section,
  .auth-flow-inner {
    padding: 74px 0 80px;
  }

  .auth-section-head {
    margin-bottom: 30px;
  }

  .auth-section-head h2,
  .auth-final-section h2 {
    font-size: 28px;
  }

  .auth-section-switch {
    width: 100%;
  }

  .auth-section-switch span {
    min-width: 0;
    flex: 1;
  }

  .auth-capability-grid,
  .auth-flow-track {
    grid-template-columns: 1fr;
  }

  .auth-flow-track {
    gap: 14px;
  }

  .auth-flow-track article {
    min-height: 0;
    padding: 20px;
  }

  .auth-proof-section {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .auth-proof-section > div {
    min-height: 132px;
    padding: 0 18px;
    border-bottom: 1px solid #e2e5e4;
  }

  .auth-proof-section > div:nth-child(2n) {
    border-right: 0;
  }

  .auth-proof-section strong {
    font-size: 32px;
  }

  .auth-final-section {
    min-height: 360px;
    padding: 70px 0;
    box-sizing: border-box;
  }

  .auth-final-actions {
    width: 100%;
  }

  .auth-final-actions > * {
    flex: 1;
  }

  .auth-landing-footer {
    min-height: 152px;
    align-items: flex-start;
    flex-direction: column;
    justify-content: center;
    gap: 14px;
  }

  .auth-footer-brand img {
    width: 104px;
  }

  .auth-open-source {
    justify-items: start;
  }

  .auth-open-source > div {
    justify-content: flex-start;
  }

  .auth-data-security {
    flex-wrap: wrap;
  }

  .auth-icp-record {
    width: 100%;
    margin-left: 22px;
  }

}

@media (prefers-reduced-motion: reduce) {
  .auth-reveal,
  .auth-stagger > *,
  .auth-reveal .auth-section-head,
  .auth-capability-media img,
  .auth-flow-track::before {
    opacity: 1 !important;
    transform: none !important;
    transition: none !important;
    animation: none !important;
  }

}
</style>
