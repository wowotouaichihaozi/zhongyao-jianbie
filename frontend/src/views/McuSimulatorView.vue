<template>
  <div class="mcu-app" :class="{ 'resource-mode': isResourceToolPage }">
    <RouterLink v-if="isResourceToolPage && !selectedProjectId" class="resource-return" to="/personalized-resources">
      <ArrowLeft :size="17" />
      <span>个性化资源</span>
    </RouterLink>

    <main v-if="catalogLoading" class="catalog-loading" aria-live="polite">
      <LoaderCircle class="spin" :size="30" />
      <strong>正在载入实验目录</strong>
    </main>

    <main v-else-if="catalogError" class="catalog-loading error" role="alert">
      <CircleAlert :size="30" />
      <strong>实验目录载入失败</strong>
      <p>{{ catalogError }}</p>
      <button type="button" @click="loadCatalog"><RefreshCw :size="16" />重试</button>
    </main>

    <main v-else-if="!selectedBoard" class="board-select-page">
      <header class="catalog-hero">
        <div>
          <span class="eyebrow">MCU LAB</span>
          <h1>单片机实验台</h1>
          <p>从预设电路开始，检查引脚能力、完成多端子接线，再编译烧录到教学仿真内核。</p>
        </div>
        <dl class="catalog-metrics">
          <div><dt>板卡</dt><dd>{{ catalog.counts?.boards || boards.length }}</dd></div>
          <div><dt>实验</dt><dd>{{ catalog.counts?.experiments || experiments.length }}</dd></div>
          <div><dt>元件</dt><dd>{{ catalog.counts?.components || components.length }}</dd></div>
        </dl>
      </header>

      <section v-if="recommendations.length" class="recommend-band">
        <div class="section-title">
          <div>
            <span>当前画像推荐</span>
            <h2>从这些实验开始</h2>
          </div>
          <Sparkles :size="22" />
        </div>
        <div class="recommend-list">
          <RouterLink
            v-for="project in recommendations.slice(0, 4)"
            :key="project.id"
            :to="`${mcuBasePath}/${project.board}/${project.id}`"
            class="recommend-item"
          >
            <span>{{ boardName(project.board) }}</span>
            <strong>{{ project.title }}</strong>
            <p>{{ project.recommendation?.reason }}</p>
            <ArrowUpRight :size="17" />
          </RouterLink>
        </div>
      </section>

      <section class="board-section">
        <div class="section-title">
          <div><span>选择目标</span><h2>板卡与体系结构</h2></div>
        </div>
        <div class="board-grid">
          <RouterLink
            v-for="board in boards"
            :key="board.id"
            class="board-card"
            :to="`${mcuBasePath}/${board.id}`"
          >
            <div class="board-card-visual" :class="board.id">
              <wokwi-arduino-uno v-if="board.id === 'arduino'"></wokwi-arduino-uno>
              <div v-else class="dip-preview"><i v-for="n in 20" :key="n"></i><b>AT89S52</b></div>
            </div>
            <div class="board-card-copy">
              <span>{{ board.subtitle }}</span>
              <strong>{{ board.title }}</strong>
              <p>{{ board.simulationBoundary }}</p>
              <ul>
                <li>{{ board.pins.length }} 个可检查引脚</li>
                <li>{{ boardExperimentCount(board.id) }} 个实验预设</li>
              </ul>
            </div>
            <ArrowRight :size="21" />
          </RouterLink>
        </div>
      </section>

      <footer class="source-footer">
        <ShieldCheck :size="18" />
        <span>实验原理参考 Arduino Examples、AVR8js 与开源 8051 模拟器；每个实验均保留来源与许可信息。</span>
      </footer>
    </main>

    <main v-else-if="!selectedProjectId" class="experiment-page">
      <header class="catalog-topbar">
        <RouterLink class="brand-link" :to="mcuBasePath"><Cpu :size="20" />MCU LAB</RouterLink>
        <div>
          <strong>{{ boardInfo?.title }}</strong>
          <span>{{ boardInfo?.subtitle }}</span>
        </div>
        <RouterLink class="icon-command" :to="mcuBasePath" title="切换板卡"><PanelsTopLeft :size="18" />切换板卡</RouterLink>
      </header>

      <section class="experiment-body">
        <header class="experiment-head">
          <div>
            <span class="eyebrow">{{ boardInfo?.mcu }}</span>
            <h1>实验项目</h1>
            <p>预设电路已经按引脚能力完成接线，可直接烧录运行，也可以在画布中继续添加元件。</p>
          </div>
          <div class="recommend-state" :class="{ bound: recommendationMeta.profileBound }">
            <Sparkles :size="18" />
            <span>{{ recommendationMeta.profileBound ? '已结合当前学习画像排序' : '按课程进阶顺序排序' }}</span>
          </div>
        </header>

        <div class="experiment-filters">
          <label class="search-field"><Search :size="17" /><input v-model="projectQuery" placeholder="搜索 GPIO、PWM、传感器或元件" /></label>
          <select v-model="difficultyFilter" aria-label="难度筛选">
            <option value="">全部难度</option>
            <option v-for="difficulty in difficulties" :key="difficulty" :value="difficulty">{{ difficulty }}</option>
          </select>
          <span>{{ filteredProjects.length }} 个项目</span>
        </div>

        <div class="experiment-grid">
          <article
            v-for="project in filteredProjects"
            :key="project.id"
            class="experiment-card"
            :class="{ recommended: recommendationFor(project.id), blank: project.mode === 'blank' }"
          >
            <RouterLink class="experiment-main" :to="`${mcuBasePath}/${selectedBoard}/${project.id}`">
              <div class="experiment-preview" :class="project.board">
                <span v-if="recommendationFor(project.id)" class="recommend-badge">推荐</span>
                <div class="mini-board">{{ project.board === '8051' ? 'AT89S52' : 'UNO' }}</div>
                <div class="mini-parts">
                  <span v-for="part in project.parts.slice(0, 5)" :key="part.id" :class="componentDefinition(part)?.visual || 'part'"></span>
                </div>
              </div>
              <div class="experiment-copy">
                <div class="meta-line"><span>{{ project.difficulty }}</span><span>{{ project.durationMinutes ? `${project.durationMinutes} 分钟` : '自由搭建' }}</span></div>
                <h2>{{ project.title }}</h2>
                <p>{{ project.summary }}</p>
                <div class="tag-row"><span v-for="tag in project.tags.slice(0, 4)" :key="tag">{{ tag }}</span></div>
                <p v-if="recommendationFor(project.id)" class="recommend-reason">{{ recommendationFor(project.id).reason }}</p>
              </div>
            </RouterLink>
            <footer>
              <span>{{ project.steps?.length || 0 }} 步 · {{ project.parts.length }} 个预设元件</span>
              <a
                v-for="source in projectSources(project).slice(0, 1)"
                :key="source.id"
                :href="source.url"
                target="_blank"
                rel="noopener noreferrer"
              >{{ source.license }}<ExternalLink :size="13" /></a>
            </footer>
          </article>
        </div>
      </section>
    </main>

    <main v-else class="workbench-shell">
      <header class="workbench-topbar">
        <RouterLink class="brand-link compact" :to="mcuBasePath"><Cpu :size="19" />MCU LAB</RouterLink>
        <div class="project-identity">
          <strong>{{ activeProject?.title || '实验项目' }}</strong>
          <span>{{ boardInfo?.mcu }} · {{ activeProject?.difficulty }} · {{ codeFileName }}</span>
        </div>
        <div class="top-actions">
          <RouterLink class="top-action" :to="`${mcuBasePath}/${selectedBoard}`"><LayoutGrid :size="16" />实验目录</RouterLink>
          <button type="button" class="top-action" @click="openGuide"><ListChecks :size="16" />实验步骤</button>
          <button type="button" class="top-action" @click="saveDiagram"><Save :size="16" />保存布局</button>
          <button type="button" class="flash-action" @click="openFlashDialog"><Upload :size="16" />编译烧录</button>
        </div>
      </header>

      <div class="workbench-tabs">
        <button type="button" :class="{ active: !showDiagramJson && !showGuide }" @click="showCode"><FileCode2 :size="15" />{{ codeFileName }}</button>
        <button type="button" :class="{ active: showDiagramJson && !showGuide }" @click="showDiagram"><Braces :size="15" />diagram.json</button>
        <button type="button" :class="{ active: showGuide }" @click="openGuide"><ListChecks :size="15" />实验步骤 {{ guideProgress.done }}/{{ guideProgress.total }}</button>
        <span v-if="firmware" class="firmware-chip"><CheckCircle2 :size="14" />{{ firmware.id }}</span>
      </div>

      <section class="workbench-grid">
        <section class="editor-pane">
          <header>
            <div><span>{{ showGuide ? '实验步骤' : (showDiagramJson ? 'diagram.json' : codeFileName) }}</span><em>{{ showGuide ? `${guideProgress.done}/${guideProgress.total} 已完成` : boardInfo?.language }}</em></div>
            <button v-if="!showGuide" type="button" title="编译并虚拟烧录" @click="openFlashDialog"><Flame :size="16" />烧录</button>
          </header>
          <div v-if="showGuide" class="guide-sheet">
            <header>
              <span>GUIDED LAB</span>
              <strong>{{ activeProject?.summary }}</strong>
              <p>按顺序完成接线、代码检查和验收。烧录通过后，前四步会自动记为完成。</p>
            </header>
            <ol>
              <li v-for="(step, index) in guideSteps" :key="step.id" :class="{ done: isGuideStepDone(index) }">
                <button type="button" :title="isGuideStepDone(index) ? '标记为未完成' : '标记为完成'" @click="toggleGuideStep(index)">
                  <CheckCircle2 v-if="isGuideStepDone(index)" :size="21" />
                  <Circle v-else :size="21" />
                </button>
                <div>
                  <span>步骤 {{ String(index + 1).padStart(2, '0') }}</span>
                  <strong>{{ step.title }}</strong>
                  <p>{{ step.detail }}</p>
                  <ul v-if="step.checks?.length">
                    <li v-for="check in step.checks" :key="check">{{ check }}</li>
                  </ul>
                </div>
              </li>
            </ol>
          </div>
          <div v-else class="code-area">
            <pre class="line-gutter">{{ lineNumbers }}</pre>
            <textarea
              v-if="!showDiagramJson"
              v-model="codeText"
              class="code-editor"
              spellcheck="false"
              aria-label="单片机代码编辑器"
            ></textarea>
            <textarea v-else :value="diagramJson" readonly class="code-editor" spellcheck="false" aria-label="电路 JSON"></textarea>
          </div>
        </section>

        <section class="sim-pane">
          <div class="sim-toolbar">
            <button type="button" class="tool-primary" :class="{ stop: isRunning }" :title="isRunning ? '停止仿真' : '运行仿真'" @click="toggleRun">
              <Square v-if="isRunning" :size="17" fill="currentColor" />
              <Play v-else :size="17" fill="currentColor" />
              <span>{{ isRunning ? '停止' : '运行' }}</span>
            </button>
            <button type="button" class="tool-button" title="单步执行" @click="stepOnce"><StepForward :size="17" /></button>
            <button type="button" class="tool-button" title="复位仿真" @click="resetSimulation"><RotateCcw :size="17" /></button>
            <button type="button" class="tool-button with-label" :class="{ active: partsMenuOpen }" @click="partsMenuOpen = !partsMenuOpen"><Library :size="17" /><span>元件库</span></button>
            <div v-if="pendingConnection" class="connection-hint"><Cable :size="16" />请选择主板引脚连接 {{ pendingConnection.label }}</div>
            <div class="sim-spacer"></div>
            <span class="engine-label">教学仿真 · {{ boardInfo?.clockHz?.toLocaleString() }} Hz</span>
          </div>

          <aside v-if="partsMenuOpen" class="parts-drawer">
            <header><strong>元件库</strong><button type="button" title="关闭" @click="partsMenuOpen = false"><X :size="17" /></button></header>
            <label><Search :size="16" /><input v-model="componentQuery" placeholder="搜索元件" /></label>
            <div class="component-categories">
              <button v-for="category in componentCategories" :key="category" type="button" :class="{ active: componentCategory === category }" @click="componentCategory = category">{{ category }}</button>
            </div>
            <div class="component-list">
              <button v-for="component in filteredComponents" :key="component.id" type="button" @click="addPart(component.id)">
                <span class="component-icon"><Plus :size="16" /></span>
                <span><strong>{{ component.label }}</strong><em>{{ component.description }}</em></span>
              </button>
            </div>
          </aside>

          <div ref="canvasRef" class="circuit-canvas">
            <div class="canvas-grid">
              <svg class="wires-layer" viewBox="0 0 1120 720" aria-label="电路接线">
                <path
                  v-for="wire in visibleWires"
                  :key="wire.id"
                  :d="wirePath(wire)"
                  :stroke="wire.color"
                  :class="{ highlighted: selectedPinId === wire.from || pendingConnection?.partId === wire.partId }"
                  fill="none"
                  stroke-width="3"
                  stroke-linecap="round"
                />
              </svg>

              <div
                class="board-stage"
                :class="selectedBoard"
                :style="{ left: boardPosition.x + 'px', top: boardPosition.y + 'px', width: boardDimensions.width + 'px', height: boardDimensions.height + 'px' }"
                @pointerdown="startBoardDrag"
              >
                <div class="pin-column left">
                  <button
                    v-for="pin in boardPinsLeft"
                    :key="pin.id"
                    type="button"
                    :class="pinButtonClass(pin)"
                    :title="pinTitle(pin)"
                    @pointerdown.stop
                    @click="connectBoardPin(pin)"
                  ><span>{{ pin.label }}</span><i></i></button>
                </div>

                <div class="board-art">
                  <wokwi-arduino-uno v-if="selectedBoard === 'arduino'"></wokwi-arduino-uno>
                  <div v-else class="mcs51-chip"><span>AT89S52</span><small>MCS-51</small></div>
                </div>

                <div class="pin-column right">
                  <button
                    v-for="pin in boardPinsRight"
                    :key="pin.id"
                    type="button"
                    :class="pinButtonClass(pin)"
                    :title="pinTitle(pin)"
                    @pointerdown.stop
                    @click="connectBoardPin(pin)"
                  ><i></i><span>{{ pin.label }}</span></button>
                </div>
              </div>

              <article
                v-for="part in parts"
                :key="part.id"
                class="circuit-part"
                :class="[componentDefinition(part)?.visual, { active: partActive(part) }]"
                :style="{ left: part.x + 'px', top: part.y + 'px', minHeight: partHeight(part) + 'px' }"
                @pointerdown="startDrag($event, part)"
              >
                <header>
                  <span>{{ part.label }}</span>
                  <button type="button" title="删除元件" @pointerdown.stop @click="removePart(part.id)"><Trash2 :size="14" /></button>
                </header>

                <div class="part-visual" @pointerdown.stop>
                  <wokwi-led
                    v-if="componentDefinition(part)?.visual === 'led'"
                    :color="part.state?.color || 'red'"
                    :value="partActive(part) ? 1 : 0"
                  ></wokwi-led>
                  <wokwi-rgb-led v-else-if="componentDefinition(part)?.visual === 'rgb-led'"></wokwi-rgb-led>
                  <wokwi-led-bar-graph v-else-if="componentDefinition(part)?.visual === 'led-bar'"></wokwi-led-bar-graph>
                  <wokwi-pushbutton
                    v-else-if="componentDefinition(part)?.visual === 'button'"
                    :pressed="part.state?.pressed"
                    @pointerdown.stop="setPartPressed(part, true)"
                    @pointerup.stop="setPartPressed(part, false)"
                    @pointerleave.stop="setPartPressed(part, false)"
                  ></wokwi-pushbutton>
                  <wokwi-potentiometer v-else-if="componentDefinition(part)?.visual === 'potentiometer'"></wokwi-potentiometer>
                  <wokwi-photoresistor-sensor v-else-if="componentDefinition(part)?.visual === 'photoresistor'"></wokwi-photoresistor-sensor>
                  <wokwi-buzzer v-else-if="componentDefinition(part)?.visual === 'buzzer'" :has-sound="partActive(part)"></wokwi-buzzer>
                  <wokwi-servo v-else-if="componentDefinition(part)?.visual === 'servo'" :angle="part.state?.angle || 0"></wokwi-servo>
                  <wokwi-hc-sr04 v-else-if="componentDefinition(part)?.visual === 'hc-sr04'" :distance="part.state?.distanceCm || 35"></wokwi-hc-sr04>
                  <wokwi-dht22 v-else-if="componentDefinition(part)?.visual === 'dht22'" :temperature="part.state?.temperature || 24" :humidity="part.state?.humidity || 58"></wokwi-dht22>
                  <wokwi-7segment v-else-if="componentDefinition(part)?.visual === '7segment'"></wokwi-7segment>
                  <wokwi-lcd1602 v-else-if="componentDefinition(part)?.visual === 'lcd1602'"></wokwi-lcd1602>
                  <wokwi-ssd1306 v-else-if="componentDefinition(part)?.visual === 'ssd1306'"></wokwi-ssd1306>
                  <div v-else-if="componentDefinition(part)?.visual === 'relay'" class="relay-visual"><PlugZap :size="28" /></div>
                  <div v-else-if="componentDefinition(part)?.visual === 'serial'" class="serial-visual"><Terminal :size="28" /><b>{{ serialLines.length }}</b></div>
                  <div v-else-if="componentDefinition(part)?.visual === 'crystal'" class="crystal-visual">11.0592<br />MHz</div>
                  <div v-else class="generic-visual"><CircuitBoard :size="30" /></div>
                </div>

                <label v-if="analogControl(part)" class="sensor-control" @pointerdown.stop>
                  <span>{{ analogControl(part).label }}</span>
                  <input v-model.number="part.state[analogControl(part).key]" type="range" :min="analogControl(part).min" :max="analogControl(part).max" />
                  <em>{{ part.state[analogControl(part).key] }}</em>
                </label>

                <div class="terminal-list" @pointerdown.stop>
                  <div v-for="(terminal, terminalIndex) in partTerminals(part)" :key="terminal.id" class="terminal-row">
                    <button
                      type="button"
                      class="terminal-dot"
                      :class="{ pending: isPendingTerminal(part, terminal), connected: Boolean(part.connections?.[terminal.id]) }"
                      :style="{ '--wire-color': terminalColor(terminal, terminalIndex) }"
                      :title="`点击后选择主板引脚连接 ${terminal.label}`"
                      @click="beginTerminalConnection(part, terminal)"
                    ></button>
                    <span>{{ terminal.label }}</span>
                    <select v-model="part.connections[terminal.id]" @change="terminalChanged(part, terminal)">
                      <option value="">未连接</option>
                      <option v-for="pin in compatiblePins(terminal)" :key="pin.id" :value="pin.id">{{ pin.label }}</option>
                    </select>
                  </div>
                </div>
                <footer><span>{{ partStatus(part) }}</span><em>{{ componentDefinition(part)?.category }}</em></footer>
              </article>
            </div>
          </div>

          <div class="runtime-console">
            <section>
              <header><Terminal :size="15" />串口监视器</header>
              <div><p v-for="(line, index) in serialLines" :key="index">{{ line }}</p></div>
            </section>
            <section>
              <header><ListTree :size="15" />执行日志</header>
              <div><p v-for="(line, index) in logs" :key="index" :class="line.type">{{ line.time }} {{ line.text }}</p></div>
            </section>
            <section class="pin-inspector">
              <header><Waypoints :size="15" />引脚检查</header>
              <div v-if="selectedPinInfo">
                <strong>{{ selectedPinInfo.label }} <small>物理脚 {{ selectedPinInfo.physicalPin }}</small></strong>
                <p>{{ selectedPinInfo.note || '通用引脚' }}</p>
                <span v-for="capability in selectedPinInfo.capabilities" :key="capability">{{ capability }}</span>
              </div>
              <div v-else><p>点击主板引脚查看能力和已连接元件。</p></div>
            </section>
          </div>
        </section>
      </section>

      <div v-if="flashDialogOpen" class="dialog-backdrop" @click.self="closeFlashDialog">
        <section class="flash-dialog" role="dialog" aria-modal="true" aria-labelledby="flash-title">
          <header>
            <div><span>VIRTUAL FLASH</span><h2 id="flash-title">编译与虚拟烧录</h2></div>
            <button type="button" title="关闭" @click="closeFlashDialog"><X :size="19" /></button>
          </header>
          <p class="flash-boundary">烧录目标：{{ boardInfo?.mcu }}。此窗口验证教学代码子集、引脚能力和元件接线，不会写入真实开发板。</p>

          <ol class="flash-steps">
            <li v-for="phase in flashPhases" :key="phase.id" :class="phase.status">
              <LoaderCircle v-if="phase.status === 'running'" class="spin" :size="18" />
              <CheckCircle2 v-else-if="phase.status === 'done'" :size="18" />
              <CircleAlert v-else-if="phase.status === 'error'" :size="18" />
              <Circle v-else :size="18" />
              <span><strong>{{ phase.label }}</strong><em>{{ phase.detail }}</em></span>
            </li>
          </ol>

          <div v-if="flashResult" class="flash-result" :class="flashResult.valid ? 'success' : 'failure'">
            <div>
              <CheckCircle2 v-if="flashResult.valid" :size="23" />
              <CircleAlert v-else :size="23" />
              <span>
                <strong>{{ flashResult.valid ? '虚拟固件已就绪' : '烧录检查未通过' }}</strong>
                <em v-if="flashResult.firmware">{{ flashResult.firmware.id }} · 约 {{ flashResult.firmware.bytesEstimated }} bytes</em>
              </span>
            </div>
            <ul v-if="flashDiagnostics.length">
              <li v-for="(diagnostic, index) in flashDiagnostics" :key="`${diagnostic.code}-${index}`" :class="diagnostic.level">
                <span>{{ diagnostic.level === 'error' ? '错误' : '提醒' }}</span>{{ diagnostic.message }}
              </li>
            </ul>
          </div>

          <footer>
            <button type="button" class="secondary" @click="closeFlashDialog">关闭</button>
            <button v-if="!flashResult?.valid" type="button" class="primary" :disabled="flashBusy" @click="compileAndFlash">
              <LoaderCircle v-if="flashBusy" class="spin" :size="17" />
              <Flame v-else :size="17" />
              {{ flashBusy ? '正在检查' : '检查并烧录' }}
            </button>
            <button v-else type="button" class="primary" @click="runFlashedProgram"><Play :size="17" />运行固件</button>
          </footer>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Braces,
  Cable,
  CheckCircle2,
  Circle,
  CircleAlert,
  CircuitBoard,
  Cpu,
  ExternalLink,
  FileCode2,
  Flame,
  LayoutGrid,
  Library,
  ListChecks,
  ListTree,
  LoaderCircle,
  PanelsTopLeft,
  Play,
  PlugZap,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  ShieldCheck,
  Sparkles,
  Square,
  StepForward,
  Terminal,
  Trash2,
  Upload,
  Waypoints,
  X,
} from 'lucide-vue-next'
import '@wokwi/elements'
import { flashMcuProgram, getMcuCatalog, getMcuRecommendations, saveMcuExperiment } from '../services/api.js'
import { markNodeCacheComplete } from '../services/learningPathNodeCache.js'

