# 嵌智学航

## 竞赛提交包构建与启动

竞赛平台要求 `94015785作品.zip` 与 `94015785源码.zip` 分别不超过 1 GB。作品包使用 Windows x64 便携 Python 和预构建前端，可通过根目录 `一键启动.bat` 启动；为控制体积，提交模式不内置 FFmpeg，视频后处理会在系统安装 FFmpeg 后自动启用，不影响画像、个性化路径、多智能体资源、知识检索、管理端和 PPT 工作台等核心评审流程。

便携包构建命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-portable-package.ps1 -OutputDirectory portable\submission -ExcludeFfmpeg
```

评委解压 `94015785作品.zip` 后，先双击 `检查完整性.bat`，再双击 `一键启动.bat`。用户端、移动端网页、管理端和 PPT 工作台分别位于 `http://127.0.0.1:3000`、`http://127.0.0.1:3000/m/`、`http://127.0.0.1:3000/admin/` 和 `http://127.0.0.1:3000/ppt/`；默认管理员账号和密码为 `admin123` / `admin123`。联网 AI 功能需要在 `backend/.env` 中配置接口密钥，提交包不包含任何真实密钥。

评委也可以直接访问远程体验环境：<https://lzhan.xyz>。远程环境用于快速查看完整交互效果；正式评分或验证本地部署行为时，请以解压后的 `94015785作品.zip` 为准。

嵌智学航是面向高校嵌入式与单片机课程的个性化学习多智能体平台。系统以“嵌小智”为唯一总控入口，通过 Agent Harness、Skill Manifest 与 MCP JSON-RPC 调度学习画像、学习路径、六类资源、学习验证、智能辅导、效果评估和数字人面试，形成“采集分析 -> 资源生成 -> 学习验证 -> 反馈调整”的完整闭环。

当前 Manifest 1.6.1 只登记 22 个有对应实现的 Harness 角色：1 个嵌小智 Supervisor、18 个专业角色和 3 个多模态运行时处理角色；不把上下文步骤、审核步骤或无实现的占位名称重复计作智能体。Manifest 同时声明 18 个可调用 Skill、18 个 Handler 映射、18 个 MCP Tool、1 个 MCP Server、1 个 MCP Resource 和 1 个 MCP Prompt。所有业务 Skill 都由嵌小智 Supervisor 通过 Agent Harness 调度，并保留 `runId`、结构化 Handoff、共享黑板、质量审核、安全审核、当前画像 ID 与模型运行信息。`generated-video-agent` 有实际后台任务执行器、路由和 Handler，但采用用户确认后的延迟执行链，没有单独注册为第 19 个 Skill，因此只计角色、不增加 Skill 数。

## 目录结构

```text
code6.14/
├─ backend/              Flask 后端服务
├─ frontend/             Vue 主前端
├─ mobile/               Capacitor Android 与移动端网页源码
├─ microprogram/         微信小程序源码（需微信开发者工具）
├─ admin/                Vue 管理端源码
├─ img/                  主前端静态资源，包含 mind-map、video-search、ppt
├─ ppth5/                PPT H5 源码，可重新构建 img/ppt
├─ deploy.sh             Linux 服务器部署脚本
├─ start-all.bat         Windows 本地启动脚本
├─ THIRD_PARTY_NOTICES.md 第三方软件与素材许可声明
└─ README.md
```

## 主要功能

- 嵌小智总控与扩展：22 个已实现 Harness 角色和 18 个可调用 Skill 由 `backend/agent_manifests/xiaozhi_agents.json` 统一声明。角色数严格按 Manifest 中有实际职责的条目统计，执行步骤和占位名称不计入智能体数量。Handler Registry 在启动时校验重复 ID、缺失处理器、非法权限和 MCP 映射。新增可调用业务能力通过 Manifest、Handler 与 MCP 接入，不修改 Supervisor 主流程。
- 学习画像：首次补齐十个画像维度时创建报告；后续重新评估、会话补全和证据更新都会合并到当前画像并原位保存，保持画像 ID、名称、版本和历史位置不变，只有明确选择另一份历史画像时才切换当前画像。
- 多模态对话输入：嵌小智悬浮窗和学习画像对话均支持图片、视频、PDF、Word、PPT 与文本附件。附件先经过登录用户隔离、格式/数量/大小校验并持久化；图片与文档尝试提取文字，视频保留为可追溯学习证据，随后以不可覆盖系统指令的受控上下文交给总控或学习画像智能体。嵌小智输入区固定在悬浮窗底部，并兼容中文输入法组合输入；请求失败时保留原始文本和附件，允许直接重试。
- 嵌小智双视图：`陪伴式助手` 只承载对话，不再显示全局“资源任务”或“最近任务”列表。仅当用户在该轮对话中明确要求生成任务、且后端确实在该条回复的 `cards` 中返回任务时，回复下方才出现对应完整任务页面的缩放预览气泡；气泡持续展示排队、生成、完成或失败状态，点击会在新标签页沿原任务路由打开题库、PPT、导图、视频等完整页面，普通聊天不会出现任务预览。`Agent Harness` 只展示嵌小智总控与专项智能体的连接拓扑、当前动作、运行状态及 Skill/MCP 能力计数，不渲染资源 iframe、任务窗口或后台任务日志。前端验证命令为 `cd frontend && npm run build`，浏览器验收需覆盖普通消息无任务气泡、显式生成回复的内联预览、新标签页跳转、拓扑内部滚动及桌面/移动视口边界。
- 学习画像详细执行信息：`POST /api/learning-profile/analyze-stream` 使用队列式 SSE 实时推送嵌小智总控、学习上下文、Skill Registry、MCP Tool、JSON 契约、质量审核、内容安全、保存报告和后台人像排队事件。画像报告生成页展示当前智能体、模型、`runId`、执行进度、累计耗时、审核得分以及每条事件的结构化详情；只展示计数与审核元数据，不输出 API Key、原始 Prompt 或完整画像隐私内容。
- 画像人像与报告仪表盘：学习画像、画像报告和历史记录始终使用同一套三级侧栏；侧栏下方的 `#learning-profile-digital-human-stage` 真实挂载讯飞数字人组件，在画像对话页同步播报智能体回复，切换到报告或历史页时释放会话。数字人连接失败只显示降级状态，文字对话、历史消息和输入框继续可用，不挂载本地形象或静态兜底人物。报告主体包含六项摘要、十维能力条、六维雷达、证据矩阵、AI 结论和推荐方案；后端通过 APIMart Seedream 4.5 基于学习方向、目标、风格与薄弱点生成非真人化学习者插画，并把图片二进制按报告 ID 保存到 SQLite 的 `learning_profile_portraits` 表。报告头像读取、生成、缺失或失败期间先展示内置的非真人默认学习者头像及真实状态提示；数据库中的报告专属头像变为 `ready` 后立即替换默认图。报告保存后会立即排队生成，接口不再同步等待生图；前端轮询数据库状态并在 `ready` 后通过认证接口读取 BLOB，失败或超时会退出加载态并提供重试。服务从 `backend/.env` 读取 `SEEDREAM_BASE_URL` 与 `SEEDREAM_API_KEY`，模型固定为 `seedream-4-5`、最低使用服务支持的 `2K` 分辨率；提交后通过 `/v1/tasks/{task_id}` 轮询结果，轮询时限与间隔分别由 `IMAGE2_POLL_TIMEOUT_SECONDS`、`IMAGE2_POLL_INTERVAL_SECONDS` 控制。
- 效果评估：`/effect-assessment` 汇总聊天、题单与考试、MCU 实验、资源调用和学习路径完成记录，展示前后能力雷达、薄弱点与可验证的进步；可在该页自动更新当前画像，不新增画像条目。
- 学习路径：学习画像保存完成后，后端立即创建可追踪且幂等的 `learning_path` 后台任务，无需用户先进入学习路径页面；路径根据该画像的目标、薄弱点和偏好生成，并由资源路由智能体逐任务选择子智能体、补齐参数和后台预生成结果。
- 渐进式学习路径：后台任务先生成并保存第一周，再基于同一画像逐周补全后续周，每周生成 7-10 个可验收任务与资源入口。用户中途打开页面时读取 `meta.backgroundGeneration` 显示进度并轮询数据库，不会另起重复规划；后台失败后仍可通过原有页面生成接口继续缺失周次。生产环境使用独立路径执行器承载画像后的长任务，避免占满普通资源或视频任务线程池。
- 题库生成：支持文档上传、题目生成、考试记录与 AI 评分。考试会同时兼容题单内嵌题目和会话顶层题目；空题单不会启动计时、写入历史或提交评估证据，并提供明确返回入口。考试计时按会话开始后的真实经过时间计算，进行中可确认退出，移动端不会横向溢出。
- 登录深链恢复：访问受保护的二级或更深页面时，路由守卫会把同源 `path + query + hash` 带到登录页；运行中遇到 401 也使用同一规则。登录完成后回到原目标，外部地址、协议相对地址、畸形地址和登录循环均回退到默认学习画像页。
- PPT 生成：`/personalized-resources/ppt` 全屏嵌入精简版 OhMyPPT（仅首页与会话，默认包豪斯风格），普通访问进入快速创建，学习路径携带主题、要求和页数时直接进入可恢复的生成会话；原有 Harness 后台任务与 `/ppt-generator/generating/:sessionId` 继续兼容。
- 思维导图：静态 H5 工具集成在 `/mind-map`。
- 视频查找：B 站学习视频检索集成在 `/video-search`，后端提供必要代理、主题筛选和封面字段；该能力是视频检索，不宣称生成视频成片。
- 单片机模拟器：内置 Arduino Uno 与 AT89S52 两套板卡、21 个实验预设和 17 类可选元件；支持五步实验指南、完整引脚能力检查、多端子接线联动、代码编辑、虚拟编译烧录、运行记录保存，以及结合当前画像和历史实验的推荐接口。
- 个性化资源：基于画像、实验和路径生成学习资源。资源历史页会合并持久化任务与旧版本地记录，并明确区分加载中、部分来源失败、全部失败和真实空记录；资源详情页通过 URL 中的任务/资源身份调用 `GET /api/xiaozhi/tasks/:taskId` 恢复内容，旧版本地缓存只作为带来源标记的兼容回退。详情页展示任务来源、画像依据、规划策略、专项智能体、Harness 运行与 Handoff、Skill/MCP、质量审核、验证状态和知识引用；未返回的证据明确标为“未返回”，不会伪造分数或智能体。Markdown 先转义再有限渲染，Mermaid 使用严格安全模式，模型生成的 HTML PPT 只在禁用脚本且带 CSP 的沙箱 iframe 中预览。
- 资源学习反馈闭环：资源详情可记录“完成学习”“需要巩固”或“暂时受阻”，反馈按当前用户、任务 ID 与资源缓存键组合隔离，避免同一生成任务中的多个资源互相覆盖。已有学习路径节点会同步完成状态；没有对应节点时不会创建伪路径缓存。提交后可继续查看效果评估、返回学习路径，或在需要巩固时转入智能导师。
- 智能辅导：`/smart-tutor` 展示嵌小智通过 `learning.tutor.answer` Skill 生成的苏格拉底追问、费曼复述任务、三级提示、带解析练习、Mermaid 学习流程、学习卡、知识引用和 Harness 执行轨迹；同一页面支持悬浮窗嵌入预览与新页面完整打开。
- 数字人面试：集成讯飞数字人 SDK、题目生成、追问和可选关键帧分析。数字人连接、销毁和播报是独立的限时 best-effort 支线，面试 API 返回首题、下一题或总结后会立即解锁文字输入、发送、结束与重新开始；数字人或摄像头失败不会覆盖面试状态，也不会阻断完整文字面试。`/api/avatar/config`、`/api/avatar/diagnostics` 与备用会话接口均要求登录，防止匿名请求消耗数字人额度。

