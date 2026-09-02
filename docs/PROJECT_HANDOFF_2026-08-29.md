# 中药鉴别项目交接文档

更新时间：2026-08-29

本文档用于在新的 Codex 对话中继续维护本仓库。它记录当前代码基线、已确认的产品决策、运行方式、验证结果和风险边界，不包含 API Key、服务器密码或其他私密配置。

## 1. 新对话先读什么

按以下顺序阅读：

1. 根目录 `AGENTS.md`：仓库安全规则和强制工作流。
2. 根目录 `SCORING_MATRIX.md`：官方 A3 评分项、现有证据和缺口。
3. 根目录 `README.md`：完整功能、运行、部署和知识库说明。
4. 本文档：当前分支状态、用户已确认的设计边界和下一步建议。

修改时应保护用户数据和已有工作区内容。禁止清理未跟踪文件、覆盖用户数据库、提交 `.env`，也禁止使用破坏性 Git 命令。

## 2. 当前 Git 基线

| 项目 | 当前值 |
| --- | --- |
| 仓库 | `https://github.com/wowotouaichihaozi/zhongyao-jianbie.git` |
| 工作分支 | `codex/learning-experience-polish` |
| 当前提交 | `5a814bf`：`chore: sync latest project updates` |
| 已同步主线 | `origin/main` = `6486676` |
| 远端同名分支 | `d950992`，当前本地领先 14 个提交 |
| 是否已推送本轮整合 | 否 |
| 同步前恢复点 | `stash@{0}: codex: preserve personalized resources before upstream sync` |

`5a814bf` 的含义：完整接受最新主线更新，同时保留用户反复确认过的个性化资源工作台，只在该页面加入主线新增的第六个“药材模型识别”工具；另外修复了主线中岐小智弹窗的 `Map` 命名冲突。

当前工作区还包含用户或运行期文件，不能批量清理或提交：

- `backend/data/profile_workflow.sqlite` 有本地运行数据改动。
- `backend/venv/`、`logs/`、`output/`、`frontend/test-output/` 是本机环境或验证产物。
- `frontend/public/images/`、`img/images/resource-topic-patterns-v1/`、`img/images/resource-topics/` 和 `frontend/src/components/TopicSolidGlyph.vue` 是未跟踪的历史方案或镜像资源，仓库规则要求保留。
- `backend/agent_harness/__pycache__/` 和 LangGraph 图片是运行生成文件。

新对话开始时先执行 `git status --short --branch`，不要假设上述状态仍完全相同。

## 3. 项目一句话定位

这是一个面向中医药学习的个性化多智能体平台。核心不是单个 AI 工具，而是可演示、可追踪的完整学习闭环：

```text
学习画像采集/更新
  -> 画像驱动的分周路径规划
  -> 多类型学习资源生成与检索
  -> 学习验证和反馈
  -> 岐小智辅导
  -> 效果评估
  -> 画像与路径调整
```

产品完整性要求：

- 至少 6 个可更新画像维度；当前正式画像为 10 维。
- 至少 5 种可演示资源类型。
- 画像依赖、多智能体协作、知识引用、安全/质量审核、结构化校验和长任务进度要对评委可见。
- 不得声称运行系统无法实际演示的能力或证据。

## 4. 主要技术结构

| 目录 | 作用 |
| --- | --- |
| `backend/` | Flask 主后端、SQLite、画像/路径/资源 API、Harness、MCP、知识检索和模型集成 |
| `frontend/` | Vue 3 + Vite 主用户端，默认开发端口 `5088` |
| `admin/` | Vue 3 + TypeScript + Soybean Admin 管理端 |
| `mobile/` | Vue 3 + Capacitor 移动端与 Android 工程 |
| `microprogram/` | 微信小程序 |
| `ppth5/` | OhMyPPT H5 工作台及 FastAPI 服务，默认端口 `8765` |
| `img/` | 主前端公共静态资源；`frontend/vite.config.js` 的 `publicDir` 指向这里 |
| `docs/` | 智能体协议、知识来源和本交接文档 |
| `scripts/` | 便携包、知识库、药材模型、生产包构建脚本 |

