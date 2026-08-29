# A3 Scoring Optimization Tracker

- [x] 2026-08-29：知识网络镜头速度微调：将聚焦过渡放慢到约 0.7 秒，保留缓入缓出拉镜效果，避免镜头切换过快。验证：runner 非清理构建通过（2238 modules）；`node --test frontend/tests/knowledgeNetworkRunner.test.mjs` 3/3；`node frontend/tests/knowledgeNetworkRunner.e2e.mjs` 桌面/移动通过。

- [x] 2026-08-29：知识网络镜头平滑修复：将相机位置与 OrbitControls 目标点改为同一时间轴的缓动插值，移除结束时的硬跳定位，避免“先拉近一段再闪现到目标”。验证：runner 非清理构建通过（2238 modules）；`node --test frontend/tests/knowledgeNetworkRunner.test.mjs` 3/3；`node frontend/tests/knowledgeNetworkRunner.e2e.mjs` 桌面/移动通过。

- [x] 2026-08-29：星图导航关键词搜索：在导航面板顶部增加搜索框，按标题、知识域、学习说明、关键词和标签匹配节点；结果可直接打开详情并沿用现有层级上下文，移动端详情仍嵌入导航滚动区。验证：runner 非清理构建通过（2238 modules）；`node --test frontend/tests/knowledgeNetworkRunner.test.mjs` 3/3；`node frontend/tests/knowledgeNetworkRunner.e2e.mjs` 桌面/移动通过。

- [x] 2026-08-29：知识网络移动端叶子节点导航状态修复：具体知识点选中后保留其祖先子主题，避免“具体知识点”层被卸载；移动端详情纳入已展开导航的滚动内容，避免详情浮层遮挡导航项。验证：runner 非清理构建通过（2238 modules）；`node --test frontend/tests/knowledgeNetworkRunner.test.mjs` 3/3；`node frontend/tests/knowledgeNetworkRunner.e2e.mjs` 桌面/移动通过。

- [x] 2026-08-29：知识网络第六轮连线修复：边数据端点确认直接读取源/目标节点坐标；关系线保持节点之间的直线连接，稳定三维布局提供自然斜角，避免整齐的 90°/180° 方向；节点作为清晰锚点渲染，铭牌从节点中心偏移。选中二/三级节点或知识域时，仅保留当前父子路径关系线，其他关系线隐藏，避免无关暗线残留。保持布局、原版星图外观、导航、分类和镜头交互。验证：runner 非清理构建通过（2238 modules）；`frontend/tests/knowledgeNetworkRunner.test.mjs` 3/3；本地 `http://127.0.0.1:5088/knowledge-network?codexPreview=1` 桌面/移动 E2E 均通过域聚焦、节点居中、知识详情与无横向溢出检查。
- [x] 2026-08-29：知识网络连线渲染稳固：关系线关闭视锥裁剪并设置明确渲染顺序，避免相机移动或深度层叠时出现线段被裁掉、视觉上未落到节点的错觉；知识网络嵌入页增加构建版本查询参数，强制浏览器获取最新直线连线资产，避免旧弧线脚本缓存。验证：runner 构建、知识网络单测 3/3、桌面/移动 E2E、主前端非清理构建均通过。
- [x] 2026-08-29：定位“线与点视觉错位”的根因：铭牌整体横向偏移时连同其白色锚点一起移动，导致锚点脱离真实节点中心；改为仅偏移文字，锚点固定在铭牌中心并与节点坐标重合。关系线数据与节点仍共用同一坐标源。验证：runner 构建、知识网络单测 3/3、桌面/移动 E2E、主前端非清理构建均通过。
- [x] 2026-08-29：进一步修正铭牌定位基准：`Html center` 会按不同文字宽度改变整块铭牌的视觉中心，节点容易被背景覆盖而产生漂移错觉；改为以节点坐标作为铭牌左侧锚点，铭牌整体右移，锚点固定在左边，文字宽度不再影响连线参照。验证：runner 构建、知识网络单测 3/3、桌面/移动 E2E 通过。
- [x] 2026-08-29：移除铭牌内的装饰白点，避免用户把它误认为可连线节点；保留真实 Three.js 节点作为唯一连线锚点，并让铭牌从节点右侧显示。验证：runner 构建、知识网络单测 3/3、桌面/移动 E2E 通过。
- [x] 2026-08-29：修复筛选切换后旧骨架线残留：Three Fiber 复用 `lineSegments/bufferGeometry` 实例，导致主题节点更新而关系线仍停留在上一主题；为普通线和高亮线的对象与几何体加入筛选状态 key，确保每次主题/子主题切换都重建当前关系线。验证：runner 构建、知识网络单测 3/3、桌面/移动 E2E 通过。
- [x] 2026-08-29：分支布局与具体知识点聚焦优化：为每个父节点的兄弟分支加入稳定随机旋转和最小距离约束，保留自然角度并避免节点叠加；点击具体知识点时额外保留同一子主题下的同级知识点及其关系线，避免不必要地隐藏兄弟节点。验证：runner 构建、知识网络单测 3/3、桌面/移动 E2E 通过。
- [x] 2026-08-29：知识域低饱和配色：节点与关系线按导航中的知识域颜色分组，统一向中性灰白压低饱和度，使用 MeshBasic/LineBasic 材质直接着色，不增加灯光或额外光照计算；选中路径提高线条透明度，保证不同知识域仍可辨识。验证：runner 构建、知识网络单测 3/3、桌面/移动 E2E 通过。
- [x] 2026-08-29：修复具体知识点点击后导航缩回：移除 `selectFromNavigation` 在打开详情面板时强制关闭导航的行为，点击叶子知识点后保留完整的知识域、主题和子主题上下文，详情面板独立打开。验证：runner 构建、知识网络单测 3/3、桌面/移动 E2E 通过。
- [x] 2026-08-29：加固具体知识点导航展开状态：打开叶子知识点详情时显式设置 `navigationOpen=true`，并更新嵌入 iframe 版本参数，确保已有浏览器标签不会继续使用旧导航脚本。验证：runner 构建、知识网络单测 3/3、桌面/移动 E2E 通过。
- [x] 2026-08-29：导航父节点详情联动：从导航点击主题或子主题时同步打开对应知识详情面板，并保持导航展开；知识域按钮仍只切换域视角，不弹出详情。验证：runner 构建、知识网络单测 3/3、桌面/移动 E2E 通过。
- [x] 2026-08-29：导航与父节点内容补全：导航面板高度扩展到接近整屏，知识域、主题、子主题和知识点可连续浏览；适配器为根节点、主题和子主题自动生成结构化学习说明，引用其下级条目并补充学习重点，避免父节点只有重复摘要。验证：runner 构建、知识网络单测 3/3、桌面/移动 E2E 通过。

- [x] 2026-08-29：知识网络第五轮重叠排查与修复：确认同级节点的字符串偏移在相似 ID 下产生近似坐标碰撞，导致知识域内子主题和知识点叠成团；改为按同级节点稳定均匀分布，并为每个父节点局部星群加入稳定三维朝向，保持当前总览尺度、原版星图外观、导航、分类和镜头交互。数值复核显示同级最近距离由约 `0.04` 提升至约 `2.1`。验证：runner 非清理构建通过（2238 modules）；`frontend/tests/knowledgeNetworkRunner.test.mjs` 3/3；本地 `http://127.0.0.1:5088/knowledge-network?codexPreview=1` 的桌面/移动 E2E 均通过域聚焦、节点居中、知识详情与无横向溢出检查。

- [x] 2026-08-29：知识网络第四轮空间尺度调整：将根节点到知识域中心的半径收紧至 `9.5`，同时将域内主题、子主题和知识点展开半径调整为 `5.0`、`2.2`、`1.2`，以减少总览中心到边缘的空旷感，并拉开同域内的层级节点。保留原版星图外观、导航、分类和镜头交互。验证：runner 非清理构建通过（2238 modules）；`frontend/tests/knowledgeNetworkRunner.test.mjs` 3/3；本地 `http://127.0.0.1:5088/knowledge-network?codexPreview=1` 的 `1440x900` 和 `390x844` E2E 均通过域聚焦、节点居中、知识详情与无横向溢出检查；主前端 `npm.cmd run build -- --emptyOutDir=false` 通过（4013 modules）。

- [x] 2026-08-29：知识网络第三轮交互收敛：将同一知识域的主题、子主题和知识点整理为稳定局部星群；选知识域时镜头平滑聚焦该域主题簇；选中节点或域后提高对应路径亮度、压低其他节点与关系线，铭牌不再拦截画布点击。保留原版星图背景、材质和手动旋转/缩放/平移。验证：`frontend/tests/knowledgeNetworkRunner.test.mjs` 3/3；runner 非清理构建通过（2238 modules）；主前端非清理构建通过（4013 modules）；本地 `http://127.0.0.1:5088/knowledge-network?codexPreview=1` 在 `1440x900` 与 `390x844` 完成知识域→主题→子主题→知识点下钻，域簇居中、选中节点居中、详情可见且无横向溢出。