## 知识网络展示

`/knowledge-network` 是与学习画像、学习路径和个性化资源并列的独立二维知识网络功能页，顶部主导航可直接进入；旧地址 `/personalized-resources/knowledge-network` 仅保留兼容重定向。图谱前端直接参考并改编 GPL-3.0 开源项目 [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki) 的 Graph View：Sigma.js 3 使用 WebGL 绘制节点、边和标签，Graphology 保存图结构，ForceAtlas2 通过独立 Web Worker 完成布局。当前作品索引会形成 12,000 余个真实文档节点；接口只返回文档元数据及关系，不会把全部 chunk 正文一次发送到浏览器，引用片段继续按节点展开。

## 智能体数字孪生展示

`/agent-digital-twin` 是与 `/knowledge-network` 相互独立的架构展示功能页，主导航提供“数字孪生”入口，TvT.js 场景嵌入在导航栏下方并填满剩余视口。页面直接复用用户提供并确认具有商业授权的 TvT.js / `networkLinkTopology` 静态场景，资源位于 `img/digital-twin`，由主前端同源发布：Vite 开发环境跟随 `5088` 端口，构建后一键启动环境跟随后端统一入口 `3000` 端口，不需要单独启动 `5174` 服务。

当前场景包含 14 个展示节点和 22 条展示连线，用于表达主控、能力组、知识资源、实验与评估之间的信息流。一个展示节点可以代表一个能力组，因此这些节点不计入 Harness 智能体角色数量，也不改变 22 个 Harness 角色和 18 个注册 Skill 的真实统计口径。页面固定标记为“架构展示 · 非实时运行”，不宣称展示真实实时调用记录；数字孪生只增强答辩展示层，不替换学习画像、学习路径、资源生成、实验与效果评估闭环。

数字孪生包装页把固定 `1920x1080` 场景按可用视口等比缩放，桌面和移动端均不要求横向滚动；同源资源预检失败时显示原因与重试入口。OhMyPPT 全屏包装页在 iframe 上方保留“返回个性化资源”，加载前预检 `/ppt/`，失败时不会留下空白全屏页面，并提供重试。

验证方式：在 `frontend` 目录执行 `npm run test:wrapper-pages` 和 `npm run build -- --emptyOutDir=false`，确认构建产物包含 `dist/digital-twin/index.html`；运行一键启动脚本后登录并访问 `http://127.0.0.1:3000/agent-digital-twin`。开发环境可访问 `http://127.0.0.1:5088/agent-digital-twin`。

万级图谱保留全部真实节点与关系。页面使用由节点 ID 和知识域生成的稳定分区坐标：知识域通过黄金角、紧凑椭圆半径和稳定哈希扰动形成不规则且可复现的交叠分布，域中心间距约为单域尺度的 1.90 倍，并限制最外层半径扰动以形成连续知识云；域内以文档真实 `topics` 为锚点再次形成主题子簇，每个子簇使用独立方向的椭圆尺度、三阶与五阶波瓣边界及非对称扰动，避免文档聚成规则圆球。没有主题标签的文档进入所属域的通用有机分区。刷新不会随机漂移，也不再形成等距圆环。节点尺寸和标签密度随节点总量、连接度动态调整，拖动视图时暂停边和标签绘制。关系边采用确定性语义缩放和深靛蓝色低透明度渲染：总览绘制约 4% 的骨架边，随缩放按 8%、14% 和 24% 逐级展开；搜索、悬停或选中节点时用青绿色高亮可读的直接关系。所有边始终保存在 Graphology 中并计入真实统计，适应视图也基于完整图结构，因此视觉降噪不改变接口数据或知识关系口径。

对于度数过高的知识中枢或热点主题，悬停时最多高亮 16 条、选中时最多高亮 32 条确定性代表关系，并在检查节点时隐藏无关背景边；详情面板仍显示真实关联总数并可继续检索具体文档。超过 2,500 个节点时默认使用由节点 ID 生成的稳定坐标，仅在用户点击“重新布局”时调用 ForceAtlas2 Worker，避免浏览和悬停期间节点移动。

为了在分区降噪后仍体现整体知识结构，页面将真实存在的“知识中枢 → 知识域”关系作为常驻青蓝色主干，并固定显示中枢与知识域标签。后端还会识别真实文档中跨知识域重复出现的规范化主题，用低亮紫蓝色链式桥接这些主题节点；链式结构避免同主题全连接造成过绘制，关系统计包含这些 `shared_topic` 边。主干与跨域桥接均直接来自图谱接口，不新增装饰关系或虚构语义。