后端关键入口：

- `backend/app.py`：统一 API 和生产静态入口。
- `backend/database_schema.py`：SQLite 表结构和迁移。
- `backend/learning_agents.py`：画像驱动的路径和资源编排。
- `backend/agent_harness/`：Supervisor、Handler、共享状态和执行运行时。
- `backend/agent_manifests/xiaozhi_agents.json`：22 个已实现角色和 18 个 Skill 的声明。
- `backend/profile_agent_context.py`：按用户和画像隔离的智能体会话。
- `backend/knowledge_retrieval_agent.py`、`backend/hybrid_knowledge.py`：QA、文档和图谱混合检索。
- `backend/herb_model_catalog.py`：20 味 3D 药材模型目录。

主前端关键入口：

- `frontend/src/router/index.js`：用户端路由和鉴权。
- `frontend/src/App.vue`、`frontend/src/components/TopNavbar.vue`：全局壳层。
- `frontend/src/components/FloatingLogoLauncher.vue`：岐小智悬浮助手和多智能体进度。
- `frontend/src/styles/motion.css`：共享动效与 `prefers-reduced-motion` 降级。
- `frontend/src/services/api.js`：主 API 客户端。

## 5. 主要用户入口

| 路由 | 功能 |
| --- | --- |
| `/learning-profile` | 10 维学习画像采集、更新、报告和历史 |
| `/learning-path/stage/overview` | 分周学习路径总览 |
| `/learning-path/week/:stageId` | 周任务和学习验证 |
| `/personalized-resources` | 个性化资源专题工作台 |
| `/personalized-resources/herb-model` | 20 味 3D 药材模型识别 |
| `/herb-recognition` | 本地 YOLO / 可选视觉模型药材识别 |
| `/knowledge-network` | 课程知识关系网络和知识自生长 |
| `/life-tree` | 学习证据驱动的三维生命树 |
| `/smart-tutor` | 苏格拉底追问、费曼复述、提示和练习 |
| `/effect-assessment` | 学习效果、能力变化和路径调整 |
| `/digital-human-interview` | 讯飞数字人学习访谈，失败时文字流程可继续 |
| `/admin/` | 管理端；数字孪生架构展示已迁移到管理端 |
| `/ppt/` | OhMyPPT H5 工作台 |

## 6. 必须保护的个性化资源模块

这是用户近期反复修改并最终确认的模块。后续同步主线时，不要直接采用主线的资源列表、搜索、分页或其他重新设计覆盖它。

核心文件：

- `frontend/src/views/PersonalizedResourcesView.vue`
- `frontend/tests/personalizedResourcesWorkspace.e2e.mjs`
- `frontend/tests/personalizedResourcesBrowsing.test.mjs`
- `frontend/tests/personalizedResourcesBrowsing.e2e.mjs`
- `img/images/resource-topic-patterns-v2/`
- `img/images/resource-topic-icons-v2/`

当前上方有 6 个真实工具入口：

1. AI 视频课程
2. 题库生成
3. PPT 生成
4. 思维导图
5. 药材模型识别
6. 视频查找

当前资源区不是按周次或类型做搜索分页，而是 8 个中医课程专题：八纲辨证、药材识别、性味归经、方剂配伍、四诊合参、经络腧穴、养生健康、医案研习。每张卡使用不同的透明 PNG 纹理和独立 PNG 实心图标；专题优先打开匹配的真实历史资源，无匹配时进入真实现有能力，不能伪造学习人数、评分或完成度。

已确认的视觉要求：

- 课程卡采用“色彩背景 + 简约纹理 + 右侧实心图标”的信息结构，并保持本项目独立的视觉与交互设计。
- 图标必须是普通透明 PNG，不再用 SVG 拼接；简约不等于简单，应有明确的中医语义和少量镂空纹理。
- 纹理不能八张同构换方向；当前 v2 分别使用曲面、弧线/点阵、宽波浪、方点、灌木圆瓣、等高线、斜色带和网点云。
- 桌面 6 个工具同排，移动端为 `2 x 3`；专题卡桌面 4 列、移动端 1 列。
- 页面必须保留加载、真实空态、部分失败、完整失败、无画像和交互状态。