- [x] 2026-08-29：在已恢复的原版知识星图中，仅补充“选中节点即平滑居中拉近”的镜头行为；保留原有星系外观、节点布局、连线、标签和 OrbitControls 自动旋转/缩放/平移。验证：`node --test frontend/tests/knowledgeNetworkRunner.test.mjs` 为 3/3；runner 非清理构建通过（2238 modules）；本地 `http://127.0.0.1:5088/knowledge-network?codexPreview=1` 在 `1440x900` 和 `390x844` 下完成领域→主题→子主题→知识点下钻，选中铭牌位于画布中心附近且详情可见；主前端 `npm.cmd run build -- --emptyOutDir=false` 通过（4013 modules）。

- [x] 2026-08-29：按用户明确要求回退知识网络的星系画布外观、节点布局和画布交互到仓库当前 HEAD 的原版实现；保留 runner 外层已经完成的知识域、主题、子主题、具体知识点导航与分类，以及实质知识条目详情。不为原版随机位置与导航目录的潜在匹配偏差继续调参。验证：`node --test frontend/tests/knowledgeNetworkRunner.test.mjs` 为 3/3；runner 非清理构建通过（2238 modules）；本地 `http://127.0.0.1:5088/knowledge-network?codexPreview=1` 在 `1440x900` 和 `390x844` 下完成抽屉导航、领域→主题→子主题→知识点下钻、详情显示与原版画布拖拽回归；主前端 `npm.cmd run build -- --emptyOutDir=false` 通过（4013 modules）。

- [x] 2026-08-29：撤回本轮未授权的知识网络星图改动；新增 runner 组件与构建产物移至 `archive/knowledge-network-constellation-reverted-20260829/`，未删除文件，原有源码与未跟踪用户文件保持不变。

- [x] 2026-08-29（已回退）：曾尝试将知识网络星图改为双旋臂星团并调整镜头、连线和铭牌；按用户随后确认，当前运行版本已恢复仓库 HEAD 原版星图，不再以该视觉方案作为现状。

- [~] 2026-08-28：同步生产环境 SQLite 数据库到本地可恢复副本，并重构个性化资源页的历史资源检索体验：降低多色卡片与胶囊控件造成的模板感，增加关键词搜索、类型筛选、结果计数和分页；仅在本地验证，不部署生产。

- [x] 2026-08-28：将数字孪生架构展示从用户端迁移到管理员端：移除用户导航入口与旧页面分包，旧地址 `/agent-digital-twin` 改为跳转个性化资源；管理员菜单新增 `/admin/digital-twin` 独立页面，复用现有同源 1920×1080 三维场景并提供自适应缩放、加载失败重试、刷新和全屏控制。验证：包装页契约 4/4、管理员 TypeScript 检查、用户端和管理员端非清理生产构建、`git diff --check` 均通过；生产增量部署用户端 168 个文件、管理员端 171 个文件，发布包 SHA-256 分别为 `D45AE6BB85C880C08AC44D40E4E0FBE8AC4171BA9908D25F8F37F5BE77F2BF88` 和 `139B3EB19CF8218870F383C4A2BE9075DC767D4907BF3F47633D071CE85CBA7A`，旧入口备份于 `/var/www/feishengwangying/backups/20260828-153100-digital-twin-admin/`。线上入口与关键分包哈希和本地产物一致；管理员路由、数字孪生分包、同源场景及旧用户端地址均可访问，`/api/health`、`/ppt-api/health`、`/api/ppt-h5/health` 为 HTTP 200，Nginx、主后端和 PPT API 服务保持 active。

- [x] 2026-08-28：按用户确认的交互位置，将多智能体协同进度从页面级独立悬浮窗移入岐小智“陪伴式助手”对话滚动区，作为一张可折叠生成依据的助手消息卡；新工作流自动打开对话面板并恢复真实 SSE/后台任务状态，不再额外遮挡业务页面。验证：静态工作流契约 9/9、资源详情契约 5/5、非清理生产构建通过；本地与生产 `1440x900` 实际页面均仅有一个协同卡，卡片边界完整位于助手对话窗口内且页面无横向溢出。按用户要求不再做移动端专项验收。生产采用 170 文件增量包部署，发布包 SHA-256 为 `AD8E193341CB9918A7C388A5FAF80B4F3BDD79AC3D4D1E6757B08E23D1EE96B8`，旧入口备份于 `/var/www/feishengwangying/backups/20260828-141656-embedded-workflow/index.html.before`；公网入口为 HTTP 200，本地与生产入口哈希一致，主 API、PPT API、Nginx 及两个服务保持健康。

Last updated: 2026-08-29

- [x] 2026-08-28：增强岐小智在“画像构建→后台学习路径规划”闭环中的可见性，并收口任务详情页冗余信息。画像分析 SSE、画像对话完成后返回的真实路径任务与 `xiaozhi_tasks` 周进度统一接入一个全局单实例多智能体进度卡，支持跨路由续接、完成跳转、失败保留与移动端避让；PPT、思维导图、讲义、视频、动画和智能辅导详情优先展示实际学习内容，任务来源、画像、Harness、Skill、质量与引用统一折叠到悬浮卡“生成依据”中。周任务页只保留一个周次标题并移除重复任务编号栏。验证：工作流进度测试 9/9、资源详情测试 5/5、资源详情桌面/移动合约、画像开发工具测试 3/3、包装页测试 4/4 及非清理生产构建通过；进度完全来自真实 SSE 与后台任务状态，不使用伪进度。生产部署采用仅前端增量覆盖且保留旧哈希资源的方式，旧入口备份于 `/var/www/feishengwangying/backups/20260828-140116-xiaozhi-detail/index.html.before`，发布包 SHA-256 为 `E2D5A8E28FAD328A5C33DED914662D081145BFA516210C0243EE92C59E72DFD0`；公网入口、周任务深链、资源详情、动画页、主健康接口与两个 PPT 健康接口均为 HTTP 200，当前主包及相关路由分包均可访问，Nginx 配置有效且主后端/PPT 服务保持 active。

- [x] 2026-08-28：在包含本地 YOLO 与 DeepSeek 校准的主线中合并 20 味 3D 药材模型资源、正确答案保护和学习路径站内返回修复，同时保留六阶段中医药学习地标、F4 十维画像测试工具、全站动效及 Python 3.10 兼容修复。验证：药材后端 13/13、前端专项 14/14、非清理生产构建（4015 modules）通过；生产服务实际加载 20 味模型目录、45 类 YOLO 映射及 YOLO 权重，主后端与 Nginx 均为 active，公开健康接口、YOLO 页面、药材模型页、学习路径、背景、模型和纹理资源均正常返回。按项目约束未使用浏览器控制技能。

- [x] 2026-08-27：修复每周学习任务页调用不存在的 `normalizeResourceType()` 导致 Vue 渲染阶段 `ReferenceError` 和整页白屏的问题，统一改用已定义的 `normalizeTaskResourceType()`，并补充禁止旧函数引用的导航回归检查。验证：前端药材选项/双功能/导航测试 5/5、非清理生产构建通过；生产部署前备份入口，增量覆盖并保留旧哈希资源，登录态学习路径配置、`week-1` 阶段与资源任务接口均为 HTTP 200，新入口、周任务 JS/CSS 和目标路由均为 HTTP 200，主后端与 Nginx 均保持 active。
- [x] 2026-08-27：修复药材模型任务强制新标签页打开导致进入时白屏、返回按钮无法回到学习路径的问题；两个学习路径入口统一在当前标签页打开药材任务，返回按钮优先退回站内历史，直接访问时按 `source/stageId` 回对应周任务或回个性化资源。验证：导航与选项回归 4/4、前端非清理构建通过、入口 94 项动态依赖完整；生产新入口、药材页、两个学习路径脚本、目标路由和健康接口均为 200，Nginx、主后端与 PPT API 均为 active。
- [x] 2026-08-27：修复药材模型识别把正确答案和全部干扰项打乱后再截断、导致正确答案可能遗漏的问题；改为先选最多 3 个不重复干扰项，再与正确答案统一打乱。验证：选项单元测试 2/2、真实 20 味目录每味随机 100 次共 2000 组全部包含唯一正确答案且选项无重复，前端非清理生产构建通过。增量部署保留旧哈希资源并原子切换入口，Nginx、主后端和 PPT API 均为 active；生产 HTTPS 虚拟主机的新入口、药材脚本、样式、目标路由和健康接口均返回 200。
- [x] 2026-08-27：移除学习画像对话的大模型失败固定问句兜底，模型调用失败、无效输出或连续重复回复时由 API 明确返回 `503 / MODEL_UNAVAILABLE`；重复输出先执行一次真实模型重试。服务端会话仅在完整模型回合成功后写入，前端不再把旧 `localStorage` 对话拼接到空服务端会话。新增 20 种可独立加载的药材模型辨识资源，并让正常七项以上周路径稳定包含一个目录内药材任务；短历史路径不被覆盖。验证：画像 API 69 项加 7 个子测试、药材资源 7 项、前端会话 3 项、非清理生产构建全部通过；本地真实 DeepSeek 两轮画像从“学习目标”推进到“薄弱知识点”，回复不同且保存 4 条消息。生产增量部署后主后端、Nginx、PPT 服务均为 active，药材 OBJ 与 WebP 分别返回 200 和完整字节；生产 DeepSeek 账户随后返回 `402 Insufficient Balance`，画像接口按新契约明确返回模型不可用且不再输出模板问题，充值后无需改代码即可恢复。