该页的数据口径来自当前课程索引、当前用户私有知识、真实 Harness 运行和反哺候选。`GET /api/knowledge-network/overview?view=atlas&limit=15000` 返回文档级图谱，默认调用仍保留聚合视图。搜索框在浏览器内对当前全部节点执行轻量相似度排序，依次考虑名称精确匹配、前缀、包含、来源、知识域、分词命中与字符二元组相似度，返回前 10 个结果；点击或键盘回车会直接定位原图谱节点，不另造搜索节点或删减图谱。Vue 适配实现位于 `frontend/src/components/KnowledgeSigmaGraph.vue`，布局 Worker 位于 `frontend/src/workers/knowledge-graph-layout.worker.js`，上游 GPL-3.0 许可证保存在 `frontend/public/vendor/llm-wiki/LICENSE`。它是“LLM Wiki 启发的可审计知识演化网络”，不宣称实现自动递归重写知识库的完整 LLM Wiki 引擎，也不包含 3D 或数字孪生能力。

知识网络顶部保留“关系网络”和“AI 知识库自生长”两个固定模式。“关系网络”只展示本地课程索引和当前用户私有知识，不再混入智能体运行、审核候选等展示节点；正式 `course_knowledge_index.json` 是文档关系的唯一课程索引来源，`course_knowledge_index_catalog.json` 是由该索引生成的文档级只读投影，使低内存部署无需反序列化全部切片文本即可展示同等数量的真实文档节点。便携源码包未携带体积较大的原始 `rag文档` 时，课程知识加载器会只读已打包索引，禁止用空语料覆盖正式索引。“AI 知识库自生长”用于用户隔离的长期对话记忆：嵌小智总控与学习画像每完成一轮对话，后端都会先保存原始用户消息，再在智能体回复后补全核心摘要、主题和目标/偏好/薄弱点等学习信号。最近完成的记忆通过 `longTermMemories` 合并到下一轮智能体上下文，并进入平台学习证据；聊天内容不会被当作已经核验的课程事实，也不会直接写入可信 RAG 文档。

对话记忆保存在 `knowledge_growth_memories`，每条记录保留来源入口、来源消息、原始问答、提取器版本和时间，按用户鉴权隔离。`scripts/seed-conversation-growth-demo.py` 可为本地 `admin123` 幂等写入六轮明确标注的答辩演示对话，同时清理旧版候选/审核演示数据。相关接口均要求登录：

- `GET /api/knowledge-network/overview`
- `GET /api/knowledge-network/expand`
- `GET /api/knowledge-growth/overview`

验证命令：

```powershell
python -m py_compile backend/app.py backend/database_schema.py backend/showcase_network.py backend/knowledge_growth.py
python -m unittest backend.tests.test_showcase_network backend.tests.test_knowledge_growth backend.tests.test_course_knowledge_portable_cache
python scripts/seed-conversation-growth-demo.py
npm --prefix frontend run build
```

### 课程知识扩充

作品运行目录额外加入 105 MB 规范化文本，覆盖 FreeRTOS、RISC-V、LVGL、TinyUSB、lwIP、Raspberry Pi Pico SDK、CMSIS 5/6、Mbed OS、CppUTest 与 Unity Test。每个文本文件头部记录原仓库、commit、许可证、原始路径、SHA-256 与导入日期；详细清单位于 `docs/knowledge-expansion-sources.json`。导入过程不保留 Git 历史、二进制图片、构建目录、依赖目录或临时下载文件。完整作品目录的临时 ZIP 试算为 922.12 MB，低于 1 GB 并保留约 101.88 MB 安全余量；试算压缩包已删除。

为了避免源码包和作品包重复携带大语料，源码只保存可重复执行的导入脚本；开发时可通过 `COURSE_KNOWLEDGE_CORPUS_DIR` 与 `COURSE_KNOWLEDGE_INDEX_PATH` 指向作品目录中的语料和索引。重建命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\expand-course-knowledge.ps1 `
  -CorpusDirectory "<作品目录>\rag文档" `
  -IndexPath "<作品目录>\backend\data\course_knowledge_index.json"