注意：Vite 的 `publicDir` 是根目录 `img/`，因此页面实际使用的资源应放在 `img/images/...`。`frontend/public/images/` 中的镜像目前未跟踪，不要误认为生产唯一来源。

## 7. 其他已确认的定制功能

### 学习路径学院地图

- 文件：`frontend/src/views/LearningPathStageDetailView.vue`
- 六个节点是代码构建的 SVG 建筑，不是 AI 生成房屋图片。
- 地标从小书舍、药圃、诊堂逐步发展为讲院、藏经阁和知识殿堂。
- 后期建筑略大但增长受控，最后一座中楼明显更高。
- 鼠标悬停向上浮动。
- 页面进入时左右卡片和六个建筑在 0.5 秒内依次浮现。
- 背景为 `/learning-path-academy-background-v1.png`。
- 回归用例：`frontend/tests/learningPathAcademy.e2e.mjs`。

### F4 学习画像测试工具

- 文件：`frontend/src/views/LearningProfileView.vue`、`frontend/src/utils/learningProfileDeveloperTools.js`。
- 在学习画像页按普通 `F4` 打开隐藏开发面板。
- “一键补充”必须写入真实后端画像数据，使学习路径可以使用，不是只改前端显示。
- 支持清除测试画像。
- 回归用例：`learningProfileDeveloperTools.test.mjs` 和 `learningProfileDeveloperTools.e2e.mjs`。

### 全站动效

- 共享样式：`frontend/src/styles/motion.css`。
- 卡片/面板插入、弹窗、岐小智窗口、内部标签切换和导航状态使用轻量 `transform + opacity`。
- 路由组件保持直接挂载，不能重新引入可能造成白屏的路由卸载动画。
- 必须保留 reduced-motion 降级和连续切页不白屏测试。
- 最新主线曾让 Lucide `Map` 图标遮蔽原生 `Map`，已在 `FloatingLogoLauncher.vue` 改为 `MapIcon`，不要改回。

## 8. 最近一次主线同步带来的更新

当前代码已包含 `origin/main@6486676` 的主要更新：

- 按画像隔离的智能体工作流上下文。
- 登录流程稳定性修复。
- AI 视频自动封面与资源工作流进度收口。
- 每周任务白屏修复。
- 20 味药材模型资源和站内学习路径返回。
- 管理端数字孪生页面。

个性化资源页没有采用主线的新搜索/分页重构，只补了药材模型入口。这是有意的产品选择，不是漏合并。

## 9. 本地启动方式

### 统一入口，适合完整演示

```powershell
Set-Location C:\Users\xushen\Desktop\xfb\lizihan
.\start-frontend-backend.bat
```

该脚本构建用户端和管理端，然后启动或复用 Flask `3000`：

- 用户端：`http://127.0.0.1:3000`
- 管理端：`http://127.0.0.1:3000/admin/`
- 健康检查：`http://127.0.0.1:3000/api/health`

### 分开开发

```powershell
.\start-backend.bat
.\start-frontend.bat
```

- 后端默认 `3000`。
- Vite 默认 `5088`，并把 `/api` 代理到 `3000`、`/ppt-api` 代理到 `8765`。
- 若端口已被健康服务占用，启动脚本会复用；若端口占用但健康检查失败，会显示 PID 后退出。

### 启动完整套件

```powershell
.\start-all.bat
```

它还会构建管理端并启动 OhMyPPT `8765`，要求 Node.js、npm、pnpm、后端虚拟环境和 `ppth5/backend/.venv` 可用。

交接时本机观察到 `3000`、`5088` 和本轮验证用的 `5089` 都在监听；这是临时进程状态。新对话必须重新检查端口，不要直接终止不明进程。

## 10. 验证命令

