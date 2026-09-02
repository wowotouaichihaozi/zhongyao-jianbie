# 第三方开源项目与许可说明

本项目为“中药鉴别”多智能体学习平台，部分模块参考或基于第三方开源项目进行二次开发。项目展示、比赛答辩、论文或交付材料中应保留本说明，并遵守各原项目许可证要求。

## Three.js 与生命树设计参考

- Three.js：https://github.com/mrdoob/three.js ，MIT License，前端依赖版本 `0.185.1`。
- 用途：`/life-tree` 的 WebGL 场景、低多边形树体、相机控制、光照、节点拾取和响应式渲染。
- 集成位置：`frontend/src/components/LifeTreeScene.vue`；依赖声明位于 `frontend/package.json` 与锁文件。
- 本项目修改：未修改 Three.js 依赖源码；生命树几何、状态颜色、数据适配、节点详情和闭环跳转均为本项目实现。

生命树设计阶段还核对了 `dgreenheck/ez-tree`（MIT）、`vasturiano/3d-force-graph`（MIT）、`vasturiano/r3f-forcegraph`（MIT）、`andrico1234/beautiful-skill-tree`（GPL-3.0）和 `SkyeShark/SeedThree`（MIT）的公开仓库。它们只作为树形生成、三维关系图和技能树交互的调研参考；本项目没有复制、改写或打包上述五个仓库的源码、样式与素材，也不把它们声明为产品运行依赖。

## 混合中医知识语料

以下 Hugging Face 数据集以固定 revision 下载，经过文本规范化、去重、切片、压缩和 FTS5 索引后进入 `backend/data/tcm_hybrid_corpus.db.gz`。项目不修改上游许可证，不把数据集内容声明为平台原创；构建清单保留输入文件 SHA-256、纳入数量和输出数据库双重哈希。

- `SylvanL/Traditional-Chinese-Medicine-Dataset-SFT`：https://huggingface.co/datasets/SylvanL/Traditional-Chinese-Medicine-Dataset-SFT ，revision `412f3ff8417bdf1d7d0e2157c4e5d2323a74b5e5`，Apache-2.0；用于中医 QA 检索。
- `SylvanL/Traditional-Chinese-Medicine-Dataset-Pretrain`：https://huggingface.co/datasets/SylvanL/Traditional-Chinese-Medicine-Dataset-Pretrain ，revision `fd01649d8e019ed2b002119e0fd74076c5f7b73d`，Apache-2.0；完整纳入 `CPT_tcmKnowledge_source2_12889.json` 并切分为文档片段。
- `ZJUFanLab/TCMChat-dataset-600k`：https://huggingface.co/datasets/ZJUFanLab/TCMChat-dataset-600k ，revision `c65f284fc43d7de94ecc83e58dac0db281d73295`，Apache-2.0；用于 QA 子集及中医基础理论、中药学、方剂学、伤寒论教材切片。
- `shuyuej/CMMLU-Traditional-Chinese-Medicine-Benchmark`：https://huggingface.co/datasets/shuyuej/CMMLU-Traditional-Chinese-Medicine-Benchmark ，revision `0008b9c567ed5c81f5c855312fe32abb07ea1742`，Apache-2.0；用于中医多项选择 QA 检索与检索回归。

运行时只把这些资料用于课程学习内容的检索增强，并保留 `educational_only;not_for_clinical_diagnosis_or_prescription` 安全标记。数据可能包含错误、历史表述或不适用于具体个体的内容；平台要求至少两类独立知识路由一致后才允许按证据生成，否则明确标记为待核验。实际诊疗、用药和处方必须由具备资质的专业人员完成。

## 知识网络展示

### nashsu/llm_wiki

- 原项目：https://github.com/nashsu/llm_wiki
- 许可证：GNU General Public License v3.0；原始许可证保存在 `frontend/public/vendor/llm-wiki/LICENSE`。
- 用途：知识网络页直接参考并改编其 `graph-view.tsx` 与 `graph-layout-worker.ts`，采用 Sigma.js WebGL、Graphology 图结构、ForceAtlas2 后台布局、密度自适应节点/标签、搜索定位、筛选、缩放和适应视图等实现方式。
- 本项目适配：改写为 Vue 3 组件，接入真实课程索引、用户私有知识、Harness 运行和反哺数据；未复制其 Tauri、React 编辑器或知识生成后端。
- 集成位置：`frontend/src/components/KnowledgeSigmaGraph.vue` 与 `frontend/src/workers/knowledge-graph-layout.worker.js`。
- 分发要求：上述改编代码及包含它的衍生分发须遵守 GPL-3.0，并向接收者提供相应源码与许可证文本。

### Sigma.js / Graphology / ForceAtlas2

- Sigma.js：https://github.com/jacomyal/sigma.js ，MIT License。
- Graphology：https://github.com/graphology/graphology ，MIT License。
- graphology-layout-forceatlas2：https://github.com/graphology/graphology-layout-forceatlas2 ，MIT License。
- 用途：分别承担 WebGL 图谱渲染、图结构管理和 ForceAtlas2 布局，依赖版本记录在 `frontend/package.json` 与锁文件中。