const route = useRoute()
const isResourceToolPage = computed(() => Boolean(route.meta?.resourceTool))
const mcuBasePath = computed(() => (isResourceToolPage.value ? '/personalized-resources/mcu-simulator' : '/mcu-simulator'))
const selectedBoard = computed(() => String(route.params.board || ''))
const selectedProjectId = computed(() => String(route.params.projectId || ''))

const catalogLoading = ref(true)
const catalogError = ref('')
const catalog = ref({ boards: [], components: [], experiments: [], sources: [], counts: {} })
const recommendations = ref([])
const recommendationMeta = ref({ profileBound: false, historyCount: 0 })
const boards = computed(() => catalog.value.boards || [])
const components = computed(() => catalog.value.components || [])
const experiments = computed(() => catalog.value.experiments || [])
const sources = computed(() => catalog.value.sources || [])
const boardInfo = computed(() => boards.value.find(item => item.id === selectedBoard.value) || null)
const boardProjects = computed(() => experiments.value.filter(item => item.board === selectedBoard.value))
const codeFileName = computed(() => (selectedBoard.value === '8051' ? 'main.asm' : 'sketch.ino'))

const projectQuery = ref('')
const difficultyFilter = ref('')
const difficulties = computed(() => [...new Set(boardProjects.value.map(item => item.difficulty).filter(Boolean))])
const recommendationMap = computed(() => new Map(recommendations.value.map(item => [item.id, item.recommendation || {}])))
const filteredProjects = computed(() => {
  const query = projectQuery.value.trim().toLowerCase()
  const sorted = [...boardProjects.value].sort((left, right) => {
    const leftScore = recommendationMap.value.get(left.id)?.score || 0
    const rightScore = recommendationMap.value.get(right.id)?.score || 0
    return rightScore - leftScore
  })
  return sorted.filter(project => {
    if (difficultyFilter.value && project.difficulty !== difficultyFilter.value) return false
    if (!query) return true
    const text = [project.title, project.summary, ...(project.tags || []), ...(project.knowledgePoints || [])].join(' ').toLowerCase()
    return text.includes(query)
  })
})

const activeProjectId = ref('')
const activeProject = computed(() => experiments.value.find(item => item.id === activeProjectId.value) || null)
const codeText = ref('')
const showDiagramJson = ref(false)
const showGuide = ref(true)
const completedGuideSteps = ref([])
const partsMenuOpen = ref(false)
const parts = ref([])
const logs = ref([])
const serialLines = ref(['Serial monitor ready'])
const canvasRef = ref(null)
const boardPosition = ref({ x: 620, y: 105 })
const selectedPinId = ref('')
const pendingConnection = ref(null)
const componentQuery = ref('')
const componentCategory = ref('全部')

const isRunning = ref(false)
const firmware = ref(null)
const flashDialogOpen = ref(false)
const flashBusy = ref(false)
const flashResult = ref(null)
const flashPhases = ref(createFlashPhases())
const arduinoProgram = ref({ constants: {}, setup: [], loop: [] })
const arduinoRuntime = ref(createArduinoRuntime())
const mcu8051Program = ref({ instructions: [], labels: {}, size: 0 })
const mcu8051State = ref(create8051State())
let runTimer = null
let dragState = null
let boardDragState = null
let partSeed = 1
let loadingProject = false