任何前端构建都使用非清理方式：

```powershell
Set-Location frontend
npm.cmd run build -- --emptyOutDir=false
```

当前模块的高价值检查：

```powershell
Set-Location frontend

node --test tests\herbAnswerOptions.test.mjs tests\herbModelNavigation.test.mjs tests\personalizedResourcesBrowsing.test.mjs tests\xiaozhiWorkflowProgress.test.mjs tests\authRedirect.test.mjs

$env:E2E_BASE_URL = 'http://127.0.0.1:5088'
npm.cmd run test:personalized-resources:e2e
npm.cmd run test:motion-system:e2e
npm.cmd run test:learning-path-academy:e2e
npm.cmd run test:learning-profile-developer-tools:e2e
```

后端重点检查：

```powershell
Set-Location backend
.\venv\Scripts\python.exe -m unittest tests.test_profile_agent_context -v
```

`backend/venv` 在本次交接时没有安装 `pytest`，运行 pytest 用例前应明确安装测试依赖或使用已有环境，不能把“缺少 pytest”误判为业务失败。

最近一次已通过的证据：

- 前端聚焦契约测试 22/22。
- 个性化资源 Playwright 覆盖桌面/移动、填充、交互、空、警告、错误、无画像和加载状态。
- 真实登录浏览检查：8 个专题、6 个工具、全部图片加载成功。
- 全站动效、reduced-motion、移动端和连续路由切换通过。
- 后端画像上下文、知识检索和药材模型聚焦测试 14 项通过。
- 非清理生产构建通过，转换 4013 个模块；只有既有的大分包体积警告。

## 11. 当前风险和未完成项

1. 当前整合提交尚未推送，远端同名分支仍停在 `d950992`。推送前要再次检查状态和远端权限。
2. 根 README 列出的多份标准交付文档实际尚不存在；当前 `docs/` 主要包含智能体协议、知识来源和本交接文档。这仍是文档完整性风险。
3. 正式演示视频、答辩 PPT、完整真实队员案例和评委账号 E2E 证据尚需归档。
4. 不要把开发预览参数、固定演示数据或本地缓存当作生产证据。
5. 不要把数字孪生描述成实时镜像；当前是管理端的架构展示。
6. 服务器部署、API Key 同步或远端推送属于外部状态变更，需要用户明确要求后再执行，并且不得把凭据写进文档、日志或 Git。

## 12. 下一次改动的安全流程

1. 读 `AGENTS.md`、评分矩阵、本交接文档和相关源码。
2. 运行 `git status --short --branch`，识别并保护用户文件。
3. `git fetch origin` 后比较主线，不要盲目覆盖个性化资源模块。
4. 小范围实现，沿用 Vue、设计 token 和 Lucide；专题位图继续使用 PNG。
5. 真实路由验证桌面和移动端，以及适用的加载、空、错误、填充和交互状态。
6. 运行聚焦测试和 `npm run build -- --emptyOutDir=false`。
7. 检查 `git diff`，只暂存意图文件，绝不暂存 `.env`、SQLite、venv、logs 或 output。
8. 未经用户明确要求，不部署、不推送、不改远端数据。

## 13. 可直接发给新对话的开场提示

```text
继续维护 C:\Users\xushen\Desktop\xfb\lizihan。
先完整阅读 AGENTS.md、SCORING_MATRIX.md 和 docs/PROJECT_HANDOFF_2026-08-29.md，再检查 git status。
当前基线是 codex/learning-experience-polish@5a814bf，已包含 origin/main@6486676，但尚未推送。
个性化资源页是用户确认过的保护模块：保持当前 8 个专题 PNG 卡片和响应式状态，只把主线新增的“药材模型识别”作为第六工具保留，不能用主线搜索/分页版本覆盖。
保护 backend/data/profile_workflow.sqlite 和所有未跟踪文件，不要提交 .env，不要清理或删除文件。完成后做桌面/移动端状态检查和非清理构建。
我接下来要改的是：<在这里填写新需求>。
```
