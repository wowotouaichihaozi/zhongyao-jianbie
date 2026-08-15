# A3 评分证据矩阵

更新时间：2026-08-15

本矩阵按官方《评分表-A3-基于大模型的个性化资源生成与学习多智能体系统开发-0710》组织。它记录可核验事实、复现入口和剩余风险，不填写自评分。官方“功能技术指标要求”标注为 30 分，但五个子项按表面分值合计为 31 分；本项目保留原始子项，不自行改算总分。

## 1. 创新价值与实用性（35 分）

| 评分项 | 分值 | 当前证据 | 验证入口 | 证据状态与风险 |
| --- | ---: | --- | --- | --- |
| 功能实用性 | 10 | 公网平台、用户/管理员角色、学习闭环、移动端与二维码入口；生产静态资源按路由分块并缓存 | `https://lzhan.xyz/`；`/api/health`；`/api/item/{a1,b7,c4}` | 已部署。最终仍需按演示脚本完成桌面与移动人工走查 |
| 方案创新性 | 15 | 画像采集 -> 路径规划 -> 六类周资源 -> 学习验证/反馈 -> 智能辅导 -> 效果评估与路径调整 | `README.md`“核心能力”“学习路径渐进生成”；`/learning-profile`、`/learning-path`、`/effect-assessment` | 闭环代码与页面存在；正式演示截图和完整参赛队员案例尚未归档 |
| 技术创新性 | 10 | Supervisor + 共享黑板 + Skill Registry + MCP + Handoff + 质量/安全审核；讯飞文本/语音/数字人及国产视觉/图像/视频模型 | `backend/agent_harness/`、`backend/agent_manifests/xiaozhi_agents.json`、`README.md`“真实模型能力” | 架构与测试可核验；需在答辩中用真实运行轨迹证明深度协同，不只展示架构图 |

## 2. 功能实现及技术要求（官方 45 分）

| 评分项 | 分值 | 当前证据 | 验证入口 | 证据状态与风险 |
| --- | ---: | --- | --- | --- |
| 系统完善度 | 10 | 画像、路径、资源生成、验证反馈、辅导、评估与调整均有路由/API；长任务有进度、失败和重试状态 | `README.md`；`frontend/src/router/index.js`；`backend/app.py` | 主链完整。仍需一套从新画像到路径调整的录屏级验收 |
| 对话式学习画像自主构建 | 8 | 对话生成与更新十个画像维度，报告含六维雷达、证据矩阵、AI 结论与画像人像 | `/learning-profile`；`backend/tests/test_learning_profile_api.py` | 代码与自动测试覆盖；需用一名真实队员完成并截图多轮画像更新 |
| 多智能体协同的资源生成 | 10 | 每周固定覆盖题库、PPT、思维导图、视频查找、MCU 模拟和 AI 视频讲解六类；资源详情展示画像依据、Harness、质量审核和知识引用 | `/personalized-resources`；`backend/scoring_evidence_suite.py`；`frontend/src/views/ResourceDetailView.vue` | 类型数满足。正式 5 个真实讯飞资源案例与质量报告需由 E2E 流程最终生成并归档 |
| 个性化路径规划与资源推送 | 3 | 路径读取画像目标、薄弱点、偏好、时间与学习证据；候选只在审核通过后落库，降级路径禁止派发资源 | `/learning-path`；`backend/tests/test_learning_profile_api.py` | 自动测试通过；需要归档 3-5 组不同画像导致不同路径/资源的截图或报告 |
| 智能辅导（加分项） | 5 | `learning.tutor.answer` 输出苏格拉底追问、费曼复述、三级提示、练习、学习卡与引用 | `/smart-tutor`；`backend/harness_real_e2e.py`；`backend/scoring_evidence_suite.py` | 真实验收脚本已覆盖 5 个不同场景；最终真实模型调用产物尚未运行并归档 |
| 学习效果评估（加分项） | 5 | 达成率、掌握率、前后雷达、知识热力图、可应用路径调整计划 | `/effect-assessment`；`backend/scoring_evidence_suite.py` | 三组确定性评估场景通过单测；仍需在最终账号形成 3 组可视化案例 |
| 功能创新 | 5 | 讯飞数字人面试、智能体数字孪生架构展示、知识自生长记忆、MCU 仿真实验 | `/digital-human-interview`、`/agent-digital-twin`、`/knowledge-network`、`/mcu-simulator` | 功能存在；答辩必须说明数字孪生是架构展示而非实时运行，避免过度声明 |