This file is the source of truth for the current scoring review and frontend refinement work. Update it before and after every implementation batch.

## Status legend

- `[ ]` Not started
- `[~]` In progress
- `[x]` Complete and verified
- `[!]` Blocked or needs a product decision

## 2026-08-27 药材识别第一版

- [x] 新增主导航“药材识别”，第一版只提供实际可运行的本地 YOLO 药材名称识别：图片上传和浏览器摄像头锁帧均提交到受鉴权 API；不实现 mock、云端模型、视频抽帧、识别历史或学习闭环占位。模型与 45 类中文映射已导入 `backend/models/`，接口仅返回一个中文药材名称。验证：项目 venv 下 Python 编译与 2 项类别映射/旧类别标签解码测试通过；本地 `3002` 服务中未鉴权请求为 HTTP 401，带本地预览登录令牌上传参考项目样图返回 HTTP 200 和模型实际结果“肉苁蓉”；前端以 `npm.cmd run build -- --emptyOutDir=false` 非清理构建，桌面 1440x900 与移动 390x844 实际上传识别均通过，移动端无横向溢出且结果卡片不被底部导航遮挡。截图：`C:/Users/30949/.codex/visualizations/2026/08/27/01a041ce-ac44-7d12-a7f4-f37f0737bc2b/herb-recognition-desktop.png`、`C:/Users/30949/.codex/visualizations/2026/08/27/01a041ce-ac44-7d12-a7f4-f37f0737bc2b/herb-recognition-mobile-final.png`。
- [x] 增加“AI 校准”入口，上传图片仅调用 `deepseek-v4-flash-vision-exp`，不触发 YOLO 或融合回退；已完成独立 API、模型/地址/超时/上下文窗口配置和 6 项后端单元测试（含 DeepSeek 官方 `/chat/completions` 地址、无密钥失败与“不得调用 YOLO”断言）。本地 `3000` 服务携带预览授权实际请求 DeepSeek，对非药材图片返回真实 422“未返回可确认的药材名称”，未降级到本地模型；Flask 托管构建产物与开发服务器均在桌面 `1440x900`、移动 `390x844` 验证 AI 校准可切换、按钮文案更新且无横向溢出。截图：`C:/Users/30949/.codex/visualizations/2026/08/27/01a041ce-ac44-7d12-a7f4-f37f0737bc2b/herb-ai-final-desktop.png`、`C:/Users/30949/.codex/visualizations/2026/08/27/01a041ce-ac44-7d12-a7f4-f37f0737bc2b/herb-ai-final-mobile.png`。主前端 `npm.cmd run build -- --emptyOutDir=false` 已通过；同时将既有 `LearningProfileView.vue` 的用户头像改为与同页机器人头像一致的静态 URL 绑定，恢复该构建。
- [x] 提交前重新验证前端构建时，收口 `LearningProfileView.vue` 中既有机器人和用户头像的静态 URL 解析问题，改为运行时变量引用且不改变视觉效果；`npm.cmd run build -- --emptyOutDir=false` 已通过。

## 2026-08-27 生命树学习闭环可视化

- [x] 新增独立 `/life-tree` 功能模块，用三维树冠承载当前画像、知识掌握、周路径、资源反馈和效果评估证据；节点区分已掌握、学习中、薄弱、推荐下一步与待验证，不把缺失证据伪装为完成状态。节点详情提供证据说明、关联阶段和资源/测评入口，形成画像到再评估的可操作闭环。验证：3 项生命树数据模型测试与前端非清理构建通过；2026-08-27 增量部署后 `/life-tree` 返回 HTTP 200，主后端与 Nginx 保持 active。

## 2026-08-27 数字孪生中医语义清理

- [x] 清理 `/agent-digital-twin` 静态节点、大屏指标、趋势图、模型调用图和协同信息流中残留的单片机、仿真与实验实践措辞，改为中医学习智能体、辨证协同、画像证据、医案实践和四诊合参语义；保留原有三维拓扑、数据结构和交互方式。验证：包装页递归嵌套测试与前端非清理构建通过；2026-08-27 增量部署后 `/agent-digital-twin` 返回 HTTP 200。

## 2026-08-27 混合知识路由与交叉验证

- [x] 在现有中医课程文档切块、用户私有文档和知识图谱基础上增加结构化 QA 对检索，统一为 `QA + Document + Graph RAG` 混合路由；当前可复现语料包含 `101,968` 条去重 QA、`31,668` 个文档切片和 `1,601` 个图谱节点，完整纳入 SylvanL 的 `12,889` 条中医预训练资料。路由器按问题主体与属性执行标题精确检索、FTS5 召回、路由内重排和多源证据融合，输出可追溯引用、证据覆盖、交叉验证状态及“允许生成 / 需进一步核验”决策；检索验证页同步展示三路命中和审核结论。验证：压缩与解压数据库连续两次构建哈希一致；黄连、独活寄生汤、八纲辨证、阴阳消长四类实问命中正确主体，缓存后典型耗时约 `315-407 ms`；5 项混合路由/便携缓存测试、2 项私有知识隔离 API 测试、前端非清理构建均通过。2026-08-27 生产增量部署前创建 `backups/20260827-before-hybrid-knowledge`，上传暂存区与本地后端哈希、前端 `3,135` 文件和 `207,104,182` 字节完全一致；重启主后端后真实 `admin123` 登录与 `/api/knowledge/retrieve` 均为 HTTP 200，线上统计和交叉验证结论正确，主后端、Nginx 与 PPT API 均健康。

## 2026-08-26 三维中医药知识网络替换

- [x] 按用户最新要求，将 `/knowledge-network` 改为直接呈现 `wu-xing-holo-core (1).zip` 的原始 React/Vite 页面，不对 ZIP 中的源码作任何行级修改，也不再做 Vue/Three.js 重写。附件原始 `src/data.ts` 保持不变；ZIP 外部新增构建期数据适配层，将原页面原样使用的 `nodes`、`edges` 接口指向用户提供的 `中医药知识库_1600节点_知识讲解_实质内容版.json`。按用户后续要求，外层现在保留与数字孪生页一致的主站导航：桌面为顶部 72px 导航，手机为不遮挡画布的底部导航。验证：原页面构建及主前端非清理构建通过；`5089` 桌面 1440x900、移动 390x844 以及当前项目 Flask `3001` 桌面实际路由均显示主导航、无横向溢出、画布可拖拽、无控制台或请求错误；截图位于 `frontend/test-output/visual-audit/knowledge-network-navbar-*-clean.png`。ZIP 源文件未修改。生产验证：2026-08-26 将提交 `4370ac9` 的前端产物增量部署至 `lzhan.xyz`，保留旧哈希资源和入口备份；`/knowledge-network`、原始嵌入页及其 JS/CSS 均返回 HTTP 200，桌面 `1440x900` 与移动 `390x844` 均渲染 WebGL 画布、1600+ 节点矩阵和知识总览，无横向溢出或控制台错误；Nginx、主后端和 PPT API 均保持 active 且健康接口为 HTTP 200。
## Safety and scope

- [x] Active repository identified as `94015785源码/嵌智学航源码` inside the current workspace.
- [x] Project-wide rules added in `AGENTS.md`.
- [x] Recursive deletion and all file/directory deletion are prohibited; obsolete items must be moved and recorded.
- [x] Existing untracked environment files identified and excluded from this work and future commits.
- [x] The former resource detail implementation was moved to `frontend/src/views/legacy/ResourceDetailView.legacy.vue`; no file was deleted.

### Local runtime configuration recovery

- [x] Synchronized the approved remote deployment's `/var/www/feishengwangying/backend/.env` to local `backend/.env` without exposing credentials; restarted the backend and verified the avatar config, signed URL, and LLM token through redacted diagnostics on 2026-08-27.

### Learning-profile developer fixture