### Apache ECharts

- 用途：平台其他统计图表和数据可视化。
- 原项目：https://github.com/apache/echarts
- 许可证：Apache License 2.0
- 集成位置：`frontend/package.json` 中的 `echarts`。

### Quartz 与 Obsidian Graph View 参考边界

- Quartz 原项目：https://github.com/jackyzha0/quartz ，MIT License。
- Obsidian Graph View 用途：仅作为知识关系浏览的视觉和交互参考；本项目没有复制或打包 Obsidian 客户端代码，也不宣称与 Obsidian 官方存在关联。
- Quartz 用途：参考公开知识关系、反向链接和逐层浏览思路，未复制 Quartz 站点源码或主题文件。

### 扩充课程知识来源

以下内容以规范化纯文本形式进入便携作品的课程知识库。每份文件保留仓库、commit、许可证、原始路径和 SHA-256；精确 commit 与文件数量见 `docs/knowledge-expansion-sources.json`。

- FreeRTOS Kernel，MIT：https://github.com/FreeRTOS/FreeRTOS-Kernel
- RISC-V ISA Manual，CC BY 4.0：https://github.com/riscv/riscv-isa-manual
- LVGL，MIT：https://github.com/lvgl/lvgl
- TinyUSB，MIT：https://github.com/hathach/tinyusb
- lwIP，BSD 3-Clause：https://github.com/lwip-tcpip/lwip
- Raspberry Pi Pico SDK，BSD 3-Clause：https://github.com/raspberrypi/pico-sdk
- Arm CMSIS 5 / CMSIS 6，Apache License 2.0：https://github.com/ARM-software/CMSIS_5 与 https://github.com/ARM-software/CMSIS_6
- Arm Mbed OS，Apache License 2.0：https://github.com/ARMmbed/mbed-os
- CppUTest，BSD 3-Clause：https://github.com/cpputest/cpputest
- Unity Test，MIT：https://github.com/ThrowTheSwitch/Unity

## Soybean Admin

- 用途：本项目管理端基于 Soybean Admin 进行二次开发与集成。
- 原项目：Soybean Admin
- 原项目地址：https://github.com/soybeanjs/soybean-admin
- 许可证：MIT License
- 本项目修改：已将其作为项目内管理端基础工程，并结合本项目登录入口、业务菜单和一键启动脚本完成集成。

MIT License 允许使用、复制、修改、合并、发布、分发、再授权和商业使用。使用时需保留原项目版权声明和许可证文本。本项目保留 `admin/LICENSE` 作为 Soybean Admin 的原始许可证文件。

## OnMyPPT / Oh My PPT

- 用途：本项目 PPT 生成功能参考 OnMyPPT / Oh My PPT 的功能思路与 H5 实现进行二次开发和平台集成。
- 原项目：OnMyPPT / Oh My PPT
- 许可证：Apache License 2.0
- 本项目修改：已将 PPT H5 能力接入主前端 `/ppt/` 与后端 `/api/ppt-h5/generate`，并按本项目绿色教育平台风格和业务流程进行适配。

Apache License 2.0 允许使用、修改、分发和商业使用。使用时需保留许可证文本、版权声明；如果原项目包含 `NOTICE` 文件，也应保留。本项目保留 `ppth5/LICENSE` 与 `ppth5/NOTICE`。

## Mind Map Wizard

- 用途：本项目思维导图生成功能使用 Mind Map Wizard 的 SVG 渲染、缩放、拖拽与节点交互能力。
- 原作者：Linus Schärli
- 原项目：https://github.com/Linus-sch/Mind-Map-Wizard
- 许可证：Creative Commons Attribution-NonCommercial 4.0 International License，简称 CC BY-NC 4.0
- 许可证地址：https://creativecommons.org/licenses/by-nc/4.0/
- 商业授权联系：contact@mindmapwizard.com
- 使用位置：`img/mind-map-wizard/embedded/renderer.js`、`interaction.js`、`mind-map-elements.css`
- 本项目修改：新增隔离嵌入页、`postMessage` 通信桥、Vue 工具栏和 Markdown/旧 Mermaid 兼容层；不包含原项目的模型 API、账号、分析统计和付费功能。

CC BY-NC 4.0 允许在非商业目的下分享、改编和使用，但必须署名、提供许可证链接，并说明是否进行了修改。该许可证包含 NonCommercial 限制，不允许未经授权的商业使用。若本项目后续用于商业化、收费 SaaS、企业交付或其他商业场景，应联系原作者获取商业授权。

## Vue Flow

- 用途：AI 视频工作台的可交互流程图、节点连线、画布背景和缩放控件。
- 原项目：https://github.com/bcakmakoglu/vue-flow
- 许可证：MIT License
- 集成位置：`frontend/package.json` 中的 `@vue-flow/core`、`@vue-flow/background` 与 `@vue-flow/controls`。
- 本项目修改：未修改依赖源码；根据本项目持久化视频任务状态生成节点、边、进度和详情面板。