const guideSteps = computed(() => activeProject.value?.steps || [])
const guideProgress = computed(() => ({
  done: completedGuideSteps.value.length,
  total: guideSteps.value.length,
}))

const componentIndex = computed(() => new Map(components.value.map(item => [item.id, item])))
const componentCategories = computed(() => ['全部', ...new Set(components.value.map(item => item.category))])
const filteredComponents = computed(() => {
  const query = componentQuery.value.trim().toLowerCase()
  return components.value.filter(component => {
    if (componentCategory.value !== '全部' && component.category !== componentCategory.value) return false
    return !query || `${component.label} ${component.description} ${component.category}`.toLowerCase().includes(query)
  })
})
const boardPins = computed(() => boardInfo.value?.pins || [])
const boardPinsLeft = computed(() => boardPins.value.filter(pin => pin.side === 'left').sort((a, b) => a.order - b.order))
const boardPinsRight = computed(() => boardPins.value.filter(pin => pin.side === 'right').sort((a, b) => a.order - b.order))
const boardDimensions = computed(() => (selectedBoard.value === '8051' ? { width: 270, height: 540 } : { width: 300, height: 450 }))
const selectedPinInfo = computed(() => boardPins.value.find(pin => pin.id === selectedPinId.value) || null)

const lineNumbers = computed(() => {
  const value = showDiagramJson.value ? diagramJson.value : codeText.value
  return Array.from({ length: Math.max(1, value.split('\n').length) }, (_, index) => index + 1).join('\n')
})
const diagramJson = computed(() => JSON.stringify({
  schema: 'mcu-lab-diagram/v2',
  board: selectedBoard.value,
  projectId: activeProjectId.value,
  boardPosition: boardPosition.value,
  parts: parts.value.map(part => ({
    id: part.id,
    componentId: part.componentId,
    label: part.label,
    x: part.x,
    y: part.y,
    connections: part.connections,
    state: part.state,
  })),
}, null, 2))
const visibleWires = computed(() => {
  const wires = []
  parts.value.forEach(part => {
    partTerminals(part).forEach((terminal, terminalIndex) => {
      const pin = part.connections?.[terminal.id]
      if (!pin) return
      wires.push({
        id: `${part.id}-${terminal.id}`,
        partId: part.id,
        terminalId: terminal.id,
        terminalIndex,
        from: pin,
        color: terminalColor(terminal, terminalIndex),
      })
    })
  })
  return wires
})
const flashDiagnostics = computed(() => {
  const errors = (flashResult.value?.diagnostics?.errors || []).map(item => ({ ...item, level: 'error' }))
  const warnings = (flashResult.value?.diagnostics?.warnings || []).map(item => ({ ...item, level: 'warning' }))
  return [...errors, ...warnings]
})

onMounted(loadCatalog)

watch(
  () => [catalogLoading.value, selectedBoard.value, selectedProjectId.value],
  ([loading, board, projectId]) => {
    if (loading) return
    if (projectId) loadProjectById(projectId)
    loadRecommendations(board)
  },
  { immediate: true },
)

watch(codeText, () => {
  if (!loadingProject) {
    firmware.value = null
    flashResult.value = null
  }
})

async function loadCatalog() {
  catalogLoading.value = true
  catalogError.value = ''
  try {
    catalog.value = await getMcuCatalog()
  } catch (error) {
    catalogError.value = error?.response?.data?.msg || error?.message || '无法连接 MCU 实验目录接口'
  } finally {
    catalogLoading.value = false
  }
}

async function loadRecommendations(board = '') {
  if (catalogLoading.value) return
  try {
    const result = await getMcuRecommendations({
      board,
      topic: route.query.topic || route.query.keyword || '',
      weakPoint: route.query.weakPoint || route.query.requirements || '',
      learningGoal: route.query.learningGoal || '',
      limit: board ? 12 : 5,
    })
    recommendations.value = result.recommendations || []
    recommendationMeta.value = result
  } catch {
    recommendations.value = []
  }
}

function boardName(boardId) {
  return boards.value.find(item => item.id === boardId)?.title || boardId
}

function boardExperimentCount(boardId) {
  return experiments.value.filter(item => item.board === boardId).length
}

function recommendationFor(projectId) {
  return recommendationMap.value.get(projectId) || null
}

function projectSources(project) {
  return (project?.sourceIds || []).map(id => sources.value.find(item => item.id === id)).filter(Boolean)
}

function componentDefinition(part) {
  return componentIndex.value.get(part?.componentId || part?.type) || null
}

function partTerminals(part) {
  return componentDefinition(part)?.terminals || []
}

function loadProjectById(projectId) {
  const project = experiments.value.find(item => item.id === projectId)
  if (!project || activeProjectId.value === project.id) return
  loadProject(project)
}

function loadProject(project) {
  stopRun(false)
  loadingProject = true
  activeProjectId.value = project.id
  codeText.value = project.code || ''
  showGuide.value = true
  showDiagramJson.value = false
  completedGuideSteps.value = loadGuideProgress(project.id)
  parts.value = (project.parts || []).map(part => ({
    id: String(part.id || `part-${Date.now()}-${partSeed++}`),
    componentId: part.componentId || part.type,
    label: part.label || part.componentId || part.type || '元件',
    x: Number(part.x) || 0,
    y: Number(part.y) || 0,
    connections: { ...(part.connections || {}) },
    state: { ...(part.state || {}) },
  }))
  boardPosition.value = selectedBoard.value === '8051' ? { x: 630, y: 70 } : { x: 620, y: 110 }
  const saved = loadSavedDiagram(project.id)
  if (saved) {
    boardPosition.value = saved.boardPosition || boardPosition.value
    parts.value = Array.isArray(saved.parts) ? saved.parts : parts.value
  }
  logs.value = [{ type: 'info', time: currentTime(), text: `已加载：${project.title}` }]
  serialLines.value = ['Serial monitor ready']
  selectedPinId.value = ''
  pendingConnection.value = null
  firmware.value = null
  flashResult.value = null
  resetRuntimeState()
  partSeed = Math.max(1, parts.value.length + 1)
  nextTick(() => {
    loadingProject = false
    if (canvasRef.value) {
      canvasRef.value.scrollLeft = Math.max(
        0,
        boardPosition.value.x + boardDimensions.value.width - canvasRef.value.clientWidth + 34,
      )
      canvasRef.value.scrollTop = 0
    }
  })
}

function showCode() {
  showGuide.value = false
  showDiagramJson.value = false
}

function showDiagram() {
  showGuide.value = false
  showDiagramJson.value = true
}

function openGuide() {
  showGuide.value = true
  showDiagramJson.value = false
}

function guideProgressKey(projectId = activeProjectId.value) {
  return `mcu-guide-v1-${selectedBoard.value}-${projectId}`
}

function loadGuideProgress(projectId) {
  try {
    const parsed = JSON.parse(localStorage.getItem(guideProgressKey(projectId)) || '[]')
    return Array.isArray(parsed) ? parsed.filter(index => Number.isInteger(index)) : []
  } catch {
    return []
  }
}

function persistGuideProgress() {
  if (!activeProjectId.value) return
  localStorage.setItem(guideProgressKey(), JSON.stringify(completedGuideSteps.value))
}

function isGuideStepDone(index) {
  return completedGuideSteps.value.includes(index)
}

function toggleGuideStep(index) {
  completedGuideSteps.value = isGuideStepDone(index)
    ? completedGuideSteps.value.filter(item => item !== index)
    : [...completedGuideSteps.value, index].sort((left, right) => left - right)
  persistGuideProgress()
}

function completeGuideThrough(stepId) {
  const target = guideSteps.value.findIndex(step => step.id === stepId)
  if (target < 0) return
  completedGuideSteps.value = Array.from(new Set([
    ...completedGuideSteps.value,
    ...Array.from({ length: target + 1 }, (_item, index) => index),
  ])).sort((left, right) => left - right)
  persistGuideProgress()
}