- [x] Added an `F4`-only developer panel that submits fixed data for all ten learning-profile dimensions through the formal analysis stream, persists and activates the returned report, and triggers the existing learning-path background task. Clearing current data requires a second confirmation and preserves historical versions. Verified the fixture contract (3/3), backend completed-profile/path scheduling and stream contracts (4/4), non-clean production build (4,008 modules), and mocked formal SSE persistence at `1440x900` and `390x844`, including a server report ID, `isActive=true`, filled `10/10`, clear-confirmation, no horizontal overflow, no page errors, and screenshot review. Screenshots are retained under ignored `logs/learning-profile-developer-tools/`; no paid live-model generation was performed during automated verification.

## Scoring review

- [x] Extract the official scoring table, point weights, thresholds, and judge-visible evidence.
- [~] Map the rubric to current routes, APIs, agents, documentation, and demo evidence.
- [x] Record the initial high-risk evidence list in priority order.

### Official score structure and thresholds

| Priority | Scoring area | Points | Judge-visible threshold or evidence |
| --- | --- | ---: | --- |
| P0 | System completeness | 10 | A coherent, operable loop from collection and analysis through generation, verification, feedback, tutoring, assessment, and adjustment; capabilities must be presented as agents. |
| P0 | Dynamic learning profile | 8 | Dialogue-based construction, intelligent analysis, updates, and at least 6 visible dimensions using a real team member as a demonstrable learner. |
| P0 | Personalized multimodal resources | 10 | At least 5 actually generated resource types and at least 5 demonstrable cases; quality evaluation and hallucination controls must be visible. |
| P0 | Personalized path and recommendation | 3 | Profile-driven recommendations with high fit and 3-5 verifiable cases; show reasons, profile evidence, match, and adjustment. |
| P0 | Intelligent tutoring | 5 | Different and multimodal question types, accurate guided/Socratic answers, and at least 5 cases. |
| P0 | Effect assessment | 5 | Goal attainment, mastery, heatmap, radar, plan adjustment, and at least 3 cases. |
| P1 | Practicality and frontend experience | 10 | Complete and stable behavior, clear and novel interaction, low template/AI feel, multiple devices and roles, and cloud deployment. |
| P1 | Solution innovation | 15 | A visible closed loop, distinction from traditional learning, educational methods, and hallucination prevention. |
| P1 | Technical innovation | 10 | Real multimodal generation, deep multi-agent collaboration, multiple endpoints, and defensible technology choices. |
| P1 | Additional functional innovation | 5 | Extra agents or capabilities such as a digital human must connect to the main agent and learning flow. |
| P1 | Demo video and presentation | 10 | System operation is at least 60% of the video; slides include value, architecture, functions, stack, implementation, innovation, and hallucination controls. |
| P2 | Documentation | 10 | Development, test, deployment, AI implementation detail, source/data, diagrams, and a complete learner case with screenshots. |
| P2 | Bonus evidence | 10 | Existing Xunfei, private knowledge, external API, domestic stack, real-scene test, and AI Coding evidence should be made verifiable. |

The nominal 30-point technical-indicator subsection has child rows totaling 31 points. Intelligent tutoring and effect assessment are also labelled as bonus items while appearing in the required complete loop. Treat every child requirement as required and do not claim a calculated total beyond the official table.

### Initial evidence risks

1. Deep pages can look like independent tools unless they expose the responsible agent, profile basis, handoff, quality/source review, and the next closed-loop action.
2. A resource card or placeholder does not prove actual generation; generated detail pages need inspectable content and a learning-verification action.
3. Path recommendations need visible profile evidence and adjustment rationale, not only ordered tasks.
4. Loading, empty, error, and long-running states must preserve a judge-friendly route through the demo.
5. The required case counts need repeatable seeded/demo data and documentation, not last-minute live generation alone.

## Frontend route audit

- [x] Inventory primary, secondary, and deeper routes.
- [ ] Review shared page shell, breadcrumbs/back navigation, typography, spacing, responsive behavior, and state handling.
- [ ] Review learning-profile child pages.
- [ ] Review learning-path stage and task detail pages.
- [ ] Review personalized-resource generators and generated-resource detail pages.
- [ ] Review quiz generation, exam session, and result/history pages.
- [ ] Review knowledge, tutor, assessment, simulator, and interview detail flows.

## Planned implementation phases

### Learning-profile conversation recovery

- [~] Preserve legacy browser chat records when an empty server session is returned during startup; keep the fallback scoped to that initialized session and never carry it into a new session.

### Phase 1 - Highest-impact deep-page polish

- [x] Select generated-resource history and detail as the first route group.
- [x] Mark affected scoring items and acceptance criteria.
- [x] Implement the smallest coherent page group.
- [x] Distinguish resource-history loading, partial-source failure, full failure, and true empty states with retry actions.
- [x] Verify build without cleaning output directories.
- [x] Verify desktop and mobile routes with synthetic task data and no production-database writes.
- [x] Resolve final review findings for Markdown mind maps, collision-safe feedback-key normalization, and HTML PPT network isolation.
- [x] Update this tracker and commit the verified phase.

Acceptance criteria for this batch:

- A task-backed resource detail can be restored from its URL after refresh through the authenticated task API, while legacy local cache remains an explicitly labelled fallback.
- Loading, unavailable/error, retry, populated, and feedback-complete states provide a clear next action and do not silently redirect.
- Model-produced Markdown is HTML-escaped before limited rendering; HTML PPT output is isolated in a sandboxed iframe; Mermaid uses the installed package with strict security.
- The page exposes only returned profile, planning, responsible-agent, orchestration, quality-review, verification, and knowledge-source evidence, with honest unavailable labels.
- Learners can record either completion or a need for reinforcement and then continue to effect assessment or learning-path adjustment.

### Phase 2 - Remaining scoring-critical page states

- [x] Prioritize the highest-risk remaining states after Phase 1 evidence review.
- [x] Preserve and validate authenticated desktop deep links through both router-guard and runtime-401 login flows.
- [x] Harden exam-session payload normalization, zero-question recovery, persistence guards, timing, exit controls, and responsive layout.
- [x] Ensure embedded-assistant learning-path candidates are persisted only after agent review succeeds; never let degraded fallback output overwrite an accepted path.
- [x] Distinguish learning-path loading/generation failures from a genuine no-profile or not-generated state and provide retry/recovery actions.
- [~] Add focused regression tests, run backend/frontend checks and non-clean builds, then verify applicable routes at 1440x900 and 390x844.

Acceptance criteria for this batch:

- A protected URL preserves its path, query, and hash through login; only same-origin internal targets are accepted, and login loops or external/protocol-relative targets fall back safely.
- An exam payload with valid top-level questions renders normally; a genuinely empty exam never starts timing, exposes completion, writes history, or submits assessment evidence, and offers a clear return route.
- Exam timing is derived from elapsed wall-clock time, the active session has a deliberate exit path, and the page does not horizontally overflow on a 390px viewport.
- Embedded-assistant path and stage tasks treat generated paths as candidates until orchestration review passes; rejected or degraded output leaves the previously accepted profile-scoped configuration unchanged.
- Existing degraded paths are visibly non-personalized and cannot prepare resources; network/load failures never masquerade as “no profile” or a successfully personalized path.

### Deep-page wrapper polish

- [x] Fit the 1920x1080 digital-twin scene to desktop and mobile viewports while preserving an inspectable architecture canvas and explicit loading/error recovery.
- [x] Add an explicit return path, preflight failure state, and retry action to the navbar-free PPT workbench wrapper without changing the embedded OhMyPPT engine.
- [~] Add focused tests, run a non-clean frontend build, and visually verify both routes at 1440x900 and 390x844.

Acceptance criteria for this batch:

- The digital-twin route does not require horizontal scrolling at either target viewport and keeps its loading/error state centered in the available frame.
- The PPT workbench never traps the learner in a blank full-screen iframe: it provides return, loading, unavailable, and retry controls, and successful preflight still fills the remaining viewport.

### Repository integrity - Admin log route

- [x] Scope the admin ignore rule to the runtime root `admin/logs/` directory so `admin/src/views/logs/index.vue` is included in source control.
- [x] Verify the tracked route from an isolated clean source copy: frozen-lockfile install, typecheck, and production build with `--emptyOutDir=false` all pass without copying environment files.

### Production performance and capacity

- [x] Measure the live origin, static assets, application services, and host capacity before changing production.
- [x] Stop only application services proven unrelated to `lzhan.xyz` and the three QR item routes, then reverify every retained endpoint.
- [x] Restore effective immutable caching for fingerprinted assets while keeping SPA HTML uncached.
- [x] Split learner routes into page-level chunks so secondary-page code and CSS are loaded on demand.
- [x] Replace oversized always-on animation media and defer below-the-fold landing media without removing source assets.
- [~] Run focused deployment tests, a non-clean frontend build, bundle-size comparison, and user-led desktop/mobile checks before phased production deployment.