MIT License 允许使用、复制、修改、合并、发布、分发、再授权和商业使用，发布时应保留原版权和许可证声明。

## 单片机实验台开源参考

以下仓库于 2026-07-15 通过 GitHub 项目信息核对。只有 Wokwi Elements 作为前端依赖直接进入构建产物；其余仓库用于实验主题、引脚行为和仿真边界核对，未复制其源码。

### Wokwi Elements

- 用途：Arduino Uno、LED、按键、传感器与显示器的浏览器电子元件外观。
- 原项目：https://github.com/wokwi/wokwi-elements
- 许可证：MIT License
- 集成位置：`frontend/package.json` 中的 `@wokwi/elements`。
- 本项目修改：未修改依赖源码；在 Vue 工作台外层实现端子合同、接线 SVG、状态联动和烧录校验。

### Arduino Examples

- 用途：GPIO、按键、PWM、ADC 和串口实验主题及基础代码结构参考。
- 原项目：https://github.com/arduino/arduino-examples
- 许可证：CC0-1.0
- 集成方式：参考实验原理并重新编写教学预设，未复制仓库源码目录。

### AVR8js

- 用途：ATmega328P 指令级仿真架构和浏览器仿真边界参考。
- 原项目：https://github.com/wokwi/avr8js
- 许可证：MIT License
- 集成方式：当前未把 AVR8js 执行内核打包进产品；实验台明确标记为教学解释器，避免把浏览器状态联动表述成真实 AVR 指令级执行。

### Learn 8051 / emu8051

- 用途：MCS-51 汇编实验组织、RAM/堆栈/端口行为和指令级模拟器边界核对。
- 原项目：https://github.com/kopytjuk/learn-8051
- 原项目：https://github.com/jarikomppa/emu8051
- 许可证：两个仓库均为 MIT License。
- 集成方式：用于原理与测试案例参考，未复制其源文件；当前页面仅支持声明的教学指令子集。

## 展示与分发合规说明

本项目用于比赛、课程展示、评审或其他分发场景时，应在 README、答辩文档或项目说明中明确：

- 管理端基于 Soybean Admin 二次开发。
- PPT 生成功能参考 OnMyPPT / Oh My PPT 并按 Apache License 2.0 保留许可说明。
- 思维导图功能参考 Mind Map Wizard，并遵守 CC BY-NC 4.0 的署名和非商业限制。

不得删除第三方项目的版权声明和许可证文本，也不得暗示原作者或原项目对本项目进行了官方背书。

## Mobile PWA dependencies

The independent `mobile/` frontend uses the following open-source packages in addition to the Vue, Vite, Axios, and Lucide dependencies already used by the learner frontend:

- DOMPurify, Mozilla Public License 2.0 or Apache License 2.0, for sanitizing generated HTML and SVG before rendering.
- marked, MIT License, for Markdown parsing.
- vite-plugin-pwa, MIT License, for the scoped `/m/` web app manifest and service worker build.
- Playwright, Apache License 2.0, and Vitest, MIT License, for mobile viewport and component regression tests.

These packages do not provide or embed model credentials, user data, generated resources, or third-party learning content.

## TvT.js / three-vue-tres / networkLinkTopology

- 用途：`/agent-digital-twin` 智能体数字孪生架构展示页的 Three.js 场景、模型、节点底座、信息流连线与大屏组件。
- 上游项目：https://github.com/hawk86104/three-vue-tres
- 场景来源：https://www.icegl.cn/tvtstore/networkLinkTopology.html
- 集成位置：`img/digital-twin`
- 授权边界：本项目使用的静态包由用户提供，用户确认已购买相应商业授权。此处不将该素材声明为 Apache-2.0、MIT 或其他未核实的开源许可证；再分发、商业使用和二次授权应继续遵守购买时取得的授权条款。
- 本项目修改：载入用户编辑的 `lData.json`，调整项目标题、节点标签、展示节点与连线，并通过 Vue `iframe` 同源集成。该页面只作架构展示，不宣称实时智能体调用，也不将展示节点计入 Harness 智能体数量。

## Mobile layout references and Android packaging

- Ionic Conference App (`ionic-team/ionic-conference-app`), MIT License: bottom-tab and grouped schedule layout reference only.
- Moodle App (`moodlehq/moodleapp`), Apache License 2.0: timeline, course hierarchy, loading, and profile-list interaction reference only.
- Ant Design Mobile (`ant-design/ant-design-mobile`), MIT License: compact mobile information hierarchy reference only.
- Vant (`youzan/vant`), MIT License: Vue mobile form, status, and list pattern reference only.
- Capacitor Core, CLI, and Android (`ionic-team/capacitor`), MIT License: native Android WebView shell and build integration.

No source code, visual assets, user data, or business logic was copied from the four layout-reference applications or component libraries. The mobile pages were implemented in the project's existing Vue component system and use original Image2-generated concept drafts.