## 3. 配套文档丰富度（10 分）

| 评分要求 | 当前证据 | 证据状态与风险 |
| --- | --- | --- |
| 开发、测试、部署说明 | `README.md` 已含运行、配置与验证命令；`docs/A3-scoring-optimization-tracker.md` 记录优化与验收 | README 声明的 `docs/DEVELOPMENT_GUIDE.md`、`docs/TEST_GUIDE.md` 等 7 份标准文档尚未创建，这是当前最高文档风险 |
| 源码、测试、知识库数据 | 源码与自动测试在 Git；`docs/knowledge-expansion-sources.json` 记录扩展知识来源 | 大体具备；需补知识库规模复核命令和许可证边界说明文档 |
| 架构图、功能图、技术栈、实现与创新 | README 有文字说明，数字孪生页有架构展示 | 缺独立系统设计文档和面向评委的静态架构/功能图 |
| 完整用户案例与效果截图 | 评分证据脚本可生成结构化报告 | 正式测试报告、截图和参赛队员完整案例尚未归档 |

## 4. 演示视频与 PPT 效果（10 分）

| 评分要求 | 当前证据 | 证据状态与风险 |
| --- | --- | --- |
| 视频清晰、逻辑清楚、实操占比至少 60% | 平台已有可演示闭环和稳定公网地址 | 未在当前 Git 树发现最终演示视频与脚本，无法核验时长、清晰度和实操占比 |
| PPT 覆盖价值、架构、功能、技术栈、核心实现、创新与幻觉防控 | OhMyPPT 工作台和生成链已部署 | 未在当前 Git 树发现最终答辩 PPT，无法核验内容完整性与 AI 味 |

## 5. 附加分（10 分）

| 方向 | 当前证据 | 证据状态与风险 |
| --- | --- | --- |
| 讯飞 AI 工具/模型 | Spark X2 Agent、讯飞超拟人 TTS、讯飞数字人 | 代码和生产配置已接入；密钥只在环境变量。答辩需展示脱敏配置与真实调用结果 |
| 前沿技术与多模态 | 多智能体 Harness、MCP、Seedream 4.5、Seedance、视觉预处理 | 已实现；需以真实任务产物证明，不以模型名称代替效果 |
| 实际场景测试与幻觉防控 | 嵌入式课程知识库引用、输出契约、质量与安全审核、降级结果拒绝 | 自动测试存在；正式案例报告尚待生成 |
| 私有知识库与外部接口 | 用户隔离知识库、MCP JSON-RPC、二维码/API 路由 | 功能存在；独立 API 说明文档尚缺 |
| 软硬件结合/国产模型数据库/AI Coding | MCU 模拟器、国产模型链、AI Coding 说明入口 | `docs/AI_CODING_USAGE.md` 尚缺；真实硬件演示证据尚未归档 |

## 可重复验证

```powershell
# 后端路径、画像、Harness 与 MCP 契约
Set-Location backend
python -m pytest tests/test_learning_profile_api.py -q
python -m pytest tests/test_agent_manifest_and_harness.py tests/test_mcp_protocol.py -q
python -m unittest tests.test_harness_real_e2e tests.test_scoring_evidence_suite -v
Set-Location ..

# 前端深链、考试、包装页与生产构建
Set-Location frontend
npm run test:auth-redirect
npm run test:question-exam-session
npm run test:wrapper-pages
npm run build -- --emptyOutDir=false
Set-Location ..

# 最终真实模型证据（需要本地服务、激活画像与验收账号密码）
$env:HARNESS_E2E_PASSWORD = "<评审账号密码>"
python backend/harness_real_e2e.py --base-url http://localhost:3000 --output-dir .\测试报告
python backend/scoring_evidence_suite.py --output-dir .\测试报告
```

## 当前优先级

1. 用最终评审账号运行真实 Harness E2E，归档 5 类资源、5 个辅导、4 组推荐和 3 个评估证据。
2. 创建 README 已声明的开发、需求、测试、系统设计、MCP API、知识库和 AI Coding 七份标准文档。
3. 制作并核验演示脚本、最终 PPT 和视频，保证系统实操占比不低于 60%。
4. 完成学习路径、数字孪生和 PPT 包装页的桌面/移动人工视觉验收并归档截图。