### Static learning-profile face assets

- [x] Restore the learning-profile face base image and segmented PNG assets to the Vite static source directory; the deployed build previously contained only `manifest.json`, causing browser-visible 404s for the face layers.

Verification: `npm run build -- --emptyOutDir=false`; the built `frontend/dist/learning-face-cropped-split/` contains 20 files. The same directory was copied to production without restarting application services; `manifest.json`, the base image, both nested `segments/...` URLs and legacy root-level segment URLs return HTTP 200 from `https://lzhan.xyz`. The missing `/icon.png` was also restored from the existing platform logo asset. The deployed profile chunk now appends `?v=20260825` and fetches the manifest with `cache: no-store` to bypass stale browser/Nginx cache entries.

Acceptance criteria for this batch:

- `/`, `/api/health`, `/ppt-api/health`, and `/api/item/{a1,b7,c4}` remain available after unrelated services stop.
- Fingerprinted `/assets/` responses are cacheable for one year and immutable; `index.html` and SPA history fallbacks remain explicitly uncached.
- Loading one learner route does not eagerly include every other learner view in the entry bundle.
- The floating assistant no longer requires a 10 MB GIF download, and below-the-fold landing images do not block initial rendering.
- Production changes are deployed in small verified batches with an immediate configuration rollback path.

### Doubao Seedream 4.5 image-generation migration

- [x] Verify the Doubao Seedream 4.5 submission, authentication, parameter, and task-polling contract through the APIMart service channel.
- [x] Route learning-profile portraits, learning-video first frames, and PPT illustration generation through `seedream-4-5`.
- [x] Add mocked contract tests for the model ID, 2K minimum resolution, Bearer authentication, asynchronous polling, result parsing, and failure handling.
- [x] Update environment examples and root README claims without storing credentials in Git.
- [x] Run focused backend and PPT checks, commit only migration files, then deploy the backend configuration and code in small verified batches.
- [x] Add a lightweight generated default learner portrait for loading, missing, and failed report states; replace it only after the report-specific database portrait is ready.

Acceptance criteria for this batch:

- Every tracked runtime image-generation path submits `seedream-4-5` to APIMart's `/v1/images/generations`; legacy provider selections cannot silently fall back to a previous image model.
- Seedream requests use supported aspect-ratio values and `2K` or `4K` resolution, never the unsupported `1K` value.
- API credentials remain in ignored local/server environment configuration and never appear in source, logs, tests, commits, or user-facing responses.
- Asynchronous tasks are polled through `/v1/tasks/{task_id}`, temporary result URLs are downloaded promptly, and empty, failed, cancelled, timed-out, or malformed responses produce explicit errors.

### Phase 3 - Demo evidence and documentation consistency

- [~] Reconcile UI labels, README claims, scoring evidence, and repeatable verification steps.
- [x] Make the real Harness E2E run five distinct `learning.tutor.answer` cases while preserving one registry probe per Skill.
- [x] Make the scoring summary resolve those tutoring tasks directly from the E2E report and redacted raw-artifact directory; retain the former manually collected directory as a compatibility fallback.
- [x] Replace the machine-specific scoring command with a repository-relative, two-stage real-E2E and evidence-summary workflow.
- [x] Add `SCORING_MATRIX.md` with the official score structure, current verifiable evidence, reproduction entry points, and explicit unresolved risks without claiming a self-score.
- [ ] Run the five tutoring calls against the final review account and archive the redacted evidence package; unit tests prove the pipeline contract but are not presented as real model evidence.

### Domestic model labeling and Bailian vision migration

- [x] Replace the unavailable Kimi vision route with Alibaba Bailian Qwen3-VL-Plus and route uploaded audio through Qwen3-Omni-Flash before the Spark handoff.
- [x] Reconcile the landing-page model cards with the actual domestic runtime: Spark X2 Flash, Qwen3-VL-Plus, Qwen3-Omni-Flash, Doubao Seedream 4.5, Seedance, and Xunfei speech/avatar services.
- [x] Update the Agent Manifest, runtime routing evidence, README, and focused tests without exposing provider credentials.
- [x] Verify real text, visual, and audio model requests, the full backend suite, and non-clean frontend/PPT builds locally.
- [x] Route digital-interview camera frames through Qwen3-VL-Plus evidence extraction before Spark scoring, and disable the legacy MiMo text fallback.
- [ ] Deploy this model-routing batch to production only after the user resumes deployment; production remains on the restored pre-change configuration.

### DeepSeek official text and vision routing

- [x] Confirm the configured credential can access the official `https://api.deepseek.com/models` endpoint and that `deepseek-v4-flash-vision-exp` is available to the account.
- [x] Confirm one real text request and one real image-understanding request through the official OpenAI-compatible `/chat/completions` endpoint without exposing credentials.
- [ ] Make digital-human learning interviews honor `LLM_PROTOCOL=openai` instead of incorrectly forcing the DeepSeek credential through `/v1/messages`.
- [ ] Align runtime defaults, public model labels, README, focused tests, and live API evidence with DeepSeek text/vision routing.

### DeepSeek PPT generation output budget

- [x] Remove the standalone OhMyPPT 9000-token batch ceiling, use the verified 32768-token production default, and allow both PPT generation paths to be configured up to the 131072-token ceiling accepted by `deepseek-v4-flash-vision-exp`.
- [x] Add request-payload regression coverage and verify one-page plus representative multi-page PPT generation against the real DeepSeek endpoint.
- [x] Deploy the verified PPT backend, then confirm the public health and generation flow before committing this batch.
- [x] Bypass inherited HTTP proxy settings for the main backend's loopback OhMyPPT health and generation requests; otherwise the running local services can both be healthy while the main API reports an upstream HTTP 502.

Acceptance criteria for this batch:

- Every standalone OhMyPPT batch sends the configured high completion budget instead of deriving and capping it at 9000 tokens.
- The Flask fallback PPT generator uses the same documented default and never takes a completion budget from untrusted request input.
- A real multi-page request returns the requested number of parseable HTML slides without local-template substitution.
- Credentials remain only in ignored environment files and are absent from source, tests, logs, staged changes, and user-facing output.

Local evidence on 2026-08-26: DeepSeek accepted intentionally short requests carrying `max_tokens=32768`, `65536`, and `131072`; the real one-page OhMyPPT generation returned 1/1 parseable page, and the real five-page generation at 32768 returned 5/5 ordered pages across the 3+2 batch split. All five pages contained scoped style markup and non-empty HTML (2686-4407 characters). A 131072 five-page request remained unfinished after five minutes and was stopped, so 131072 is retained as an explicit configurable ceiling rather than the default. Focused tests passed: standalone batch generation 3/3, Flask PPT/parser/client/runtime hardening 11/11, and DeepSeek interview/routing 10/10; Python compilation passed.

Production evidence on 2026-08-26: backed up and deployed the three Flask PPT integration files plus the standalone OhMyPPT backend file, preserved both production `.env` files and the existing database, and restarted only `feishengwangying-backend` and `feishengwangying-pptapi`. Both services remained active. Public `/ppt-api/health` and `/api/ppt-h5/health` returned HTTP 200 with `deepseek-v4-flash-vision-exp`, OpenAI protocol, and `maxCompletionTokens=32768`. An authenticated production request to `/api/ppt-h5/generate` returned 1/1 grounded page with 11532 characters of HTML and orchestration status `complete`.

### Learning-path PPT background generation recovery

- [x] Ensure learning-path PPT tasks start generating immediately after persistence and automatically resume through the existing bounded retry path after a backend restart.
- [x] Add focused regression coverage for immediate executor submission and startup recovery without changing the explicit confirmation rule for AI video.
- [x] Preserve the PPT session identifier, page count, route, source parameters, cache key, progress, stage and error across queued, running, failed and completed task writes.
- [x] Show persisted learning-path and XiaoZhi PPT tasks in the OhMyPPT session list, with active polling, progress/page counts, errors and a route back to the original platform task.
- [x] Build both affected frontends without cleaning their output directories; deploy and verify the backend and public routes before committing.

Local evidence on 2026-08-26: Python compilation passed. Eight focused backend tests passed for complete-path week queuing, immediate dedicated PPT executor submission, persisted PPT state preservation, startup recovery, bounded failed-resource retry, parallel clickable-task dispatch, bounded planner concurrency, and background idempotency. `npm run typecheck:web` passed for OhMyPPT. The OhMyPPT Vite build and main Vue build both completed with `--emptyOutDir=false`; only the existing large-chunk warnings remained.

