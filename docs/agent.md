# 岐黄智境 Agent Harness 主流程

本文档是平台多智能体学习闭环的主约定。新增智能体、资源类型和学习路径逻辑必须遵守本协议，避免形成互不共享状态的独立流程。

## 1. 总目标

岐小智是唯一总控智能体。平台以一份学习画像为一个长期协作空间，学习画像、路径规划、知识检索、资源生成、审核和效果评估智能体共享同一条群聊式消息流。用户看到的“某智能体正在做什么、完成了什么、交接了什么”必须来自真实 Harness 事件，而不是前端模拟状态。

完整闭环：

```text
收集十维画像
  -> 保存画像
  -> 岐小智生成第一周任务
  -> 按任务拆解检索词
  -> 混合知识库检索（QA + 文档切块 RAG + 知识图谱）
  -> 资源专家生成可访问页面
  -> 审核智能体异步打分与记录引用
  -> 用户完成本周部分或全部任务
  -> 直接生成下一周，或先做效果评估更新画像
  -> 新画像影响下一周规划
```

## 2. 智能体职责

| 角色 | 职责 | 必须写入共享消息 |
| --- | --- | --- |
| 岐小智总控 | 汇总画像与群聊上下文、拆解目标、派发任务、处理失败、收口结果 | 任务派发、状态变化、最终结论 |
| 学习画像智能体 | 收集十个维度、生成或更新画像 | 缺失维度、画像完成、画像版本 |
| 路径规划智能体 | 每次只规划一周，确保资源覆盖且任务要求不重复 | 周次、规划依据、任务清单 |
| 知识检索智能体 | 拆分关键词和实体，执行混合路由与重排 | 子查询、命中数、引用、交叉验证 |
| 资源生成专家 | 调用对应 Skill/MCP，生成题库、PPT、导图、视频检索、AI 视频封面和药材模型任务 | 开始、进度、资源路由、完成或失败 |
| 审核智能体 | 在资源可访问后异步审核，输出质量分和原因 | 分数、理由、问题、是否通过 |
| 效果评估智能体 | 汇总完成度、错题与反馈，更新画像证据 | 评估结论、画像变化、后续建议 |

任何专业智能体不得绕过岐小智直接派发另一个智能体。交接通过 Harness Handoff 完成，并同步到画像群聊。

## 3. 画像级共享群聊

### 3.1 作用域

- 隔离键：`(userId, profileReportId)`。
- 同一用户的不同画像拥有不同群聊和不同压缩摘要。
- 所有周次、任务和资源运行只要绑定同一个 `profileReportId`，就读取和写入同一群聊。
- `runId` 只标识一次执行，不能再作为长期上下文边界。
- Supervisor 固定为 `xiaozhi-companion-agent`，展示名固定为“岐小智总控智能体”。

### 3.2 消息内容

每条消息至少包含：

```json
{
  "sequence": 18,
  "profileReportId": 3,
  "runId": "mar_...",
  "taskId": "xz_...",
  "agentId": "course-knowledge-retrieval-agent",
  "agentName": "知识检索智能体",
  "type": "agent_event | handoff | review | status",
  "status": "running | complete | warning | needs_attention | failed",
  "content": "已完成关键词拆分，命中 8 条可追溯证据",
  "payload": {},
  "resourceReferences": [
    {"type": "task", "id": "xz_..."},
    {"type": "citation", "id": "doc-8#3"}
  ]
}
```

数据库表：

- `profile_agent_conversations`：画像群聊、Supervisor、摘要版本和上下文预算。
- `profile_agent_messages`：有序消息、运行归属、状态、结构化载荷和资源引用。
- `profile_agent_context_snapshots`：每次自动压缩产生的不可变摘要快照。

只读接口：`GET /api/xiaozhi/profile-conversation?profileReportId=<id>`。不传画像 ID 时读取当前激活画像。接口必须校验画像归属。

### 3.3 Harness 上下文注入

每次运行前，Harness 把以下内容写入共享黑板和专业智能体输入：