function loadSavedDiagram(projectId) {
  try {
    const raw = localStorage.getItem(`mcu-diagram-v2-${selectedBoard.value}-${projectId}`)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function saveDiagram() {
  localStorage.setItem(`mcu-diagram-v2-${selectedBoard.value}-${activeProjectId.value}`, diagramJson.value)
  addLog('布局与接线已保存到本地。', 'success')
}

function currentTime() {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

function addLog(text, type = 'info') {
  logs.value.push({ type, time: currentTime(), text })
  if (logs.value.length > 100) logs.value.shift()
}

function compatiblePins(terminal) {
  const accepts = new Set(terminal.accepts || [])
  return boardPins.value.filter(pin => (pin.capabilities || []).some(capability => accepts.has(capability)))
}

function beginTerminalConnection(part, terminal) {
  pendingConnection.value = {
    partId: part.id,
    terminalId: terminal.id,
    label: `${part.label}.${terminal.label}`,
    accepts: terminal.accepts || [],
  }
}

function isPendingTerminal(part, terminal) {
  return pendingConnection.value?.partId === part.id && pendingConnection.value?.terminalId === terminal.id
}

function connectBoardPin(pin) {
  selectedPinId.value = pin.id
  if (!pendingConnection.value) return
  const accepts = new Set(pendingConnection.value.accepts || [])
  if (!(pin.capabilities || []).some(capability => accepts.has(capability))) {
    addLog(`${pin.id} 不满足 ${pendingConnection.value.label} 的能力要求。`, 'error')
    return
  }
  const part = parts.value.find(item => item.id === pendingConnection.value.partId)
  if (!part) return
  part.connections[pendingConnection.value.terminalId] = pin.id
  addLog(`${pendingConnection.value.label} 已连接 ${pin.id}。`, 'success')
  pendingConnection.value = null
  invalidateFirmware()
}

function terminalChanged(part, terminal) {
  selectedPinId.value = part.connections?.[terminal.id] || ''
  pendingConnection.value = null
  invalidateFirmware()
}

function pinButtonClass(pin) {
  const connected = parts.value.some(part => Object.values(part.connections || {}).includes(pin.id))
  return {
    connected,
    selected: selectedPinId.value === pin.id,
    compatible: pendingConnection.value && (pin.capabilities || []).some(capability => pendingConnection.value.accepts.includes(capability)),
    incompatible: pendingConnection.value && !(pin.capabilities || []).some(capability => pendingConnection.value.accepts.includes(capability)),
  }
}

function pinTitle(pin) {
  return `${pin.id} · 物理脚 ${pin.physicalPin} · ${(pin.capabilities || []).join(' / ')}${pin.note ? ` · ${pin.note}` : ''}`
}

function addPart(componentId) {
  const component = componentIndex.value.get(componentId)
  if (!component) return
  const usedPins = new Set(parts.value.flatMap(part => Object.values(part.connections || {})))
  const connections = {}
  component.terminals.forEach(terminal => {
    const options = compatiblePins(terminal)
    const sharedRail = (terminal.accepts || []).includes('ground')
      || (terminal.accepts || []).some(item => item.startsWith('power-'))
    const available = sharedRail ? options[0] : options.find(pin => !usedPins.has(pin.id))
    if (available) {
      connections[terminal.id] = available.id
      if (!sharedRail) usedPins.add(available.id)
    }
  })
  const index = parts.value.length
  const part = {
    id: `part-${Date.now()}-${partSeed++}`,
    componentId,
    label: component.label,
    x: 70 + (index % 3) * 225,
    y: 65 + (index % 3) * 190,
    connections,
    state: defaultComponentState(componentId),
  }
  parts.value.push(part)
  partsMenuOpen.value = false
  invalidateFirmware()
  const missingRequired = component.terminals.filter(terminal => terminal.required && !connections[terminal.id]).length
  addLog(
    missingRequired
      ? `已添加元件：${component.label}，${missingRequired} 个必接端子需要手动选择引脚。`
      : `已添加元件：${component.label}`,
    missingRequired ? 'warning' : 'info',
  )
}

function defaultComponentState(componentId) {
  if (['potentiometer', 'photoresistor'].includes(componentId)) return { value: 512 }
  if (componentId === 'hc-sr04') return { distanceCm: 35 }
  if (componentId === 'dht22') return { temperature: 24, humidity: 58 }
  if (componentId === 'servo') return { angle: 90 }
  return {}
}

function removePart(partId) {
  parts.value = parts.value.filter(part => part.id !== partId)
  if (pendingConnection.value?.partId === partId) pendingConnection.value = null
  invalidateFirmware()
}

function invalidateFirmware() {
  firmware.value = null
  flashResult.value = null
}

function startDrag(event, part) {
  if (!canvasRef.value || event.target.closest('button, select, input, a')) return
  const rect = canvasRef.value.getBoundingClientRect()
  dragState = { id: part.id, offsetX: event.clientX - rect.left + canvasRef.value.scrollLeft - part.x, offsetY: event.clientY - rect.top + canvasRef.value.scrollTop - part.y }
  window.addEventListener('pointermove', dragMove)
  window.addEventListener('pointerup', stopDrag, { once: true })
}

function dragMove(event) {
  if (!dragState || !canvasRef.value) return
  const rect = canvasRef.value.getBoundingClientRect()
  const part = parts.value.find(item => item.id === dragState.id)
  if (!part) return
  part.x = clamp(event.clientX - rect.left + canvasRef.value.scrollLeft - dragState.offsetX, 24, 870)
  part.y = clamp(event.clientY - rect.top + canvasRef.value.scrollTop - dragState.offsetY, 24, 560)
}

function stopDrag() {
  dragState = null
  window.removeEventListener('pointermove', dragMove)
}

function startBoardDrag(event) {
  if (!canvasRef.value || event.target.closest('button')) return
  const rect = canvasRef.value.getBoundingClientRect()
  boardDragState = { offsetX: event.clientX - rect.left + canvasRef.value.scrollLeft - boardPosition.value.x, offsetY: event.clientY - rect.top + canvasRef.value.scrollTop - boardPosition.value.y }
  window.addEventListener('pointermove', boardDragMove)
  window.addEventListener('pointerup', stopBoardDrag, { once: true })
}

function boardDragMove(event) {
  if (!boardDragState || !canvasRef.value) return
  const rect = canvasRef.value.getBoundingClientRect()
  boardPosition.value = {
    x: clamp(event.clientX - rect.left + canvasRef.value.scrollLeft - boardDragState.offsetX, 360, 810),
    y: clamp(event.clientY - rect.top + canvasRef.value.scrollTop - boardDragState.offsetY, 34, 230),
  }
}

function stopBoardDrag() {
  boardDragState = null
  window.removeEventListener('pointermove', boardDragMove)
}

function wirePath(wire) {
  const part = parts.value.find(item => item.id === wire.partId)
  if (!part) return ''
  const start = boardPinPoint(wire.from)
  const end = partTerminalPoint(part, wire.terminalIndex)
  const midX = (start.x + end.x) / 2
  return `M ${start.x} ${start.y} C ${midX} ${start.y}, ${midX} ${end.y}, ${end.x} ${end.y}`
}

function boardPinPoint(pinId) {
  const pin = boardPins.value.find(item => item.id === pinId)
  if (!pin) return { x: boardPosition.value.x, y: boardPosition.value.y }
  const sidePins = pin.side === 'left' ? boardPinsLeft.value : boardPinsRight.value
  const index = Math.max(0, sidePins.findIndex(item => item.id === pin.id))
  const gap = (boardDimensions.value.height - 52) / Math.max(1, sidePins.length - 1)
  return {
    x: boardPosition.value.x + (pin.side === 'left' ? 0 : boardDimensions.value.width),
    y: boardPosition.value.y + 26 + index * gap,
  }
}

function partTerminalPoint(part, terminalIndex) {
  const onLeftOfBoard = part.x < boardPosition.value.x
  const controlOffset = analogControl(part) ? 44 : 0
  return {
    x: part.x + (onLeftOfBoard ? 210 : 0),
    y: part.y + 132 + controlOffset + terminalIndex * 29,
  }
}

function terminalColor(terminal, index) {
  const accepts = terminal.accepts || []
  if (accepts.includes('ground')) return '#111827'
  if (accepts.some(item => item.startsWith('power-'))) return '#dc2626'
  if (accepts.some(item => item.startsWith('i2c-'))) return index % 2 ? '#7c3aed' : '#0891b2'
  const palette = ['#2563eb', '#16a34a', '#d97706', '#db2777', '#7c3aed', '#0891b2', '#ea580c', '#4f46e5']
  return palette[index % palette.length]
}

function partHeight(part) {
  return 170 + partTerminals(part).length * 31 + (analogControl(part) ? 44 : 0)
}

function analogControl(part) {
  const visual = componentDefinition(part)?.visual
  if (['potentiometer', 'photoresistor'].includes(visual)) return { key: 'value', label: '模拟值', min: 0, max: 1023 }
  if (visual === 'hc-sr04') return { key: 'distanceCm', label: '距离 cm', min: 2, max: 400 }
  if (visual === 'dht22') return { key: 'temperature', label: '温度 °C', min: -10, max: 60 }
  return null
}

function setPartPressed(part, pressed) {
  part.state.pressed = pressed
}

function partSignalPins(part) {
  return partTerminals(part)
    .filter(terminal => !(terminal.accepts || []).includes('ground') && !(terminal.accepts || []).some(item => item.startsWith('power-')))
    .map(terminal => part.connections?.[terminal.id])
    .filter(Boolean)
}

function partActive(part) {
  const visual = componentDefinition(part)?.visual
  if (visual === 'button') return Boolean(part.state?.pressed)
  if (visual === 'servo') return Number(part.state?.angle || 0) > 0
  if (visual === 'buzzer') return Boolean(part.state?.active || partSignalPins(part).some(readOutputPin))
  if (visual === 'relay') return partSignalPins(part).some(readOutputPin)
  if (visual === 'led-bar' || visual === '7segment' || visual === 'rgb-led') return partSignalPins(part).some(readOutputPin)
  if (visual === 'led') return partSignalPins(part).some(readOutputPin)
  return false
}

function partStatus(part) {
  const visual = componentDefinition(part)?.visual
  if (visual === 'button') return part.state?.pressed ? 'LOW · pressed' : 'HIGH · released'
  if (visual === 'servo') return `${Math.round(part.state?.angle || 0)}°`
  if (visual === 'hc-sr04') return `${part.state?.distanceCm || 35} cm`
  if (visual === 'dht22') return `${part.state?.temperature || 24}°C / ${part.state?.humidity || 58}%`
  if (visual === 'serial') return `${serialLines.value.length} lines`
  if (visual === 'ssd1306' || visual === 'lcd1602') return part.state?.text || 'ready'
  return partActive(part) ? 'HIGH' : 'LOW'
}

function readOutputPin(pin) {
  if (selectedBoard.value === '8051') return Boolean(read8051Pin(pin))
  return Boolean(arduinoRuntime.value.pins[pin]?.value || arduinoRuntime.value.pins[pin]?.pwm)
}

function createFlashPhases() {
  return [
    { id: 'source', label: '代码检查', detail: '检查入口、语句和指令集', status: 'idle' },
    { id: 'wiring', label: '接线检查', detail: '核对端子、电源和引脚能力', status: 'idle' },
    { id: 'firmware', label: '生成虚拟固件', detail: '创建可追踪固件指纹', status: 'idle' },
    { id: 'flash', label: '写入教学内核', detail: '准备浏览器仿真运行时', status: 'idle' },
  ]
}

function openFlashDialog() {
  flashDialogOpen.value = true
  flashResult.value = null
  flashPhases.value = createFlashPhases()
}

function closeFlashDialog() {
  if (!flashBusy.value) flashDialogOpen.value = false
}

async function compileAndFlash() {
  flashBusy.value = true
  flashResult.value = null
  flashPhases.value = createFlashPhases()
  try {
    flashPhases.value[0].status = 'running'
    await nextTick()
    const result = await flashMcuProgram({
      board: selectedBoard.value,
      projectId: activeProjectId.value,
      code: codeText.value,
      parts: parts.value,
    })
    flashPhases.value[0].status = result.diagnostics?.errors?.some(item => item.code.includes('SOURCE') || item.code.includes('ARDUINO') || item.code.includes('8051') || item.code.includes('SETUP') || item.code.includes('LOOP')) ? 'error' : 'done'
    flashPhases.value[1].status = result.diagnostics?.errors?.some(item => item.code.includes('PIN') || item.code.includes('TERMINAL') || item.code.includes('COMPONENT')) ? 'error' : 'done'
    flashPhases.value[2].status = result.valid ? 'done' : 'error'
    flashPhases.value[3].status = result.valid ? 'done' : 'idle'
    flashResult.value = result
    if (result.valid) {
      if (!prepareProgram()) throw new Error('前端解释器未能载入程序')
      firmware.value = result.firmware
      completeGuideThrough('flash')
      addLog(`虚拟烧录完成：${result.firmware.id}`, 'success')
      await recordExperiment(true, result)
      markLearningNodeComplete()
    } else {
      addLog(`烧录检查发现 ${result.diagnostics?.errors?.length || 0} 个错误。`, 'error')
    }
  } catch (error) {
    flashPhases.value.find(phase => phase.status === 'running').status = 'error'
    flashResult.value = {
      valid: false,
      diagnostics: { errors: [{ code: 'FLASH_REQUEST_FAILED', message: error?.response?.data?.msg || error?.message || '烧录服务不可用' }], warnings: [] },
    }
  } finally {
    flashBusy.value = false
  }
}

async function recordExperiment(passed, result) {
  try {
    await saveMcuExperiment({
      experiment_id: activeProjectId.value,
      experiment_name: activeProject.value?.title,
      passed,
      weak_points: passed ? [] : (result?.diagnostics?.errors || []).map(item => item.message),
      run_data: {
        board: selectedBoard.value,
        firmwareId: result?.firmware?.id,
        partCount: parts.value.length,
        wireCount: visibleWires.value.length,
        diagnostics: result?.diagnostics,
      },
    })
  } catch (error) {
    addLog(`实验记录保存失败：${error?.message || '网络异常'}`, 'warning')
  }
}

function markLearningNodeComplete() {
  const cacheKey = String(route.query.cacheKey || '').trim()
  if (!cacheKey || !activeProject.value) return
  markNodeCacheComplete(cacheKey, {
    resourceType: 'mcu',
    title: activeProject.value.title,
    board: selectedBoard.value,
    projectId: activeProject.value.id,
    firmwareId: firmware.value?.id,
    route: route.fullPath,
  })
}

function runFlashedProgram() {
  flashDialogOpen.value = false
  startRun()
}

function toggleRun() {
  if (isRunning.value) stopRun()
  else if (!firmware.value) openFlashDialog()
  else startRun()
}

function stepOnce() {
  if (!firmware.value) {
    openFlashDialog()
    return
  }
  stopRun(false)
  if (selectedBoard.value === '8051') step8051()
  else {
    const wait = stepArduinoLoop()
    addLog(`Arduino loop 单步完成${wait ? `，延时 ${wait}ms` : ''}`)
  }
}

function startRun() {
  if (!firmware.value || !prepareProgram()) return
  isRunning.value = true
  addLog('仿真开始。', 'success')
  if (selectedBoard.value === '8051') schedule8051Batch()
  else {
    runArduinoSetup()
    scheduleArduinoStep(30)
  }
}

function stopRun(shouldLog = true) {
  isRunning.value = false
  if (runTimer) window.clearTimeout(runTimer)
  runTimer = null
  if (shouldLog) addLog('仿真已停止。')
}

function resetSimulation() {
  stopRun(false)
  resetRuntimeState()
  serialLines.value = ['Serial monitor ready']
  addLog('MCU、端口和外设状态已复位。')
}

function resetRuntimeState() {
  arduinoRuntime.value = createArduinoRuntime()
  arduinoProgram.value = { constants: {}, setup: [], loop: [] }
  mcu8051State.value = create8051State()
  mcu8051Program.value = { instructions: [], labels: {}, size: 0 }
  parts.value.forEach(part => {
    if (componentDefinition(part)?.visual === 'button') part.state.pressed = false
    if (componentDefinition(part)?.visual === 'buzzer') part.state.active = false
  })
}

function prepareProgram() {
  try {
    if (selectedBoard.value === '8051') {
      mcu8051Program.value = assemble8051(codeText.value)
      if (!mcu8051Program.value.size) throw new Error('未找到可执行的 8051 指令')
      mcu8051State.value = create8051State()
    } else {
      arduinoProgram.value = parseArduinoProgram(codeText.value)
      if (!arduinoProgram.value.loop.length) throw new Error('未找到 loop() 中的可执行语句')
      arduinoRuntime.value = createArduinoRuntime(arduinoProgram.value.constants)
    }
    return true
  } catch (error) {
    addLog(`程序载入失败：${error.message}`, 'error')
    return false
  }
}

function createArduinoRuntime(constants = {}) {
  const pins = {}
  for (let index = 0; index < 14; index += 1) pins[`D${index}`] = { mode: 'INPUT', value: false, pwm: 0 }
  for (let index = 0; index < 6; index += 1) pins[`A${index}`] = { mode: 'INPUT', value: false, pwm: 0 }
  return { loopPc: 0, setupPc: 0, pins, vars: {}, constants: { ...constants }, servoPins: {}, displayAddress: 0x3c, warnings: {} }
}

function parseArduinoProgram(code) {
  const cleaned = code.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '')
  const constants = {}
  cleaned.replace(/(?:const\s+)?(?:int|long|byte|bool)\s+([A-Za-z_]\w*)\s*=\s*([^;]+);/g, (_match, name, value) => {
    const numeric = Number(value.trim())
    constants[name] = Number.isNaN(numeric) ? value.trim() : numeric
    return _match
  })
  return { constants, setup: extractFunctionStatements(cleaned, 'setup'), loop: extractFunctionStatements(cleaned, 'loop') }
}

function extractFunctionStatements(code, name) {
  const start = code.search(new RegExp(`void\\s+${name}\\s*\\([^)]*\\)\\s*\\{`))
  if (start < 0) return []
  const braceStart = code.indexOf('{', start)
  let depth = 0
  let end = braceStart
  for (; end < code.length; end += 1) {
    if (code[end] === '{') depth += 1
    else if (code[end] === '}') {
      depth -= 1
      if (depth === 0) break
    }
  }
  return code.slice(braceStart + 1, end).replace(/[{}]/g, ' ').split(';').map(item => item.trim()).filter(Boolean)
}

function runArduinoSetup() {
  const runtime = arduinoRuntime.value
  arduinoProgram.value.setup.forEach(statement => executeArduinoStatement(runtime, statement))
}

function scheduleArduinoStep(delay) {
  if (!isRunning.value) return
  runTimer = window.setTimeout(() => {
    if (!isRunning.value) return
    scheduleArduinoStep(stepArduinoLoop() || 70)
  }, Math.max(35, Math.min(Number(delay) || 35, 1500)))
}

function stepArduinoLoop() {
  const runtime = arduinoRuntime.value
  const loop = arduinoProgram.value.loop
  if (!loop.length) return 100
  const statement = loop[runtime.loopPc]
  runtime.loopPc = (runtime.loopPc + 1) % loop.length
  return executeArduinoStatement(runtime, statement)
}

function executeArduinoStatement(runtime, statement) {
  const text = statement.trim()
  let match = text.match(/^pinMode\s*\((.+?),\s*(INPUT_PULLUP|INPUT|OUTPUT)\s*\)$/)
  if (match) {
    const pin = resolvePin(match[1], runtime)
    ensureArduinoPin(runtime, pin).mode = match[2]
    return 0
  }
  match = text.match(/^delay\s*\((.+?)\)$/)
  if (match) return Number(resolveValue(match[1], runtime)) || 0
  match = text.match(/^delayMicroseconds\s*\((.+?)\)$/)
  if (match) return 0
  if (/^Serial\.begin\s*\(/.test(text)) return 0
  match = text.match(/^Serial\.println\s*\(([\s\S]+)\)$/)
  if (match) {
    serialLines.value.push(String(resolveValue(match[1], runtime)))
    if (serialLines.value.length > 60) serialLines.value.shift()
    return 0
  }
  match = text.match(/^(?:int|bool|boolean|long|float|byte)?\s*([A-Za-z_]\w*)\s*=\s*(.+)$/)
  if (match && !/^(digitalWrite|analogWrite)/.test(text)) {
    runtime.vars[match[1]] = resolveValue(match[2], runtime)
    return 0
  }
  match = text.match(/^digitalWrite\s*\((.+?),\s*(.+)\)$/)
  if (match) {
    const pin = resolvePin(match[1], runtime)
    const target = ensureArduinoPin(runtime, pin)
    target.value = Boolean(resolveValue(match[2], runtime))
    target.pwm = 0
    return 0
  }
  match = text.match(/^analogWrite\s*\((.+?),\s*(.+)\)$/)
  if (match) {
    const pin = resolvePin(match[1], runtime)
    const target = ensureArduinoPin(runtime, pin)
    target.pwm = clamp(Number(resolveValue(match[2], runtime)) || 0, 0, 255)
    target.value = target.pwm > 0
    return 0
  }
  match = text.match(/^([A-Za-z_]\w*)\.attach\s*\((.+)\)$/)
  if (match) {
    runtime.servoPins[match[1]] = resolvePin(match[2], runtime)
    return 0
  }
  match = text.match(/^([A-Za-z_]\w*)\.write\s*\((.+)\)$/)
  if (match) {
    const pin = runtime.servoPins[match[1]]
    const angle = clamp(Number(resolveValue(match[2], runtime)) || 0, 0, 180)
    parts.value.filter(part => componentDefinition(part)?.visual === 'servo' && part.connections?.SIG === pin).forEach(part => { part.state.angle = angle })
    return 0
  }
  match = text.match(/^tone\s*\((.+?)(?:,\s*(.+?))?\)$/)
  if (match) {
    const pin = resolvePin(match[1], runtime)
    parts.value.filter(part => componentDefinition(part)?.visual === 'buzzer' && part.connections?.SIG === pin).forEach(part => { part.state.active = true; part.state.frequency = Number(resolveValue(match[2] || '440', runtime)) })
    return 0
  }
  match = text.match(/^noTone\s*\((.+?)\)$/)
  if (match) {
    const pin = resolvePin(match[1], runtime)
    parts.value.filter(part => componentDefinition(part)?.visual === 'buzzer' && part.connections?.SIG === pin).forEach(part => { part.state.active = false })
    return 0
  }
  match = text.match(/^i2cDisplayBegin\s*\((.+)\)$/)
  if (match) { runtime.displayAddress = Number(resolveValue(match[1], runtime)); return 0 }
  match = text.match(/^i2cDisplayText\s*\((.+)\)$/)
  if (match) {
    const value = String(resolveValue(match[1], runtime))
    parts.value.filter(part => componentDefinition(part)?.visual === 'ssd1306').forEach(part => { part.state.text = value })
    return 0
  }
  addLog(`教学解释器跳过语句：${text}`, 'warning')
  return 0
}

function ensureArduinoPin(runtime, pin) {
  if (!runtime.pins[pin]) runtime.pins[pin] = { mode: 'INPUT', value: false, pwm: 0 }
  return runtime.pins[pin]
}

function resolvePin(expression, runtime) {
  const value = resolveValue(expression, runtime)
  if (/^[DA]\d+$/.test(String(value))) return String(value)
  return `D${Number(value) || 0}`
}

function resolveValue(expression, runtime) {
  let text = String(expression ?? '').trim()
  while (text.startsWith('(') && text.endsWith(')')) text = text.slice(1, -1).trim()
  const ternary = splitTernary(text)
  if (ternary) return resolveValue(ternary.condition, runtime) ? resolveValue(ternary.truthy, runtime) : resolveValue(ternary.falsy, runtime)
  for (const operator of ['==', '!=', '>=', '<=', '>', '<']) {
    const pair = splitTopLevel(text, operator)
    if (!pair) continue
    const left = resolveValue(pair[0], runtime)
    const right = resolveValue(pair[1], runtime)
    if (operator === '==') return left === right
    if (operator === '!=') return left !== right
    if (operator === '>=') return Number(left) >= Number(right)
    if (operator === '<=') return Number(left) <= Number(right)
    if (operator === '>') return Number(left) > Number(right)
    return Number(left) < Number(right)
  }
  for (const operator of ['+', '-', '*', '/', '%']) {
    const pair = splitTopLevel(text, operator)
    if (!pair) continue
    const left = Number(resolveValue(pair[0], runtime)) || 0
    const right = Number(resolveValue(pair[1], runtime)) || 0
    if (operator === '+') return left + right
    if (operator === '-') return left - right
    if (operator === '*') return left * right
    if (operator === '/') return right ? left / right : 0
    return right ? left % right : 0
  }
  let match = text.match(/^digitalRead\s*\((.+)\)$/)
  if (match) return readArduinoInput(resolvePin(match[1], runtime)) ? 'HIGH' : 'LOW'
  match = text.match(/^analogRead\s*\((.+)\)$/)
  if (match) return readAnalogInput(resolvePin(match[1], runtime))
  match = text.match(/^map\s*\((.+),\s*(.+),\s*(.+),\s*(.+),\s*(.+)\)$/)
  if (match) {
    const [value, inMin, inMax, outMin, outMax] = match.slice(1).map(item => Number(resolveValue(item, runtime)))
    return Math.round((value - inMin) * (outMax - outMin) / Math.max(1, inMax - inMin) + outMin)
  }
  match = text.match(/^pulseIn\s*\((.+?),\s*(.+)\)$/)
  if (match) {
    const pin = resolvePin(match[1], runtime)
    const sensor = parts.value.find(part => componentDefinition(part)?.visual === 'hc-sr04' && part.connections?.ECHO === pin)
    return (sensor?.state?.distanceCm || 35) * 58
  }
  match = text.match(/^dhtRead(Humidity|Temperature)\s*\((.+)\)$/)
  if (match) {
    const pin = resolvePin(match[2], runtime)
    const sensor = parts.value.find(part => componentDefinition(part)?.visual === 'dht22' && part.connections?.DATA === pin)
    return match[1] === 'Humidity' ? (sensor?.state?.humidity || 58) : (sensor?.state?.temperature || 24)
  }
  if (text === 'HIGH' || text === 'true') return true
  if (text === 'LOW' || text === 'false') return false
  const stringMatch = text.match(/^["']([\s\S]*)["']$/)
  if (stringMatch) return stringMatch[1]
  if (/^0x[0-9a-f]+$/i.test(text)) return Number.parseInt(text, 16)
  if (/^-?\d+(?:\.\d+)?$/.test(text)) return Number(text)
  if (text in runtime.vars) return runtime.vars[text]
  if (text in runtime.constants) return runtime.constants[text]
  if (/^A[0-5]$/.test(text)) return text
  return text
}

function splitTopLevel(text, operator) {
  let depth = 0
  let quote = ''
  for (let index = 0; index <= text.length - operator.length; index += 1) {
    const char = text[index]
    if (quote) { if (char === quote && text[index - 1] !== '\\') quote = ''; continue }
    if (char === '"' || char === "'") { quote = char; continue }
    if (char === '(') depth += 1
    else if (char === ')') depth -= 1
    else if (depth === 0 && text.slice(index, index + operator.length) === operator) return [text.slice(0, index).trim(), text.slice(index + operator.length).trim()]
  }
  return null
}

function splitTernary(text) {
  const question = splitTopLevel(text, '?')
  if (!question) return null
  const branches = splitTopLevel(question[1], ':')
  return branches ? { condition: question[0], truthy: branches[0], falsy: branches[1] } : null
}

function readArduinoInput(pin) {
  const button = parts.value.find(part => componentDefinition(part)?.visual === 'button' && part.connections?.SIG === pin)
  if (button) {
    const pinState = arduinoRuntime.value.pins[pin]
    if (pinState?.mode !== 'INPUT_PULLUP') {
      const warningKey = `floating-button-${pin}`
      if (!arduinoRuntime.value.warnings[warningKey]) {
        arduinoRuntime.value.warnings[warningKey] = true
        addLog(`${pin} 上的按键输入未启用 INPUT_PULLUP，释放时电平悬空；仿真按 LOW 处理。`, 'warning')
      }
      return false
    }
    return !button.state?.pressed
  }
  return Boolean(arduinoRuntime.value.pins[pin]?.value)
}

function readAnalogInput(pin) {
  const sensor = parts.value.find(part => ['potentiometer', 'photoresistor'].includes(componentDefinition(part)?.visual) && Object.values(part.connections || {}).includes(pin))
  return clamp(Number(sensor?.state?.value ?? 512), 0, 1023)
}

function assemble8051(code) {
  const labels = {}
  const instructions = []
  code.split(/\r?\n/).forEach(sourceLine => {
    let line = sourceLine.replace(/;.*/, '').trim()
    if (!line || /^(ORG|END|DB)\b/i.test(line)) return
    const label = line.match(/^([A-Za-z_]\w*):\s*(.*)$/)
    if (label) {
      labels[label[1].toUpperCase()] = instructions.length
      line = label[2].trim()
      if (!line) return
    }
    const [op, ...rest] = line.split(/\s+/)
    instructions.push({ op: op.toUpperCase(), args: splitAsmArgs(rest.join(' ')), raw: line })
  })
  return { instructions, labels, size: instructions.length }
}

function splitAsmArgs(text) {
  return text.split(',').map(item => item.trim()).filter(Boolean)
}

function create8051State() {
  return { pc: 0, a: 0, b: 0, sp: 0x07, dptr: 0, psw: 0, carry: 0, p0: 0xff, p1: 0xff, p2: 0xff, p3: 0xff, r: Array(8).fill(0), ram: Array(256).fill(0), sfr: {}, callStack: [] }
}

function schedule8051Batch() {
  if (!isRunning.value) return
  runTimer = window.setTimeout(() => {
    for (let index = 0; index < 8 && isRunning.value; index += 1) step8051(false)
    schedule8051Batch()
  }, 75)
}

function step8051(logStep = true) {
  const program = mcu8051Program.value
  if (!program.size && !prepareProgram()) return
  const state = mcu8051State.value
  const instruction = program.instructions[state.pc]
  if (!instruction) { stopRun(false); addLog('PC 超出程序范围。', 'error'); return }
  const oldPc = state.pc
  const jumped = execute8051Instruction(state, instruction, program.labels)
  if (!jumped) state.pc += 1
  if (logStep) addLog(`PC=${hex16(oldPc)} ${instruction.raw} · A=${hex8(state.a)} P1=${hex8(state.p1)}`)
}

function execute8051Instruction(state, instruction, labels) {
  const [a0, a1, a2] = instruction.args
  const jump = label => { state.pc = label === '$' ? state.pc : (labels[String(label).toUpperCase()] ?? state.pc); return true }
  switch (instruction.op) {
    case 'MOV': set8051Operand(state, a0, get8051Operand(state, a1)); break
    case 'INC': set8051Operand(state, a0, get8051Operand(state, a0) + 1); break
    case 'DEC': set8051Operand(state, a0, get8051Operand(state, a0) - 1); break
    case 'RL': state.a = ((state.a << 1) | (state.a >> 7)) & 0xff; break
    case 'RR': state.a = ((state.a >> 1) | ((state.a & 1) << 7)) & 0xff; break
    case 'RLC': { const next = (state.a >> 7) & 1; state.a = ((state.a << 1) | state.carry) & 0xff; state.carry = next; break }
    case 'RRC': { const next = state.a & 1; state.a = ((state.a >> 1) | (state.carry << 7)) & 0xff; state.carry = next; break }
    case 'SETB': set8051Bit(state, a0, 1); break
    case 'CLR': set8051Bit(state, a0, 0); break
    case 'CPL': set8051Bit(state, a0, get8051Bit(state, a0) ? 0 : 1); break
    case 'SJMP': case 'JMP': case 'LJMP': case 'AJMP': return jump(a0)
    case 'JB': if (get8051Bit(state, a0)) return jump(a1); break
    case 'JNB': if (!get8051Bit(state, a0)) return jump(a1); break
    case 'JC': if (state.carry) return jump(a0); break
    case 'JNC': if (!state.carry) return jump(a0); break
    case 'JZ': if (state.a === 0) return jump(a0); break
    case 'JNZ': if (state.a !== 0) return jump(a0); break
    case 'DJNZ': { const value = byte(get8051Operand(state, a0) - 1); set8051Operand(state, a0, value); if (value !== 0) return jump(a1); break }
    case 'CJNE': { const left = get8051Operand(state, a0); const right = get8051Operand(state, a1); state.carry = left < right ? 1 : 0; if (left !== right) return jump(a2); break }
    case 'ADD': state.a = byte(state.a + get8051Operand(state, a1 || a0)); break
    case 'ADDC': state.a = byte(state.a + get8051Operand(state, a1 || a0) + state.carry); break
    case 'SUBB': state.a = byte(state.a - get8051Operand(state, a1 || a0) - state.carry); break
    case 'ANL': set8051Operand(state, a0, get8051Operand(state, a0) & get8051Operand(state, a1)); break
    case 'ORL': set8051Operand(state, a0, get8051Operand(state, a0) | get8051Operand(state, a1)); break
    case 'XRL': set8051Operand(state, a0, get8051Operand(state, a0) ^ get8051Operand(state, a1)); break
    case 'PUSH': state.sp = byte(state.sp + 1); state.ram[state.sp] = get8051Operand(state, a0); break
    case 'POP': set8051Operand(state, a0, state.ram[state.sp]); state.sp = byte(state.sp - 1); break
    case 'ACALL': case 'LCALL': state.callStack.push(state.pc + 1); return jump(a0)
    case 'RET': state.pc = state.callStack.pop() ?? state.pc; return true
    case 'NOP': break
    default: addLog(`暂不支持 8051 指令：${instruction.raw}`, 'warning')
  }
  return false
}

function get8051Operand(state, argument = '') {
  const text = String(argument).trim().toUpperCase()
  if (text.startsWith('#')) return parse8051Number(text.slice(1))
  if (text === 'A' || text === 'ACC') return state.a
  if (text === 'B') return state.b
  if (text === 'C') return state.carry
  if (text === 'SP') return state.sp
  if (text === 'DPTR') return state.dptr
  if (text === 'DPL') return state.dptr & 0xff
  if (text === 'DPH') return (state.dptr >> 8) & 0xff
  if (/^R[0-7]$/.test(text)) return state.r[Number(text.slice(1))]
  if (text === '@R0' || text === '@R1') return state.ram[state.r[Number(text.slice(2))]]
  if (/^P[0-3]$/.test(text)) return read8051Port(state, text)
  if (/^P[0-3]\.[0-7]$/.test(text)) return get8051Bit(state, text)
  if (/^[0-9A-F]+H$/.test(text) || /^0X/.test(text) || /^\d+$/.test(text)) return read8051Direct(state, parse8051Number(text))
  return 0
}

function set8051Operand(state, argument = '', value) {
  const text = String(argument).trim().toUpperCase()
  const next = byte(value)
  if (text === 'A' || text === 'ACC') state.a = next
  else if (text === 'B') state.b = next
  else if (text === 'C') state.carry = next ? 1 : 0
  else if (text === 'SP') state.sp = next
  else if (text === 'DPTR') state.dptr = Number(value) & 0xffff
  else if (text === 'DPL') state.dptr = (state.dptr & 0xff00) | next
  else if (text === 'DPH') state.dptr = (state.dptr & 0x00ff) | (next << 8)
  else if (/^R[0-7]$/.test(text)) state.r[Number(text.slice(1))] = next
  else if (text === '@R0' || text === '@R1') state.ram[state.r[Number(text.slice(2))]] = next
  else if (/^P[0-3]$/.test(text)) state[text.toLowerCase()] = next
  else if (/^P[0-3]\.[0-7]$/.test(text)) set8051Bit(state, text, next)
  else if (/^[0-9A-F]+H$/.test(text) || /^0X/.test(text) || /^\d+$/.test(text)) write8051Direct(state, parse8051Number(text), next)
}

function read8051Direct(state, address) {
  const direct = Number(address) & 0xff
  if (direct < 0x80) return state.ram[direct]
  if (direct === 0x80) return state.p0
  if (direct === 0x81) return state.sp
  if (direct === 0x82) return state.dptr & 0xff
  if (direct === 0x83) return (state.dptr >> 8) & 0xff
  if (direct === 0x90) return state.p1
  if (direct === 0xa0) return state.p2
  if (direct === 0xb0) return state.p3
  if (direct === 0xd0) return (state.psw & 0x7f) | (state.carry << 7)
  if (direct === 0xe0) return state.a
  if (direct === 0xf0) return state.b
  return state.sfr[direct] ?? 0
}

function write8051Direct(state, address, value) {
  const direct = Number(address) & 0xff
  const next = byte(value)
  if (direct < 0x80) state.ram[direct] = next
  else if (direct === 0x80) state.p0 = next
  else if (direct === 0x81) state.sp = next
  else if (direct === 0x82) state.dptr = (state.dptr & 0xff00) | next
  else if (direct === 0x83) state.dptr = (state.dptr & 0x00ff) | (next << 8)
  else if (direct === 0x90) state.p1 = next
  else if (direct === 0xa0) state.p2 = next
  else if (direct === 0xb0) state.p3 = next
  else if (direct === 0xd0) { state.psw = next; state.carry = (next >> 7) & 1 }
  else if (direct === 0xe0) state.a = next
  else if (direct === 0xf0) state.b = next
  else state.sfr[direct] = next
}

function get8051Bit(state, argument = '') {
  const text = String(argument).trim().toUpperCase()
  if (text === 'C') return state.carry
  const match = text.match(/^P([0-3])\.([0-7])$/)
  if (!match) return 0
  const pin = `P${match[1]}.${match[2]}`
  const button = parts.value.find(part => componentDefinition(part)?.visual === 'button' && part.connections?.SIG === pin)
  if (button) return button.state?.pressed ? 0 : 1
  return (state[`p${match[1]}`] >> Number(match[2])) & 1
}

function set8051Bit(state, argument = '', value) {
  const text = String(argument).trim().toUpperCase()
  if (text === 'C') { state.carry = value ? 1 : 0; return }
  const match = text.match(/^P([0-3])\.([0-7])$/)
  if (!match) return
  const key = `p${match[1]}`
  const mask = 1 << Number(match[2])
  state[key] = value ? state[key] | mask : state[key] & ~mask
}

function read8051Port(state, argument) {
  const port = String(argument).toLowerCase()
  let value = state[port] ?? 0xff
  parts.value.filter(part => componentDefinition(part)?.visual === 'button').forEach(part => {
    const pin = part.connections?.SIG
    const match = String(pin || '').match(new RegExp(`^${port.toUpperCase()}\\.([0-7])$`))
    if (!match) return
    const mask = 1 << Number(match[1])
    value = part.state?.pressed ? value & ~mask : value | mask
  })
  return value
}

function read8051Pin(pin) {
  const match = String(pin || '').match(/^P([0-3])\.([0-7])$/)
  if (!match) return 0
  return (mcu8051State.value[`p${match[1]}`] >> Number(match[2])) & 1
}

function parse8051Number(text) {
  const normalized = String(text).trim().toUpperCase()
  if (/^[01]+B$/.test(normalized)) return Number.parseInt(normalized.slice(0, -1), 2)
  if (/^[0-9A-F]+H$/.test(normalized)) return Number.parseInt(normalized.slice(0, -1), 16)
  if (/^0X[0-9A-F]+$/.test(normalized)) return Number.parseInt(normalized, 16)
  return Number.parseInt(normalized, 10) || 0
}

function byte(value) { return ((Number(value) || 0) % 256 + 256) % 256 }
function clamp(value, min, max) { return Math.max(min, Math.min(max, value)) }
function hex8(value) { return `${byte(value).toString(16).toUpperCase().padStart(2, '0')}H` }
function hex16(value) { return `${(Number(value) & 0xffff).toString(16).toUpperCase().padStart(4, '0')}H` }

onBeforeUnmount(() => {
  stopRun(false)
  window.removeEventListener('pointermove', dragMove)
  window.removeEventListener('pointermove', boardDragMove)
})
</script>

<style scoped>
.mcu-app {
  min-height: 100vh;
  color: #111714;
  background: #ffffff;
}

button,
input,
select,
textarea {
  font: inherit;
  letter-spacing: 0;
}

button,
a {
  -webkit-tap-highlight-color: transparent;
}

.resource-return {
  position: fixed;
  top: 18px;
  left: 20px;
  z-index: 40;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 38px;
  padding: 0 12px;
  border: 1px solid #d9dfdc;
  border-radius: 6px;
  background: #fff;
  color: #1d2a25;
  text-decoration: none;
  font-size: 13px;
  font-weight: 700;
  box-shadow: 0 4px 14px rgba(12, 20, 16, 0.08);
}

.catalog-loading {
  min-height: 100vh;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 12px;
  color: #263b32;
}

.catalog-loading p { margin: 0; color: #596760; }
.catalog-loading button { display: inline-flex; align-items: center; gap: 7px; min-height: 38px; border: 0; border-radius: 5px; padding: 0 14px; background: #145c3f; color: #fff; cursor: pointer; }
.spin { animation: spin 0.9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.board-select-page,
.experiment-body {
  width: min(1460px, 100%);
  margin: 0 auto;
  padding: 88px 42px 44px;
}

.catalog-hero {
  min-height: 210px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 40px;
  padding-bottom: 34px;
  border-bottom: 1px solid #dfe4e1;
}

.eyebrow,
.section-title span,
.experiment-head .eyebrow {
  color: #176445;
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}

.catalog-hero h1,
.experiment-head h1 {
  margin: 8px 0 0;
  color: #0b0f0d;
  font-size: 42px;
  line-height: 1.12;
  letter-spacing: 0;
}

.catalog-hero p,
.experiment-head p {
  max-width: 760px;
  margin: 14px 0 0;
  color: #46534d;
  font-size: 16px;
  line-height: 1.75;
}

.catalog-metrics {
  display: flex;
  margin: 0;
  border: 1px solid #dce2df;
  border-radius: 7px;
  overflow: hidden;
}

.catalog-metrics div { min-width: 92px; padding: 15px 18px; border-right: 1px solid #dce2df; background: #f8faf9; }
.catalog-metrics div:last-child { border-right: 0; }
.catalog-metrics dt { color: #65716b; font-size: 12px; }
.catalog-metrics dd { margin: 4px 0 0; color: #101713; font-size: 24px; font-weight: 800; }

.recommend-band,
.board-section { padding: 34px 0 6px; }
.board-section { margin-top: 12px; }
.section-title { display: flex; align-items: center; justify-content: space-between; color: #176445; }
.section-title h2 { margin: 4px 0 0; color: #101512; font-size: 24px; }

.recommend-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.recommend-item {
  position: relative;
  min-height: 134px;
  padding: 17px 38px 17px 17px;
  border: 1px solid #cbdad2;
  border-radius: 7px;
  color: #111714;
  text-decoration: none;
  background: #fbfdfc;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.recommend-item:hover { transform: translateY(-2px); border-color: #4c876d; box-shadow: 0 12px 28px rgba(18, 74, 51, 0.1); }
.recommend-item > span { color: #176445; font-size: 11px; font-weight: 800; }
.recommend-item strong { display: block; margin-top: 7px; font-size: 16px; }
.recommend-item p { margin: 8px 0 0; color: #59655f; font-size: 12px; line-height: 1.5; }
.recommend-item svg { position: absolute; top: 17px; right: 15px; color: #176445; }

.board-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; margin-top: 20px; }
.board-card { min-height: 240px; display: grid; grid-template-columns: 190px minmax(0, 1fr) auto; align-items: center; gap: 26px; padding: 25px; border: 1px solid #d8deda; border-radius: 8px; background: #fff; color: inherit; text-decoration: none; transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease; }
.board-card:hover { transform: translateY(-2px); border-color: #557c69; box-shadow: 0 16px 34px rgba(18, 36, 28, 0.1); }
.board-card-visual { height: 178px; display: grid; place-items: center; overflow: hidden; border-radius: 6px; background: #edf4f0; }
.board-card-visual wokwi-arduino-uno { width: 185px; transform: rotate(-4deg); }
.dip-preview { position: relative; width: 96px; height: 164px; display: grid; grid-template-columns: repeat(2, 1fr); align-items: stretch; padding: 5px 0; background: #252927; border-radius: 5px; }
.dip-preview i:nth-child(odd) { border-left: 8px solid #d6d8d7; }
.dip-preview i:nth-child(even) { border-right: 8px solid #d6d8d7; }
.dip-preview b { position: absolute; inset: 0; display: grid; place-items: center; color: #e8ece9; font-size: 12px; writing-mode: vertical-rl; }
.board-card-copy > span { color: #176445; font-size: 12px; font-weight: 700; }
.board-card-copy strong { display: block; margin-top: 5px; color: #0d120f; font-size: 24px; }
.board-card-copy p { margin: 11px 0 0; color: #515e57; font-size: 13px; line-height: 1.65; }
.board-card-copy ul { display: flex; gap: 18px; margin: 15px 0 0; padding: 0; list-style: none; color: #263e33; font-size: 12px; font-weight: 700; }
.board-card > svg { color: #176445; }
.source-footer { display: flex; align-items: center; gap: 10px; margin-top: 32px; padding: 18px 0; border-top: 1px solid #e2e6e4; color: #536159; font-size: 13px; }

.experiment-page { min-height: 100vh; background: #fafbfa; }
.catalog-topbar,
.workbench-topbar { height: 58px; display: flex; align-items: center; gap: 20px; padding: 0 20px; border-bottom: 1px solid #d9dfdc; background: #fff; }
.brand-link { display: inline-flex; align-items: center; gap: 8px; color: #111714; text-decoration: none; font-weight: 900; }
.catalog-topbar > div { display: grid; gap: 1px; }
.catalog-topbar > div strong { font-size: 14px; }
.catalog-topbar > div span { color: #68736d; font-size: 11px; }
.icon-command { margin-left: auto; display: inline-flex; align-items: center; gap: 7px; color: #233a2f; text-decoration: none; font-size: 13px; font-weight: 700; }
.experiment-body { padding-top: 46px; }
.experiment-head { display: flex; align-items: end; justify-content: space-between; gap: 30px; }
.experiment-head h1 { font-size: 34px; }
.recommend-state { display: inline-flex; align-items: center; gap: 8px; padding: 10px 12px; border: 1px solid #d9dfdc; border-radius: 6px; color: #5e6a64; background: #fff; font-size: 12px; }
.recommend-state.bound { color: #145c3f; border-color: #b9d5c7; background: #f6fbf8; }
.experiment-filters { display: flex; align-items: center; gap: 10px; margin-top: 30px; padding: 11px; border: 1px solid #dce1de; background: #fff; }
.search-field { flex: 1; min-width: 220px; display: flex; align-items: center; gap: 8px; padding: 0 10px; border: 1px solid #d5dcd8; border-radius: 5px; }
.search-field input { width: 100%; height: 38px; border: 0; outline: 0; color: #121713; background: transparent; }
.experiment-filters select { height: 40px; min-width: 130px; border: 1px solid #d5dcd8; border-radius: 5px; padding: 0 10px; background: #fff; color: #202a25; }
.experiment-filters > span { min-width: 86px; color: #66716b; text-align: right; font-size: 12px; }

.experiment-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 18px; }
.experiment-card { min-width: 0; overflow: hidden; border: 1px solid #d9dfdc; border-radius: 8px; background: #fff; transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease; }
.experiment-card:hover { transform: translateY(-2px); border-color: #6d8d7c; box-shadow: 0 13px 28px rgba(16, 34, 25, 0.09); }
.experiment-card.recommended { border-color: #8bb6a0; }
.experiment-card.blank { border-style: dashed; }
.experiment-main { display: block; color: inherit; text-decoration: none; }
.experiment-preview { position: relative; height: 128px; overflow: hidden; background: #edf3f0; border-bottom: 1px solid #e0e5e2; }
.experiment-preview.\38 051 { background: #f1f2f1; }
.recommend-badge { position: absolute; top: 10px; left: 10px; z-index: 2; padding: 4px 7px; border-radius: 4px; background: #145c3f; color: #fff; font-size: 10px; font-weight: 800; }
.mini-board { position: absolute; right: 28px; top: 25px; width: 82px; height: 78px; display: grid; place-items: center; border: 5px solid #dbe4df; border-radius: 5px; background: #1f7454; color: #fff; font-size: 11px; font-weight: 900; transform: rotate(-4deg); }
.experiment-preview.\38 051 .mini-board { background: #242927; border-width: 3px; }
.mini-parts { position: absolute; left: 24px; bottom: 24px; display: flex; align-items: end; gap: 8px; }
.mini-parts span { width: 22px; height: 34px; border: 2px solid #94a29b; border-radius: 3px; background: #fff; }
.mini-parts span.led,
.mini-parts span.rgb-led { width: 22px; height: 22px; border-radius: 50%; background: #e34848; }
.mini-parts span.button { height: 20px; background: #303633; }
.mini-parts span.led-bar { width: 56px; height: 18px; background: #27302c; }
.experiment-copy { min-height: 226px; padding: 18px; }
.meta-line { display: flex; gap: 8px; color: #176445; font-size: 11px; font-weight: 800; }
.meta-line span + span::before { content: '·'; margin-right: 8px; color: #8a9690; }
.experiment-copy h2 { margin: 9px 0 0; color: #111714; font-size: 18px; }
.experiment-copy > p { margin: 9px 0 0; color: #57645d; font-size: 13px; line-height: 1.6; }
.tag-row { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 14px; }
.tag-row span { padding: 4px 7px; border-radius: 4px; background: #f0f3f1; color: #415047; font-size: 10px; }
.recommend-reason { color: #176445 !important; font-weight: 700; }
.experiment-card > footer { display: flex; align-items: center; justify-content: space-between; min-height: 42px; padding: 0 18px; border-top: 1px solid #e4e8e6; color: #6b756f; font-size: 11px; }
.experiment-card > footer a { display: inline-flex; align-items: center; gap: 4px; color: #2d5b45; text-decoration: none; font-weight: 700; }

.workbench-shell { height: 100vh; min-width: 1060px; display: grid; grid-template-rows: 58px 36px minmax(0, 1fr); overflow: hidden; background: #202422; color: #eef2ef; }
.workbench-topbar { border-color: #303633; background: #151917; color: #fff; }
.brand-link.compact { color: #fff; }
.project-identity { min-width: 0; display: grid; gap: 2px; }
.project-identity strong { overflow: hidden; color: #fff !important; font-size: 14px; text-overflow: ellipsis; white-space: nowrap; }
.project-identity span { color: #9ba8a1; font-size: 11px; }
.top-actions { margin-left: auto; display: flex; gap: 7px; }
.top-action,
.flash-action { height: 34px; display: inline-flex; align-items: center; gap: 7px; padding: 0 11px; border: 1px solid #39423d; border-radius: 5px; background: #202623; color: #edf1ef; text-decoration: none; font-size: 12px; cursor: pointer; }
.flash-action { border-color: #176445; background: #176445; color: #fff; font-weight: 800; }
.workbench-tabs { display: flex; align-items: end; gap: 2px; padding: 0 12px; background: #e6e9e7; color: #141a17; }
.workbench-tabs button { height: 31px; display: inline-flex; align-items: center; gap: 6px; padding: 0 13px; border: 0; border-radius: 5px 5px 0 0; background: transparent; color: #3d4943; cursor: pointer; font-size: 12px; }
.workbench-tabs button.active { background: #fff; color: #111714; font-weight: 800; }
.firmware-chip { margin-left: auto; align-self: center; display: inline-flex; align-items: center; gap: 5px; color: #176445; font-family: Consolas, monospace; font-size: 10px; }
.workbench-grid { min-height: 0; display: grid; grid-template-columns: minmax(350px, 0.78fr) minmax(650px, 1.22fr); }
.editor-pane { min-width: 0; min-height: 0; display: grid; grid-template-rows: 42px minmax(0, 1fr); border-right: 1px solid #343a37; background: #1b1f1d; }
.editor-pane > header { display: flex; align-items: center; justify-content: space-between; padding: 0 12px; border-bottom: 1px solid #303633; }
.editor-pane > header > div { display: flex; align-items: baseline; gap: 10px; }
.editor-pane > header span { font-size: 12px; font-weight: 800; }
.editor-pane > header em { color: #aeb9b3 !important; font-size: 10px; font-style: normal; }
.editor-pane > header button { display: inline-flex; align-items: center; gap: 6px; height: 30px; border: 1px solid #4d5a53; border-radius: 4px; background: #252c28; color: #dfe6e2; cursor: pointer; font-size: 11px; }
.code-area { min-height: 0; display: grid; grid-template-columns: 52px minmax(0, 1fr); background: #1b1f1d; }
.line-gutter { margin: 0; padding: 15px 10px; overflow: hidden; color: #69736e; text-align: right; font: 12px/21px Consolas, monospace; background: #171a19; user-select: none; }
.code-editor { width: 100%; height: 100%; box-sizing: border-box; resize: none; border: 0; outline: 0; padding: 15px 18px; background: #1b1f1d; color: #dce5e0; caret-color: #6ee7b7; font: 13px/21px Consolas, monospace; }
.guide-sheet { min-height: 0; overflow: auto; background: #f8faf9; color: #111714; }
.guide-sheet > header { display: grid; gap: 7px; padding: 20px 22px 17px; border-bottom: 1px solid #dce2de; background: #fff; }
.guide-sheet > header span { color: #176445; font-size: 10px; font-weight: 900; }
.guide-sheet > header strong { font-size: 16px; line-height: 1.45; }
.guide-sheet > header p { margin: 0; color: #5d6862; font-size: 11px; line-height: 1.55; }
.guide-sheet > ol { margin: 0; padding: 0; list-style: none; }
.guide-sheet > ol > li { display: grid; grid-template-columns: 30px minmax(0, 1fr); gap: 10px; padding: 17px 20px; border-bottom: 1px solid #e1e6e3; }
.guide-sheet > ol > li > button { width: 26px; height: 26px; display: grid; place-items: center; padding: 0; border: 0; background: transparent; color: #89958f; cursor: pointer; }
.guide-sheet > ol > li.done > button { color: #176445; }
.guide-sheet > ol > li > div { min-width: 0; }
.guide-sheet > ol > li > div > span { color: #718078; font-size: 9px; font-weight: 800; }
.guide-sheet > ol > li > div > strong { display: block; margin-top: 3px; font-size: 13px; }
.guide-sheet > ol > li > div > p { margin: 6px 0 0; color: #56625c; font-size: 11px; line-height: 1.55; overflow-wrap: anywhere; }
.guide-sheet > ol > li.done > div > strong { color: #176445; }
.guide-sheet ul { display: grid; gap: 4px; margin: 9px 0 0; padding-left: 16px; color: #38463f; font-size: 10px; line-height: 1.45; }
.sim-pane { position: relative; min-width: 0; min-height: 0; display: grid; grid-template-rows: 50px minmax(0, 1fr) 184px; background: #313633; }
.sim-toolbar { display: flex; align-items: center; gap: 7px; padding: 0 11px; border-bottom: 1px solid #414844; background: #282e2b; }
.sim-toolbar button { height: 34px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; border: 1px solid #46504b; border-radius: 5px; background: #353d39; color: #eef2ef; cursor: pointer; }
.tool-primary { min-width: 82px; padding: 0 13px; border-color: #1d7450 !important; background: #176445 !important; font-weight: 800; }
.tool-primary.stop { border-color: #a43d39 !important; background: #8e302d !important; }
.tool-button { width: 35px; }
.tool-button.with-label { width: auto; padding: 0 11px; }
.tool-button.active { border-color: #739485; background: #45544d; }
.connection-hint { display: flex; align-items: center; gap: 6px; padding: 7px 9px; border-radius: 4px; background: #fff3c7; color: #513d05; font-size: 11px; font-weight: 700; }
.sim-spacer { flex: 1; }
.engine-label { color: #9aa59f; font-size: 10px; }
.parts-drawer { position: absolute; top: 50px; left: 10px; z-index: 30; width: 330px; max-height: min(620px, calc(100vh - 280px)); display: grid; grid-template-rows: auto auto auto minmax(0, 1fr); border: 1px solid #4d5752; border-radius: 7px; background: #202522; box-shadow: 0 18px 46px rgba(0, 0, 0, 0.38); overflow: hidden; }
.parts-drawer > header { display: flex; align-items: center; justify-content: space-between; min-height: 45px; padding: 0 13px; border-bottom: 1px solid #353c38; }
.parts-drawer > header button { border: 0; background: transparent; color: #dce3df; cursor: pointer; }
.parts-drawer > label { display: flex; align-items: center; gap: 8px; margin: 10px; padding: 0 9px; border: 1px solid #3c4540; border-radius: 5px; background: #181c1a; }
.parts-drawer > label input { width: 100%; height: 34px; border: 0; outline: 0; background: transparent; color: #fff; }
.component-categories { display: flex; gap: 5px; overflow-x: auto; padding: 0 10px 9px; }
.component-categories button { flex: 0 0 auto; height: 27px; padding: 0 8px; border: 1px solid #3c4540; border-radius: 4px; background: transparent; color: #aeb8b3; cursor: pointer; font-size: 10px; }
.component-categories button.active { border-color: #4f8a70; background: #164f38; color: #fff; }
.component-list { min-height: 0; overflow: auto; padding: 6px; }
.component-list > button { width: 100%; display: grid; grid-template-columns: 30px minmax(0, 1fr); gap: 8px; align-items: center; padding: 9px; border: 0; border-radius: 5px; background: transparent; color: #eef2ef; text-align: left; cursor: pointer; }
.component-list > button:hover { background: #303733; }
.component-icon { width: 28px; height: 28px; display: grid; place-items: center; border-radius: 4px; background: #176445; color: #fff; }
.component-list strong { display: block; font-size: 12px; }
.component-list em { display: block; margin-top: 3px; overflow: hidden; color: #9aa59f; font-size: 10px; font-style: normal; text-overflow: ellipsis; white-space: nowrap; }
.circuit-canvas { min-height: 0; overflow: auto; background-color: #f1f3f2; background-image: linear-gradient(#dfe4e1 1px, transparent 1px), linear-gradient(90deg, #dfe4e1 1px, transparent 1px); background-size: 20px 20px; }
.canvas-grid { position: relative; width: 1120px; height: 720px; }
.wires-layer { position: absolute; inset: 0; z-index: 3; width: 1120px; height: 720px; pointer-events: none; }
.wires-layer path { opacity: 0.75; filter: drop-shadow(0 1px 0 rgba(255, 255, 255, 0.9)); transition: opacity 0.15s ease, stroke-width 0.15s ease; }
.wires-layer path.highlighted { opacity: 1; stroke-width: 5; }
.board-stage { position: absolute; z-index: 5; box-sizing: border-box; cursor: grab; user-select: none; }
.board-stage:active { cursor: grabbing; }
.board-art { position: absolute; inset: 24px 30px; display: grid; place-items: center; }
.board-art wokwi-arduino-uno { width: 260px; transform: rotate(90deg) scale(0.92); }
.mcs51-chip { width: 120px; height: 430px; display: grid; place-content: center; justify-items: center; gap: 9px; border-radius: 7px; background: #222724; color: #e8eeeb; box-shadow: inset 0 0 0 2px #0f1210, 0 12px 28px rgba(18, 25, 21, 0.2); }
.mcs51-chip::before { content: ''; position: absolute; top: 34px; width: 18px; height: 9px; border-radius: 0 0 12px 12px; background: #f1f3f2; }
.mcs51-chip span { writing-mode: vertical-rl; font-size: 17px; font-weight: 900; }
.mcs51-chip small { color: #9aa49f; writing-mode: vertical-rl; }
.pin-column { position: absolute; top: 0; bottom: 0; z-index: 6; display: flex; flex-direction: column; justify-content: space-between; }
.pin-column.left { left: -42px; align-items: end; }
.pin-column.right { right: -42px; align-items: start; }
.pin-column button { position: relative; min-width: 62px; height: 19px; display: flex; align-items: center; justify-content: flex-end; gap: 5px; padding: 0 4px; border: 0; background: transparent; color: #26312b; cursor: pointer; font: 9px Consolas, monospace; }
.pin-column.right button { justify-content: flex-start; }
.pin-column button i { width: 9px; height: 9px; flex: 0 0 auto; border: 2px solid #fff; border-radius: 50%; background: #818c86; box-shadow: 0 0 0 1px #4a5550; }
.pin-column button.connected i { background: #176445; box-shadow: 0 0 0 1px #0d5135, 0 0 7px rgba(23, 100, 69, 0.55); }
.pin-column button.selected { color: #0c5b3a; font-weight: 900; }
.pin-column button.selected i { background: #0f7a4e; transform: scale(1.3); }
.pin-column button.compatible i { background: #f59e0b; animation: pinPulse 0.8s ease-in-out infinite alternate; }
.pin-column button.incompatible { opacity: 0.28; }
@keyframes pinPulse { to { transform: scale(1.35); } }
.circuit-part { position: absolute; z-index: 6; width: 210px; box-sizing: border-box; padding-bottom: 9px; border: 1px solid #bac4bf; border-radius: 7px; background: #fff; color: #121814; box-shadow: 0 8px 22px rgba(20, 32, 26, 0.12); cursor: grab; user-select: none; }
.circuit-part:active { cursor: grabbing; }
.circuit-part.active { border-color: #42a878; box-shadow: 0 0 0 2px rgba(39, 155, 101, 0.15), 0 10px 24px rgba(20, 32, 26, 0.14); }
.circuit-part > header { height: 34px; display: flex; align-items: center; justify-content: space-between; padding: 0 8px 0 10px; border-bottom: 1px solid #e1e5e3; background: #f5f7f6; border-radius: 7px 7px 0 0; font-size: 11px; font-weight: 800; }
.circuit-part > header button { width: 25px; height: 25px; display: grid; place-items: center; border: 0; background: transparent; color: #65716b; cursor: pointer; }
.part-visual { height: 78px; display: grid; place-items: center; overflow: hidden; }
.part-visual > * { max-width: 150px; max-height: 70px; }
.part-visual wokwi-led { width: 42px; }
.part-visual wokwi-pushbutton { width: 58px; cursor: pointer; }
.part-visual wokwi-led-bar-graph { width: 130px; }
.part-visual wokwi-hc-sr04 { width: 130px; }
.part-visual wokwi-lcd1602 { width: 160px; }
.relay-visual,
.serial-visual,
.generic-visual { width: 70px; height: 52px; display: flex; align-items: center; justify-content: center; gap: 6px; border: 2px solid #68766f; border-radius: 5px; background: #e8eeeb; color: #1d4f38; }
.serial-visual { background: #202522; color: #7ce4b3; }
.crystal-visual { padding: 7px 18px; border: 2px solid #8a918d; border-radius: 50%; background: #d8dcda; color: #313a35; text-align: center; font: 10px Consolas, monospace; }
.sensor-control { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 7px; padding: 0 9px 8px; color: #4e5b54; font-size: 9px; }
.sensor-control input { width: 100%; accent-color: #176445; }
.sensor-control em { color: #176445; font-style: normal; font-weight: 800; }
.terminal-list { display: grid; gap: 4px; padding: 0 8px; }
.terminal-row { display: grid; grid-template-columns: 14px 32px minmax(0, 1fr); align-items: center; gap: 4px; min-height: 25px; }
.terminal-dot { width: 10px; height: 10px; padding: 0; border: 2px solid #fff; border-radius: 50%; background: #a6afa9; box-shadow: 0 0 0 1px #69746e; cursor: crosshair; }
.terminal-dot.connected { background: var(--wire-color); box-shadow: 0 0 0 1px var(--wire-color); }
.terminal-dot.pending { transform: scale(1.35); box-shadow: 0 0 0 2px #f59e0b; }
.terminal-row > span { color: #536059; font: 9px Consolas, monospace; }
.terminal-row select { min-width: 0; width: 100%; height: 23px; border: 1px solid #d8ddda; border-radius: 3px; background: #fafbfa; color: #27312c; font-size: 9px; }
.circuit-part > footer { display: flex; justify-content: space-between; padding: 7px 9px 0; color: #176445; font-size: 9px; font-weight: 800; }
.circuit-part > footer em { color: #7a8580; font-style: normal; font-weight: 600; }
.runtime-console { min-height: 0; display: grid; grid-template-columns: 1fr 1.2fr 0.95fr; border-top: 1px solid #424944; background: #1d211f; }
.runtime-console section { min-width: 0; display: grid; grid-template-rows: 32px minmax(0, 1fr); border-right: 1px solid #353b38; }
.runtime-console section:last-child { border-right: 0; }
.runtime-console header { display: flex; align-items: center; gap: 6px; padding: 0 10px; border-bottom: 1px solid #303633; color: #c4cdc8; font-size: 10px; font-weight: 800; }
.runtime-console section > div { overflow: auto; padding: 7px 10px; }
.runtime-console p { margin: 0 0 4px; color: #b9c3be !important; font: 10px/1.45 Consolas, monospace; }
.runtime-console p.success { color: #7ce4b3; }
.runtime-console p.warning { color: #f5c96c; }
.runtime-console p.error { color: #ff8f89; }
.pin-inspector strong { color: #fff !important; font-size: 12px; }
.pin-inspector strong small { margin-left: 5px; color: #a0aca6 !important; font-size: 9px; }
.pin-inspector span { display: inline-block; margin: 4px 4px 0 0; padding: 3px 5px; border-radius: 3px; background: #2d3832; color: #92dfb8; font-size: 8px; }
.dialog-backdrop { position: fixed; inset: 0; z-index: 100; display: grid; place-items: center; padding: 20px; background: rgba(5, 9, 7, 0.68); }
.flash-dialog { width: min(620px, 100%); max-height: calc(100vh - 40px); overflow: auto; border: 1px solid #ced6d2; border-radius: 8px; background: #fff; color: #101713; box-shadow: 0 26px 70px rgba(0, 0, 0, 0.3); }
.flash-dialog > header { display: flex; align-items: start; justify-content: space-between; padding: 20px 22px 15px; border-bottom: 1px solid #e0e5e2; }
.flash-dialog > header span { color: #176445; font-size: 10px; font-weight: 900; }
.flash-dialog h2 { margin: 4px 0 0; font-size: 22px; }
.flash-dialog > header button { width: 32px; height: 32px; display: grid; place-items: center; border: 0; background: transparent; color: #4e5b54; cursor: pointer; }
.flash-boundary { margin: 0; padding: 14px 22px; color: #56635c; font-size: 12px; line-height: 1.6; background: #f7f9f8; }
.flash-steps { display: grid; gap: 0; margin: 0; padding: 8px 22px; list-style: none; }
.flash-steps li { display: grid; grid-template-columns: 24px minmax(0, 1fr); gap: 8px; min-height: 54px; align-items: center; border-bottom: 1px solid #e9ecea; color: #87918c; }
.flash-steps li.done { color: #176445; }
.flash-steps li.running { color: #1d5e99; }
.flash-steps li.error { color: #a1302c; }
.flash-steps li span { display: grid; gap: 3px; }
.flash-steps strong { font-size: 12px; }
.flash-steps em { color: #7c8781; font-size: 10px; font-style: normal; }
.flash-result { margin: 8px 22px 4px; padding: 14px; border: 1px solid #d8dfdb; border-radius: 6px; }
.flash-result.success { border-color: #a9d0bd; background: #f4fbf7; }
.flash-result.failure { border-color: #e1b5b2; background: #fff7f6; }
.flash-result > div { display: flex; align-items: center; gap: 9px; }
.flash-result > div > span { display: grid; gap: 3px; }
.flash-result strong { font-size: 13px; }
.flash-result em { color: #65716b; font: 10px Consolas, monospace; }
.flash-result ul { display: grid; gap: 6px; margin: 12px 0 0; padding: 0; list-style: none; }
.flash-result li { color: #4e5953; font-size: 11px; line-height: 1.45; }
.flash-result li span { display: inline-block; margin-right: 6px; padding: 2px 5px; border-radius: 3px; background: #f1c9c6; color: #7a1e1a; font-size: 9px; font-weight: 800; }
.flash-result li.warning span { background: #f5e3ad; color: #6b4c00; }
.flash-dialog > footer { display: flex; justify-content: flex-end; gap: 8px; padding: 16px 22px 20px; }
.flash-dialog > footer button { min-height: 38px; display: inline-flex; align-items: center; gap: 7px; padding: 0 14px; border-radius: 5px; cursor: pointer; font-weight: 800; }
.flash-dialog > footer .secondary { border: 1px solid #d3dad6; background: #fff; color: #354139; }
.flash-dialog > footer .primary { border: 1px solid #176445; background: #176445; color: #fff; }
.flash-dialog > footer button:disabled { cursor: wait; opacity: 0.65; }

:global(#app .workbench-shell .project-identity strong) { color: #fff !important; }
:global(#app .workbench-shell .editor-pane > header em) { color: #aeb9b3 !important; }
:global(#app .workbench-shell .runtime-console p) { color: #b9c3be !important; }
:global(#app .workbench-shell .pin-inspector strong) { color: #fff !important; }
:global(#app .workbench-shell .pin-inspector strong small) { color: #a0aca6 !important; }

@media (max-width: 1080px) {
  .board-select-page,
  .experiment-body { padding-left: 24px; padding-right: 24px; }
  .recommend-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .experiment-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .board-card { grid-template-columns: 150px minmax(0, 1fr) auto; }
  .board-card-visual { height: 150px; }
}

@media (max-width: 720px) {
  .resource-return { top: 10px; left: 10px; }
  .board-select-page { padding: 70px 16px 26px; }
  .catalog-hero { min-height: 0; grid-template-columns: 1fr; align-items: start; gap: 22px; }
  .catalog-hero h1 { font-size: 34px; }
  .catalog-metrics { width: 100%; }
  .catalog-metrics div { flex: 1; min-width: 0; }
  .recommend-list,
  .board-grid,
  .experiment-grid { grid-template-columns: 1fr; }
  .board-card { grid-template-columns: 105px minmax(0, 1fr); gap: 15px; padding: 16px; }
  .board-card > svg { display: none; }
  .board-card-visual { height: 120px; }
  .board-card-visual wokwi-arduino-uno { width: 120px; }
  .board-card-copy strong { font-size: 19px; }
  .board-card-copy p { display: -webkit-box; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 3; }
  .board-card-copy ul { display: grid; gap: 4px; }
  .catalog-topbar { padding: 0 12px; }
  .catalog-topbar > div span { display: none; }
  .icon-command { font-size: 0; }
  .experiment-body { padding: 28px 14px; }
  .experiment-head { align-items: start; flex-direction: column; }
  .experiment-filters { align-items: stretch; flex-direction: column; }
  .experiment-filters > span { text-align: left; }
  .experiment-copy { min-height: 0; }
}
</style>