Production evidence on 2026-08-26: backed up and deployed `backend/app.py`, `backend/portable_server.py`, the main frontend dist and the OhMyPPT H5 dist without deleting production files. The main backend compiled, restarted and remained active; `/api/health`, `/ppt-api/health` and `/api/ppt-h5/health` all returned HTTP 200. Authenticated PPT history returned 18 persisted tasks; the newest completed task retained its session ID, PPT payload and route. The deployed OhMyPPT session page rendered all 18 server tasks, including completed 6/6 page counts and historical failure details, without console errors. At 390 x 844 it had no horizontal overflow; the personalized-resource page also had no horizontal overflow and kept only the `个性化资源` and `历史资源` heading levels at mobile and 1912 px desktop widths.

### OhMyPPT history cache-bust and direct history routing

- [x] Map the platform `tab=history` route to OhMyPPT `#/sessions` instead of the workbench home page.
- [x] Version the embedded OhMyPPT entry URL so a previously loaded browser document cannot hide the newly deployed server-history UI.
- [x] Send no-store response headers for both `/ppt/` and `/ppt/index.html` in the canonical production Nginx configuration.

Production evidence on 2026-08-26: backed up the active Nginx site, deployed the canonical exact PPT entry rules, passed `nginx -t`, reloaded Nginx and kept the service active. `/ppt/?v=20260826-ppt-history-v2` returned HTTP 200 with `no-cache, no-store, must-revalidate` and referenced the current `index-PX28YSB2.js` bundle. The deployed bundle contained both server-history sections. Browser verification of the versioned `#/sessions` route rendered 20 persisted server tasks; the two newest tasks were complete at 6/6 pages and no console errors were reported. The main frontend's deployed PPT wrapper chunk contained the version key, history route and `tab=history` mapping. Wrapper tests passed 2/2, production deployment tests passed 7/7, and both affected frontends built with `--emptyOutDir=false`.

### Admin login cache policy

- [x] Prevent stale admin login HTML from pinning an old authentication bundle while retaining immutable caching for fingerprinted admin assets.

Production evidence on 2026-08-26: backed up the active site as `/etc/nginx/sites-available/lzhan.xyz.pre-admin-cache-20260826`, deployed the canonical admin entry and asset cache rules, passed `nginx -t`, and reloaded Nginx without restarting application services. `/admin/login` returned HTTP 200 with `no-cache, no-store, must-revalidate`; its current `/admin/assets/index-BHmfjGhf.js` returned HTTP 200 with a one-year immutable cache. The admin login API continued to return success code `0000` with a token. Deployment configuration tests passed 7/7.

Acceptance criteria for this batch:

- Image uploads are sent to the configured Bailian OpenAI-compatible endpoint with `qwen3-vl-plus`; audio uploads use the Bailian native multimodal endpoint with `qwen3-omni-flash`; both are then handed to Spark as grounded evidence text.
- Vision credentials are independent from the Spark text-model credential and remain only in ignored local/server environment files.
- User-visible model labels describe the models that actually execute each capability; no Kimi or GPT Image label remains in the active product surface.
- A failed vision call remains an explicit marked fallback and cannot masquerade as successful model evidence.

### Shared AI coding workspace

- [x] Deploy DeepSeek Harness as a non-root shared workspace on the isolated sandbox host.
- [x] Add the authenticated `/ai-coding` navigation route with visible connection, failure, and retry states.
- [x] Proxy the Harness runtime through the `lzhan.xyz` origin without exposing provider credentials or the sandbox port.
- [x] Verify service status, unauthenticated rejection, and authenticated static accessibility without invoking the model.
- [x] Restore the authenticated Harness command-menu RPC path without exposing the main application's remaining `/api` routes.
- [x] Add authenticated shared-workspace attachments and bounded ZIP extraction without accepting a browser-provided server path.

Acceptance criteria for this batch:

- All website users intentionally share one Harness workspace and session store; the wrapper embeds Harness directly below the main navigation without duplicating a title/status row.
- The DeepSeek API credential remains server-only and is never included in tracked files, frontend assets, API responses, or logs.
- Harness runs under a dedicated non-root account and accepts traffic only through the authenticated main-site proxy.
- Loading and connection failures never leave a blank page, and the user can retry without reloading the full application.

### Learner-facing demo copy cleanup

- [x] Remove presentation-oriented prefixes from seeded conversation memories and replace the visible demo-source label with neutral product language.
- [x] Re-seed the production conversation-growth examples and verify that the TinyUSB memory retains the learning request without presentation wording.

### Learning-evidence encoding guard

- [x] Reject corrupted knowledge-point labels before they can enter effect-assessment heatmaps or dynamic learning-path adjustments.
- [x] Repair the two affected production tasks and their resource metadata without regenerating the learner's existing path.

### 中药鉴别中医领域文案全量迁移（已完成）

- [x] 将学习画像、个性化路径、资源生成、数字人访谈、测评与反馈中的活动提示词统一迁移为中医学习语境。
- [x] 同步 Web、移动端和微信小程序的默认示例、空状态与引导文案，保留现有功能入口和交互流程。
- [x] 数字人面试统一使用中医基础、四诊、辨证、中药、方剂、医案、知识依据与安全边界能力维度，同时保留历史接口 ID 兼容旧会话。
- [x] 更新画像开场与数字人生命周期回归测试；后端聚焦测试 7/7、前端画像对话测试 3/3、Web 与移动端非清理构建通过。
- [x] 收尾清理活动页面残留的“岗位/面试”和嵌入式 PPT 默认文案；数字人模块统一为“学习访谈”，后端提示与评价同步使用学习者语境。

本阶段只替换活动业务文案与默认内容。已下线的 MCU 模拟器源码、旧测试夹具和历史兼容字段继续保留，但不会由新导航、学习路径或资源工作流触达；内置旧知识库数据迁移不在本次换皮范围内。

收尾验证：Python 编译通过；数字人生命周期与画像开场后端测试 7/7、前端画像对话测试 3/3 通过；Web、移动端非清理构建通过；小程序配置与品牌素材检查通过。浏览器在 `http://localhost:5088/digital-human-interview` 验证了“学习访谈”导航、课程领域、学习方向、访谈主题、学习层级及中医选项，页面无控制台错误。浏览器响应式视口覆盖本轮未生效，未新增手机宽度截图证据；移动端沿用本批次此前的实际页面验证与本轮构建结果。

### Whole-site interaction motion pass

- [x] Adapted the reference project's restrained surface and overlay motion patterns into a shared learner-frontend motion layer. Added staggered async card/panel entry, real enter/leave lifecycles for the XiaoZhi window and task banner, animated XiaoZhi tab/settings changes, continuous navigation indicators, press/focus feedback, and a complete `prefers-reduced-motion` fallback without changing learning-loop state. Route components remain directly mounted so motion never controls route rendering. Verified the non-clean production build; wrapper tests 2/2; resource-detail tests 5/5; synthetic resource-detail error/retry/populated/feedback E2E at desktop/mobile widths; and the new motion E2E at 1440x900, 390x844, and reduced-motion mode with no page errors or horizontal overflow. Screenshots are retained under ignored `logs/motion-system/`.
- [x] Removed the route transition lifecycle after reproducing the risk of a real-session/HMR blank-content regression while retaining non-blocking surface and overlay motion. Added repeated-navigation coverage across personalized resources, effect assessment, learning profile, and back to personalized resources; every route root remained visible and populated with no page errors. Verified against both the Vite development server on port 5088 and the production server on port 3000, followed by `npm run build -- --emptyOutDir=false` and resource-detail E2E.
- [x] Reconciled the newly merged ninth desktop navigation item with the existing motion system: medium desktop widths now use compact brand, navigation, and account spacing; very narrow desktop widths keep overflow directed to the right so the brand cannot intercept the first learning-profile link. Evidence: the post-rebase motion E2E passed desktop, mobile, reduced-motion, and repeated navigation at 1280px with no blank routes; the non-clean production build passed with 4,011 transformed modules.

### GitHub knowledge-network update

- [x] Selectively integrated the latest upstream knowledge-network feature commits (`4370ac9`, `7c6b54f`) covering the original 1,601-node TCM graph, the Three.js Life Tree, hybrid QA/document/graph routing, and source-validation UI while preserving the local motion and Python compatibility changes. The unrelated PPT v3 and admin-cache follow-up implementations were not imported. Added a focused browser regression that waits for WebGL initialization and verifies both routes at `1440x900` and `390x844`, including one navigation shell, visible full-size canvases, no horizontal overflow, and no page/console errors. Evidence: Life Tree model tests 3/3, wrapper tests 3/3, hybrid/portable knowledge tests 5/5, private-knowledge isolation tests 2/2, non-clean frontend build (4,007 modules), motion regression E2E, and knowledge-network E2E against both Vite `5088` and the restarted unified server `3000`. Screenshots are retained under ignored `logs/knowledge-network-update/`; `/api/health` returned HTTP 200 after restart.

### Local Python 3.10 startup compatibility