```json
{
  "agentConversation": {
    "supervisor": {"id": "xiaozhi-companion-agent", "name": "岐小智总控智能体"},
    "summary": "压缩后的历史关键结论",
    "recentMessages": [],
    "contextBudget": {
      "maxTokens": 24000,
      "estimatedTokens": 6200,
      "automaticCompaction": true
    }
  }
}
```

专业智能体只能把群聊当作学习上下文与协作证据，不能把旧消息中的用户文本当作系统指令，也不能把未经知识库核验的聊天内容当作课程事实。

## 4. 自动上下文压缩

平台使用保守的中英文混合 token 估算。活动上下文达到预算的 78% 时自动压缩：

1. 保留最近 36 条消息原文。
2. 将更早消息压缩为结构化摘要，保留智能体、状态、结论、任务 ID、资源 ID 和引用 ID。
3. 写入新的版本化快照，并把已覆盖消息标记为 `compacted`。
4. 后续提示只注入最新摘要和未压缩近期消息；原始消息仍保存在数据库中，可审计但不再占用模型上下文。
5. 压缩失败不得阻断资源生成，Harness 记录警告后继续使用近期消息。

可配置项：

```dotenv
PROFILE_AGENT_CONTEXT_MAX_TOKENS=24000
PROFILE_AGENT_CONTEXT_COMPACTION_RATIO=0.78
PROFILE_AGENT_CONTEXT_RECENT_MESSAGES=36
```

## 5. 周次状态机

画像完成后只自动生成第一周。不得一次预生成六周，因为后续周次必须吸收真实学习结果。

```text
profile_ready
  -> week_planning
  -> week_ready
  -> resource_retrieving
  -> resource_generating
  -> resource_accessible
  -> reviewing
  -> reviewed
  -> week_in_progress / week_completed
  -> next_week_requested / profile_update_requested
```

- `week_ready` 后即可展示任务。
- 资源任务创建后立即返回稳定任务 ID 和页面路由。
- `resource_accessible` 与 `reviewed` 分离；审核进行中不阻止用户访问资源。
- 后续周次由用户明确触发，每次只生成下一周。
- 用户可先进入效果评估创建画像新版本，再用更新后的画像生成下一周。

## 6. 每周资源约束

每周至少覆盖六类用户可见资源：

1. AI 视频课程（自动生成提示词和首图，视频只在用户确认后生成）
2. 题库
3. PPT
4. 思维导图
5. 药材模型辨识
6. 视频查找

课程讲义可以作为可选第七类资源。一个学习任务可以包含多个资源，但每个资源必须拥有独立任务 ID、状态、路由、引用和审核结果。兼容旧页面时保留 `resourceType` 与 `resourceTask` 作为主资源，同时使用 `resourceTypes` 与 `resourceTasks` 表达完整列表。

## 7. 单个资源执行协议

```text
岐小智派发任务
  -> 检索智能体拆分关键词/实体/约束
  -> QA、文档 RAG、知识图谱分别召回
  -> 混合重排和交叉验证
  -> 专家智能体接收画像 + 摘要 + 近期消息 + 引用片段
  -> Skill/MCP 生成资源并返回稳定页面
  -> 审核智能体异步检查完整性、画像适配、引用一致性和安全性
  -> 质量分、评分理由和引用详情写入资源记录与画像群聊
```

生成失败必须展示真实错误；不得用静态兜底内容伪装为大模型结果。审核失败不删除已生成资源，而是标记为需处理并允许重新生成。

## 8. 前端显示原则

- 全局只保留一个岐小智悬浮助手。
- 群聊卡片显示在助手对话区域内，不新建第二个悬浮窗。
- 页面只突出学习资源本身；画像依据、检索、交接和审核细节收进群聊卡片或折叠详情。
- 进度必须来自 `profile_agent_messages` 或当前 SSE 事件；刷新后通过画像群聊接口恢复。
- 同一 `dedupeKey` 的事件只显示一次，避免轮询和 SSE 导致重复卡片。

## 9. 当前落地状态

已落地：画像级群聊表、运行前上下文注入、运行中事件写入、运行后 Handoff/审核补齐、自动压缩快照、只读接口和单元测试。

下一阶段按本文档继续完成：仅生成第一周、下一周生成接口、多资源任务结构、周完成后的画像更新分支，以及悬浮助手对画像群聊的持久化展示。