```

## 本地运行

### 1. 后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

默认端口是 `3000`。健康检查：

```text
http://localhost:3000/api/health
```

### 2. 单端口前端

前端构建产物由 Flask 在 `3000` 端口直接托管，浏览器只需要访问：

```text
http://localhost:3000
```

前端路由、`/api/*`、视频封面代理和 PPT 聚合接口均保持同源。首次或前端更新后运行：

```bash
start-frontend-backend.bat
```

该脚本会先执行 `frontend/npm run build`，再启动或复用 `3000` 后端。`frontend/npm run dev` 的 `5088` 仅保留给前端开发调试，不是用户访问入口。
### 单片机实验台

入口：`/personalized-resources/mcu-simulator`。实验台目录与接线合同统一由
`backend/mcu_catalog.py` 提供，前端不再维护一份容易漂移的硬编码副本。

- 板卡：Arduino Uno 暴露 D0-D13、A0-A5 和电源/参考引脚能力；AT89S52 展示完整 40 Pin DIP、P3 复用功能与 P0 开漏输出警告。
- 实验：Arduino 侧包含 GPIO、按键、交通灯、PWM、ADC、串口、光照、超声波、舵机、DHT22、I2C OLED 和继电器；8051 侧包含流水灯、按键、七段数码管、交通灯、蜂鸣器、RAM、堆栈和端口镜像，另提供两套空白工程。
- 元件：17 类元件均声明真实端子、必接状态和可接受引脚能力；用户可点击元件端子再点击主板引脚完成接线，SVG 导线、下拉选择和引脚检查器同步更新。
- 步骤：每个预设由后端生成目标、元件、逐端子接线、烧录和验收五步指南；烧录校验通过后自动完成前四步，验收项由用户逐项确认。
- 推荐：推荐排序读取当前激活画像的目标、薄弱点、资源偏好和最近 60 条 MCU 实验记录；学习路径中的 MCU 任务会在创建后台任务时自动解析成合法板卡与预设，跳过已有通过记录，并保存推荐分数、原因和来源。用户明确指定合法预设时保持原选择。
- 原理约束：后端同时校验代码入口、受支持语句、元件必接端子、引脚存在性、I2C/PWM/ADC/UART 等能力和 P0 外接上拉提示。`analogWrite(2, ...)` 这类与 Uno 硬件能力冲突的代码会被拒绝。
- 仿真边界：当前“烧录”生成可追踪的虚拟固件指纹，并运行浏览器教学解释器，不会编译 AVR 机器码或写入 USB 开发板。精确机器周期、中断竞争、电气负载、舵机供电和真实外设时序必须在实板或完整指令级仿真器中复验，页面会持续显示该边界。

认证接口：

- `GET /api/mcu/catalog`：返回板卡、引脚、元件、实验、五步指南和开源来源；支持 `board`、`query`、`difficulty`、`component` 筛选。
- `POST /api/mcu/recommend`、`POST /api/mcu/recommendations`：根据画像、请求主题和实验历史返回推荐结果及可解释原因；指定 `board` 时只返回该体系实验，`excludeCompleted=true` 时优先推进未完成项目。
- `POST /api/mcu/flash`：校验代码与接线并生成稳定虚拟固件 ID；失败返回 `422` 和结构化诊断。
- `POST /api/mcu/save-experiment`：保存实验结果，未知实验 ID 或超过 20KB 的运行数据会被拒绝。
- `GET /api/mcu/experiments`：返回当前用户最近的实验记录，并兼容读取旧版本遗留的截断 JSON。

验证命令：

```bash
python -m pytest backend/tests/test_mcu_catalog.py backend/tests/test_mcu_api.py -q
cd frontend
npm run build
```

### 多模态输入接口

- `POST /api/multimodal-inputs`：`multipart/form-data` 上传，字段 `files` 最多 4 个、单个最大 50 MB，`context` 标记调用场景。
- `GET /api/multimodal-inputs/<inputId>/file`：按当前登录用户校验归属后读取图片、视频或文件，支持视频 Range 请求。
- `/api/xiaozhi/chat`、学习画像会话消息和背景对话接口均接受 `attachments` 数组；只认后端已登记且属于当前用户的附件 ID。

```bash
cd backend && python -m unittest tests.test_multimodal_inputs -v
```

### 画像人像持久化

- `POST /api/learning-profile/profiles/<reportId>/portrait`：幂等启动后台头像任务并立即返回；任务已运行时返回同一 `generating` 状态，已有数据库图片时直接复用。请求体 `{ "force": true }` 用于失败后重试或画像内容更新后的重生。
- `GET /api/learning-profile/profiles/<reportId>/portrait/status`：返回 `missing`、`generating`、`ready` 或 `failed`，以及是否已持久化、重试次数和安全截断后的错误信息；画像列表与详情接口也会合并数据库中的真实头像状态。
- `GET /api/learning-profile/profiles/<reportId>/portrait`：按当前登录用户校验画像归属后返回图片。
- 启动时会把旧目录 `backend/data/profile_portraits/profile-*.png` 中能匹配到报告的图片迁入数据库，并把报告中的头像地址改为稳定的报告接口；旧地址仍保留兼容读取，但同样需要登录和归属校验。
- 头像元数据写入不会修改画像的语义更新时间，避免仅加载头像就触发学习路径重新生成。
- 并发认领使用 SQLite 写事务和一次性 `generation_token`；服务启动会立即释放上次进程遗留的 `generating` 任务，前端打开对应报告时自动重新入队，旧 worker 不能覆盖新任务结果。

## 文本与多模态模型路由

平台按照输入模态使用固定的预处理链，配置依据为[讯飞星辰 MaaS Astron Coding Plan](https://www.xfyun.cn/doc/spark/CodingPlan.html)：

```text
文本 ------------------------------> Spark X2 Agent (xsparkx2agent, 256k)
图片 -> Kimi-K2.6 (xopkimik26, 256k) -> 视觉证据文本 -> Spark X2 Agent
文件 -> 本地结构化文字提取 ------------> 提取文字 ----> Spark X2 Agent
```

图片会先归一化尺寸并移除 EXIF 方向差异，Kimi 只负责提取可验证的文字、图表、电路和界面事实，不直接回答用户；文档原始二进制不会发送给文本模型。预处理结果作为不可信学习证据写入上下文，不能覆盖系统提示。实际模型、上下文长度和交接目标可通过 `GET /api/llm/runtime`、附件的 `processingRoute` 以及 Harness `modelRuntime.routing` 查看。视觉模型失败时仅允许使用带“待核验”标记的 OCR 结果，不能静默伪装成 Kimi 输出。

相关配置：`ANTHROPIC_MODEL=xsparkx2agent`、`VISION_LLM_MODEL=xopkimik26`、`LLM_CONTEXT_WINDOW=262144`、`VISION_LLM_CONTEXT_WINDOW=262144`。密钥仍只保存在后端 `.env`。

首页“真实模型能力”区按照实际代码与服务端配置公开模型分工：主控和文本智能体使用讯飞星火 Spark X2 Agent（`xsparkx2agent`）；国产视觉模型 Kimi K2.6（`xopkimik26`）负责视觉证据预处理；国产 Seedance 模型负责视频生成，默认通过 Coze 工作流调用 Seedance 1.5，并提供 `doubao-seedance-2.0-mini` 与 `doubao-seedance-2.0` 可选引擎。学习画像插画、视频首帧和 PPT 配图统一使用 APIMart Seedream 4.5（固定模型 ID `seedream-4-5`）；视频旁白默认使用讯飞超拟人语音合成 WebSocket 服务，发音人由 `XFYUN_TTS_VOICE` 指定。讯飞数字人播报属于数字人 SDK 能力，`x4_yezi` 是服务端配置音色，不计作独立大模型。首页不展示密钥、工作流 ID 或服务端地址。

多模型由 `XiaoZhiAgentHarness` 统一封装，运行时架构标识为 `agent-harness-supervisor-blackboard`：Supervisor 与共享黑板接收画像、任务和学习证据；`model_routing.py` 按模态选择文本、视觉或本地文档提取链路；版本化 Skill 通过 Skill Registry、MCP Tool Gateway 与 Handler Registry 调用真实执行器；输入输出经过 JSON 契约校验，并进入质量审核、安全审核、检查点持久化和可观察执行轨迹。该架构说明同步展示在首页模型区。

## PPT H5 集成说明

PPT 功能使用 OhMyPPT 的独立 FastAPI 生成引擎。用户工作台和智能体后台任务共用同一生成引擎，后台任务继续保留嵌小智总控、画像绑定和 Harness 审核链：

```text
主前端 /personalized-resources/ppt
        ↓ 全屏 iframe
精简 OhMyPPT /ppt/#/（首页、会话、快速创建、返回个性化资源）
        ↓ 主题参数存在时创建稳定会话并直接进入生成页
OhMyPPT FastAPI 127.0.0.1:8765

嵌小智 / 学习路径后台任务
        ↓ Flask /api/ppt-h5/generate-background
Supervisor / Skill / MCP / Handoff / 质量与安全审核
        ↓ OhMyPPT FastAPI
/ppt-generator/generating/:sessionId?xzTask=:taskId
```

智能体统一入口 `POST /api/personalized-resources/agent-task` 在 `resourceType=ppt` 时会接收 `topic`、`prompt/userMessage`、`pageCount/pages`、`styleName`、`styleDescription`、`cacheKey` 等参数，创建稳定的 OhMyPPT `sessionId`，并立即在任务结果中返回 `ppt.sessionId`、`ppt.pageCount`、`ppt.route` 和 `/ppt-generator/generating/:sessionId?...&xzTask=:taskId`。因此嵌小智、学习路径任务卡或后续 MCP Tool 只需要传参即可启动后台生成，用户打开窗口后看到的是持续更新的生成状态，不需要再次填写主题或页数。

浏览器不会直接携带模型 API Key 调用 OhMyPPT。Flask 与 FastAPI 之间使用带时间戳的 HMAC 内部签名传递当前用户选择的协议、模型地址和模型名；FastAPI 同时校验地址白名单、页数、HTML 结构和外部资源。解析层兼容严格 JSON、标准分隔格式以及中英文 Markdown 字段，但只有返回指定页数且每页包含有效 HTML 时才算成功；生成失败不会使用本地模板伪装为成功。

OhMyPPT 默认使用 `Spark X2 Agent`（`xsparkx2agent`）。独立引擎优先读取 `ppth5/backend/.env`，示例见 `ppth5/backend/.env.example`；模型密钥只保存在服务端环境文件中，不写入浏览器配置、构建产物或 API 响应。原始 H5 的快速创建把该模型识别为服务端托管模型；本机回环地址可在开发模式下使用默认模型，线上浏览器请求必须通过主站登录态校验，智能体后台请求继续使用 HMAC 内部签名。

为避免模型一次返回整份长 HTML 导致读取超时，OhMyPPT 默认按每批 3 页、最多 2 批并行生成，再按原始页码合并并执行页数、HTML 安全与结构校验。失败信息会标明具体页段，系统不会因单批超时而重复执行整份 PPT；批大小与并发数可通过 `OHMYPPT_LLM_BATCH_SIZE`、`OHMYPPT_LLM_MAX_PARALLEL` 调整。

原始 H5 在等待整份模型结果时会持续展示当前阶段、已等待时长和保守进度，模型尚未返回时进度不会伪装为页面已完成；“取消生成”会中止当前浏览器请求。模型返回后再进入页面解析、结构校验和逐页写入阶段。

默认模型请求最长等待 600 秒且不自动整单重跑，避免五页生成在 300 秒超时后静默从头执行；失败会显示为失败状态，由用户主动决定是否重试。

主站工作台使用稳定查询指纹创建 OhMyPPT 会话，相同学习任务刷新后会恢复同一会话；未传页数时默认生成 6 页。演示优先使用原生 Fullscreen API，内置浏览器不提供该 API 时自动切换到页面级全屏，点击动画完成后继续翻页，并支持 `Esc` 退出。

`GET /api/personalized-resources/ppt/tasks` 从 SQLite 返回 Harness 后台 PPT 任务的历史和运行状态；每条完成记录保留 `profileReportId`、`runId`、Skill、MCP Tool 和审核结果。OhMyPPT 工作台中的“会话”负责直接创建内容的浏览器侧恢复与继续编辑。

相关文件：

- Flask 委派入口：`backend/ppt_h5.py`
- OhMyPPT 签名客户端：`backend/ohmyppt_client.py`
- Flask 路由：`backend/app.py`
- OhMyPPT FastAPI：`ppth5/backend/main.py`
- PPT H5 源码：`ppth5/`
- 已集成静态产物：`img/ppt/`
- 主前端工作台容器：`frontend/src/views/PptWorkbenchView.vue`
- 兼容版任务入口页：`frontend/src/views/PptGeneratorView.vue`
- 独立任务页：`frontend/src/views/PptGeneratingView.vue`

如果修改了 `ppth5` 源码，需要重新构建并同步静态产物：

```bash
cd ppth5
npm install
npm run web:build
```

然后把 `ppth5/dist-web` 的内容复制到：

```text
img/ppt/
```

再构建主前端。

## 构建

### 前端构建

```bash
cd frontend
npm install
npm run build
```

构建结果输出到：

```text
frontend/dist/
```

因为 `frontend/vite.config.js` 的 `publicDir` 指向 `../img`，所以 `img/ppt`、`img/mind-map-wizard`、`img/video-search` 会随主前端一起进入构建产物。

### 后端检查

```bash
cd backend
python -m py_compile app.py ppt_h5.py
```

## 学习路径渐进生成

学习路径入口 `/learning-path` 直接展示由“第一周、第二周”等节点组成的周次地图，避免周次与任务层级颠倒。选择一个周次后，才进入该周的具体任务列表；任务页可返回周次地图。

周次节点会跳转至 `/learning-path/week/:stageId`。该页面沿用周学习计划的卡片布局，但卡片内容改为所选周的动态任务节点，例如目标拆解、概念建模、示例跟做、实操验证、专项测评与复盘迭代；任务卡片继续使用其对应的资源入口。

旧地址 `/learning-path/stage/:stageId` 仅保留 `overview` 作为周次地图；其他旧阶段地址会自动迁移到对应的周任务页，避免再次出现“地图展示任务、列表展示周次”的反向流程。

1. 学习画像报告保存后，后端以 `(user_id, profile_report_id)` 检查已有完整路径和活动任务，并在同一 SQLite 写事务中幂等创建 `xiaozhi_tasks.task_type=learning_path` 后台任务。
2. 独立路径执行器先以 `generationPhase: "first-week"` 保存第一周，再以 `generationPhase: "remaining-weeks"` 和已有 `existingConfig` 逐周合并后续路径；每周的 Harness 运行都绑定同一个后台 `taskId`。
3. `GET /api/learning-path/config` 在 `meta.backgroundGeneration` 返回任务 ID、状态、进度、当前阶段和已保存周数。页面只轮询该状态并恢复数据库结果；`POST /api/learning-path/generate-stream` 与非流式 `POST /api/learning-path/generate` 保留为失败重试和兼容入口。
4. 已规范化路径使用无数据库写入的只读快路径；只有首次读取旧版结构并确实发生格式迁移时才回写一次，不再在每次 GET 中镜像更新两张路径表。`meta.activeProfileSummary` 随配置返回当前画像 ID、名称和版本，周次地图无需再请求完整画像历史。`GET /api/learning-path/stages/{stageId}?includeConfig=0` 只返回周任务、路径元数据和更新时间，旧调用不传参数时仍保留完整 `config` 以兼容现有客户端。

流式接口实时返回 Supervisor、画像上下文、知识库检索、Skill Registry、MCP Tool、输出契约、质量审核、内容安全和结果保存事件。周次地图右下角提供可折叠的详细输出窗口，展示当前智能体、执行阶段、尝试次数、审核状态、`runId` 和时间线；失败时保留结构化错误码及重试入口，不再把后端异常隐藏成无限“生成中”。Skill 输出契约允许 `partial` 渐进路径先返回 1 个阶段，质量审核仍要求非 `partial` 完整路径至少包含 3 个阶段，并继续拒绝降级或带错误的产物。

嵌小智生成的完整路径或临时补出的阶段路径先作为候选结果存在，只有 Harness 结构、质量与安全审核全部通过后才写入当前画像的路径配置；审核拒绝不会覆盖此前已接受的路径。历史规则降级路径会标记为 `personalizationStatus=degraded`，页面显示重新生成入口，后端同时拒绝其周资源准备请求，避免未经模型审核的路径继续消耗资源生成额度。配置加载失败和生成失败分别显示，不会伪装成“没有画像”或成功路径。

自动生成使用数据库事务和活动任务检查避免多标签页、多进程或重复画像完成请求并发规划；学习证据版本只由聊天、答题、实验和资源使用等真实学习行为计算，路径生成写入本身不会再次触发路径重建。

每份学习画像都有独立的学习路径。路径以 `(user_id, profile_report_id)` 为复合主键持久化到 SQLite 的 `learning_path_profile_configs`，`user_learning_path_configs` 仅保留为当前画像兼容镜像；画像完成后的后台任务、页面兼容生成和嵌小智主动生成都会写入指定画像记录。历史页可新建互不覆盖的画像、查看每份画像的路径状态并直接打开对应路径。切换到从未生成路径的旧画像时也会自动排队，而不再要求先进入路径页面；已有完整路径会直接恢复，不会被清空、改写或触发重复模型调用。部署初始化会把旧用户路径按其 `profileReportId` 自动迁移到新表。

每周完整任务集固定覆盖题库生成、PPT生成、思维导图、视频查找、单片机模拟器和 AI 视频讲解六类资源智能体，每类至少出现一次；视频查找仍是检索能力，AI 视频讲解使用独立的 `generated_video` 类型。学习路径智能体在生成周任务时一次性产出结构化 `resourceType`、`resourceParams`、`resourcePrompt` 和 `resourceSelectionReason`，保存前执行整周六类覆盖收口；资源派发阶段直接复用这些参数，不再为每个节点重复调用一次资源路由模型。路径只为 AI 视频创建 `waiting_for_user` 的待确认任务，入口携带画像相关主题与提示词；用户打开工作台、选择模型并确认前不会调用任何视频模型或消耗视频生成额度。资源计划版本 `profile-routed-resources-v19-weekly-six-resource-coverage` 会让 `v18` 历史完整周重新编排，避免任何一类资源缺失或单一资源过度集中。

完整学习路径保存后，后端把所有已启用周次投入周资源准备线程池。每一周使用快速派发模式：先在一次短事务中为全部节点创建持久化任务记录和带 `xzTask` 的页面入口，再把题库、PPT、导图、视频查找和单片机实验等普通资源全部提交共享后台执行器；接口不会等待资源生成完成。普通资源默认最多 10 路并行，可通过 `RESOURCE_AGENT_MAX_WORKERS` 在 1-12 之间调整。不同周写回时通过用户级短锁重读最新配置并只合并当前周，避免并发覆盖任务 ID 或进度。`generated_video` 是唯一例外：入口立即可点击，但状态为 `waiting_for_user`，用户进入三栏视频工作台后编辑提示词、时长、风格、音色、清晰度和模型，并手动确认后才启动原任务。

周详情页调用 `POST /api/learning-path/stages/:stageId/prepare-resources` 并传入 `{ "parallelDispatch": true, "advance": false }`。响应返回后，无论任务是 `queued`、`running`、`complete`、`waiting` 还是 `failed`，只要任务记录已建立，卡片都保留可打开入口；前端每 2 秒通过 `GET /api/learning-path/stages/:stageId/resource-tasks` 更新状态，并用“资源生成中 / 资源已生成 / 待用户确认 / 生成失败”区分。重复进入或重复派发会复用现有任务 ID，不会再次消耗模型调用。各资源生成任务自身仍经过嵌小智 Harness 的结构化输出、知识依据、质量审核与安全审核；单任务失败按原上限重试，不阻塞其他任务。任务卡片按序号使用不同强调色，悬浮只改变阴影，不改变位置或尺寸。周资源和路径生成并发上限还可通过 `LEARNING_PATH_WEEK_PREPARATION_MAX_WORKERS` 与 `LEARNING_PATH_GENERATION_MAX_WORKERS` 调整。

节点的 `taskId`、缓存键和结果路由会写回 SQLite。缓存键包含资源编排版本；升级资源语义规则时只解除旧节点缓存引用，历史任务记录仍保留，但错误的旧路由不会重新挂回当前周。重复进入、刷新或在同一版本编排完成后继续调用接口都会复用原任务，不会重复消耗模型请求；`GET /api/learning-path/stages/:stageId/resource-tasks` 用于轮询生成状态。带 `xzTask` 的思维导图页直接读取后台 `selectedResource.content`，通过隔离 iframe 接入 Mind Map Wizard 的 SVG 布局与交互引擎，支持滚轮缩放、拖拽、适应屏幕、全屏和 SVG 下载；页面不会再次调用模型。新任务使用 `# / ## / ###` Markdown 导图契约，至少包含 4 个有具体含义的主分支，并在节点中保留课程知识库引用；数据库中的旧 Mermaid `mindmap` 内容会由前端兼容转换后继续显示。

思维导图后台任务不再依赖当前页面内存或 URL 临时状态。`GET /api/personalized-resources/mind-map/tasks` 按当前用户从 SQLite 读取导图任务及 `queued / running / complete / failed` 状态；基础导图页展示历史记录，并在存在后台任务时定时同步状态。用户离开后重新进入仍可查看进度或打开已完成导图，失败任务可基于原主题重新生成；任务详情页右上角提供历史记录入口。

思维导图创建首页采用 Mind Map Wizard 风格的集中式工作台：圆角主题输入器、快捷主题和生成按钮位于首屏中央，并明确展示画像适配、课程知识引用与质量审校三项真实生成能力。历史任务移至创建区下方，以响应式卡片网格展示持久化任务；空历史仅显示紧凑提示，不再占用固定侧栏。验证命令为 `cd frontend && npm run build`，浏览器验收覆盖桌面与移动视口、快捷主题回填、空历史和已有任务状态。

路径智能体会读取当前激活学习画像中的目标、薄弱点、资源偏好与可投入时间，动态决定周主题和 7-10 个任务。每个阶段详情页展示“学习任务与资源”，任务节点可跳转到导图、PPT、视频、题库、单片机实验等个性化资源。

可用以下命令进行基础校验：

```bash
cd backend
python -m py_compile app.py learning_agents.py resource_workflow.py
cd ..
python -m pytest backend/tests -q

# 六类周资源覆盖、并行收口、延迟 AI 视频和多画像路径回归
python -m pytest backend/tests/test_learning_path_progressive.py backend/tests/test_learning_profile_api.py backend/tests/test_learning_profile_versions.py backend/tests/test_learning_profile_greeting_guard.py -q

# 画像 BLOB、异步状态、并发幂等、失败重试
python -m pytest backend/tests/test_learning_profile_api.py backend/tests/test_profile_portrait_service.py -q

# 多画像路径隔离、切换恢复与旧路径迁移
python -m pytest backend/tests/test_learning_path_profile_switch.py -q

# OhMyPPT 委派、内部签名、模型输出解析和结构校验
python -m pytest backend/tests/test_ohmyppt_parser.py backend/tests/test_ohmyppt_client.py backend/tests/test_model_runtime_hardening.py -q

# 评分表硬指标案例：5 类资源、4 组推荐、5 个辅导、3 个评估
# 先启动统一 3000 入口，并为已有激活画像的验收账号设置密码。
$env:HARNESS_E2E_PASSWORD = "<评审账号密码>"
python backend/harness_real_e2e.py --base-url http://localhost:3000 --output-dir .\测试报告
python backend/scoring_evidence_suite.py --output-dir .\测试报告

# 不调用真实模型的证据链回归测试
Set-Location backend
python -m unittest tests.test_harness_real_e2e tests.test_scoring_evidence_suite -v
Set-Location ..

# 登录深链与考试会话：单元契约 + Playwright 桌面/移动验收
Set-Location frontend
npm run test:auth-redirect
npm run test:auth-redirect:e2e
npm run test:question-exam-session
npm run test:question-exam-session:e2e
npm run build -- --emptyOutDir=false
Set-Location ..

cd frontend
npm run build
npm run test:learning-profile-chat

# 先启动统一 3000 入口，再故意悬挂数字人配置请求验证面试 fail-open 全流程
npm run test:interview-fail-open

# start-all.bat 启动后检查独立引擎与 Flask 聚合健康状态
curl http://127.0.0.1:8765/api/health
curl http://localhost:3000/api/ppt-h5/health
```

## 软件杯赛题对照

本项目的功能调整遵循 `C:\Users\han\Desktop\03_项目与作品\软件杯\赛题要求` 中的赛题、评分细则和操作文档。涉及智能体、学习画像、学习路径、资源生成、生成进度、知识库、安全审核、评估、部署等重要改动时，均应同时核对以下赛题要求并更新本 README：

- 对话式动态学习画像，支持随学更新。
- 多智能体协同生成不少于五类个性化、多模态资源。
- 基于画像、进度与掌握情况的动态学习路径和资源推送。
- 采集分析、资源生成、学习验证、反馈调整的完整闭环。
- 知识库依据、防幻觉与内容安全审核，以及可见的生成进度追踪。

资源历史与详情闭环的聚焦验证命令：

```powershell
Set-Location frontend
npm run test:resource-detail
$env:E2E_BASE_URL = 'http://127.0.0.1:5088'
npm run test:resource-detail:e2e
npm run build -- --emptyOutDir=false

Set-Location ../backend
python -m pytest tests/test_learning_profile_api.py tests/test_harness_real_e2e.py tests/test_mcp_protocol.py -q
```

资源详情 E2E 在桌面 `1440x900` 与移动 `390x844` 视口中拦截合成 API 响应，验证 URL 恢复、404 重试、真实证据、脚本注入隔离、Markdown 导图分支、两类反馈分支、闭环入口和横向溢出；它不写入生产 SQLite。

标准交付文档：

- `docs/DEVELOPMENT_GUIDE.md`：开发环境、扩展子智能体、数据迁移和提交检查。
- `docs/REQUIREMENTS_ANALYSIS.md`：大学生学习痛点、用户场景、功能/非功能需求及技术结合点。
- `docs/TEST_GUIDE.md`：18 个 Skill、MCP JSON-RPC、真实讯飞和浏览器验收方法。
- `docs/SYSTEM_DESIGN.md`：22 个已实现 Harness 角色、18 个 Skill、Supervisor、共享黑板、Handoff 和完整学习闭环。
- `docs/MCP_API_REFERENCE.md`：MCP JSON-RPC 方法、14 个 Tool、Resource URI 与外部调用示例。
- `docs/KNOWLEDGE_BASE.md`：6223 份课程资料（535.8 MB）、检索索引、引用、防幻觉、开放资料来源/许可和使用边界。
- `docs/AI_CODING_USAGE.md`：AI Coding 使用范围、真实案例、人工约束与可复现证据。
- `SCORING_MATRIX.md`：按 110 分评分表逐项维护当前证据、风险和下一步动作。
- `测试报告/本地无法保证得分清单-20260712.md`：主观评分、外部授权、线上稳定性、真实硬件和正式提交风险。

Codex 项目专用技能位于：

```text
C:\Users\han\.codex\skills\software-cup-requirements
```

## 部署

Linux 服务器上可使用：

```bash
bash deploy.sh
```

部署后的主要访问路径：

```text
https://lzhan.xyz/
https://lzhan.xyz/api/health
https://lzhan.xyz/ppt/
https://lzhan.xyz/api/ppt-h5/health
https://lzhan.xyz/ppt-api/health
```

当前部署结构中，PPT 不需要 Electron、xvfb 或 Node 后端服务，但需要 `feishengwangying-pptapi.service` 在回环地址 `127.0.0.1:8765` 运行 OhMyPPT FastAPI。生产 Nginx 的 `/ppt-api/` 仅作为同源服务入口；生成接口仍要求服务端内部签名，不能绕过嵌小智直接调用。

## 配置

后端配置优先读取环境变量，默认值集中在：

```text
backend/api_config.py
```

常用配置项：

- `PORT`：后端端口，默认 `3000`
- `FRONTEND_ORIGIN`：允许跨域的前端地址
- `ANTHROPIC_BASE_URL`
- `ANTHROPIC_AUTH_TOKEN`
- `ANTHROPIC_MODEL`
- `AVATAR_APP_ID`、`AVATAR_API_KEY`、`AVATAR_API_SECRET`、`AVATAR_SCENE_ID`、`AVATAR_ID`：讯飞数字人 APPID、鉴权信息、接口服务 ID 与该服务已授权的形象 ID；源码不提供账号或形象默认值，必须写入 `backend/.env` 或进程环境。`AVATAR_LEGACY_ENABLED` 仅在配置了兼容旧通道的形象 ID 时开启。
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

生产环境必须使用环境变量提供数字人和模型凭据，不要把密钥写入源码、README、前端构建产物或日志。登录后可调用 `GET /api/avatar/diagnostics` 检查主通道与备用通道，诊断响应只返回脱敏配置与状态。

## 第三方开源说明

本项目部分模块参考或基于第三方开源项目进行二次开发：

- 管理端：基于 Soybean Admin，MIT License。
- PPT 生成功能：参考 OnMyPPT / Oh My PPT，Apache License 2.0。
- 思维导图功能：参考 Mind Map Wizard，CC BY-NC 4.0，仅允许非商业使用，商业化需单独授权。

思维导图嵌入引擎位于 `img/mind-map-wizard/embedded/`。其中 `renderer.js`、`interaction.js` 和 `mind-map-elements.css` 来自 Mind Map Wizard，项目新增 `bridge.js`、嵌入页及 Vue 通信组件，以接收嵌小智后台生成的 Markdown，而未接入原项目的模型密钥、账号、分析统计或付费逻辑。

比赛展示时可以替换项目 Logo、名称和界面风格，但需在项目说明、答辩材料或 README 中保留来源、许可证和二次开发说明。详细内容见：

```text
THIRD_PARTY_NOTICES.md
```

## 超级管理员运行监控

管理端 `/admin/logs` 为只读服务器运行监控页，仅配置的超级管理员账号可访问。页面每 10 秒刷新 CPU、内存、磁盘、系统负载、项目服务和项目相关进程；后端每 30 秒采集一次，并将不含密钥、完整命令行和用户内容的 JSON 记录写入 `logs/system-monitor.jsonl`。日志单文件上限 5 MB，最多保留 5 个轮转文件。

接口为 `GET /api/admin/runtime`，普通用户及非超级管理员均返回 403。用户端和管理员端登录请求均设为 12 秒超时，服务器资源耗尽时会显示明确提示，不会长期停留在登录中状态。

验证命令：

```powershell
python -m pytest backend/tests/test_system_monitor.py -q
Set-Location frontend; npm run build
Set-Location ../admin; pnpm install --frozen-lockfile; pnpm run typecheck; pnpm run build
```

## 默认账号

后端初始化会创建管理员账号，默认值来自配置：

```text
用户名：admin123
密码：admin123
```

## 清理说明

本提取版没有包含：

- `node_modules`
- Python 虚拟环境
- `frontend/dist`
- `ppth5/dist-web`
- `backend/data`
- 日志文件
- 压缩包
- 截图与临时调试文件

安装依赖和构建产物请在目标环境中重新生成。

## AI generated learning video

`/personalized-resources/video-generator` adds an on-demand `generated_video` resource alongside the existing video-search tool. Its frontend is adapted from the local `纯AI视频工作流` workbench into the platform shell: creation parameters remain on the left, a clickable Vue Flow execution graph occupies the center, and node facts, segment batches, media previews and persisted logs are shown on the right. Browser-side compositing was not copied; the current platform keeps authenticated SQLite tasks and server-side FFmpeg output. Learning-path preparation creates one `waiting_for_user` entry for every week and only stores the profile-grounded prompt. It never chooses a model or calls a media API. The learner opens the workbench, chooses the engine and resolution, then explicitly calls `POST /api/personalized-resources/generated-videos/{task_id}/start` to start that same persisted task.

Seedance 1.5 remains the default and runs through `COZE_SEEDANCE_15_WORKFLOW_ID`, `COZE_SEEDANCE_15_API_BASE_URL` and the optional dedicated `COZE_SEEDANCE_15_API_TOKEN` (with the existing Coze token chain retained for compatibility). The two opt-in API engines use `VIDEO_VIDEO_API_KEY`: `VIDEO_VIDEO_MODEL_MINI=doubao-seedance-2.0-mini` and `VIDEO_VIDEO_MODEL_FULL=doubao-seedance-2.0`. The workbench accepts `480p`, `720p` and `1080p`; server-side output is normalized respectively to `854x480`, `1280x720` and `1920x1080`. First-frame generation reuses `SEEDREAM_BASE_URL` / `SEEDREAM_API_KEY`, is fixed to `seedream-4-5`, and uses the supported `2K` resolution. Narration defaults to XFYun super-human TTS through `XFYUN_TTS_APP_ID`, `XFYUN_TTS_API_KEY`, `XFYUN_TTS_API_SECRET`, `XFYUN_TTS_URL` and `XFYUN_TTS_VOICE`; credentials remain only in ignored environment files, returned MP3 frames are converted to AAC locally, and upstream business errors fail the material instead of producing an empty track. All paths limit image/TTS/video media operations with a process-wide six-slot gate, retry each material operation up to five times, then use server-side FFmpeg to normalize video, mix TTS, burn subtitles, concatenate MP4 output, and validate H.264/AAC streams with ffprobe. Failures are persisted as `failed` instead of remaining indefinitely `running`. Output is stored under `backend/generated/video/{user_id}/{task_id}` and is only exposed through authenticated, range-capable endpoints:

- `POST /api/personalized-resources/agent-task` with `resourceType: "generated_video"`
- `POST /api/personalized-resources/generated-videos/{task_id}/start`
- `GET /api/personalized-resources/generated-videos?status=complete&limit=50&offset=0`
- `GET /api/personalized-resources/generated-videos/{task_id}/file`
- `GET /api/personalized-resources/generated-videos/{task_id}/poster`
- `GET /api/personalized-resources/generated-videos/{task_id}/segments/{segment_id}/{image|audio|video}`

Every agent-created `generated_video` task is forced into `waiting_for_user`, even when a caller omits or overrides the `deferred` flag. The task stores the profile-grounded prompt in SQLite but does not enter the video executor until the owning user calls the authenticated start endpoint. Completed tasks remain in `xiaozhi_tasks`; the personalized-resource history view reads the paginated history endpoint, replaces the former code-example category with AI video, and opens each persisted video in a new tab. Task listing and media playback are both isolated by authenticated user ID.

Prerequisites: `ffmpeg` and `ffprobe` must be available on `PATH` (or configured with `VIDEO_FFMPEG_PATH` / `VIDEO_FFPROBE_PATH`). Configure the Coze, image, video and TTS credentials only in ignored `backend/.env`; variable names and non-secret model defaults are documented in `backend/.env.example`.

Verification commands:

```powershell
python -m py_compile backend/app.py backend/video_generation.py
python -m pytest backend/tests/test_video_generation_seedance_config.py -q
python -m pytest backend/tests/test_learning_path_progressive.py backend/tests/test_learning_path_profile_switch.py backend/tests/test_learning_profile_api.py -q
python -m pytest backend/tests/test_learning_path_read_performance.py backend/tests/test_admin_default_credentials.py -q
Set-Location frontend; npm run build
```
## Unified user and admin entry

The Flask entry on `http://localhost:3000` serves both compiled frontends: the learner application at `/` and the administrator console at `/admin/`. `start-all.bat` and `start-frontend-backend.bat` build both bundles before starting/reusing the backend; they do not start Vite on `5088` or `9527`. `5088` and `9527` remain optional development-only ports for manual Vite debugging.

The administrator router keeps unauthenticated traffic inside `/admin/login`; it no longer redirects to the learner `/login` page. The production admin form and its single quick-login entry both use the same deployable `admin123` / `admin123` default as the backend seed configuration.

## Frontend release reliability

Production deployment retains prior Vite-hashed files under `frontend/dist/assets` and serves `index.html` with no-cache headers. This prevents a cached entry document from requesting a deleted JavaScript or CSS chunk after a release. Built frontend and PPT trees are synchronized with `rsync --checksum`, so a same-size entry document cannot be skipped when archive timestamps match. Both deployment scripts verify that every JS/CSS entry referenced by `index.html` exists before the release completes.

## Production migration

The production DNS for `lzhan.xyz` and `www.lzhan.xyz` targets `120.26.3.150`. The DigiCert Nginx certificate is installed outside the repository and must exist before deployment:

```text
/etc/nginx/ssl/lzhan.xyz/lzhan.xyz.pem
/etc/nginx/ssl/lzhan.xyz/lzhan.xyz.key
```

Never place the private key in a source archive. `deploy.sh` delegates to the single canonical `deploy-prod.sh`; the script validates both certificate files before changing Nginx, installs FFmpeg, creates a 2 GiB swap file only when the host has no active swap, and uses pinned `uv==0.8.14` to provision Python 3.12 instead of the Ubuntu 26.04 host's incompatible Python 3.14. It runs one Gunicorn worker with four threads. The single worker is intentional on the 2 GiB-class host: process-wide resource/video executors must not be duplicated across workers. BLAS/OpenMP thread counts are also limited to one per process.

The production learner frontend uses page-level route chunks. Nginx serves fingerprinted `/assets/` files with a one-year immutable cache, keeps stable image/font names on a seven-day cache, and always serves `index.html` and SPA history fallbacks with `no-cache, no-store`. This keeps secondary routes loadable on demand without allowing an old HTML shell to pin stale chunk names. Verify these rules with `python -m pytest backend/tests/test_production_deployment_config.py -q` and response-header checks after each phased deployment.

Deployment preserves `backend/data/` and `backend/.env` on the destination. Migrate the production SQLite databases, generated media and environment file separately before the first service start; do not replace them with local test data. The domain-specific Nginx site is `/etc/nginx/sites-available/lzhan.xyz`, so existing `han.asia` and media API virtual hosts remain independent.

Local release verification:

```powershell
python -m py_compile backend/app.py backend/video_generation.py
python -m pytest backend/tests/test_learning_path_progressive.py backend/tests/test_learning_path_profile_switch.py backend/tests/test_learning_profile_api.py -q
npm --prefix frontend run build
npm --prefix admin run build
```

Build the production-only archive after verification:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-production-package.ps1
```

The packager includes all files under `rag文档` plus the generated course index, but rejects runtime databases, portraits, generated videos, `.env`, certificate keys, virtual environments, logs and dependency directories. It writes a sibling `.sha256` checksum for upload verification.

## Windows portable distribution

`scripts/build-portable-package.ps1` creates a self-contained Windows x64 folder under `portable/`. The package keeps the backend, learner/admin/PPT source and prebuilt frontends, the complete `rag文档` corpus and `course_knowledge_index.json`, an official Python 3.12 embeddable runtime with all declared Python dependencies, and FFmpeg/ffprobe. It intentionally excludes `node_modules`, virtual environments, tests, logs, runtime SQLite databases, generated portraits/videos, `.env`, API secrets, server passwords and TLS private keys.

The portable launcher exposes the learner and administrator applications through the unified `127.0.0.1:3000` origin. OhMyPPT runs only on the internal loopback port `127.0.0.1:8765`; no browser-facing development port is required. Waitress is used for the local Flask process so the portable build does not run the debug server. AI video tasks retain the same explicit user-start gate and Seedance 1.5 default as the production application.

Build and verify the portable folder locally:

```powershell
backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt -r ppth5\backend\requirements.txt
powershell -ExecutionPolicy Bypass -File scripts\build-portable-package.ps1
powershell -ExecutionPolicy Bypass -File portable\qianzhixuehang-portable-win-x64\scripts\check-portable.ps1
```

The generated folder provides `一键启动.bat`, `停止服务.bat`, `检查完整性.bat` and `配置接口密钥.bat`. End users do not run `pip`, npm or any dependency installer. The API configuration helper creates a private `.env` from the non-secret template only when the user requests it; secrets are never copied by the packager.

All local variants use `admin123` / `admin123` as the first-run administrator credentials. `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `backend/.env` can still override these demo defaults when a different credential is required.

## Mobile PWA

The independent learner mobile application lives in `mobile/` and is deployed at `https://lzhan.xyz/m/`. It reuses the existing authenticated `/api/` contract and server-side task database; it does not add a mobile database or duplicate agent execution. The desktop learner root, `/m/`, `/api/`, `/ppt-api/`, and `/admin/` are independently routable on the production domain.

### WeChat mini program

`microprogram/` is a native WeChat mini program for AppID `wx698aeecb85c5dd8a`. Import that directory directly into WeChat DevTools. Users enter their existing platform username or email and password; the client calls `https://lzhan.xyz/api/auth/login` and stores only the returned Bearer session token. Its compact blue "today learning" workspace is intentionally distinct from the green mobile web shell while preserving the same account, evidence, task, and assessment data.

The mini-program learning loop includes password/captcha login, conversational profile collection and profile switching, profile-driven weekly paths, seven personalized resource task types, server task history and progress polling, knowledge-backed tutoring with returned citations, and effect-assessment summaries. Long-running resource jobs are polled from the persisted server task table because native mini-program networking is less reliable for long-lived SSE connections. Generated-video creation remains deferred and requires the existing second confirmation flow; the mini program does not claim to embed desktop PPT editing, MCU simulation, knowledge administration, or runtime debugging.

Before production testing, add `https://lzhan.xyz` to the WeChat Mini Program `request`, `uploadFile`, and `downloadFile` legal-domain lists. During local development only, DevTools can temporarily enable “Do not verify valid domain names, web-view, TLS version, and HTTPS certificates”. The backend can be checked independently with:

```powershell
Invoke-RestMethod https://lzhan.xyz/api/health
Invoke-RestMethod https://lzhan.xyz/api/auth/captcha
```

The five primary destinations are Home, Path, Resources, Tutor, and Me. The mobile learning loop includes conversational ten-dimension profile collection and version switching, a profile-driven vertical weekly path, seven lightweight resource-generation choices, persisted task progress and recovery, sanitized resource previews, question practice and AI scoring, knowledge-backed tutoring, learning feedback, and effect assessment. Home uses the same persisted backend evidence contract as effect assessment: path progress is derived from completed/tracked path nodes, achievement uses the backend weighted evidence rate, mastery uses question, exam, and experiment evidence, and generated-task count uses persisted resource-task records. The four metrics are refreshed from `/api/effect-assessment`, `/api/learning-path/config`, and `/api/xiaozhi/history`; none are APK-local counters. PPT editing, video workflow editing, MCU canvas simulation, digital-human interview rooms, knowledge-base administration, and runtime debugging are intentionally excluded from the first mobile release.

The PWA precaches only its application shell and versioned static assets. Authenticated profiles, generated resources, task payloads, and API responses are not stored by the service worker. AI generation keeps visible SSE or persisted task status, structured-output failures remain visible, and resource results retain citations and uncertainty markers returned by the specialist agents.

Question practice accepts both legacy top-level question arrays and the production `question_bank.questions` payload, sends AI scoring items through the backend `detail` contract, and persists the returned score evidence. Tutor submission explicitly separates the first question from follow-up requests. Mobile E2E coverage verifies these contracts together with resource-task creation, profile-missing guidance, 401 session cleanup, logout, vertical-path interaction, citations, and five responsive viewport classes.

Local development proxies `/api` and `/ppt-api` through Vite, so no local Python backend is required when the production API is available:

```powershell
npm --prefix mobile install
npm --prefix mobile run dev
```

Verification:

```powershell
npm --prefix mobile test
npm --prefix mobile run test:e2e
npm --prefix mobile run build
```

Production deployment requires a successful mobile build before running `deploy-prod.sh`. Nginx must return 200 for `/`, `/m/`, and `/api/health`.

### Android APK

`mobile/` is also packaged with Capacitor. The native build uses `/` as its router and asset base, calls `https://lzhan.xyz/api/` directly, and disables PWA service-worker generation. The browser build remains scoped to `/m/`. The backend CORS allowlist explicitly includes `https://localhost` and `capacitor://localhost`; wildcard credentialed CORS is not used.

Native builds reject non-HTTPS API base URLs. API requests, SSE streams, and backend-returned `/api/...` image, poster, video, and iframe URLs are all resolved against `https://lzhan.xyz` in the packaged WebView, so packaged media does not accidentally request the app-local `https://localhost` origin. `npm run build:native` reads this contract from `.env.native`; the source keeps the same remote fallback for native mode if that file is omitted accidentally.

The release keystore is stored outside the repository under the current Windows user's `.codex/android-signing/` directory. Its password is protected with Windows DPAPI and is exposed to Gradle only through process-scoped environment variables. Keep a secure backup of the valid `qianzhi-release-v2.jks` and its matching DPAPI credential export on the same Windows account; every future update with application id `xyz.lzhan.qianzhi` must use the same key.

Build and verify the signed APK:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-signed-apk.ps1
$apk = "mobile\android\app\build\outputs\apk\release\app-release.apk"
& "$env:USERPROFILE\.android-sdk\build-tools\36.0.0\apksigner.bat" verify --verbose --print-certs $apk
Get-FileHash $apk -Algorithm SHA256
```

The distributable APK and checksum are written under `mobile/releases/`. Android requires JDK 21 and Android SDK Platform 36; this workstation keeps the command-line SDK in `$env:USERPROFILE\.android-sdk` and Gradle 8.14.3 in `$env:USERPROFILE\.gradle-distributions`.

The current signed mobile release is version `1.0.2` with `versionCode 3`. `scripts/build-signed-apk.ps1` decrypts the external DPAPI-protected credential only into process-scoped environment variables, performs the native web build and Capacitor sync, builds the Android release, verifies it with the newest installed `apksigner`, and writes both the APK and its SHA-256 file to `mobile/releases/`. The signing key never enters the source tree or APK. Android may still show the normal “unknown source” confirmation for manually sideloaded APKs; eliminating that distribution warning requires publishing through an app store or managed-device channel, not merely adding an APK signature.