- [x] Moved whitespace normalization outside the question-option f-string so the documented Python 3.10 runtime can import the backend. Verified all top-level backend modules with `py_compile`, built the learner and admin bundles without cleaning output, received HTTP 200 from `/`, `/admin/`, their entry assets, and `/api/health`, and kept the unified local server running on port 3000.

### Learning-path academy map redesign

- [x] Replaced the hardware-oriented learning-path background with a generated, low-contrast Chinese-medicine technology landscape and replaced circular week markers with data-driven isometric academy buildings. Week order now controls continuous scale growth and five architectural tiers, from a small first-week study house through side halls, a second storey, and a knowledge beacon, while the existing profile-driven path state, completion/current status, route selection, generation console, empty/error recovery, and reduced-motion behavior remain intact. Mobile uses a taller scrollable map canvas so the profile and progress panels do not cover the first row. Evidence: Sub2API GPT Image 2 draft-low and final-high generation calls; visually reviewed 1536x1024 final and 1536x864 project crop; `npm run test:learning-path-academy:e2e` passed at 1440x900 and 390x844 with progressive-size assertions, background HTTP 200, no page errors or horizontal overflow, plus loading, empty, and error/retry states; non-clean frontend build passed with 4,010 transformed modules. Screenshots are retained under ignored `logs/learning-path-academy/`.
- [x] Second-pass architecture redesign replaced the shared expandable-house silhouette with six materially different, pure-code SVG Chinese-medicine learning landmarks: moon-gate study hut, glass herb garden, circular diagnosis courtyard, two-storey lecture academy, three-storey archive pagoda, and grand knowledge palace. The generated bitmap experiment was rejected during visual review and moved from the shipped asset path to `archive/design-experiments/learning-path-ai-landmarks-v2`; no AI-generated building is loaded by the page. The implementation uses layered isometric platforms, triangular and curved eaves, a semicircular window, circular diagnostic core, cylindrical colonnades, lattice work, balconies, water terraces, and restrained 8% outer-scale growth. Evidence: the non-clean frontend build passed with 4,010 transformed modules; `node tests/learningPathAcademy.e2e.mjs` passed at 1440x900 and 390x844, asserting six unique SVG landmarks, no bitmap nodes, 5-15% bounded size growth, no horizontal overflow, no page errors, interaction, plus loading, empty, and error/retry states. Screenshots are retained under ignored `logs/learning-path-academy/`.
- [x] Refined the second and third landmarks without changing their node containers: the apothecary hall and curved glasshouse are 11-12% larger inside the herb-garden terrace, while the four diagnosis pavilions are 24% larger around the unchanged pulse-reading core. Verified the populated and interactive map at 1440x900 and 390x844, plus loading, empty, and error/retry states with `node tests/learningPathAcademy.e2e.mjs`; the final non-clean production build passed with 4,010 transformed modules.
- [x] Enlarged and elevated only the sixth landmark's central knowledge tower: the lower hall, upper hall, and crown pavilion now scale progressively at 1.12, 1.18, and 1.22 with the upper tiers raised to form the final route's clear visual summit. Side halls, water courtyard, node footprint, and interaction geometry remain unchanged. Verified desktop/mobile populated and interactive screenshots plus loading, empty, and error/retry states with `node tests/learningPathAcademy.e2e.mjs`; the final non-clean build passed with 4,010 transformed modules.
- [x] Strengthened academy-node hover/focus feedback with a desktop lift of more than 12px, a restrained 2.5% scale increase, and a receding 80%-width ground shadow; narrow screens use a smaller lift to avoid bottom-navigation collisions, and reduced-motion mode disables the transition/scan animation. Fixed the scoped selector so the parent map-button hover state reaches the child SVG component. Browser regression now asserts the computed desktop lift and passed populated/interactive desktop and mobile routes plus loading, empty, and error/retry states; the final non-clean build passed with 4,010 transformed modules.
- [x] Replaced the generic/generated captions beneath academy landmarks with a project-specific six-stage progression: herb origin and medicinal parts, macroscopic observation, authentic/adulterant comparison, microscopic and physicochemical identification, processed/confusable-material analysis, and comprehensive identification practice. The profile-generated week title remains in node route/detail data and is included alongside the map caption in the accessible label. Browser regression asserts all six visible captions, retained generated context, desktop hover lift, no bitmap nodes, restrained growth, no overflow/page errors, and loading/empty/error states at 1440x900 and 390x844; the final non-clean build passed with 4,010 transformed modules.
- [x] Added a fast academy-map route entrance: the two overview panels float in from their respective sides, while all six code-built landmarks rise in strict left-to-right order. The final landmark completes at 485ms and the slower panel at 455ms; hover lift remains independent, and `prefers-reduced-motion` disables all new entrance motion. Evidence: `npm run test:learning-path-academy:e2e` passed populated/interactive routes at 1440x900 and 390x844, asserted ascending delays and the 500ms ceiling, checked reduced-motion mode, plus loading, empty, and error/retry states with no page errors or horizontal overflow; `npm run build -- --emptyOutDir=false` passed with 4,010 transformed modules. Final screenshots are retained under ignored `logs/learning-path-academy/`.

### OhMyPPT internal-signature recovery

- [x] Repaired production configuration drift where the isolated OhMyPPT service had an `OHMYPPT_INTERNAL_TOKEN` but the main backend did not, causing the backend to sign with an unrelated model credential and every generation request to fail with HTTP 401. Backed up both production environment files and the learner database, synchronized only the internal token without exposing or committing it, and restarted only the main backend and PPT API services. Both public/server-local health checks returned ready with the configured DeepSeek model and 32,768 completion-token budget. A signed one-page integration smoke test returned model-generated HTML, and the original failed task `xz_1787897348162_62edeff9` was regenerated in place under its existing OhMyPPT session: 6/6 pages persisted, status `complete`, progress 100%, and an empty error field. PPT API logs recorded HTTP 200 for both generation calls and no post-restart signature errors.

## Completed changes

### 中药鉴别中医主题换皮（已完成）

- [x] Web、移动端和微信小程序品牌统一为“中药鉴别”，总控助手统一为“岐小智”，更新 Logo、登录主视觉、主题色和中医学习示例文案。
- [x] 从主导航、前端路由、个性化资源入口和学习路径展示中下线 AI 编程与单片机模拟实验；保留旧实现与历史数据兼容。
- [x] 将默认首周展示内容换为中医基础、八纲辨证、方剂配伍、中药性味归经和医案辨析。
- [x] 主前端与移动端使用非清理模式构建通过；小程序配置 JSON 与新增静态资源路径检查通过。
- [x] 内置课程知识库替换为中医文档：`rag文档` 新增中医基础、四诊八纲、性味归经、方剂君臣佐使、医案辨证与中医 QA 问答，并重建 `course_knowledge_index.json`。
- [x] 总控/文本/视觉模型统一接入 DeepSeek 官方地址 `https://api.deepseek.com`（`deepseek-v4-flash-vision-exp`），并将 `api.deepseek.com` 加入运行时安全白名单。
- [ ] 后端剩余的历史嵌入式领域提示词与旧 MCU 兼容字段暂未全量改为中医语境，属于下一阶段提示词领域化；对已下线的 MCU 兼容与旧会话仍作保留。

本批次按挑战杯项目定位完成展示层换皮，不沿用软件杯 A3 的资源数量与 MCU 实验约束；原有画像、路径、生成、审核、反馈和评估业务链路保持不变。

| Date | Phase | Change | Verification | Commit |
| --- | --- | --- | --- | --- |
| 2026-08-14 | Governance | Added repository rules and this living tracker. | Reviewed and committed with Phase 1. | Phase 1 commit |
| 2026-08-14 | Phase 1 | Restored task-backed resource deep links, exposed profile/orchestration/quality/source evidence, isolated generated content, added honest history states, and separated per-resource learning feedback with closed-loop next actions. | Frontend non-clean build; resource detail unit tests 5/5; synthetic Playwright contract and visual review at 1440x900 and 390x844; backend 79 tests and 25 subtests; `git diff --check`. | This Phase 1 commit |
| 2026-08-14 | Repository integrity | Narrowed the admin runtime-log ignore rule and restored the router-referenced server-monitor page to source control. | Isolated frozen-lockfile install; admin typecheck; admin production build with `--emptyOutDir=false`; runtime `admin/logs/` remains ignored. | Admin integrity commit |
| 2026-08-15 | Production performance batches 1-3 | Stopped unrelated application services, restored desktop SPA deployment, fixed static caching, split learner views into route-level chunks, and replaced oversized initial media with WebP plus original fallbacks. | Retained live endpoints all 200; server-local homepage 17 ms and application endpoints 2-6 ms; available host memory about 1.0 GiB; deployment tests 6/6; media tests 2/2; clean non-destructive build reduced entry JS from 1.45 MB to 236.5 KB (94.4 KB transferred with gzip), entry CSS from 868 KB to 197 KB, five landing images from 10.7 MB to 0.55 MB, and the floating animation from 10.6 MB to 193 KB. | `616269e`, `f0adc6e`, `4ff47ea`; deployed and HTTP-verified |
| 2026-08-15 | Doubao Seedream 4.5 migration | Fixed all tracked image-generation paths to Doubao `seedream-4-5` through the APIMart service channel, migrated legacy PPT provider selections at runtime, and stored credentials only in ignored local/server environment files. | Backend focused tests 33/33; PPT typecheck; Seedream adapter tests 3/3; APIMart credential check HTTP 200; production backend active and public health HTTP 200. Full backend suite: 285 passed and 1 unrelated dirty-worktree learning-path test failed. | `eeffc64` plus PPT follow-up commit; backend deployed |
| 2026-08-15 | Default profile portrait | Generated a clean non-identifying Seedream 4.5 learner illustration, compressed it to a 640px WebP, and kept loading/missing/failure labels plus retry actions visible until a report-specific portrait is ready. | Default-avatar contract test 1/1; non-clean frontend build; generated source and compressed WebP visually inspected. | This default-avatar commit |
| 2026-08-15 | Phase 3 scoring evidence pipeline | Extended the real Harness run from one to five distinct intelligent-tutoring cases, linked summary generation directly to redacted E2E task artifacts, and documented a repository-relative reproduction flow. | Python compile checks; `tests.test_harness_real_e2e` and `tests.test_scoring_evidence_suite`, 13/13 passed without model calls. Formal real-model evidence remains pending. | This Phase 3 evidence commit |
| 2026-08-15 | Phase 2 auth and exam recovery | Preserved protected deep links across login and runtime 401 redirects; normalized exam payloads, blocked empty-exam timing/history/evidence writes, used wall-clock timing, and added deliberate exit plus mobile layout. | Frontend contract tests 8/8; Playwright deep-link and exam fixtures passed; non-clean production build passed. | `3f1d48f` |
| 2026-08-16 | Domestic text and multimodal routing | Routed uploaded images and digital-interview frames through Qwen3-VL-Plus, audio evidence through Qwen3-Omni-Flash, and final reasoning through Spark X2 Flash; disabled the legacy MiMo interview fallback and aligned public runtime metadata, landing/PPT labels, Manifest, README, and legacy PPT migration. Production deployment is paused by user request. | Real local text/image/audio calls succeeded; backend `296 passed, 49 subtests passed`; interview/multimodal/routing follow-up tests 15/15; main frontend non-clean build; PPT typecheck and non-clean build; `git diff --check`; tracked-diff credential scan clean. | Local changes, not committed or deployed |
| 2026-08-15 | Phase 2 learning-path integrity | Delayed embedded-assistant path persistence until Harness review, rejected degraded stage baselines, separated load/generation errors from empty profile state, and blocked resource dispatch from degraded paths in both metadata and the backend executor. | Learning-profile/path API 61/61 plus 7 subtests; Harness/MCP 32/32 plus 42 subtests; non-clean frontend build passed. Desktop/mobile visual review remains pending. | This learning-path integrity commit |
| 2026-08-15 | Deep-page wrappers | Fitted the 1920x1080 digital-twin scene into the available viewport and added return, preflight, unavailable and retry states to the OhMyPPT wrapper. | Wrapper source contracts 2/2; non-clean production build passed; route chunks remain 2.11 KB and 2.81 KB before gzip. Desktop/mobile visual review remains pending. | This wrapper-page commit |
| 2026-08-15 | A3 scoring matrix | Added a judge-facing 110-point evidence index that separates implemented facts, repeatable checks, missing real-model cases, missing documents, and unverified presentation assets. | Referenced files and routes checked; Manifest JSON parsed as 22 agents and 18 Skills; `git diff --check` passed. | This scoring-matrix commit |
| 2026-08-17 | Shared AI coding workspace | Deployed DeepSeek Harness under a non-root sandbox account, added the authenticated navbar route and direct iframe embedding, kept provider credentials behind a root-only upstream proxy, and suppressed the remote-only internal-testing notice without opening settings or credential APIs. | Isolated non-clean frontend build; Nginx config check; Harness and SSH tunnel active; unauthenticated runtime/RPC HTTP 401; authenticated desktop 1699x828 and mobile 390x844 browser checks with no plugin/RPC errors and no model call. | Local changes, deployed |
| 2026-08-17 | AI coding command menu | Forwarded only the authenticated `commands/list` and `commands/execute` RPC endpoints so the input “+” menu can load and run Harness commands without taking over the main site's general `/api` namespace. | Focused deployment-config test; Nginx config check; authenticated browser click and console verification without a model call. | Local changes, deployed |
| 2026-08-17 | AI coding attachments | Added an independent Harness attachment button for arbitrary files, fixed all uploads to the shared workspace, and automatically extracts ZIP archives through bounded traversal/symlink/zip-bomb checks. Documented the MIT community-plugin provenance while retaining a hardened server implementation. | Focused upload/extractor tests 12/12; Node/Python syntax checks; empty upload HTTP 400; authenticated browser verified attachment and command controls with no model call. | Local changes, deployed |
| 2026-08-17 | Learner-facing copy cleanup | Removed presentation-oriented prefixes from six seeded conversation memories and renamed their visible source to `示例对话`; retained the original TinyUSB learning intent. | Python compile; non-clean frontend build; production re-seed returned 6/6 completed extractions; database legacy-phrase count 0; live HTML and versioned route assets verified. | Local changes, deployed |
| 2026-08-17 | Learning-evidence encoding guard | Excluded corrupted knowledge-point labels from assessment evidence and repaired the two affected first-week tasks as `嵌入式 Linux 驱动专项巩固` and `MCU 外设配置专项巩固`, including routes, caches, task payloads, and orchestration records. | Focused backend regression 1/1; production SQLite backups created; exact legacy strings and encoded routes count 0; backend health HTTP 200; authenticated browser verified tasks 09-11 and generation states. | Local changes, deployed |
| 2026-08-26 | PPT recursion and generation recovery | Pinned the wrapper to `/ppt/index.html`, blocked recursive iframe/global-chrome duplication, made PPT batches serial by default, split failed batches into bounded single-page retries, and added explicit `recovered`/`fallback` metadata plus visible fallback pages. Rebound the stale first-week node to an existing verified 6-page deck while retaining the old task as a traceable recovery alias. | Wrapper tests 3/3; PPT batch tests 4/4; OhMyPPT client tests 3/3; Python compile; PPT typecheck; both frontends built with `--emptyOutDir=false`; production services and public health HTTP 200; direct history page has one nav, no assistant/iframe nesting, no console errors or horizontal overflow at 390x844; production SQLite backup created and repaired task/cache/configs verified as complete with 6 pages. Authenticated wrapper visual recheck remains for the user after login. | This commit, deployed before commit |

## Remaining work

- Complete the remaining rubric-to-route and shared-shell audits.
- Phase 2: visually verify the learning-path load, generation failure, degraded-path and retry states at desktop/mobile widths.
- Phase 3: create the seven README-declared `docs/*.md` deliverables and the referenced test report; `SCORING_MATRIX.md` now exists as their evidence index.
- Phase 3: run the final real Harness E2E with the review account so the five tutoring cases and scoring summary are backed by archived redacted Xunfei outputs.
- Deep-page polish: make the 1920x1080 digital-twin scene fit desktop/mobile viewports without requiring horizontal scrolling.
- Authenticated visual follow-up: after signing in, re-open `/personalized-resources/ppt?tab=history` and confirm the main wrapper displays exactly one outer toolbar, one OhMyPPT navigation and one floating assistant.
- Admin evidence integrity: label the nationwide region heatmap as deterministic demo allocation data until real region evidence is collected; all other dashboard metrics remain database-derived.

## Decision log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-08-14 | Treat the Git-backed source tree in the current workspace as the only editable project. | It is the only complete repository under the user-authorized workspace. |
| 2026-08-14 | Never delete files or directories, including generated artifacts. | Explicit user safety constraint; move items when organization is required. |
| 2026-08-14 | Use the generated-resource detail flow for Phase 1. | It joins five high-value rubric signals in one judge-visible deep page: real generation, profile dependence, agent collaboration, hallucination review, and learning feedback. |
| 2026-08-14 | Treat the Manifest counts of 22 implemented roles and 18 registered Skills as verified, but do not treat missing documentation files as delivered evidence. | The counts match `backend/agent_manifests/xiaozhi_agents.json`; the README-declared documentation paths do not exist in the current Git tree. |
| 2026-08-14 | Keep the admin heatmap but label it as demo allocation data. | `/api/admin/dashboard` derives global metrics from SQLite but builds province values through `_admin_region_demo`; presenting those values as observed regional data would overclaim evidence. |
