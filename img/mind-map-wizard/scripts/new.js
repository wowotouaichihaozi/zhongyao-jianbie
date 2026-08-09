// ===== API 配置 =====
const API_BASE_URL = window.API_BASE_URL || '/api/llm/messages';
const API_MODEL = window.API_MODEL || '平台配置模型';
// ====================

let currentMindmapTopic = '';
let generationInProgress = false;

const LEARNING_PATH_NODE_CACHE_STORAGE_KEY = 'qianzhi-learning-path-node-results:v1';

function getLearningPathNodeContext() {
	const params = new URLSearchParams(window.location.search);
	return {
		cacheKey: (params.get('cacheKey') || '').trim(),
		stageId: (params.get('stageId') || '').trim(),
		nodeId: (params.get('nodeId') || '').trim(),
		source: (params.get('source') || '').trim(),
		topic: (params.get('topic') || params.get('keyword') || params.get('q') || '').trim(),
		restore: (params.get('restore') || params.get('cached') || '').trim() === '1'
	};
}

function readLearningPathNodeCaches() {
	try {
		const parsed = JSON.parse(localStorage.getItem(LEARNING_PATH_NODE_CACHE_STORAGE_KEY) || '{}');
		return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
	} catch {
		return {};
	}
}

function extractMindmapTitle(mindmapJsonStr, fallback = 'STM32 思维导图') {
	try {
		const parsed = JSON.parse(mindmapJsonStr);
		const root = parsed?.['mm-node'] || parsed?.mmNode || parsed;
		const title = String(root?.content || '').replace(/\*|~~/g, '').trim();
		return title || fallback;
	} catch {
		return fallback;
	}
}

function buildLearningPathMindmapRoute(mindmapId) {
	const params = new URLSearchParams(window.location.search);
	params.delete('q');
	params.set('id', String(mindmapId));
	return `${window.location.pathname}?${params.toString()}`;
}

function writeLearningPathMindmapCache(patch) {
	const context = getLearningPathNodeContext();
	if (!context.cacheKey) return null;
	const caches = readLearningPathNodeCaches();
	const previous = caches[context.cacheKey] || {};
	const entry = {
		...previous,
		...patch,
		cacheKey: context.cacheKey,
		source: context.source || previous.source || 'learning-path',
		stageId: context.stageId || previous.stageId || '',
		nodeId: context.nodeId || previous.nodeId || '',
		resourceType: 'mindmap',
		topic: context.topic || previous.topic || '',
		restoredFromCache: context.restore || previous.restoredFromCache || false,
		createdAt: previous.createdAt || Date.now(),
		updatedAt: Date.now()
	};
	caches[context.cacheKey] = entry;
	try {
		localStorage.setItem(LEARNING_PATH_NODE_CACHE_STORAGE_KEY, JSON.stringify(caches));
		if (window.parent && window.parent !== window) {
			window.parent.postMessage(
				{ type: 'learning-path-node-cache-updated', cacheKey: context.cacheKey, entry },
				window.location.origin
			);
		}
	} catch { }
	return entry;
}

function restoreLearningPathMindmapFromCache(id) {
	const context = getLearningPathNodeContext();
	if (!context.cacheKey || !id) return false;
	const cache = readLearningPathNodeCaches()[context.cacheKey];
	const mindmapJson = cache?.mindmapJson;
	if (!mindmapJson || String(cache?.mindmapId || '') !== String(id)) return false;
	try {
		const history = JSON.parse(localStorage.getItem('mindmap-history') || '[]');
		const index = history.findIndex(item => String(item.id) === String(id));
		const item = {
			id,
			timestamp: cache.completedAt || cache.updatedAt || new Date().toISOString(),
			mindmap: mindmapJson
		};
		if (index >= 0) history[index] = { ...history[index], ...item };
		else history.push(item);
		localStorage.setItem('mindmap-history', JSON.stringify(history.slice(-100)));
		return true;
	} catch {
		return false;
	}
}

function markLearningPathMindmapComplete(mindmapId, mindmapJsonStr) {
	if (!mindmapId || !mindmapJsonStr) return;
	const title = extractMindmapTitle(mindmapJsonStr, getLearningPathNodeContext().topic || 'STM32 思维导图');
	writeLearningPathMindmapCache({
		status: 'complete',
		title,
		mindmapId: String(mindmapId),
		mindmapJson: mindmapJsonStr,
		route: buildLearningPathMindmapRoute(mindmapId),
		completedAt: new Date().toISOString(),
		lastOpenedAt: Date.now()
	});
}

function getLearningPathMindmapTemplate(context, rawQuery = '') {
	const cacheKey = String(context?.cacheKey || '').trim();
	const topic = String(context?.topic || rawQuery || '').trim();
	const normalizedTopic = topic.replace(/\s+/g, '').toLowerCase();
	const isWeekOneStm32Map = cacheKey === 'week1-stm32-mind-map'
		|| normalizedTopic.includes('stm32基础思维导图')
		|| normalizedTopic.includes('stm32基础');

	if (!isWeekOneStm32Map) return '';

	return `# STM32 基础思维导图

## 开发环境
### STM32CubeIDE：工程创建、编译、烧录、调试一体化
### Keil MDK：常见课程环境，关注芯片包、启动文件、下载配置
### ST-Link：连接 SWDIO、SWCLK、GND，确认驱动和目标芯片识别
### 工程目录：Core、Drivers、Startup、Linker Script

## 芯片与最小系统
### Cortex-M 内核：寄存器、异常、中断向量表
### Flash：保存程序代码，上电后从复位向量启动
### SRAM：保存运行时变量、栈和堆
### 时钟源：HSI、HSE、PLL 决定系统运行频率

## GPIO 输入输出
### 输出模式：推挽输出控制 LED、蜂鸣器等外设
### 输入模式：上拉、下拉、浮空输入读取按键状态
### 关键参数：端口、引脚、模式、速度、上下拉
### HAL 常用函数：HAL_GPIO_WritePin、HAL_GPIO_ReadPin、HAL_GPIO_TogglePin

## 时钟与初始化流程
### SystemClock_Config：配置系统时钟树和总线分频
### MX_GPIO_Init：打开端口时钟并初始化引脚
### HAL_Init：初始化 SysTick、NVIC 和 HAL 基础状态
### main 循环：初始化一次，while(1) 中持续执行任务

## 中断入门
### EXTI 外部中断：按键触发边沿检测
### NVIC：设置中断优先级并使能中断通道
### 回调函数：HAL_GPIO_EXTI_Callback 中处理业务逻辑
### 注意事项：中断内少做耗时操作，必要时置标志位到主循环处理

## 调试与验证
### 断点：观察程序是否进入目标分支
### Watch 窗口：查看变量、寄存器和引脚状态
### 串口日志：输出初始化结果和关键状态
### 现象记录：截图、接线图、代码片段和错误原因

## 第一周产出
### 能说清 STM32 工程从上电到 main 的启动流程
### 能完成 LED 闪烁或按键控制 LED 的最小实验
### 能整理 GPIO、时钟、中断之间的关系
### 能列出 3 个常见错误：未开时钟、引脚选错、下载器连接异常`;
}

document.addEventListener('DOMContentLoaded', function () {
	// 暴露 API 配置到全局作用域
	window.API_BASE_URL = API_BASE_URL;
	window.API_MODEL = window.API_MODEL || API_MODEL;

	initializeAiDisableToggle();
	initializeModelSelector();
});

function initializeAiDisableToggle() {
	if (window.__mmwAiDisableToggleInit) return;
	window.__mmwAiDisableToggleInit = true;

	const stored = localStorage.getItem('mmw-disable-ai-features');
	const isDisabled = stored === 'true';
	window.MMW_DISABLE_AI_FEATURES = isDisabled;

	const disableButton = document.getElementById('disable-ai-button');
	const disableToggle = document.getElementById('disable-ai-toggle');
	if (disableButton) {
		disableButton.addEventListener('click', (event) => {
			if (event.target && event.target.closest('#disable-ai-toggle')) {
				return;
			}
			event.preventDefault();
			if (!disableToggle) return;
			disableToggle.checked = !disableToggle.checked;
			const nextEnabled = disableToggle.checked;
			window.MMW_DISABLE_AI_FEATURES = !nextEnabled;
			localStorage.setItem('mmw-disable-ai-features', String(!nextEnabled));
			updateAiFeaturesUI();
		});
	}
	if (disableToggle) {
		disableToggle.addEventListener('change', () => {
			const nextEnabled = disableToggle.checked;
			window.MMW_DISABLE_AI_FEATURES = !nextEnabled;
			localStorage.setItem('mmw-disable-ai-features', String(!nextEnabled));
			updateAiFeaturesUI();
		});
	}

	updateAiFeaturesUI();
}

function updateAiFeaturesUI() {
	const isDisabled = Boolean(window.MMW_DISABLE_AI_FEATURES);
	const disableButton = document.getElementById('disable-ai-button');
	const disableToggle = document.getElementById('disable-ai-toggle');
	if (disableButton) {
		disableButton.classList.remove('active');
	}
	if (disableToggle) {
		disableToggle.checked = !isDisabled;
	}

	const regenerateBtn = document.getElementById('regenerate-button');
	if (regenerateBtn) {
		regenerateBtn.style.display = isDisabled ? 'none' : '';
	}

	const modelDropdown = document.querySelector('.model-selector-container');
	if (modelDropdown) {
		modelDropdown.style.display = isDisabled ? 'none' : '';
	}

	const prompt = document.getElementById('prompt');
	if (prompt) {
		prompt.placeholder = isDisabled ? '输入您的主题（手动思维导图）' : '输入文本或URL...';
	}
}

window.toggleAiFeatures = function () {
	const next = !window.MMW_DISABLE_AI_FEATURES;
	window.MMW_DISABLE_AI_FEATURES = next;
	localStorage.setItem('mmw-disable-ai-features', String(next));
	updateAiFeaturesUI();
};

async function initializeModelSelector() {
	const runtime = typeof window.loadLlmRuntime === 'function'
		? await window.loadLlmRuntime()
		: (window.LLM_RUNTIME || {});
	const currentModelName = document.getElementById('current-model-name');
	if (currentModelName) {
		currentModelName.textContent = runtime.model || window.API_MODEL || API_MODEL;
	}
}

function extractContextUrlsFromBackend(data) {
	try {
		const urls = [];

		const pushMaybeUrl = (v) => {
			if (!v) return;
			if (typeof v === 'string') {
				urls.push(v);
				return;
			}
			if (typeof v === 'object') {
				const u = v.url || v.href || v.link;
				if (typeof u === 'string') urls.push(u);
			}
		};

		if (Array.isArray(data?.contexturls)) data.contexturls.forEach(pushMaybeUrl);
		if (Array.isArray(data?.contextUrls)) data.contextUrls.forEach(pushMaybeUrl);

		if (Array.isArray(data?.context?.urls)) data.context.urls.forEach(pushMaybeUrl);
		if (Array.isArray(data?.context?.links)) data.context.links.forEach(pushMaybeUrl);

		if (Array.isArray(data?.tags)) {
			for (const tag of data.tags) {
				if (typeof tag !== 'string') continue;
				const str = tag.trim();
				if (!str) continue;

				const re = /<url>\s*([\s\S]*?)\s*<\/url>/gi;
				let m;
				while ((m = re.exec(str)) !== null) {
					const u = String(m[1] || '').trim();
					if (u) urls.push(u);
				}

				if (!str.includes('<url>') && /^https?:\/\//i.test(str)) {
					urls.push(str);
				}
			}
		}

		// Extract URL citations from compatible provider annotations.
		if (Array.isArray(data?.choices?.[0]?.message?.annotations)) {
			for (const annotation of data.choices[0].message.annotations) {
				if (annotation.type === 'url_citation' && annotation.url_citation?.url) {
					urls.push(annotation.url_citation.url);
				}
			}
		}

		return normalizeContextUrls(urls);
	} catch {
		return [];
	}
}

function normalizeContextUrls(input) {
	const arr = Array.isArray(input) ? input : (input ? [input] : []);
	const out = [];
	for (const item of arr) {
		if (typeof item !== 'string') continue;
		let u = item.trim();
		if (!u) continue;

		u = u.replace(/^<url>\s*/i, '').replace(/\s*<\/url>$/i, '').trim();
		u = u.replace(/^['"\(\[]+/, '').replace(/['"\)\]]+$/, '').trim();
		u = u.replace(/[\s\]\)\}\>"'.,;:!?]+$/g, '').trim();
		if (!/^https?:\/\//i.test(u)) continue;

		try {
			const parsed = new URL(u);
			if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
				out.push(u);
			}
		} catch {
		}
	}
	return Array.from(new Set(out));
}

async function generateMindmap(mindmapTopic, isRegenerate = false) {
	if (generationInProgress) {
		return;
	}

	if (window.MMW_DISABLE_AI_FEATURES) {
		createManualMindMap();
		return;
	}

	if (!mindmapTopic) {
		console.error('Mindmap generation stopped: missing topic.');
		return;
	}

	generationInProgress = true;

	if (!isRegenerate) {
		document.getElementById('header').style.display = 'none';
		document.getElementById('mindmap').style.display = 'none';
	}
	const loadingAnim = document.getElementById('loading-animation');
	if (loadingAnim) loadingAnim.style.display = 'flex';

	if (isRegenerate) {
		const regenerateBtn = document.getElementById('regenerate-button');
		regenerateBtn?.classList.add('rotating');
	}

	currentMindmapTitle = mindmapTopic;
	document.getElementById('mindmap').style.display = 'block';

	try {
		const useWebSearch = false;
		const searchInstruction = '- Use only your internal knowledge (no web search)';

		const requestPayload = {
			messages: [
				{
					role: 'user',
					content: `Create a comprehensive, fact-rich mind map about ${mindmapTopic.trim()} using the following structure:

# Matching Mind Map Title
## Branch 1
### Sub Branch A
### Sub Branch B
## Branch 2

- Each text element must be aligned to a specific hierarchical level using a new line plus the appropriate number of # symbols
- Aim for 2-3 levels of depth to keep the mind map scannable and not overwhelming but keep lenght relative to input depth.
- For large enumerations (6+ items), combine related items into comma-separated lists within a single branch rather than creating excessive sub-branches

- Include **specific, concrete details and facts**, not just category labels
  - Bad: "## Education" 
  - Good: "## Education: PhD in Physics from MIT (2015)"
- Avoid generic structural sections like "Overview," "Introduction," or "Conclusion" this is a mind map, not an essay
- If the topic contains extensive information, prioritize breadth over depth and consolidate where necessary
- Focus on the most relevant and interesting information that creates a useful knowledge structure
- Make the branches have different lengths for making the mind map visually more interesting.
- The mind map should be in the language of the user input.
- The title should be as short as possible.
- The mind map should have at least 3 branches going out of the title node.
- Research Instruction: ${searchInstruction}

**Output Format:**
Structure your response exactly like this:
{
	"markdown": "# Main Topic\\n\\n## Subtopic 1\\n- Point A\\n- Point B\\n\\n## Subtopic 2\\n- Point C\\n- Point D"
}  
`
				}
			],
			max_completion_tokens: 2000,
			temperature: 0.7,
			response_format: { type: 'json_object', schema: 'mindmap_markdown', required: ['markdown'] },
			thinking: { type: 'disabled' }
		};

		const response = await window.callLlmChatCompletion(requestPayload);

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));

			if (response.status === 401) {
				throw new Error('模型服务鉴权失败，请检查嵌小智模型设置。');
			} else if (response.status === 429) {
				throw new Error('请求频率超限。请稍后再试。');
			} else if (response.status === 402) {
				throw new Error('余额不足。请检查您的账户余额。');
			} else {
				throw new Error(errorData.error?.message || `API error: ${response.status}`);
			}
		}

		const data = await response.json();

		if (!data.choices || !data.choices[0] || !data.choices[0].message) {
			throw new Error('API 响应无效');
		}

		let parsedContent;
		try {
			const content = data.choices[0].message.content.trim();
			const jsonMatch = content.match(/\{[^]*"markdown"[^]*\}/);

			if (jsonMatch) {
				let jsonContent = jsonMatch[0];
				try {
					parsedContent = JSON.parse(jsonContent);
				} catch (jsonError) {
					const markdownMatch = jsonContent.match(/"markdown"\s*:\s*"([^]*?)"\s*\}/);
					if (markdownMatch) {
						let markdownContent = markdownMatch[1]
							.replace(/\\n/g, '\n')
							.replace(/\\r/g, '\r')
							.replace(/\\t/g, '\t')
							.replace(/\\"/g, '"')
							.replace(/\\\\/g, '\\');
						parsedContent = { markdown: markdownContent };
					} else {
						throw jsonError;
					}
				}
			} else {
				parsedContent = { markdown: content };
			}
		} catch (parseError) {
			console.error('Failed to parse API response as JSON:', parseError);
			console.error('Raw content:', data.choices[0].message.content);
			throw new Error('来自 API 的响应格式无效');
		}

		if (!parsedContent.markdown) {
			throw new Error('来自 API 的响应无效：缺少必要的 markdown 字段');
		}

		const topic = parsedContent.topic || mindmapTopic;
		const markdown = parsedContent.markdown;

		if (!markdown || typeof markdown !== 'string' || markdown.trim().length === 0) {
			throw new Error('生成的内容为空或无效');
		}

		const sanitizedMarkdown = markdown
			.replace(/<script[^>]*>.*?<\/script>/gi, '')
			.replace(/javascript:/gi, '')
			.replace(/on\w+\s*=/gi, '')
			.trim();

		if (sanitizedMarkdown.length === 0) {
			throw new Error('生成的内容未通过安全验证');
		}

		const responseData = {
			topic: topic,
			raw: sanitizedMarkdown
		};

		const { topic: finalTopic, markdown: finalMarkdown } = formatMarkdown(responseData);
		const contextUrls = useWebSearch ? extractContextUrlsFromBackend(data) : [];

		if (finalMarkdown) {
			await window.renderMindmap(finalMarkdown, {
				...(contextUrls.length ? { contextUrls } : {}),
				playPopAnimation: true
			});
			try {
				await fetch(
				'https://stats.mindmapwizard.com/hit/mmw-os/mind-map-generated', {
				method: 'GET',
				});
			} catch (trackingError) {
				console.error('Tracking Error:', trackingError);
			}
			let mmjsonStr = '';
			try {
				const ed = document.getElementById('json-editor');
				mmjsonStr = ed?.value || localStorage.getItem('json-mindmap-content') || '';
			} catch { }

			if (!mmjsonStr || !mmjsonStr.trim().startsWith('{')) {
				const fallback = {
					"mm-settings": { "spacing": 30, "border-radius": 4 },
					"mm-node": { "content": finalTopic || mindmapTopic, "children": [] }
				};
				mmjsonStr = JSON.stringify(fallback);
			}

			let mindmapId;
			if (!isRegenerate) {
				mindmapId = saveMindmapToHistory(mmjsonStr);
			} else {
				const urlObj = new URL(window.location);
				const existingId = urlObj.searchParams.get('id');
				if (existingId) {
					const history = JSON.parse(localStorage.getItem('mindmap-history') || '[]');
					const idx = history.findIndex(it => String(it.id) === String(existingId));
					if (idx >= 0) {
						history[idx].mindmap = mmjsonStr;
						history[idx].timestamp = new Date().toISOString();
						localStorage.setItem('mindmap-history', JSON.stringify(history));
						if (typeof loadMindmapsLeftSidebar === 'function') { loadMindmapsLeftSidebar(); }
						mindmapId = history[idx].id;
					} else {
						mindmapId = saveMindmapToHistory(mmjsonStr);
					}
				} else {
					mindmapId = saveMindmapToHistory(mmjsonStr);
				}
			}

			const navLinks = document.querySelector('.nav-links');
			if (navLinks) {
				navLinks.classList.add('padding-right');
			}

			currentMindmapTitle = (function () {
				try {
					const o = JSON.parse(mmjsonStr);
					const r = o['mm-node'] || o.mmNode || o;
					const t = String(r?.content || '').trim();
					return t || (finalTopic || mindmapTopic);
				} catch { return finalTopic || mindmapTopic; }
			})();

			const url = new URL(window.location);
			if (url.searchParams.has('q')) {
				url.searchParams.delete('q');
			}
			if (mindmapId) {
				url.searchParams.set('id', mindmapId);
			}
			window.history.replaceState({}, '', url.toString());
		} else {
			throw new Error('处理后生成的 markdown 内容为空或无效。');
		}

		if (loadingAnim) loadingAnim.style.display = 'none';
		document.getElementById('button-container').style.display = 'flex';

		if (isRegenerate) {
			const regenerateBtn = document.getElementById('regenerate-button');
			regenerateBtn?.classList.remove('rotating');
		}

		if (window.innerWidth > 885) {
			document.getElementById('chat-toggle-btn')?.click();
		}

	} catch (error) {
		console.error('Error generating the mindmap:', error);

		let userMessage = '生成思维导图时发生错误。';
		let shouldShowError = true;

		if (error.message.includes('Rate limit')) {
			userMessage = '请求过多。请稍等片刻后重试。';
		} else if (error.message.includes('network') || error.message.includes('fetch')) {
			userMessage = '网络错误。请检查您的连接并重试。';
		} else if (error.message.includes('security')) {
			userMessage = '内容验证失败。请尝试其他主题。';
		}

		if (shouldShowError) {
			showErrorPopup(userMessage, mindmapTopic);
		}

		if (loadingAnim) loadingAnim.style.display = 'none';

		if (isRegenerate) {
			const regenerateBtn = document.getElementById('regenerate-button');
			regenerateBtn?.classList.remove('rotating');
		}

	} finally {
		generationInProgress = false;
		hideHeader();
	}
}


async function expandMindMapNodeCore() {
	if (!window.currentNodeElement) return;
	if (window.MMW_DISABLE_AI_FEATURES) return;

	try {
		const contextMenus = document.querySelectorAll('.context-menu');
		contextMenus.forEach(menu => menu.remove());

		const nodeEl = window.currentNodeElement;
		const nodeId = nodeEl.getAttribute('data-node-id');
		const textElement = nodeEl.querySelector('text');
		const nodeText = textElement ? textElement.textContent : '';

		if (!nodeId || !nodeText) return;

		const loader = document.getElementById('node-expand-loader');
		if (loader) loader.classList.add('active');
		const ratingPopup = document.getElementById('ratingPopup');
		if (ratingPopup) {
			ratingPopup.classList.remove('show');
		}

		let branchContext = '';
		if (window.getBranchContext) {
			branchContext = window.getBranchContext(nodeId);
		}

		try {
			const systemPrompt = `You are a helpful assistant that expands specific topics within a mind map. 
The user will provide the relevant Context (the path leading to the current node to expand).

Your task is to generate detailed child branches for the provided node based on the context.

Rules:
1. Output MUST be valid Markdown.
2. The "Target Node" string must be the Root of your response (Level 1 Header '#') and you can rename it if you want.
3. The new children must be Level 2 Headers ('##') which can have Level 3 children ('###').
4. You should not generate more than 5 new mind map elements (children across all levels).
5. Provide detailed, factual, and concrete sub-branches.
6. The generated content should be in the same language as the context.
Context: ${branchContext}`;

			const requestPayload = {
				messages: [
					{ role: 'system', content: systemPrompt },
					{
						role: 'user',
						content: `Target Node: ${nodeText}\n\nContext:\n${branchContext}`
					}
				],
				max_completion_tokens: 1200,
				temperature: 0.5,
				thinking: { type: 'disabled' }
			};

			const response = await window.callLlmChatCompletion(requestPayload);

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.error || errorData.message || `Backend error with status: ${response.status}`);
			}

			const data = await response.json();

			if (!data.choices || !data.choices[0] || !data.choices[0].message) {
				throw new Error('API 响应无效');
			}

			let parsedContent;
			try {
				const content = data.choices[0].message.content.trim();
				const jsonMatch = content.match(/\{[^]*"markdown"[^]*\}/);

				if (jsonMatch) {
					let jsonContent = jsonMatch[0];
					try {
						parsedContent = JSON.parse(jsonContent);
					} catch (jsonError) {
						const markdownMatch = jsonContent.match(/"markdown"\s*:\s*"([^]*?)"\s*\}/);
						if (markdownMatch) {
							let markdownContent = markdownMatch[1]
								.replace(/\\n/g, '\n')
								.replace(/\\r/g, '\r')
								.replace(/\\t/g, '\t')
								.replace(/\\"/g, '"')
								.replace(/\\\\/g, '\\');
							parsedContent = { markdown: markdownContent };
						} else {
							throw jsonError;
						}
					}
				} else {
					parsedContent = { markdown: content };
				}
			} catch (parseError) {
				console.error('Failed to parse API response as JSON:', parseError);
				console.error('Raw content:', data.choices[0].message.content);
				throw new Error('来自 API 的响应格式无效');
			}

			const markdown = parsedContent?.markdown;

			if (markdown && window.replaceNodeChildren) {
				const oldChildren = window.replaceNodeChildren(nodeId, markdown);
				if (loader) loader.classList.remove('active');
				window.expandNodeChildren(nodeId);

				try {
					await fetch(
					'https://stats.mindmapwizard.com/hit/mmw-os/mind-map-expanded', {
					method: 'GET',
					});
				} catch (trackingError) {
					console.error('Tracking Error:', trackingError);
				}

				if (oldChildren) {
					const existingRevertContainer = document.getElementById('revert-changes-container');

					if (existingRevertContainer) {
						const revertContainer = existingRevertContainer.cloneNode(true);
						existingRevertContainer.parentNode.replaceChild(revertContainer, existingRevertContainer);

						const revertTimer = revertContainer.querySelector('#revert-timer');

						revertContainer.classList.add('active');
						let timeLeft = 10;
						if (revertTimer) revertTimer.textContent = timeLeft;

						const timerInterval = setInterval(() => {
							timeLeft--;
							if (revertTimer) revertTimer.textContent = timeLeft;
							if (timeLeft <= 0) {
								clearInterval(timerInterval);
								revertContainer.classList.remove('active');
							}
						}, 1000);

						revertContainer.onclick = () => {
							clearInterval(timerInterval);
							revertContainer.classList.remove('active');
							if (window.restoreNodeChildren) {
								window.restoreNodeChildren(nodeId, oldChildren);
							}
						};
					}
				}
			} else {
				throw new Error('来自扩展服务的响应无效');
			}

		} catch (error) {
			console.error('Failed to expand node:', error);
			if (loader) loader.classList.remove('active');
			showInfoSnackbar('扩展节点失败：' + error.message);
		}

	} catch (error) {
		console.error('Error in expandMindMapNode:', error);
		const loader = document.getElementById('node-expand-loader');
		if (loader) loader.classList.remove('active');
	}
}

function initiateGenerationProcess(providedTopic) {
	if (generationInProgress) {
		return;
	}

	const mindmapTopic = providedTopic || document.getElementById('prompt')?.value.trim();
	if (!mindmapTopic) {
		return;
	}

	const headerLines = mindmapTopic.split('\n').filter(line => line.trim().startsWith('#'));
	if (headerLines.length > 6) {
		createLocalMindMapFromMarkdown(mindmapTopic)
			.catch(error => {
				console.error('Error during local mindmap generation:', error);
			});
		return;
	}

	if (window.MMW_DISABLE_AI_FEATURES) {
		createManualMindMap();
		return;
	}

	currentMindmapTopic = mindmapTopic;

	document.getElementById('header').style.display = 'none';
	generateMindmap(mindmapTopic, false);
}

function initializeMainButtons() {
	if (window.mainButtonsInitialized) {
		return;
	}
	window.mainButtonsInitialized = true;

	const prompt = document.getElementById('prompt');
	const generateBtn = document.getElementById('generate-mindmap-btn');
	const regenerateBtn = document.getElementById('regenerate-button');

	generateBtn?.addEventListener('click', (e) => {
		if (e) e.preventDefault();
		initiateGenerationProcess();
	});

	regenerateBtn?.addEventListener('click', function (e) {
		if (e) e.preventDefault();
		if (window.MMW_DISABLE_AI_FEATURES) {
			createManualMindMap();
			return;
		}
		const promptValue = document.getElementById('prompt')?.value?.trim();
		if (promptValue) {
			generateMindmap(promptValue, true);
		} else if (currentMindmapTitle) {
			generateMindmap(currentMindmapTitle, true);
		} else {
			initiateGenerationProcess();
		}
	});

	const shadowPrompt = document.createElement('textarea');
	shadowPrompt.style.position = 'absolute';
	shadowPrompt.style.top = '-9999px';
	shadowPrompt.style.left = '-9999px';
	shadowPrompt.style.visibility = 'hidden';
	shadowPrompt.style.height = 'auto';
	shadowPrompt.style.overflow = 'hidden';
	shadowPrompt.setAttribute('rows', '1');
	document.body.appendChild(shadowPrompt);

	const syncShadowStyles = () => {
		const styles = window.getComputedStyle(prompt);
		shadowPrompt.style.width = styles.width;
		shadowPrompt.style.fontFamily = styles.fontFamily;
		shadowPrompt.style.fontSize = styles.fontSize;
		shadowPrompt.style.lineHeight = styles.lineHeight;
		shadowPrompt.style.padding = styles.padding;
		shadowPrompt.style.boxSizing = styles.boxSizing;
		shadowPrompt.style.border = styles.border;
	};

	const adjustHeight = () => {
		syncShadowStyles();
		shadowPrompt.value = prompt.value;

		shadowPrompt.style.height = 'auto';
		const newHeight = shadowPrompt.scrollHeight;

		prompt.style.height = newHeight + 'px';

		if (newHeight > 160) {
			prompt.style.overflowY = 'auto';
		} else {
			prompt.style.overflowY = 'hidden';
		}
	};

	prompt?.addEventListener('input', adjustHeight);
	window.addEventListener('resize', adjustHeight);

	if (prompt) {
		setTimeout(() => {
			adjustHeight();
		}, 0);
	}

	prompt?.addEventListener('keydown', function (event) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			initiateGenerationProcess();
			if (prompt) {
				prompt.value = '';
				adjustHeight();
			}
		}
	});
}


function closeLeftSidebar() {
	try {
		const leftSidebar = document.getElementById('leftSidebar');
		const app = document.getElementById('app');
		const mindmap = document.getElementById('mindmap');
		const menubar = document.getElementById('menubar');
		const undoRedoContainer = document.getElementById('undo-redo-container');

		if (leftSidebar) leftSidebar.classList.remove('open');
		if (app) app.classList.remove('left-sidebar-open');
		if (mindmap) mindmap.classList.remove('left-sidebar-open');
		if (menubar) menubar.classList.remove('sidebar-open');
		document.documentElement.classList.remove('left-sidebar-open');
		if (undoRedoContainer) undoRedoContainer.classList.remove('left-sidebar-open');
		localStorage.setItem('left-sidebar-state', 'closed');
	} catch (e) {
		console.warn('closeLeftSidebar failed:', e);
	}
}

function showHeader() {
	const buttonContainer = document.getElementById('button-container');
	if (buttonContainer) {
		buttonContainer.style.display = 'none';
	}

	const inAppErrorMessage = document.getElementById('inAppErrorMessage');
	if (inAppErrorMessage) {
		inAppErrorMessage.style.display = 'none';
	}

	const app = document.getElementById('app');
	if (app) {
		app.style.display = 'block';
	}

	const mindmapElement = document.getElementById('mindmap');
	if (mindmapElement) {
		mindmapElement.style.display = 'none';
	}

	const headerElement = document.getElementById('header');
	if (headerElement) {
		headerElement.style.display = 'block'
		setTimeout(() => {
			headerElement.classList.add('active');
		}, 10);
	}

	const toolbarElement = document.querySelector('.mm-toolbar');
	if (toolbarElement) {
		toolbarElement.style.display = 'none';
	}

	const navLinks = document.getElementById('nav-links');
	if (navLinks) {
		navLinks.classList.remove('padding-right');
	}

	if (window.innerWidth > 770) {
		document.getElementById('prompt')?.focus();
	}

	if (window.innerWidth < 770) {
		closeLeftSidebar();
	}

	const zoomControls = document.getElementById('zoom-controls');
	if (zoomControls) {
		zoomControls.classList.remove('show');
	}

	const undoRedoContainer = document.getElementById('undo-redo-container');
	if (undoRedoContainer) {
		undoRedoContainer.style.display = 'none';
	}

	if (window.chatManager) {
		if (window.chatManager.isOpen) {
			window.chatManager.toggle(false);
		}
		window.chatManager.reset();
	}

	closeNotesDrawer();
	removeUrlParameter('id');

	document.querySelectorAll('.mindmap-item').forEach((item) => {
		item.classList.remove('active');
	});
}

window.addEventListener("resize", updateSignUpButton);
function updateSignUpButton() {
	const signUpButton = document.querySelector(".sign-up-button");
	if (!signUpButton) return;
	if (window.innerWidth <= 435) {
		signUpButton.textContent = "注册";
	} else {
		signUpButton.textContent = "注册";
	}
}

(function () {
	let __mmwEnginePromise = null;

	function __mmwLoadScript(src) {
		return new Promise((resolve, reject) => {
			const s = document.createElement('script');
			s.src = src;
			s.async = true;
			s.onload = () => resolve();
			s.onerror = (e) => reject(new Error('Failed to load ' + src));
			document.head.appendChild(s);
		});
	}

	function __mmwDefaultSettings() {
		return {
			"spacing": 30,
			"border-radius": 4
		};
	}

	function __mmwEnsureEngineDom() {
		const mindmap = document.getElementById('mindmap');
		if (!mindmap) return;

		let svgOut = document.getElementById('svg-output');
		if (!svgOut) {
			svgOut = document.createElement('div');
			svgOut.id = 'svg-output';
			svgOut.style.width = '100%';
			svgOut.style.height = '100%';
			mindmap.innerHTML = '';
			mindmap.appendChild(svgOut);
		}

		let editor = document.getElementById('json-editor');
		if (!editor) {
			editor = document.createElement('textarea');
			editor.id = 'json-editor';
			editor.style.display = 'none';
			document.body.appendChild(editor);
		}

		const stubDefs = [
			{ id: 'slider', tag: 'div' },
			{ id: 'editor-container', tag: 'div' },
			{ id: 'app-container', tag: 'div' },
			{ id: 'zoom-in-btn', tag: 'button' },
			{ id: 'zoom-out-btn', tag: 'button' },
			{ id: 'fit-screen-btn', tag: 'button' },
			{ id: 'edit-json-btn', tag: 'button' }
		];
		stubDefs.forEach(({ id, tag }) => {
			if (!document.getElementById(id)) {
				const el = document.createElement(tag);
				el.id = id;
				el.style.display = 'none';
				document.body.appendChild(el);
			}
		});
	}

	function __mmwDebounce(fn, ms) {
		let t = null;
		return function () {
			const self = this;
			const args = arguments;
			clearTimeout(t);
			t = setTimeout(() => fn.apply(self, args), ms);
		};
	}

	function __mmwPlayMindmapPopAnimation() {
		requestAnimationFrame(() => {
			const svgEl = document.querySelector('#svg-output svg');
			if (!svgEl) return;

			svgEl.classList.remove('appearing');
			void svgEl.getBoundingClientRect();
			svgEl.classList.add('appearing');

			const stageEl = svgEl.querySelector('.mm-stage');
			const cleanup = () => svgEl.classList.remove('appearing');
			if (stageEl) {
				stageEl.addEventListener('animationend', cleanup, { once: true });
			}
			setTimeout(cleanup, 700);
		});
	}

	window.__mmwPlayMindmapPopAnimation = __mmwPlayMindmapPopAnimation;

	function __mmwAutoSave() {
		try {
			const ed = document.getElementById('json-editor');
			if (!ed) return;
			const jsonStr = ed.value || '';

			window.currentMarkdown = jsonStr;

			let derivedTopic = '思维导图';
			try {
				const parsed = JSON.parse(jsonStr || '{}');
				const root = parsed['mm-node'] || parsed.mmNode || null;
				const rootContent = root ? String(root.content || '').trim() : '';
				if (rootContent) derivedTopic = rootContent;
			} catch { }

			const nowIso = new Date().toISOString();

			const url = new URL(location.href);
			const id = url.searchParams.get('id');

			if (!id) {
				return;
			}

			let history = [];
			try { history = JSON.parse(localStorage.getItem('mindmap-history') || '[]'); } catch { history = []; }

			const idx = history.findIndex(it => String(it.id) === String(id));
			if (idx >= 0) {
				if (history[idx].mindmap !== jsonStr) {
					history[idx].mindmap = jsonStr;
					history[idx].timestamp = nowIso;
					localStorage.setItem('mindmap-history', JSON.stringify(history));
					if (typeof loadMindmapsLeftSidebar === 'function') {
						loadMindmapsLeftSidebar();
					}
				}
				return;
			}
			try {
				const pgRaw = localStorage.getItem('mindmap-playground');
				if (!pgRaw) return;
				const pg = JSON.parse(pgRaw);
				if (pg && typeof pg === 'object' && String(pg.id) === String(id)) {
					if (pg.mindmap !== jsonStr) {
						pg.mindmap = jsonStr;
						pg.timestamp = nowIso;
						localStorage.setItem('mindmap-playground', JSON.stringify(pg));
					}
				}
			} catch { }
		} catch (e) {
			console.warn('Auto-save failed:', e);
		}
	}
	const __mmwAutoSaveDebounced = __mmwDebounce(__mmwAutoSave, 400);


	function __mmwMarkdownToJson(md) {
		const lines = String(md || '').split(/\r?\n/);

		let rootContent = '思维导图向导';
		let firstHeadingLevel = null;
		let firstHeadingIndex = -1;

		for (let i = 0; i < lines.length; i++) {
			const line = lines[i].trim();
			if (!line) continue;

			const m = line.match(/^(#{1,6})\s+(.*)$/);
			if (m) {
				rootContent = m[2].trim();
				firstHeadingLevel = m[1].length;
				firstHeadingIndex = i;
				break;
			}
		}

		const root = { content: rootContent, children: [] };
		const stack = [{ level: 1, node: root }];

		lines.forEach((raw, index) => {
			const line = raw.trim();
			if (!line) return;

			if (index === firstHeadingIndex) return;

			const m = line.match(/^(#{1,6})\s+(.*)$/);
			if (m) {
				const lvl = m[1].length;
				const text = m[2].trim();
				const node = { content: text, children: [] };
				while (stack.length && stack[stack.length - 1].level >= lvl) stack.pop();
				const parent = stack[stack.length - 1]?.node || root;
				parent.children.push(node);
				stack.push({ level: lvl, node });
				return;
			}

			const b = line.match(/^([-*+]|\d+\.)\s+(.*)$/);
			if (b) {
				const text = b[2].trim();
				const node = { content: text, children: [] };
				while (stack.length > 1 && stack[stack.length - 1].isBullet) {
					stack.pop();
				}
				const parent = stack[stack.length - 1]?.node || root;
				parent.children.push(node);
				return;
			}

			const node = { content: line, children: [] };
			const parent = stack[stack.length - 1]?.node || root;
			parent.children.push(node);
		});

		return {
			"mm-settings": __mmwDefaultSettings(),
			"mm-node": root
		};
	}

	function __mmwInitEngine() {
		if (__mmwEnginePromise) return __mmwEnginePromise;
		__mmwEnsureEngineDom();

		__mmwEnginePromise = __mmwLoadScript('/mind-map-wizard/scripts/mm-rendering/renderer.js')
			.then(() => __mmwLoadScript('/mind-map-wizard/scripts/mm-rendering/interaction.js'))
			.then(() => {
				try {
					if (!window.__mmwEngineBooted) {
						window.__mmwEngineBooted = true;
						if (document.readyState !== 'loading') {
							document.dispatchEvent(new Event('DOMContentLoaded'));
						}
					}
				} catch { }

				try {
					const ed = document.getElementById('json-editor');
					if (ed) ed.addEventListener('input', __mmwAutoSaveDebounced);
				} catch { }

				try {
					let __mmwLastSavedJson = null;
					setInterval(() => {
						try {
							const ed = document.getElementById('json-editor');
							if (!ed) return;
							const val = ed.value || '';
							if (val && val !== __mmwLastSavedJson) {
								__mmwLastSavedJson = val;
								__mmwAutoSaveDebounced();
							}
						} catch { }
					}, 1000);
				} catch { }
			})
			.catch((e) => {
				console.error('Failed to initialize MMW rendering engine:', e);
				throw e;
			});

		return __mmwEnginePromise;
	}

	window.__mmwInitEngine = __mmwInitEngine;
	window.renderMindmap = async function (input, options = {}) {
		try {
			await __mmwInitEngine();

			let dataObj = null;
			if (typeof input === 'string' && input.trim().startsWith('{')) {
				try { dataObj = JSON.parse(input); } catch { dataObj = null; }
			}
			if (!dataObj) {
				const md = typeof input === 'string' ? input : String(input ?? '');
				dataObj = __mmwMarkdownToJson(md);
			}

			if (!dataObj['mm-settings']) {
				dataObj['mm-settings'] = __mmwDefaultSettings();
			}

			const hasOptContext =
				options && (Object.prototype.hasOwnProperty.call(options, 'contextUrls') || Object.prototype.hasOwnProperty.call(options, 'contexturls'));
			if (hasOptContext) {
				const optContext = Object.prototype.hasOwnProperty.call(options, 'contextUrls')
					? options.contextUrls
					: options.contexturls;
				dataObj['mm-settings'] = dataObj['mm-settings'] || __mmwDefaultSettings();
				dataObj['mm-settings'].contextUrls = normalizeContextUrls(optContext);
			}

			const jsonStr = JSON.stringify(dataObj, null, 2);
			try { localStorage.setItem('json-mindmap-content', jsonStr); } catch { }

			const editor = document.getElementById('json-editor');
			if (editor) {
				editor.value = jsonStr;
				editor.dispatchEvent(new Event('input', { bubbles: true }));
			}

			const mindmapEl = document.getElementById('mindmap');
			const svgOut = document.getElementById('svg-output');
			if (mindmapEl && svgOut && svgOut.parentNode !== mindmapEl) {
				mindmapEl.innerHTML = '';
				mindmapEl.appendChild(svgOut);
			}
			if (mindmapEl) {
				mindmapEl.style.display = 'block';
			}

			if (window.updateZoomControlsVisibility) {
				window.updateZoomControlsVisibility();
			} else {
				const zoomControls = document.getElementById('zoom-controls');
				if (zoomControls) zoomControls.classList.add('show');
			}

			window.currentMarkdown = jsonStr;

			try {
				const bc = document.getElementById('button-container');
				if (bc) bc.style.display = 'flex';
			} catch { }

			if (options && options.playPopAnimation) {
				__mmwPlayMindmapPopAnimation();
			}

			try {
			} catch { }
		} catch (e) {
			console.error('MMW engine render error:', e);
			const container = document.getElementById('mindmap');
			if (container) {
				container.innerHTML = '';
				try {
					renderErrorMessage(container, e, typeof input === 'string' ? input : '');
				} catch { }
			}
		}
	};
})();

document.addEventListener('DOMContentLoaded', function () {
	if (window.__mmwNewJsInitDone) { return; }
	window.__mmwNewJsInitDone = true;

	initializeEditMode();
	initializePopupElements();
	addMindmapActionStyles();
	initLeftSidebar();
	initializeMainButtons();
	initializeHelpPopup();
	initializePdfUpload();
	initializeWebSearchToggle();


	const randomTextElement = document.getElementById('randomText');
	if (randomTextElement) {
		randomTextElement.textContent = getRandomText();
	}
	const openSearchPopupBtn = document.getElementById('openSearchPopupBtn');
	const closeSearchPopupBtn = document.getElementById('closeSearchPopupBtn');
	const searchMindmapsPopupOverlay = document.getElementById('searchMindmapsPopupOverlay');
	const popupMindmapSearchInput = document.getElementById('popupMindmapSearchInput');

	if (openSearchPopupBtn) {
		openSearchPopupBtn.addEventListener('click', openSearchMindmapsPopup);
	}
	if (closeSearchPopupBtn) {
		closeSearchPopupBtn.addEventListener('click', closeSearchMindmapsPopup);
	}
	if (searchMindmapsPopupOverlay) {
		searchMindmapsPopupOverlay.addEventListener('click', function (e) {
			if (e.target === this) {
				closeSearchMindmapsPopup();
			}
		});
	}
	if (popupMindmapSearchInput) {
		popupMindmapSearchInput.addEventListener('input', (event) => {
			filterAndDisplayMindmapsInPopup(event.target.value);
		});
		document.addEventListener('keydown', function (e) {
			if (e.key === 'Escape' && searchMindmapsPopupOverlay.classList.contains('active')) {
				closeSearchMindmapsPopup();
			}
		});
	}

	try {
		const manualLinks = document.querySelectorAll('a.manual-btn, .page-links a');
		manualLinks.forEach((el) => {
			el.addEventListener('click', (e) => {
				e.preventDefault();
				if (typeof window.createManualMindMap === 'function') {
					window.createManualMindMap();
				}
			}, { passive: false });
		});
	} catch (e) {
		console.warn('Manual create handler setup failed:', e);
	}

	window.setTimeout(() => {
		try {
			handleUrlParameters();
		} catch (error) {
			console.error('Failed to handle mind map URL parameters:', error);
			const app = document.getElementById('app');
			if (app) app.style.display = '';
			const loadingAnimation = document.getElementById('loading-animation');
			if (loadingAnimation) loadingAnimation.style.display = 'none';
		}
	}, 0);
});

function initializeWebSearchToggle() {
	const toggleContainer = document.getElementById('web-search-toggle');
	const checkbox = document.getElementById('web-search-checkbox');
	if (!toggleContainer || !checkbox) return;

	const stored = localStorage.getItem('mmw-web-search-enabled');
	const isEnabled = stored === null ? true : stored === 'true';
	checkbox.checked = isEnabled;
	window.MMW_USE_WEB_SEARCH = isEnabled;

	checkbox.addEventListener('change', () => {
		const enabled = checkbox.checked;
		window.MMW_USE_WEB_SEARCH = enabled;
		localStorage.setItem('mmw-web-search-enabled', String(enabled));
	});
}

function initializePdfUpload() {
	const uploadButton = document.querySelector('.upload-pdf-button');
	if (!uploadButton) return;

	let fileInput = document.getElementById('pdf-file-input');
	if (!fileInput) {
		fileInput = document.createElement('input');
		fileInput.type = 'file';
		fileInput.accept = 'application/pdf,.pdf';
		fileInput.id = 'pdf-file-input';
		fileInput.style.display = 'none';
		document.body.appendChild(fileInput);
	}

	ensureDragDropOverlay();

	uploadButton.addEventListener('click', (e) => {
		e.preventDefault();
		e.stopPropagation();
		fileInput.click();
	});

	fileInput.addEventListener('change', (e) => {
		const file = e.target.files && e.target.files[0];
		if (!file) return;
		if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
			showErrorPopup('请选择一个 PDF 文件。', '');
			fileInput.value = '';
			return;
		}
		handlePdfUpload(file);
		fileInput.value = '';
	});

	const headerElement = document.getElementById('header');
	if (!headerElement) return;

	const preventDefaults = (e) => {
		e.preventDefault();
		e.stopPropagation();
	};

	const highlight = () => {
		headerElement.classList.add('drag-over');
	};

	const unhighlight = () => {
		headerElement.classList.remove('drag-over');
	};

	let dragCounter = 0;
	let isDraggingOverHeader = false;

	headerElement.addEventListener('dragenter', (e) => {
		preventDefaults(e);
		dragCounter++;
		if (!isDraggingOverHeader) {
			isDraggingOverHeader = true;
			highlight();
			showDragDropOverlay();
		}
	}, false);

	headerElement.addEventListener('dragleave', (e) => {
		preventDefaults(e);
		dragCounter--;
		setTimeout(() => {
			const rect = headerElement.getBoundingClientRect();
			const isMouseOverHeader = e.clientX >= rect.left && e.clientX <= rect.right &&
				e.clientY >= rect.top && e.clientY <= rect.bottom;
			if (!isMouseOverHeader && isDraggingOverHeader) {
				isDraggingOverHeader = false;
				unhighlight();
				hideDragDropOverlay();
			}
		}, 10);
	}, false);

	['dragenter', 'dragover', 'dragleave'].forEach((eventName) => {
		headerElement.addEventListener(eventName, preventDefaults, false);
	});

	headerElement.addEventListener('dragover', () => {
		highlight();
	}, false);

	const overlay = document.getElementById('drag-drop-overlay');
	if (overlay) {
		overlay.addEventListener('drop', (e) => {
			preventDefaults(e);
			const dt = e.dataTransfer;
			const files = dt?.files || [];
			unhighlight();
			if (files.length > 0) {
				const file = files[0];
				if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
					handlePdfUpload(file);
				} else {
					showErrorPopup('请拖放一个 PDF 文件。', '');
				}
			}
			hideDragDropOverlay();
		}, false);

		overlay.addEventListener('dragover', preventDefaults, false);
	}

	document.addEventListener('dragover', preventDefaults, false);
	document.addEventListener('dragleave', (e) => {
		preventDefaults(e);
		if (e.clientX <= 0 || e.clientY <= 0 || e.clientX >= window.innerWidth || e.clientY >= window.innerHeight) {
			isDraggingOverHeader = false;
			hideDragDropOverlay();
		}
	}, false);

	document.addEventListener('drop', (e) => {
		preventDefaults(e);
		isDraggingOverHeader = false;
		hideDragDropOverlay();
	}, false);
}

function ensureDragDropOverlay() {
	let overlay = document.getElementById('drag-drop-overlay');
	if (overlay) return overlay;

	overlay = document.createElement('div');
	overlay.id = 'drag-drop-overlay';
	overlay.className = 'drag-drop-overlay';
	overlay.innerHTML = `
		<div class="drag-drop-content">
			<div class="drag-drop-icon">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"
					stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M4 12v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"></path>
					<polyline points="16 6 12 2 8 6"></polyline>
					<line x1="12" x2="12" y1="2" y2="12"></line>
				</svg>
			</div>
			<h2>将 PDF 文件拖放到此处</h2>
			<p>释放以上传并生成思维导图</p>
		</div>
	`;

	document.body.appendChild(overlay);
	return overlay;
}

function showDragDropOverlay() {
	const overlay = document.getElementById('drag-drop-overlay');
	if (overlay) {
		overlay.classList.add('active');
	}
}

function hideDragDropOverlay() {
	const overlay = document.getElementById('drag-drop-overlay');
	if (overlay) {
		overlay.classList.remove('active');
	}
}

function readFileAsDataUrl(file) {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(reader.result);
		reader.onerror = () => reject(reader.error || new Error('Failed to read file.'));
		reader.readAsDataURL(file);
	});
}

async function handlePdfUpload(file) {
	if (!file) return;
	if (generationInProgress) return;

	const maxSizeBytes = 15 * 1024 * 1024;
	if (file.size > maxSizeBytes) {
		showErrorPopup('PDF 文件过大。请上传小于 15 MB 的文件。', '');
		return;
	}

	generationInProgress = true;
	try {
		const loadingAnim = document.getElementById('loading-animation');
		if (loadingAnim) loadingAnim.style.display = 'flex';

		const dataUrl = await readFileAsDataUrl(file);
		const systemPrompt = 'You are a mind map generator. Return only valid JSON that matches the provided schema.';

		const requestBody = {
			messages: [
				{ role: 'system', content: systemPrompt },
				{
					role: 'user',
					content: `Generate a mind map from the document: ${file.name} in its content language. Return valid JSON with "title" and "markdown" fields.`
				}
			],
			max_completion_tokens: 2200,
			temperature: 0.7,
			response_format: { type: 'json_object', schema: 'mindmap_markdown', required: ['markdown'] },
			thinking: { type: 'disabled' }
		};

		const response = await window.callLlmChatCompletion(requestBody);

		if (!response.ok) {
			const errorText = await response.text();
			if (response.status === 400 && errorText.includes('File is too large')) throw new Error('FILE_TOO_LARGE');
			if (response.status === 503 && errorText.includes('Cloudflare')) throw new Error('FILE_TOO_LARGE');
			throw new Error(`API 错误: ${response.status} ${errorText}`);
		}

		const data = await response.json();
		const message = data?.choices?.[0]?.message?.content;
		if (!message) throw new Error('模型服务返回的响应无效');

		let parsed = null;
		if (typeof message === 'string') {
			try {
				parsed = JSON.parse(message);
			} catch {
				const jsonMatch = message.match(/\{[\s\S]*\}/);
				if (jsonMatch) parsed = JSON.parse(jsonMatch[0]);
			}
		} else if (typeof message === 'object') {
			parsed = message;
		}

		if (!parsed || !parsed.markdown) {
			throw new Error('来自 API 的响应无效：缺少必要的 markdown 字段');
		}

		const responseData = {
			topic: parsed.title || file.name.replace(/\.pdf$/i, ''),
			raw: String(parsed.markdown || '').trim()
		};

		const { topic: finalTopic, markdown: finalMarkdown } = formatMarkdown(responseData);
		if (!finalMarkdown) throw new Error('处理后生成的 markdown 内容为空或无效。');
		hideHeader();
		await window.renderMindmap(finalMarkdown, { playPopAnimation: true });
		try {
			await fetch(
			'https://stats.mindmapwizard.com/hit/mmw-os/mind-map-generated-pdf', {
			method: 'GET',
			});
		} catch (trackingError) {
			console.error('Tracking Error:', trackingError);
		}
		let mmjsonStr = '';
		try {
			const ed = document.getElementById('json-editor');
			mmjsonStr = ed?.value || localStorage.getItem('json-mindmap-content') || '';
		} catch { }

		if (!mmjsonStr || !mmjsonStr.trim().startsWith('{')) {
			const fallback = {
				"mm-settings": { "spacing": 30, "border-radius": 4 },
				"mm-node": { "content": finalTopic, "children": [] }
			};
			mmjsonStr = JSON.stringify(fallback);
		}

		const newId = saveMindmapToHistory(mmjsonStr);
		currentMindmapTitle = finalTopic;

		const url = new URL(window.location);
		if (url.searchParams.has('q')) {
			url.searchParams.delete('q');
		}
		if (newId) {
			url.searchParams.set('id', newId);
		}
		window.history.replaceState({}, '', url.toString());

		showMindMapElements();
	} catch (error) {
		console.error('PDF upload error:', error);
		if (error.message === 'FILE_TOO_LARGE') {
			showErrorPopup('PDF 文件过大无法处理。请尝试更小的文件。', '');
		} else {
			showErrorPopup(error.message || '生成思维导图时发生错误。', '');
		}
	} finally {
		generationInProgress = false;
		const loadingAnim = document.getElementById('loading-animation');
		if (loadingAnim) loadingAnim.style.display = 'none';
	}
}



function removeUrlParameter(param) {
	const url = new URL(window.location.href);
	if (url.searchParams.has(param)) {
		url.searchParams.delete(param);
		window.history.replaceState({}, document.title, url.toString());
	}
}

function initLeftSidebar() {
	loadMindmapsLeftSidebar();
	const leftSidebar = document.getElementById('leftSidebar');
	let toggle = document.getElementById('leftSidebarToggle');
	const app = document.getElementById('app');
	const mindmap = document.getElementById('mindmap');
	const menubar = document.getElementById('menubar');
	const undoRedoContainer = document.getElementById('undo-redo-container');

	if (toggle) {
		const fresh = toggle.cloneNode(true);
		toggle.parentNode.replaceChild(fresh, toggle);
		toggle = fresh;
	}

	if (!leftSidebar || !toggle) {
		console.error('Left sidebar elements not found');
		return;
	}

	if (toggle && leftSidebar) {
		if (toggle.__leftSidebarBound) {
		} else {
			toggle.__leftSidebarBound = true;
			toggle.addEventListener('click', function () {
				leftSidebar.classList.toggle('open');

				if (app) app.classList.toggle('left-sidebar-open');
				if (mindmap) mindmap.classList.toggle('left-sidebar-open');
				if (undoRedoContainer) undoRedoContainer.classList.toggle('left-sidebar-open');

				const isOpen = leftSidebar.classList.contains('open');

				document.documentElement.classList.toggle('left-sidebar-open', isOpen);

				if (menubar) {
					menubar.classList.toggle('sidebar-open', isOpen);
				}

				localStorage.setItem('left-sidebar-state', isOpen ? 'open' : 'closed');

				try {
				} catch (e) {
					console.warn('Sidebar debug read failed:', e);
				}
			});
		}
	} else {
		console.error('Navbar toggle elements missing:', { toggle, leftSidebar });
	}

	if (!leftSidebar.querySelector('.sidebar-navbar')) {
		const navbar = document.createElement('div');
		navbar.className = 'sidebar-navbar';
		leftSidebar.insertBefore(navbar, leftSidebar.firstChild);
	}

	const sidebarState = localStorage.getItem('left-sidebar-state');
	if (sidebarState === 'open') {
		leftSidebar.classList.add('open');
		if (app) app.classList.add('left-sidebar-open');
		if (mindmap) mindmap.classList.add('left-sidebar-open');
		if (undoRedoContainer) undoRedoContainer.classList.add('left-sidebar-open');

		document.documentElement.classList.add('left-sidebar-open');

		if (menubar) {
			menubar.classList.add('sidebar-open');
		}
	}

	try {
		const lsTransformInit = window.getComputedStyle(leftSidebar).transform;
		const mmDisplayInit = mindmap ? window.getComputedStyle(mindmap).display : null;
		const mmMarginLeftInit = mindmap ? window.getComputedStyle(mindmap).marginLeft : null;
		const appDisplayInit = app ? window.getComputedStyle(app).display : null;
		const appMarginLeftInit = app ? window.getComputedStyle(app).marginLeft : null;
		const rootHasInit = document.documentElement.classList.contains('left-sidebar-open');
	} catch (e) {
		console.warn('Sidebar init debug failed:', e);
	}
}

function initializeEditMode() {
	const editModeButton = document.getElementById('customize-mode-button');
	const cancelEditButton = document.getElementById('cancel-edit');
	const saveEditButton = document.getElementById('save-edit');

	editModeButton?.addEventListener('click', () => toggleEditMode(true));
	cancelEditButton?.addEventListener('click', () => toggleEditMode(false));
	saveEditButton?.addEventListener('click', updateMindmapFromEdit);
	try {
		const balancedBtn = document.getElementById('align-balanced');
		const rightBtn = document.getElementById('align-right');
		if (balancedBtn && rightBtn) {
			const setActive = (activeBtn, inactiveBtn) => {
				activeBtn.style.background = 'var(--text-color)';
				activeBtn.style.color = 'var(--white)';
				activeBtn.style.borderColor = 'var(--text-color)';
				inactiveBtn.style.background = 'var(--mindmap-item-hover-bg)';
				inactiveBtn.style.color = 'var(--text-color)';
				inactiveBtn.style.borderColor = 'var(--light-grey)';
			};
			balancedBtn.onclick = (e) => {
				e.preventDefault();
				balancedBtn.dataset.selected = 'true';
				rightBtn.dataset.selected = 'false';
				setActive(balancedBtn, rightBtn);
			};
			rightBtn.onclick = (e) => {
				e.preventDefault();
				balancedBtn.dataset.selected = 'false';
				rightBtn.dataset.selected = 'true';
				setActive(rightBtn, balancedBtn);
			};
		}
		const styleStandard = document.getElementById('style-standard');
		const styleLines = document.getElementById('style-lines');
		const styleMinimal = document.getElementById('style-minimal');
		if (styleStandard && styleLines && styleMinimal) {
			const setStyleActive = (activeBtn) => {
				[styleStandard, styleLines, styleMinimal].forEach(btn => {
					if (btn === activeBtn) {
						btn.style.background = 'var(--text-color)';
						btn.style.color = 'var(--white)';
						btn.style.borderColor = 'var(--text-color)';
					} else {
						btn.style.background = 'var(--mindmap-item-hover-bg)';
						btn.style.color = 'var(--text-color)';
						btn.style.borderColor = 'var(--light-grey)';
					}
				});
				updatePreview();
			};
			styleStandard.onclick = (e) => { e.preventDefault(); setStyleActive(styleStandard); };
			styleLines.onclick = (e) => { e.preventDefault(); setStyleActive(styleLines); };
			styleMinimal.onclick = (e) => { e.preventDefault(); setStyleActive(styleMinimal); };
		}
	} catch { }
}

function saveMindmapToHistory(mindmapJsonStr, idOverride = null) {
	const history = JSON.parse(localStorage.getItem('mindmap-history') || '[]');
	const timestamp = new Date().toISOString();
	const newId = idOverride || Date.now();

	history.push({
		mindmap: mindmapJsonStr,
		timestamp,
		id: newId
	});

	if (history.length > 100) {
		history.shift();
	}

	localStorage.setItem('mindmap-history', JSON.stringify(history));
	markLearningPathMindmapComplete(newId, mindmapJsonStr);

	if (document.getElementById('searchMindmapsPopupOverlay')?.classList.contains('active')) {
		allMindmapHistory = JSON.parse(localStorage.getItem('mindmap-history') || '[]');
		allMindmapHistory.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
		filterAndDisplayMindmapsInPopup(document.getElementById('popupMindmapSearchInput')?.value || '');
	}
	if (typeof loadMindmapsLeftSidebar === 'function') {
		loadMindmapsLeftSidebar();
	}

	return newId;
}

function updateCurrentMindmap() {
	const mindmapElement = document.getElementById('mindmap');
	let markdown = '';
	if (mindmapElement) {
		markdown = mindmapElement.getAttribute('data-markdown') || '';
	}
	if (!markdown && typeof window.currentMarkdown === 'string') {
		markdown = window.currentMarkdown;
	}
	if (typeof markdown === 'string' && markdown.trim().startsWith('{')) {
		try {
			const obj = JSON.parse(markdown);
			const root = obj['mm-node'] || obj.mmNode || obj;
			const lines = [];
			const maxHeading = 6;
			(function walk(node, level) {
				if (!node || typeof node !== 'object') return;
				const text = String(node.content ?? '').trim();
				if (text) {
					if (level <= maxHeading) {
						lines.push(`${'#'.repeat(level)} ${text}`.trim());
					} else {
						lines.push(`- ${text}`.trim());
					}
				}
				if (Array.isArray(node.children)) {
					for (const child of node.children) walk(child, level + 1);
				}
			})(root, 1);
			markdown = lines.join('\n');
		} catch { }
	}
	currentMindmap = {
		topic: currentMindmapTitle,
		markdown: markdown,
		timestamp: new Date().toISOString(),
	};
}
function renderErrorMessage(container, error, markdown) {
	const errorMessage = document.createElement('div');
	errorMessage.textContent = '渲染思维导图时出错：' + error.message;
	errorMessage.style.color = 'var(--error-color)';
	errorMessage.style.padding = '20px';
	errorMessage.style.textAlign = 'center';
	errorMessage.style.marginTop = '50px';
	container.appendChild(errorMessage);

	const errorDetails = document.createElement('pre');
	errorDetails.textContent =
		'Markdown content (first 100 chars): ' +
		(markdown ? markdown.substring(0, 100) + '...' : 'undefined');
	errorDetails.style.fontSize = '12px';
	errorDetails.style.margin = '20px';
	errorDetails.style.padding = '10px';
	errorDetails.style.background = 'var(--background-color)';
	errorDetails.style.color = 'var(--text-color)';
	errorDetails.style.border = '1px solid var(--border-color)';
	errorDetails.style.borderRadius = '4px';
	errorDetails.style.overflow = 'auto';
	container.appendChild(errorDetails);
}

function toggleEditMode(show) {
	const mindmapElement = document.getElementById('mindmap');
	const editorElement = document.getElementById('mmCustomizationPanel');
	const editorOverlay = document.getElementById('editor-overlay');

	if (show) {
		try {
			const ed = document.getElementById('json-editor');
			const jsonStr = ed?.value || localStorage.getItem('json-mindmap-content') || '';
			let obj = {};
			try { obj = JSON.parse(jsonStr || '{}'); } catch { obj = {}; }
			const settings = obj['mm-settings'] || {};

			const roundingRange = document.getElementById('roundingRange');
			const spacingRange = document.getElementById('spacingRange');
			const branchWidthRange = document.getElementById('branchWidthRange');
			const fontSelect = document.getElementById('fontSelect');
			const balancedBtn = document.getElementById('align-balanced');
			const rightBtn = document.getElementById('align-right');

			const curRadius = Number.isFinite(settings['border-radius']) ? Number(settings['border-radius']) : 4;
			const curSpacing = Number.isFinite(settings['spacing']) ? Number(settings['spacing']) : 30;
			const curWidth = Number.isFinite(settings['mm-link-width']) ? Number(settings['mm-link-width']) : 2.5;
			const curAlign = typeof settings['branch-alignment'] === 'string' ? settings['branch-alignment'] : 'balanced';
			const curFont = (settings['font-family'] && typeof settings['font-family'] === 'string') ? settings['font-family'] : 'standard';

			if (roundingRange) roundingRange.value = String(curRadius);
			if (spacingRange) spacingRange.value = String(curSpacing);
			if (branchWidthRange) branchWidthRange.value = String(curWidth);

			const styleStandard = document.getElementById('style-standard');
			const styleLines = document.getElementById('style-lines');
			const styleMinimal = document.getElementById('style-minimal');
			const curStyle = typeof settings['style'] === 'string' ? settings['style'] : '1';

			const setStyleButton = (activeBtn) => {
				[styleStandard, styleLines, styleMinimal].forEach(btn => {
					if (btn) {
						if (btn === activeBtn) {
							btn.style.background = 'var(--text-color)';
							btn.style.color = 'var(--white)';
							btn.style.borderColor = 'var(--text-color)';
						} else {
							btn.style.background = 'var(--mindmap-item-hover-bg)';
							btn.style.color = 'var(--text-color)';
							btn.style.borderColor = 'var(--light-grey)';
						}
					}
				});
			};

			if (curStyle === '2') {
				setStyleButton(styleMinimal);
			} else if (curStyle === '4') {
				setStyleButton(styleLines);
			} else {
				setStyleButton(styleStandard);
			}

			const setActive = (activeBtn, inactiveBtn) => {
				if (!activeBtn || !inactiveBtn) return;
				activeBtn.style.background = 'var(--text-color)';
				activeBtn.style.color = 'var(--white)';
				activeBtn.style.borderColor = 'var(--text-color)';
				inactiveBtn.style.background = 'var(--mindmap-item-hover-bg)';
				inactiveBtn.style.color = 'var(--text-color)';
				inactiveBtn.style.borderColor = 'var(--light-grey)';
			};
			if (curAlign === 'right') {
				if (balancedBtn && rightBtn) {
					balancedBtn.dataset.selected = 'false';
					rightBtn.dataset.selected = 'true';
					setActive(rightBtn, balancedBtn);
				}
			} else {
				if (balancedBtn && rightBtn) {
					balancedBtn.dataset.selected = 'true';
					rightBtn.dataset.selected = 'false';
					setActive(balancedBtn, rightBtn);
				}
			}

			if (fontSelect) {
				const allowed = ['standard', 'Roboto Mono', 'PT Serif', 'Bebas Neue', 'Indie Flower', 'Open Runde'];
				fontSelect.value = allowed.includes(curFont) ? curFont : 'standard';
			}

			updatePreview();

			const inputs = [roundingRange, spacingRange, branchWidthRange, fontSelect];
			inputs.forEach(input => {
				if (input) {
					input.oninput = updatePreview;
					input.onchange = updatePreview;
				}
			});

		} catch (e) {
			console.warn('Prefill customization UI failed:', e);
		}

		editorElement.classList.add('show');
		editorOverlay.classList.add('show');
	} else {
		editorElement.classList.remove('show');
		editorOverlay.classList.remove('show');
		if (mindmapElement) mindmapElement.style.display = 'block';
	}
}

function updatePreview() {
	const roundingRange = document.getElementById('roundingRange');
	const spacingRange = document.getElementById('spacingRange');
	const branchWidthRange = document.getElementById('branchWidthRange');
	const fontSelect = document.getElementById('fontSelect');
	const styleStandard = document.getElementById('style-standard');
	const styleLines = document.getElementById('style-lines');
	const styleMinimal = document.getElementById('style-minimal');

	if (!roundingRange || !spacingRange || !branchWidthRange || !fontSelect) return;

	const radius = roundingRange.value;
	const spacing = parseInt(spacingRange.value, 10);
	const width = branchWidthRange.value;
	const font = fontSelect.value;

	const rects = document.querySelectorAll('#preview-svg rect');
	rects.forEach(rect => {
		rect.setAttribute('rx', radius);
		rect.setAttribute('ry', radius);
	});

	const links = document.querySelectorAll('#preview-svg .mm-link, #preview-svg .mm-link-straight, #preview-svg .preview-rect-underline, #preview-root-underline');
	links.forEach(link => {
		link.setAttribute('stroke-width', width);
	});

	const styleEl = document.getElementById('preview-style');
	if (styleEl) {
		const fontFamily = font === 'standard' ? 'sans-serif' : font;
		styleEl.textContent = `.mm-preview-node text{font-family:${fontFamily}, system-ui, sans-serif;}`;
	}

	const getActiveStyle = () => {
		if (styleMinimal?.style.background === 'var(--text-color)') return '2';
		if (styleLines?.style.background === 'var(--text-color)') return '4';
		return '1';
	};

	const currentStyle = getActiveStyle();

	const rootCenterY = 53;
	const nodeHeight = 38;
	const rootX = 239;
	const levelSpacing = spacing;
	const branchX = rootX + levelSpacing;
	const offset = spacing / 2 + nodeHeight / 2;
	const branch0Y = rootCenterY - offset - (nodeHeight / 2);
	const branch1Y = rootCenterY + offset - (nodeHeight / 2);

	const branch0 = document.getElementById('preview-node-0');
	const branch1 = document.getElementById('preview-node-1');

	if (branch0) branch0.setAttribute('transform', `translate(${branchX}, ${branch0Y})`);
	if (branch1) branch1.setAttribute('transform', `translate(${branchX}, ${branch1Y})`);

	const link0 = document.getElementById('preview-link-0');
	const link1 = document.getElementById('preview-link-1');

	const rootY = (currentStyle === '4') ? 77 : 53;
	const branch0TargetY = (currentStyle === '4') ? (branch0Y + 38) : (branch0Y + 19);
	const branch1TargetY = (currentStyle === '4') ? (branch1Y + 38) : (branch1Y + 19);

	const curve = levelSpacing * 0.5;
	const cp1X = rootX + curve;
	const cp2X = branchX - curve;

	if (link0) {
		const d0 = `M ${rootX},${rootY} C ${cp1X},${rootY} ${cp2X},${branch0TargetY} ${branchX},${branch0TargetY}`;
		link0.setAttribute('d', d0);
	}

	if (link1) {
		const d1 = `M ${rootX},${rootY} C ${cp1X},${rootY} ${cp2X},${branch1TargetY} ${branchX},${branch1TargetY}`;
		link1.setAttribute('d', d1);
	}

	if (roundingRange) {
		const isStyle2or4 = (currentStyle === '2' || currentStyle === '4');
		roundingRange.disabled = isStyle2or4;
		const container = roundingRange.closest('div');
		if (container) {
			container.style.opacity = isStyle2or4 ? '0.5' : '1';
			container.style.pointerEvents = isStyle2or4 ? 'none' : 'auto';
			container.style.transition = 'opacity 0.3s ease';
		}
	}

	const colorRects = document.querySelectorAll('#preview-svg rect[fill-opacity]');
	const underlines = document.querySelectorAll('#preview-svg .preview-rect-underline, #preview-root-underline');
	const curvedLinks = document.querySelectorAll('#preview-svg path.mm-link');
	const straightLinks = document.querySelectorAll('#preview-svg line.mm-link-straight');

	colorRects.forEach(rect => rect.style.display = 'block');
	underlines.forEach(line => line.style.display = 'none');
	curvedLinks.forEach(l => l.style.display = 'block');
	straightLinks.forEach(l => l.style.display = 'none');

	if (currentStyle === '2') {
		colorRects.forEach(rect => rect.style.display = 'none');
	} else if (currentStyle === '4') {
		colorRects.forEach(rect => rect.style.display = 'none');
		underlines.forEach(line => line.style.display = 'block');
	}

	curvedLinks.forEach(l => {
		l.style.transition = 'transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
		l.style.transform = 'translateY(0)';
	});
}

function handleUrlParameters() {
	const params = new URLSearchParams(location.search);
	const id = params.get('id');
	const q = params.get('q');
	const manual = params.get('manual');

	if (id) {
		loadMindMapById(id);
	} else if (q) {
		const learningPathTemplate = getLearningPathMindmapTemplate(getLearningPathNodeContext(), q);
		if (learningPathTemplate) {
			createLocalMindMapFromMarkdown(learningPathTemplate).catch((error) => {
				console.error('Failed to auto-create learning path mind map:', error);
			});
			return;
		}
		const headerLines = q.split('\n').filter(line => line.trim().startsWith('#'));
		if (headerLines.length > 10) {
			createLocalMindMapFromMarkdown(q).catch((error) => {
				console.error('Failed to auto-create mind map from URL markdown:', error);
			});
		} else {
			initiateGenerationProcess(q);
		}
		removeUrlParameter('q');
	} else if (manual === 'true') {
		createManualMindMap();
		removeUrlParameter('manual');
	}
}

function createManualMindMap() {
	if (window.__mmwManualCreateInProgress) return;
	window.__mmwManualCreateInProgress = true;

	try {
		const defaultMM = {
			"mm-settings": {
				"spacing": 30,
				"border-radius": 4,
				"branch-alignment": "right"
			},
			"mm-node": {
				"content": "新建思维导图",
				"children": [
					{
						"content": "双击输入文本",
						"children": []
					},
					{
						"content": "右键点击节点查看选项",
						"children": []
					}
				]
			}
		};

		try { currentMindmapTitle = defaultMM["mm-node"]?.content || '思维导图'; } catch (e) { }

		try { hideInitialElements(); } catch (e) { }

		const mmjsonStr = JSON.stringify(defaultMM);

		const newId = Date.now();
		saveMindmapToHistory(mmjsonStr, newId);
		updateUrlWithId(String(newId));

		renderMindmap(mmjsonStr);
		showMindMapElements();
		hideHeader();
	} catch (e) {
		console.error('Failed to create manual mind map:', e);
	} finally {
		setTimeout(() => {
			window.__mmwManualCreateInProgress = false;
		}, 50);
	}
}

window.createManualMindMap = createManualMindMap;

function updateMindmapFromEdit() {
	try {
		const ed = document.getElementById('json-editor');
		let mmjsonStr = ed?.value || localStorage.getItem('json-mindmap-content') || '';
		if (!mmjsonStr || !mmjsonStr.trim().startsWith('{')) {
			console.warn('No mind map JSON found to customize.');
			toggleEditMode(false);
			return;
		}
		let obj = {};
		try { obj = JSON.parse(mmjsonStr); } catch { obj = {}; }

		const roundingRange = document.getElementById('roundingRange');
		const spacingRange = document.getElementById('spacingRange');
		const branchWidthRange = document.getElementById('branchWidthRange');
		const fontSelect = document.getElementById('fontSelect');
		const balancedBtn = document.getElementById('align-balanced');
		const rightBtn = document.getElementById('align-right');
		const styleStandard = document.getElementById('style-standard');
		const styleLines = document.getElementById('style-lines');
		const styleMinimal = document.getElementById('style-minimal');

		obj['mm-settings'] = obj['mm-settings'] || {};
		const settings = obj['mm-settings'];

		if (spacingRange) settings['spacing'] = Number(spacingRange.value || 30);
		if (branchWidthRange) settings['mm-link-width'] = Number(branchWidthRange.value || 2.5);
		if (roundingRange) settings['border-radius'] = Number(roundingRange.value || 4);

		const getSelectedStyle = () => {
			if (styleMinimal?.style.background === 'var(--text-color)') return '2';
			if (styleLines?.style.background === 'var(--text-color)') return '4';
			return '1';
		};

		const selectedStyle = getSelectedStyle();
		if (selectedStyle === '1') {
			delete settings['style'];
		} else {
			settings['style'] = selectedStyle;
		}

		let align = 'balanced';
		if (rightBtn?.dataset.selected === 'true') align = 'right';
		if (balancedBtn?.dataset.selected === 'true') align = 'balanced';
		settings['branch-alignment'] = align;

		const selFont = (fontSelect?.value || 'standard').trim();
		if (selFont === 'standard') {
			delete settings['font-family'];
			delete settings.fontFamily;
			delete settings.fonts;
		} else {
			settings['font-family'] = selFont;
		}

		const updatedStr = JSON.stringify(obj, null, 2);
		if (ed) ed.value = updatedStr;
		try { localStorage.setItem('json-mindmap-content', updatedStr); } catch { }
		renderMindmap(updatedStr);

		try {
			const url = new URL(location.href);
			const id = url.searchParams.get('id');
			if (id) {
				const history = JSON.parse(localStorage.getItem('mindmap-history') || '[]');
				const idx = history.findIndex((item) => String(item.id) === String(id));
				if (idx >= 0) {
					history[idx].mindmap = updatedStr;
					history[idx].timestamp = new Date().toISOString();
					localStorage.setItem('mindmap-history', JSON.stringify(history));
					if (typeof loadMindmapsLeftSidebar === 'function') loadMindmapsLeftSidebar();
				}
			}
		} catch (e) {
			console.warn('Failed to update history after customization:', e);
		}
	} catch (e) {
		console.error('Failed to apply customization:', e);
	} finally {
		toggleEditMode(false);
	}
}


function closeClearPopup() {
	const popup = document.querySelector('.delete-popup');
	if (popup) {
		popup.remove();
	}
}

function confirmClear() {
	localStorage.removeItem('mindmap-history');
	localStorage.removeItem('mindmap_local');
	localStorage.removeItem('mindmap-playground');
	localStorage.removeItem('lastMindmapInput');

	closeClearPopup();

	const url = new URL(window.location.href);
	url.searchParams.delete('q');
	url.searchParams.delete('id');

	window.history.replaceState({}, document.title, url);

	window.location.reload();
}

function initializePopupElements() {
	const popupOverlay = document.createElement('div');
	popupOverlay.className = 'popup-overlay';
	popupOverlay.id = 'popupOverlay';

	const deletePopup = document.createElement('div');
	deletePopup.className = 'custom-popup';
	deletePopup.id = 'deletePopup';
	deletePopup.innerHTML = `
        <div class="popup-header">
            <h3>
                删除思维导图
            </h3>
        </div>
        <div class="popup-content">
            <div class="popup-message">确定要删除此思维导图吗？此操作无法撤销。</div>
            <div class="popup-buttons">
                <button class="popup-btn popup-btn-cancel" id="deleteCancelBtn">取消</button>
                <button class="popup-btn popup-btn-delete" id="deleteConfirmBtn">删除</button>
            </div>
        </div>
    `;

	popupOverlay.appendChild(deletePopup);

	document.body.appendChild(popupOverlay);

	setupPopupEventListeners();
}

const infoButton = document.querySelector('.info-button');
if (infoButton) {
	infoButton.addEventListener('click', function (e) {
		e.preventDefault();
		const infoMenu = document.querySelector('.info-menu');
		if (infoMenu) {
			infoMenu.classList.toggle('show');
		}
	});
}


function hideHeader() {
	const headerElement = document.getElementById('header');
	if (headerElement) {
		headerElement.classList.remove('active');
		headerElement.classList.add('header-hidden');
	}

	const handwrittenUpgradeTip = document.getElementById('handwrittenUpgradeTip');
	if (handwrittenUpgradeTip) {
		handwrittenUpgradeTip.style.display = 'none';
	}

	const app = document.getElementById('app');
	if (app) {
		app.style.display = 'none';
	}
}

function hideInitialElements() {
	try {
		const app = document.getElementById('app');
		const headerElement = document.getElementById('header');
		const mindmap = document.getElementById('mindmap');
		const toolbar = document.querySelector('.mm-toolbar');

		if (headerElement) {
			headerElement.classList.remove('active');
			headerElement.classList.add('header-hidden');
		}
		if (app) app.style.display = 'none';
		if (mindmap) mindmap.style.display = 'block';
		if (toolbar) toolbar.style.display = 'flex';
	} catch (e) {
		console.warn('hideInitialElements failed:', e);
	}
}

function showMindMapElements() {
	const mindmapElement = document.getElementById('mindmap');
	const buttonContainer = document.getElementById('button-container');
	const undoRedoContainer = document.getElementById('undo-redo-container');
	const zoomControls = document.getElementById('zoom-controls');

	if (mindmapElement) {
		mindmapElement.style.display = 'block';
	}

	if (buttonContainer) {
		buttonContainer.style.display = 'block';
	}

	if (undoRedoContainer) {
		undoRedoContainer.style.display = 'flex';
	}

	if (zoomControls) {
		zoomControls.classList.add('show');
	}

	if (window.innerWidth < 770) {
		closeLeftSidebar();
	}
	closeNotesDrawer();
}

window.__mmwResetSvgContainer = function (hard = false) {
	try {
		const mindmap = document.getElementById('mindmap');
		const svgOut = document.getElementById('svg-output');
		if (svgOut && svgOut.parentNode) {
			if (hard) {
				const fresh = svgOut.cloneNode(false);
				fresh.id = 'svg-output';
				svgOut.parentNode.replaceChild(fresh, svgOut);
			} else {
				svgOut.innerHTML = '';
			}
		} else if (mindmap) {
			const oldSvgs = mindmap.querySelectorAll('svg');
			oldSvgs.forEach(n => n.remove());
		}
	} catch (e) {
		console.warn('SVG reset failed:', e);
	}
};


function loadMindMapById(id) {
	if (!id) {
		console.error('No mind map ID provided');
		showErrorMessage('未提供思维导图 ID');
		return;
	}

	const selectedItem = document.querySelector(`.mindmap-item[data-id="${id}"]`);
	if (selectedItem) {
		selectedItem.classList.add('active');
	}
	if (window.innerWidth < 770) {
		closeLeftSidebar();
	}

	const history = JSON.parse(localStorage.getItem('mindmap-history') || '[]');
	const stringId = String(id);

	let mindMap = history.find((item) => String(item.id) === stringId);

	if (!mindMap) {
		const playgroundData = localStorage.getItem('mindmap-playground');

		if (playgroundData) {
			try {
				const playground = JSON.parse(playgroundData);

				if (playground && typeof playground === 'object' && String(playground.id) === stringId) {
					mindMap = playground;
				}
			} catch (parseError) {
				console.error('Error parsing playground data:', parseError);
			}
		}

		if (!mindMap) {
			if (restoreLearningPathMindmapFromCache(stringId)) {
				return loadMindMapById(stringId);
			}
			showHeader();
			return
		}
	}

	updateUrlWithId(stringId);
	hideInitialElements();
	showMindmapElements();
	closeNotesDrawer();
    resetMindMapHistory();

	if (typeof window.__mmwResetSvgContainer === 'function') { window.__mmwResetSvgContainer(); }

	let mmjsonStr = '';
	let markdown = '';

	if (mindMap.mindmap) {
		mmjsonStr = typeof mindMap.mindmap === 'string' ? mindMap.mindmap : JSON.stringify(mindMap.mindmap);
	} else if (mindMap.mmjson) {
		mmjsonStr = typeof mindMap.mmjson === 'string' ? mindMap.mmjson : JSON.stringify(mindMap.mmjson);
	} else if (mindMap.markdown) {
		markdown = String(mindMap.markdown);
	}
	if (mmjsonStr) {
		currentMarkdown = mmjsonStr;
		try {
			const o = JSON.parse(mmjsonStr);
			const r = o['mm-node'] || o.mmNode || o;
			const t = String(r?.content || '').trim();
			currentMindmapTitle = t.replace(/\*|~~/g, '') || '思维导图';
		} catch {
			currentMindmapTitle = '思维导图';
		}
		renderMindmap(mmjsonStr);
		currentMindmap = mindMap;
		document.title = `${currentMindmapTitle} - 思维导图向导`;
	} else if (markdown) {
		try {
			let derivedTitle = '思维导图';
			const m = markdown.match(/^#{1,6}\s+(.*)$/m);
			if (m) {
				derivedTitle = m[1].trim().replace(/\*|~~/g, '');
			}
			currentMindmapTitle = derivedTitle;
		} catch {
			const rawTopic = mindMap.topic || '思维导图';
			currentMindmapTitle = rawTopic.replace(/\*|~~/g, '');
		}
		renderMindmap(markdown);
		document.title = `${currentMindmapTitle} - 思维导图向导`;
	} else {
		console.error('Mind map has no content');
		showErrorMessage('思维导图内容为空或已损坏。');
		return;
	}

	const navLinks = document.querySelector('.nav-links');
	if (navLinks) {
		navLinks.classList.add('padding-right');
	}

	hideHeader();
	generationInProgress = false;
}

function updateUrlWithId(id) {
	const currentUrl = new URL(window.location.href);
	const urlParams = new URLSearchParams(currentUrl.search);

	urlParams.set('id', id);

	if (urlParams.has('yt-link')) urlParams.delete('yt-link');
	if (urlParams.has('q')) urlParams.delete('q');

	const newUrl = `${currentUrl.pathname}?${urlParams.toString()}`;
	window.history.pushState({
		id: id
	}, '', newUrl);
}

function showErrorMessage(message) {
	console.error(message);
	const app = document.getElementById('app');
	app.style.display = 'none';

	const mindmapContainer = document.getElementById('mindmap');
	if (mindmapContainer) {
		mindmapContainer.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100vh; flex-direction: column; text-align: center; padding: 20px;" id="inAppErrorMessage">
                <h2 style="margin-bottom: 10px;">出了点问题。</h2>
                <p>${message}</p>
                <button onclick="showHeader()" style="margin-top: 20px; padding: 8px 25px; background: var(--text-color); color: var(--white); border: none; border-radius: 40px; cursor: pointer; font-size: 0.9rem; font-family: "SF Pro Text", -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, "Avenir", "Montserrat", "Corbel", "URW Gothic", "Source Sans Pro", sans-serif;">关闭</button>
            </div>
        `;
		mindmapContainer.style.display = 'block';
		hideInitialElements();
	}
}


function loadMindmapsLeftSidebar() {
	const history = JSON.parse(localStorage.getItem('mindmap-history') || '[]');
	const playground = JSON.parse(localStorage.getItem('mindmap-playground') || 'null');
	const list = document.getElementById('leftSidebarMindmapList');

	if (!list) {
		console.error('Left sidebar mindmap list element not found');
		return;
	}

	let allMindmaps = [...history];
	if (playground) {
		const duplicateById = history.some((item) => String(item.id) === String(playground.id));
		const pgMindmapStr = (typeof playground.mindmap === 'string' ? playground.mindmap : '').trim();
		const duplicateByContent = pgMindmapStr
			? history.some((item) => (typeof item.mindmap === 'string' ? item.mindmap : '').trim() === pgMindmapStr)
			: false;
		if (!duplicateById && !duplicateByContent) {
			allMindmaps.push(playground);
		}
	}

	const sampleMarkdown = "# Mind Map\n\n## Branch\n## Branch";

	const filteredMindmaps = allMindmaps.filter(item => item.markdown !== sampleMarkdown);

	if (filteredMindmaps.length === 0) {
		list.innerHTML = `
		<div class="no-mindmaps">
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="40" height="40" color="currentColor" fill="none" stroke="var(--dark-grey)" stroke-width="1.5">
				<path d="M13.9378 3H10.0622C8.09477 3 7.11106 3 6.34921 3.5158C5.58736 4.0316 5.22202 4.94495 4.49134 6.77166L2.42914 11.9272C2.21522 12.4619 2.10826 12.7293 2.05413 13.0104C2 13.2915 2 13.5795 2 14.1555V15C2 17.8284 2 19.2426 2.87868 20.1213C3.75736 21 5.17157 21 8 21H16C18.8284 21 20.2426 21 21.1213 20.1213C22 19.2426 22 17.8284 22 15V14.1555C22 13.5795 22 13.2915 21.9459 13.0104C21.8917 12.7294 21.7848 12.4619 21.5709 11.9271L19.5087 6.77166C18.778 4.94495 18.4126 4.0316 17.6508 3.5158C16.8889 3 15.9052 3 13.9378 3Z"></path>
				<path d="M2.5 13H5.58579C6.16263 13 6.45105 13 6.71982 13.0766C6.86747 13.1187 7.00978 13.1776 7.14394 13.2523C7.38816 13.3882 7.59211 13.5921 8 14C8.40789 14.4079 8.61184 14.6118 8.85606 14.7477C8.99022 14.8224 9.13253 14.8813 9.28018 14.9234C9.54895 15 9.83737 15 10.4142 15H13.5858C14.1626 15 14.4511 15 14.7198 14.9234C14.8675 14.8813 15.0098 14.8224 15.1439 14.7477C15.3882 14.6118 15.5921 14.4079 16 14C16.4079 13.5921 16.6118 13.3882 16.8561 13.2523C16.9902 13.1776 17.1325 13.1187 17.2802 13.0766C17.5489 13 17.8374 13 18.4142 13H21.5"></path>
			</svg>
			<h3>暂无思维导图</h3>
		</div>
        `;
		return;
	}

	const sortedMindmaps = filteredMindmaps.sort((a, b) => {
		const dateA = new Date(a.timestamp);
		const dateB = new Date(b.timestamp);
		return dateB - dateA;
	});

	const deriveTopic = (entry) => {
		try {
			const s = entry.mindmap || entry.mmjson || '';
			if (s && typeof s === 'string' && s.trim().startsWith('{')) {
				const obj = JSON.parse(s);
				const root = obj['mm-node'] || obj.mmNode || obj;
				const t = String(root?.content || '').trim();
				return t.replace(/\*|~~/g, '') || '思维导图';
			}

			if (entry.markdown) {
				const m = String(entry.markdown).match(/^#{1,6}\s+(.*)$/m);
				if (m) {
					return m[1].trim().replace(/\*|~~/g, '');
				}
			}
		} catch { }
		return '思维导图';
	};

	list.innerHTML = sortedMindmaps
		.map(
			(item) => {
				const title = deriveTopic(item);
				return `
        <div class="mindmap-item" data-id="${item.id}">
            <div class="mindmap-info">
                <div class="mindmap-title">${escapeHtmlLeftSidebar(title)}</div>
                <div class="mindmap-date">${formatDateLeftSidebar(item.timestamp)}</div>
            </div>
            <div class="mindmap-actions">
                <div class="fade-overlay"></div>
                <button class="delete-btn" onclick="deleteMindmap('${item.id}')" title="删除">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-color)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                </button>
            </div>
        </div>
        `;
			}
		)
		.join('');

	document.querySelectorAll('.mindmap-item').forEach((item) => {
		item.addEventListener('click', function (e) {
			if (!e.target.closest('button')) {
				const id = this.getAttribute('data-id');
				openMindmapLeftSidebar(id);
			}
		});
	});
}

function openMindmapLeftSidebar(id) {
	document.querySelectorAll('.mindmap-item').forEach((item) => {
		item.classList.remove('active');
	});

	resetMindMapHistory();

	loadMindMapById(id);
	hideHeader()

	if (window.chatManager) {
		if (window.chatManager.isOpen) {
			window.chatManager.toggle(false);
		}
		window.chatManager.reset();
	}
}

function getMindmapFromStorage(id) {
	let history = JSON.parse(localStorage.getItem('mindmap-history') || '[]');
	let mindmap = history.find((item) => String(item.id) === String(id));
	let source = 'history';

	if (!mindmap) {
		const playground = JSON.parse(localStorage.getItem('mindmap-playground') || 'null');
		if (playground && String(playground.id) === String(id)) {
			mindmap = playground;
			source = 'playground';
		}
	}
	return { mindmap, source };
}

function renameMindmap(id) {
	const { mindmap, source } = getMindmapFromStorage(id);

	if (!mindmap) {
		console.error('Mind map not found for rename');
		return;
	}

	const newNameCallback = (id, newName) => {
		updateMindmapInStorage(id, { topic: newName });
		loadMindmapsLeftSidebar();
		if (String(currentMindmap.id) === String(id)) {
			currentMindmapTitle = newName;
			document.title = `${currentMindmapTitle} - 思维导图向导`;
		}
	};

	if (window.customPopups) {
		window.customPopups.openRenamePopup(id, mindmap.topic, newNameCallback);
	} else {
		const newName = window.prompt('输入此思维导图的新名称：', mindmap.topic);
		if (newName !== null && newName.trim() !== '') {
			newNameCallback(id, newName.trim());
		}
	}
}


function deleteMindmap(id) {
	const deleteCallback = (idToDelete) => {
		let history = JSON.parse(localStorage.getItem('mindmap-history') || '[]');
		const updatedHistory = history.filter((item) => String(item.id) !== String(idToDelete));

		if (updatedHistory.length < history.length) {
			localStorage.setItem('mindmap-history', JSON.stringify(updatedHistory));
		} else {
			const playground = JSON.parse(localStorage.getItem('mindmap-playground') || 'null');
			if (playground && String(playground.id) === String(idToDelete)) {
				localStorage.removeItem('mindmap-playground');
			}
		}
		loadMindmapsLeftSidebar();

		if (String(currentMindmap.id) === String(idToDelete)) {
			currentMarkdown = '';
			currentMindmapTitle = '';
			showHeader();

			const url = new URL(window.location.href);
			url.searchParams.delete('id');
			window.history.pushState({ path: url.href }, '', url.href);
		}
		
	};

	if (window.customPopups) {
		window.customPopups.openDeletePopup(id, deleteCallback);
	} else {
		if (confirm('确定要删除此思维导图吗？此操作无法撤销。')) {
			deleteCallback(id);
		}
	}
}

function updateMindmapInStorage(id, updates) {
	let history = JSON.parse(localStorage.getItem('mindmap-history') || '[]');
	let mindmapInHistory = history.find(item => String(item.id) === String(id));

	if (mindmapInHistory) {
		Object.assign(mindmapInHistory, updates);
		localStorage.setItem('mindmap-history', JSON.stringify(history));
	} else {
		let playground = JSON.parse(localStorage.getItem('mindmap-playground') || 'null');
		if (playground && String(playground.id) === String(id)) {
			Object.assign(playground, updates);
			localStorage.setItem('mindmap-playground', JSON.stringify(playground));
		}
	}
}

function setupPopupEventListeners() {
	const renamePopupClose = document.getElementById('renamePopupClose');
	const renameCancelBtn = document.getElementById('renameCancelBtn');
	const deleteCancelBtn = document.getElementById('deleteCancelBtn');
	const popupOverlay = document.getElementById('popupOverlay');

	if (renamePopupClose) renamePopupClose.addEventListener('click', closeRenamePopup);
	if (renameCancelBtn) renameCancelBtn.addEventListener('click', closeRenamePopup);
	if (deleteCancelBtn) deleteCancelBtn.addEventListener('click', closeDeletePopup);

	if (popupOverlay) {
		popupOverlay.addEventListener('click', function (e) {
			if (e.target === this) {
				closeAllPopups();
			}
		});
	}


	document.addEventListener('keydown', function (e) {
		if (e.key === 'Escape') {
			closeAllPopups();
		}
	});
}

function openRenamePopup(id, currentName, callback) {
	const overlay = document.getElementById('popupOverlay');
	const popup = document.getElementById('renamePopup');
	const input = document.getElementById('renameInput');
	const confirmBtn = document.getElementById('renameConfirmBtn');

	if (!overlay || !popup || !input || !confirmBtn) {
		console.error('Rename popup elements not found');
		return;
	}


	input.value = currentName;

	overlay.classList.add('active');
	popup.style.display = 'block';
	const deletePopup = document.getElementById('deletePopup');
	if (deletePopup) {
		deletePopup.style.display = 'none';
	}


	setTimeout(() => {
		input.focus();
		input.select();
	}, 100);

	confirmBtn.onclick = null;
	input.onkeydown = null;

	const handleRename = () => {
		const newName = input.value.trim();
		if (newName !== '') {
			closeRenamePopup();
			if (callback && typeof callback === 'function') {
				callback(id, newName);
			}
		} else {
			input.classList.add('error');
			setTimeout(() => {
				input.classList.remove('error');
			}, 500);
		}
	};


	input.onkeydown = function (e) {
		if (e.key === 'Enter') {
			e.preventDefault();
			handleRename();
		}
	};

	confirmBtn.onclick = handleRename;
}

function openDeletePopup(id, callback) {
	const overlay = document.getElementById('popupOverlay');
	const popup = document.getElementById('deletePopup');
	const confirmBtn = document.getElementById('deleteConfirmBtn');

	if (!overlay || !popup || !confirmBtn) {
		console.error('Delete popup elements not found');
		return;
	}

	overlay.classList.add('active');
	popup.style.display = 'block';

	const renamePopup = document.getElementById('renamePopup');
	if (renamePopup) {
		renamePopup.style.display = 'none';
	}


	confirmBtn.onclick = null;

	confirmBtn.onclick = function () {
		closeDeletePopup();
		if (callback && typeof callback === 'function') {
			callback(id);
		}
	};
}

function closeRenamePopup() {
	const overlay = document.getElementById('popupOverlay');
	const popup = document.getElementById('renamePopup');
	if (overlay) overlay.classList.remove('active');
	if (popup) popup.style.display = 'none';
}

function closeDeletePopup() {
	const overlay = document.getElementById('popupOverlay');
	const popup = document.getElementById('deletePopup');
	if (overlay) overlay.classList.remove('active');
	if (popup) popup.style.display = 'none';
}

function closeAllPopups() {
	closeRenamePopup();
	closeDeletePopup();
}

window.customPopups = {
	openDeletePopup,
};

function addMindmapActionStyles() {
	const styleId = 'mindmap-action-styles';
	if (document.getElementById(styleId)) {
		return;
	}
}

window.addEventListener('storage', function (e) {
	if (e.key === 'mindmap-history') {
		loadMindmapsLeftSidebar();
	}
});

function escapeHtml(unsafe) {
	return unsafe
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#039;');
}

window.downloadMindmap = downloadMindmap;
window.shareMindmap = shareMindmap;
window.clearHistory = clearHistory;

async function shareMindmap() {
	if (document.querySelector('.share-dialog')) {
		return;
	}

	const shareButton = document.querySelector('.share-button');
	if (shareButton) {
		shareButton.disabled = true;
		shareButton.style.opacity = '0.5';
	}

	const shareOverlay = document.createElement('div');
	shareOverlay.className = 'share-overlay';

	const dialog = document.createElement('div');
	dialog.className = 'share-dialog';
	dialog.innerHTML = `
		  <h3>分享思维导图</h3>
		  <p>正在生成分享链接...</p>
		  <div class="loading-spinner"></div>
	  `;

	document.body.appendChild(shareOverlay);
	document.body.appendChild(dialog);

	setTimeout(() => {
		shareOverlay.classList.add('show');
		dialog.classList.add('show');
	}, 10);

	window.closeShareDialog = function () {
		shareOverlay.classList.remove('show');
		dialog.classList.remove('show');

		setTimeout(() => {
			if (shareOverlay.parentNode) {
				document.body.removeChild(shareOverlay);
			}
			if (dialog.parentNode) {
				document.body.removeChild(dialog);
			}
			if (shareButton) {
				shareButton.disabled = false;
				shareButton.style.opacity = '1';
			}
		}, 300);
	}

	window.copyShareLink = function () {
		const input = document.querySelector('.share-link');
		if (input) {
			input.select();
			input.setSelectionRange(0, 99999);
			navigator.clipboard.writeText(input.value);

			const copyButton = document.querySelector('.dialog-button.confirm');
			if (copyButton) {
				copyButton.textContent = '已复制！';
				setTimeout(() => { copyButton.textContent = '复制链接'; }, 2000);
			}
		}
	}


	shareOverlay.addEventListener('click', window.closeShareDialog);

	function loadQRCodeLibrary() {
		return new Promise((resolve, reject) => {
			if (typeof QRCode !== 'undefined') {
				resolve();
				return;
			}

			const existingScript = document.querySelector('script[src="/mind-map-wizard/scripts/libraries/qrcode.min.js"]');
			if (existingScript) {
				existingScript.onload = resolve;
				existingScript.onerror = reject;
				return;
			}

			const script = document.createElement('script');
			script.src = '/mind-map-wizard/scripts/libraries/qrcode.min.js';
			script.onload = resolve;
			script.onerror = () => reject(new Error('加载二维码库失败'));
			document.head.appendChild(script);
		});
	}

	try {
		updateCurrentMindmap();
		const topic = currentMindmap.topic || currentMindmapTitle || '思维导图';
		let mmjsonStr = '';
		try {
			if (typeof window.currentMarkdown === 'string' && window.currentMarkdown.trim().startsWith('{')) {
				mmjsonStr = window.currentMarkdown;
			}
		} catch { }
		if (!mmjsonStr) {
			try {
				const stored = localStorage.getItem('json-mindmap-content') || '';
				if (stored.trim().startsWith('{')) mmjsonStr = stored;
			} catch { }
		}
		if (!mmjsonStr || !mmjsonStr.trim()) {
			throw new Error('没有可分享的 JSON 思维导图');
		}
		let mmjsonPayload;
		try {
			mmjsonPayload = JSON.parse(mmjsonStr);
		} catch {
			mmjsonPayload = mmjsonStr;
		}


		let headers = {
			'Content-Type': 'application/json',
		};

		if (typeof Clerk !== 'undefined' && Clerk.session && Clerk.session.id) {
			try {
				const token = await Clerk.session.getToken();
				if (token) {
					headers['Authorization'] = `Bearer ${token}`;
				} else {
				}
			} catch (authError) {
				console.warn(
					'Error retrieving Clerk token, proceeding without authentication.',
					authError,
				);
			}
		} else {
		}


		const response = await fetch('https://share.mindmapwizard.com/', {
			method: 'POST',
			headers: headers,
			body: JSON.stringify({
				mmjson: mmjsonPayload
			}),
		});
		if (!response.ok) {
			let errorData = {
				message: `分享思维导图失败。状态：${response.status}`,
			};
			try {
				errorData = await response.json();
			} catch (e) {
				console.error('Failed to parse error response JSON:', e);
			}
			throw new Error(
				errorData.message || `分享思维导图失败。状态：${response.status}`,
			);
		}

		const data = await response.json();

		const shareUrl = `https://mindmapwizard.com/view.html?id=${data.id}`;

		dialog.innerHTML = `
			  <div id="dialog-qr-code-container" style="margin: 20px auto; width: 144px; height: 144px;" class="qr-code-container"></div>
			  <hr style="border: 1px solid; border-color: var(--light-grey); border-radius: 5px; margin: 10px 0 10px 0;" class="qr-code-container-hr">
			  <h3>分享思维导图</h3>
			  <p>扫描二维码或复制此链接来分享您的思维导图。</p>
			  <input type="text" class="share-link" value="${shareUrl}" readonly>
			  <div class="dialog-buttons">
				  <button class="dialog-button cancel" onclick="closeShareDialog()">关闭</button>
				  <button class="dialog-button confirm" onclick="copyShareLink()">复制链接</button>
			  </div>
		  `;

		const qrCodeContainerInDialog = dialog.querySelector(
			'#dialog-qr-code-container',
		);

		if (qrCodeContainerInDialog) {
			try {
				await loadQRCodeLibrary();

				new QRCode(qrCodeContainerInDialog, {
					text: shareUrl,
					width: 128,
					height: 128,
					colorDark: '#000000',
					colorLight: '#ffffff',
					correctLevel: QRCode.CorrectLevel.H,
				});
			} catch (qrError) {
				console.error('Error loading QR code library or generating QR code:', qrError);
				qrCodeContainerInDialog.innerHTML = '<p style="color: red; text-align: center; font-size: 12px;">二维码不可用</p>';
			}
		} else {
			console.error(
				"QR code container '#dialog-qr-code-container' not found in dialog.",
			);
			dialog.innerHTML +=
				'<p style="color: red; text-align: center;">错误：无法显示二维码。</p>';
		}
	} catch (error) {
		console.error('Error sharing mindmap:', error);
		dialog.innerHTML = `
			  <h3>分享思维导图</h3>
			  <p style="color: red;">${error.message || '分享思维导图失败，请重试。'}</p>
			  <div class="dialog-buttons">
				  <button class="dialog-button cancel" onclick="closeShareDialog()">关闭</button>
			  </div>
		  `;

	} finally {
		if (shareButton) {
			shareButton.disabled = false;
			shareButton.style.opacity = '1';
		}
	}
}

const texts = [
	'用 AI 生成思维导图',
	'用 AI 生成思维导图',
	'用 AI 生成思维导图',
	'用 AI 生成思维导图',
	'您想探索什么？',
	'您想探索什么？',
	'您想探索什么？',
	'轻松研究',
	'用 AI 获取概览',
	'获取全貌',
];

function getRandomText() {
	const randomIndex = Math.floor(Math.random() * texts.length);
	return texts[randomIndex];
}

function openSearchMindmapsPopup() {
	const overlay = document.getElementById('searchMindmapsPopupOverlay');
	const searchInput = document.getElementById('popupMindmapSearchInput');
	const resultsList = document.getElementById('searchResultsList');

	if (!overlay || !searchInput || !resultsList) {
		console.error('Search popup elements not found in openSearchMindmapsPopup!');
		return;
	}

	allMindmapHistory = JSON.parse(localStorage.getItem('mindmap-history') || '[]');
	allMindmapHistory.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

	searchInput.value = '';
	filterAndDisplayMindmapsInPopup('');

	overlay.style.display = 'flex';

	setTimeout(() => {
		overlay.classList.add('active');
		setTimeout(() => searchInput.focus(), 300);
	}, 10);
}


function closeSearchMindmapsPopup() {
	const overlay = document.getElementById('searchMindmapsPopupOverlay');
	overlay.style.display = 'none';
	if (overlay) {
		overlay.classList.remove('active');
	}
}


function highlightMatch(text, term) {
	if (!term || !text) return escapeHtmlLeftSidebar(text || "");
	const termRegex = term.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&');
	const regex = new RegExp(`(${termRegex})`, 'gi');
	return text.split(regex).map(part =>
		regex.test(part) ? `<mark class="search-highlight">${escapeHtmlLeftSidebar(part)}</mark>` : escapeHtmlLeftSidebar(part)
	).join('');
}

function getSearchableMarkdown(item) {
	let content = item.markdown || item.mindmap || item.mmjson || "";
	if (content && typeof content === 'string' && content.trim().startsWith('{')) {
		try {
			return window.mmJsonToMarkdown(content);
		} catch (e) {
			console.warn('Failed to convert JSON to Markdown for search', e);
		}
	}
	return content;
}

function getContentSnippet(markdown, term) {
	if (!term || !markdown) return "";
	const lines = markdown.split(/\r?\n/);
	const lowerTerm = term.toLowerCase();

	for (let line of lines) {
		const trimmedLine = line.trim();
		if (!trimmedLine) continue;
		if (trimmedLine.toLowerCase().includes(lowerTerm)) {
			return trimmedLine
				.replace(/^#+\s*/, "")
				.replace(/^[-*+]\s+/, "")
				.replace(/^\d+\.\s+/, "")
				.trim();
		}
	}
	return "";
}

function renderSearchMindmapResults(mindmapsToDisplay) {
	const resultsList = document.getElementById('searchResultsList');
	const searchInput = document.getElementById('popupMindmapSearchInput');

	if (!resultsList) {
		console.error('Search results list element not found!');
		return;
	}

	if (mindmapsToDisplay.length === 0) {
		resultsList.innerHTML = `
            <div class="no-results-message">
                <h3>${searchInput?.value.trim()
				? '未找到结果'
				: '开始输入以搜索'
			}</h3>
                <p>${searchInput?.value.trim()
				? '请尝试其他搜索词。'
				: '您的思维导图将显示在这里。'
			}</p>
            </div>
        `;
		return;
	}

	const deriveTopic = (entry) => {
		try {
			const s = entry.mindmap || entry.mmjson || '';
			if (s && typeof s === 'string' && s.trim().startsWith('{')) {
				const obj = JSON.parse(s);
				const root = obj['mm-node'] || obj.mmNode || obj;
				const t = String(root?.content || '').trim();
				return t || '思维导图';
			}
			if (entry.markdown) {
				const m = String(entry.markdown).match(/^#{1,6}\s+(.*)$/m);
				if (m) return m[1].trim();
			}
		} catch { }
		return '思维导图';
	};

	const searchTerm = searchInput?.value.trim() || "";

	resultsList.innerHTML = mindmapsToDisplay
		.map(
			(item) => {
				const markdown = getSearchableMarkdown(item);
				const title = deriveTopic(item);
				const highlightedTitle = highlightMatch(title, searchTerm);
				const snippet = getContentSnippet(markdown, searchTerm);

				const showSnippet = searchTerm && snippet && !title.toLowerCase().includes(searchTerm.toLowerCase());

				return `
        <div class="mindmap-item" data-id="${item.id}">
            <div class="mindmap-info">
                <div class="mindmap-title">${highlightedTitle}</div>
                ${showSnippet ? `<div class="search-content-snippet">${highlightMatch(snippet, searchTerm)}</div>` : ''}
                <div class="mindmap-date">${formatDateLeftSidebar(item.timestamp)}</div>
            </div>
        </div>
        `;
			}
		)
		.join('');

	resultsList.querySelectorAll('.mindmap-item').forEach((item) => {
		item.addEventListener('click', function (e) {
			if (!e.target.closest('button')) {
				const id = this.getAttribute('data-id');
				openMindmapFromSearchPopup(id);
			}
		});
	});
}

function filterAndDisplayMindmapsInPopup(searchTerm) {
	const lowerCaseSearchTerm = searchTerm.toLowerCase().trim();

	const deriveTopic = (entry) => {
		try {
			const s = entry.mindmap || entry.mmjson || '';
			if (s && typeof s === 'string' && s.trim().startsWith('{')) {
				const obj = JSON.parse(s);
				const root = obj['mm-node'] || obj.mmNode || obj;
				const t = String(root?.content || '').trim();
				return t || '思维导图';
			}
			if (entry.markdown) {
				const m = String(entry.markdown).match(/^#{1,6}\s+(.*)$/m);
				if (m) return m[1].trim();
			}
		} catch { }
		return '思维导图';
	};

	const filteredMindmaps = lowerCaseSearchTerm ?
		allMindmapHistory.filter((item) => {
			const markdown = getSearchableMarkdown(item);
			const title = deriveTopic(item).toLowerCase();
			return title.includes(lowerCaseSearchTerm) || markdown.toLowerCase().includes(lowerCaseSearchTerm);
		}) :
		allMindmapHistory;

	renderSearchMindmapResults(filteredMindmaps);
}


function openMindmapFromSearchPopup(id) {
	closeSearchMindmapsPopup();
	openMindmapLeftSidebar(id);
}

function saveMindmapToHistory(mindmapJsonStr, idOverride = null) {
	const history = JSON.parse(localStorage.getItem('mindmap-history') || '[]');
	const timestamp = new Date().toISOString();
	const newId = idOverride || Date.now();

	history.push({
		mindmap: mindmapJsonStr,
		timestamp,
		id: newId
	});

	if (history.length > 100) {
		history.shift();
	}

	localStorage.setItem('mindmap-history', JSON.stringify(history));
	markLearningPathMindmapComplete(newId, mindmapJsonStr);

	if (document.getElementById('searchMindmapsPopupOverlay')?.classList.contains('active')) {
		allMindmapHistory = JSON.parse(localStorage.getItem('mindmap-history') || '[]');
		allMindmapHistory.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
		filterAndDisplayMindmapsInPopup(document.getElementById('popupMindmapSearchInput')?.value || '');
	}
	if (typeof loadMindmapsLeftSidebar === 'function') {
		loadMindmapsLeftSidebar();
	}

	return newId;
}

window.openSearchMindmapsPopup = openSearchMindmapsPopup;
window.closeSearchMindmapsPopup = closeSearchMindmapsPopup;
window.openMindmapFromSearchPopup = openMindmapFromSearchPopup;

window.fitMindmapSvg = function () {
	try {
		const svg = document.querySelector('#svg-output > svg') || document.getElementById('mindmap')?.querySelector('svg');
		if (!svg) return;

		svg.style.transition = 'transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)';

		svg.style.transformOrigin = '0 0';
		svg.style.transform = 'scale(1) translate(0px, 0px)';

		setTimeout(() => {
			svg.style.transition = '';
		}, 500);
	} catch (e) {
		console.warn('Failed to reset SVG transform:', e);
	}
};


function initializeDownloadFeatures() {
	if (window.downloadFeaturesInitialized) return;
	window.downloadFeaturesInitialized = true;

	const downloadBtn = document.getElementById('download-mindmap-btn');
	const popup = document.getElementById('download-options-popup');
	const closeBtn = document.getElementById('close-download-options-popup');
	const formatSelect = document.getElementById('download-format');
	const downloadFormatBtn = document.getElementById('download-btn');

	if (!downloadBtn || !popup) return;

	downloadBtn.addEventListener('click', function () {
		popup.style.display = 'flex';
		popup.classList.add('show');
	});

	closeBtn?.addEventListener('click', function () {
		popup.classList.remove('show');
		setTimeout(() => {
			popup.style.display = 'none';
		}, 300);
	});

	popup.addEventListener('click', function (event) {
		if (event.target === popup) {
			popup.classList.remove('show');
			setTimeout(() => {
				popup.style.display = 'none';
			}, 300);
		}
	});

	downloadFormatBtn?.addEventListener('click', function () {
		const format = formatSelect?.value || 'jpg';
		downloadMindmap(format);
		popup.classList.remove('show');
		setTimeout(() => {
			popup.style.display = 'none';
		}, 300);
	});

	document.getElementById('print-btn')?.addEventListener('click', function () {
		printMindmap();
		popup.classList.remove('show');
		setTimeout(() => {
			popup.style.display = 'none';
		}, 300);
	});
}

function initializeHelpPopup() {
	const helpBtn = document.getElementById('help-btn');
	const helpPopup = document.getElementById('help-popup');
	const closeHelpBtn = document.getElementById('close-help-popup');
	const closeHelpBtnAction = document.getElementById('close-help-btn-action');

	if (!helpBtn || !helpPopup) return;

	const openPopup = () => {
		helpPopup.style.display = 'flex';
		setTimeout(() => {
			helpPopup.classList.add('show');
		}, 10);
	};

	helpBtn.addEventListener('click', openPopup);

	const closePopup = () => {
		helpPopup.classList.remove('show');
		setTimeout(() => {
			helpPopup.style.display = 'none';
		}, 300);

		const urlParams = new URLSearchParams(window.location.search);
		if (urlParams.has('show')) {
			urlParams.delete('show');
			const newUrl = urlParams.toString()
				? `${window.location.pathname}?${urlParams.toString()}`
				: window.location.pathname;
			window.history.replaceState({}, '', newUrl);
		}
	};

	closeHelpBtn?.addEventListener('click', closePopup);
	closeHelpBtnAction?.addEventListener('click', closePopup);

	helpPopup.addEventListener('click', function (event) {
		if (event.target === helpPopup) {
			closePopup();
		}
	});

	const urlParams = new URLSearchParams(window.location.search);
	if (urlParams.has('show') && urlParams.get('show') === 'helppopup') {
		openPopup();
	}
}

document.getElementById('mm-fit')?.addEventListener('click', function (e) {
	e.preventDefault();
	e.stopPropagation();
	try {
		if (typeof window.fitMindmapSvg === 'function') {
			window.fitMindmapSvg();
		} else {
			const btn = document.getElementById('fit-screen-btn');
			if (btn) btn.click();
		}
	} catch (err) {
		console.warn('Fit-to-screen failed:', err);
	}
});

const zoomInBtn = document.getElementById('zoom-in-btn');
const zoomOutBtn = document.getElementById('zoom-out-btn');
const zoomControls = document.getElementById('zoom-controls');

if (zoomInBtn && zoomOutBtn) {
	zoomInBtn.addEventListener('click', function (e) {
		e.preventDefault();
		e.stopPropagation();
		if (window.zoomMindMap) {
			const svg = preview.querySelector('svg');
			if (!svg) return;
			closeContextMenus();

			svg.style.transition = 'transform 0.3s ease';

			window.zoomMindMap(1.2);

			setTimeout(() => {
				svg.style.transition = '';
			}, 500);
		}
	});

	zoomOutBtn.addEventListener('click', function (e) {
		e.preventDefault();
		e.stopPropagation();
		if (window.zoomMindMap) {
			const svg = preview.querySelector('svg');
			if (!svg) return;
			closeContextMenus();

			svg.style.transition = 'transform 0.3s ease';

			window.zoomMindMap(0.8);

			setTimeout(() => {
				svg.style.transition = '';
			}, 500);
		}
	});
}

function updateZoomControlsVisibility() {
	const mindmapContainer = document.getElementById('mindmap');
	const svg = mindmapContainer?.querySelector('svg');
	if (zoomControls) {
		if (svg && mindmapContainer.children.length > 0) {
			zoomControls.classList.add('show');
		} else {
			zoomControls.classList.remove('show');
		}
	}
}

window.updateZoomControlsVisibility = updateZoomControlsVisibility;



function printMindmap() {
	try {
		const mindmapContainer = document.getElementById('mindmap');
		const svg = mindmapContainer?.querySelector('svg');

		if (!svg) {
			throw new Error('没有可打印的思维导图。');
		}

		const printWindow = window.open('', '_blank', 'width=800,height=600');
		if (!printWindow) {
			throw new Error('打开打印窗口失败。请允许此网站的弹窗。');
		}

		const bbox = svg.getBBox();
		const padding = 40;
		const width = bbox.width + padding * 2;
		const height = bbox.height + padding * 2;

		const svgCopy = svg.cloneNode(true);
		svgCopy.setAttribute('width', width);
		svgCopy.setAttribute('height', height);
		svgCopy.setAttribute('viewBox', `${bbox.x - padding} ${bbox.y - padding} ${width} ${height}`);

		const printContent = `
			<!DOCTYPE html>
			<html>
			<head>
				<title>${currentMindmapTitle || '思维导图'} - 打印</title>
				<style>
					@media print {
						@page {
							size: auto;
						}
						body {
							margin: 0;
						}
						.print-container {
							width: 100%;
							max-width: none !important;
							height: auto;
							display: flex;
							justify-content: center;
							align-items: center;
						}
						.mindmap-svg {
							max-width: 100%;
							height: auto;
							page-break-inside: avoid;
						}
					}
					body {
						margin: 0;
						padding: 10px;
						font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
					}
					.print-container {
						width: 100%;
						display: flex;
						justify-content: center;
						align-items: center;
					}
					.mindmap-svg {
						max-width: 100%;
						height: auto;
					}
				</style>
			</head>
			<body>
				<div class="print-container">
					<div class="mindmap-svg">
						${new XMLSerializer().serializeToString(svgCopy)}
					</div>
				</div>
			</body>
			</html>
		`;

		printWindow.document.write(printContent);
		printWindow.document.close();

		printWindow.onload = function () {
			printWindow.focus();
			printWindow.print();

			printWindow.onafterprint = function () {
				printWindow.close();
			};
		};


	} catch (error) {
		console.error('Print error:', error);
		alert('准备打印思维导图时出错：' + error.message);
	}
}

function trackEvent(eventName, params = {}) {
}

const DownloadHandler = {
	getMindmapElements() {
		const container = document.getElementById('mindmap');
		const svg = container?.querySelector('svg');
		const topic = currentMindmapTitle || 'mindmap';

		if (!svg || container.children.length === 0) {
			throw new Error('没有可下载的思维导图。');
		}

		return {
			svg,
			topic
		};
	},

	async regenerateSVGForDownload() {
		const jsonStr = window.currentMarkdown;
		if (!jsonStr || typeof jsonStr !== 'string') {
			window.location.reload();
			return; 
		}

		let dataObj;
		try {
			dataObj = JSON.parse(jsonStr);
		} catch {
			throw new Error('无效的思维导图数据。');
		}

		if (!dataObj['mm-settings']) {
			dataObj['mm-settings'] = {};
		}

		dataObj['mm-settings']['font-family'] = 'system-ui';

		const modifiedJsonStr = JSON.stringify(dataObj);
		if (typeof window.__mmwInitEngine === 'function') {
			await window.__mmwInitEngine();
		}

		if (typeof window.generateSVG !== 'function') {
			throw new Error('渲染引擎不可用。请确保思维导图已加载。');
		}

		const svgString = window.generateSVG(modifiedJsonStr);

		const parser = new DOMParser();
		const svgDoc = parser.parseFromString(svgString, 'image/svg+xml');
		const svgElement = svgDoc.documentElement;

		return svgElement;
	},

	getSVGData(svg, padding = 24, forceSystemFont = false) {
		const svgCopy = svg.cloneNode(true);
		try {
			if (svgCopy.style) {
				svgCopy.style.removeProperty('transform');
				svgCopy.style.removeProperty('transform-origin');
			}
		} catch { }

		let baseW = 0;
		let baseH = 0;
		const viewBox = svg.getAttribute('viewBox');
		if (viewBox) {
			const vb = viewBox.split(/\s+|,/).map(Number);
			if (vb.length === 4 && isFinite(vb[2]) && isFinite(vb[3])) {
				baseW = vb[2];
				baseH = vb[3];
			}
		}
		if (!(baseW > 0 && baseH > 0)) {
			baseW = parseFloat(svg.getAttribute('width')) || svg.clientWidth || 0;
			baseH = parseFloat(svg.getAttribute('height')) || svg.clientHeight || 0;
		}

		baseW = Math.max(1, Math.round(baseW));
		baseH = Math.max(1, Math.round(baseH));

		const outW = baseW + padding * 2;
		const outH = baseH + padding * 2;

		svgCopy.removeAttribute('width');
		svgCopy.removeAttribute('height');
		svgCopy.setAttribute('viewBox', `${-padding} ${-padding} ${baseW + padding * 2} ${baseH + padding * 2}`);
		svgCopy.style.fontFamily = 'system-ui';

		if (forceSystemFont) {
			const allText = svgCopy.querySelectorAll('text, tspan');
			allText.forEach(t => {
				t.style.fontFamily = 'system-ui';
				t.setAttribute('font-family', 'system-ui');
			});
		}

		const svgContent = new XMLSerializer().serializeToString(svgCopy);
		return { svgContent, width: outW, height: outH };
	},

	async loadWatermarkSVG() {
		try {
			const response = await fetch('/mind-map-wizard/img/mmw-watermark.svg');
			if (!response.ok) {
				throw new Error('加载水印失败');
			}
			return await response.text();
		} catch (error) {
			console.warn('Could not load watermark:', error);
			return null;
		}
	},

	addWatermarkToSVG(svgContent, watermarkSVG, width, height) {
		if (!watermarkSVG) return svgContent;

		const parser = new DOMParser();
		const svgDoc = parser.parseFromString(svgContent, 'image/svg+xml');
		const watermarkDoc = parser.parseFromString(watermarkSVG, 'image/svg+xml');

		const mainSvg = svgDoc.documentElement;
		const watermarkElem = watermarkDoc.documentElement;

		const viewBox = mainSvg.getAttribute('viewBox');
		let viewBoxValues = [0, 0, width, height];
		if (viewBox) {
			viewBoxValues = viewBox.split(/\s+|,/).map(Number);
		}
		const [viewX, viewY, viewWidth, viewHeight] = viewBoxValues;

		const wViewBoxAttr = watermarkElem.getAttribute('viewBox');
		let wW, wH;
		let wViewBoxStr = wViewBoxAttr;

		if (wViewBoxAttr) {
			const wViewBox = wViewBoxAttr.split(/\s+|,/).map(Number);
			wW = wViewBox[2];
			wH = wViewBox[3];
		} else {
			wW = parseFloat(watermarkElem.getAttribute('width')) || 100;
			wH = parseFloat(watermarkElem.getAttribute('height')) || 100;
			wViewBoxStr = `0 0 ${wW} ${wH}`;
		}

		const minDimension = Math.min(viewWidth, viewHeight);
		let targetWidth = minDimension * 0.2;

		targetWidth = Math.max(200, Math.min(viewWidth * 0.1, targetWidth));

		const aspectRatio = wW / wH;
		const targetHeight = targetWidth / aspectRatio;

		const padding = 10;

		const nestedSvg = svgDoc.createElementNS('http://www.w3.org/2000/svg', 'svg');

		if (wViewBoxStr) nestedSvg.setAttribute('viewBox', wViewBoxStr);

		const xPos = viewX + padding;
		const yPos = (viewY + viewHeight) - targetHeight - padding;

		nestedSvg.setAttribute('x', xPos);
		nestedSvg.setAttribute('y', yPos);
		nestedSvg.setAttribute('width', targetWidth);
		nestedSvg.setAttribute('height', targetHeight);
		nestedSvg.setAttribute('opacity', '0.8');

		Array.from(watermarkElem.children).forEach(child => {
			nestedSvg.appendChild(child.cloneNode(true));
		});

		mainSvg.appendChild(nestedSvg);

		return new XMLSerializer().serializeToString(mainSvg);
	},


	triggerDownload(blob, filename) {
		const url = URL.createObjectURL(blob);
		const link = document.createElement('a');
		link.href = url;
		link.download = filename;
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		URL.revokeObjectURL(url);

		const fileExtension = filename.split('.').pop();
		trackEvent('mm_downloaded', {
			download_format: fileExtension,
			watermark_inserted: 'false'
		});
	},

	downloadMarkdown(topic) {
		let content = typeof currentMarkdown === 'string' ? currentMarkdown : '';
		if (content.trim().startsWith('{')) {
			try {
				const obj = JSON.parse(content);
				const root = obj['mm-node'] || obj.mmNode || obj;
				const lines = [];
				const maxHeading = 6;
				const cleanMarkdownNotes = (rawNotes) => {
					let notes = String(rawNotes || '')
						.replace(/<!--MM_CITATIONS_DATA:[\s\S]*?-->/g, '')
						.trim();

					if (!notes) return '';

					if (/<[a-z][\s\S]*>/i.test(notes)) {
						try {
							const parser = new DOMParser();
							const doc = parser.parseFromString(`<div>${notes}</div>`, 'text/html');
							doc.querySelectorAll('.yt-embed, .citation-tooltip, .notes-resources').forEach(el => el.remove());

							if (typeof window.domToMarkdown === 'function') {
								notes = window.domToMarkdown(doc.body);
							} else {
								doc.querySelectorAll('br').forEach(el => el.replaceWith('\n'));
								doc.querySelectorAll('a[href]').forEach(el => {
									const href = el.getAttribute('href') || '';
									const text = el.textContent || href;
									el.replaceWith(text === href ? text : `[${text}](${href})`);
								});
								notes = doc.body.textContent || '';
							}
						} catch { }
					}

					return notes
						.replace(/\n{3,}/g, '\n\n')
						.trim();
				};

				const appendNotes = (rawNotes) => {
					const notes = cleanMarkdownNotes(rawNotes);
					if (!notes) return;
					lines.push('');
					for (const noteLine of notes.split(/\r?\n/)) {
						lines.push(noteLine.trim() ? `> ${noteLine}` : '>');
					}
				};

				(function walk(node, level) {
					if (!node || typeof node !== 'object') return;
					const text = String(node.content ?? '').trim();
					if (text) {
						if (level <= maxHeading) {
							lines.push(`${'#'.repeat(level)} ${text}`.trim());
						} else {
							lines.push(`- ${text}`.trim());
						}
					}
					if (node.notes && typeof node.notes === 'string') {
						appendNotes(node.notes);
					}
					if (Array.isArray(node.children)) {
						for (const child of node.children) walk(child, level + 1);
					}
				})(root, 1);
				content = lines.join('\n');
			} catch { }
		}
		const blob = new Blob([content], { type: 'text/markdown' });
		this.triggerDownload(blob, `${topic}.md`);
	},

	async downloadSVG(svgContent, width, height, topic) {
		const watermarkSVG = await this.loadWatermarkSVG();
		const watermarkedSVG = this.addWatermarkToSVG(svgContent, watermarkSVG, width, height);

		const blob = new Blob([watermarkedSVG], {
			type: 'image/svg+xml;charset=utf-8'
		});
		this.triggerDownload(blob, `${topic}.svg`);
	},

	getOutlineData() {
		try {
			const editor = document.getElementById('json-editor');
			const jsonStr = editor?.value || window.currentMarkdown || '';
			if (!jsonStr.trim().startsWith('{')) return null;
			return JSON.parse(jsonStr);
		} catch {
			return null;
		}
	},

	async addOutlinePage(pdf, dataObj) {
		const root = dataObj?.['mm-node'] || dataObj?.mmNode;
		if (!root) return;

		const PW = 595.28, PH = 841.89;
		const ML = 56, MT = 64, MB = 52;
		const UW = PW - ML - 56;
		const INDENT = 14;

		const C_PRIMARY = [29, 29, 31];
		const C_SECONDARY = [99, 99, 102];
		const C_TERTIARY = [142, 142, 147];
		const C_QUATERNARY = [174, 174, 178];
		const C_SEPARATOR = [209, 209, 214];
		const C_GUIDE = [220, 220, 224];
		const C_HDR_BG = [246, 246, 246];

		const imageRefs = new Set();
		const collectImageRefs = (node) => {
			if (!node || typeof node !== 'object') return;
			const t = String(node.content ?? '').trim();
			if (window.ImageHandler?.isImageRef(t)) imageRefs.add(t);
			if (Array.isArray(node.children)) node.children.forEach(collectImageRefs);
		};
		collectImageRefs(root);

		const imageDataMap = {};
		if (imageRefs.size > 0 && window.ImageHandler) {
			await Promise.all([...imageRefs].map(async (ref) => {
				try {
					const url = await window.ImageHandler.loadImageAsync(ref);
					if (!url) return;
					await new Promise((resolve) => {
						const tmpImg = new Image();
						tmpImg.onload = () => {
							const canvas = document.createElement('canvas');
							canvas.width = tmpImg.naturalWidth || 400;
							canvas.height = tmpImg.naturalHeight || 300;
							const ctx = canvas.getContext('2d');
							ctx.fillStyle = '#ffffff';
							ctx.fillRect(0, 0, canvas.width, canvas.height);
							ctx.drawImage(tmpImg, 0, 0);
							imageDataMap[ref] = {
								dataUrl: canvas.toDataURL('image/jpeg', 0.85),
								width: canvas.width,
								height: canvas.height,
							};
							canvas.remove();
							resolve();
						};
						tmpImg.onerror = () => resolve();
						tmpImg.src = url;
					});
				} catch { }
			}));
		}

		pdf.addPage('a4', 'portrait');

		pdf.setFillColor(...C_HDR_BG);
		pdf.rect(0, 0, PW, 70, 'F');
		pdf.setDrawColor(...C_SEPARATOR);
		pdf.setLineWidth(0.5);
		pdf.line(0, 70, PW, 70);

		const titleText = String(root.content || '思维导图').trim();
		pdf.setFont('helvetica', 'bold');
		pdf.setFontSize(19);
		pdf.setTextColor(...C_PRIMARY);
		const titleLines = pdf.splitTextToSize(titleText, UW);
		pdf.text(titleLines, ML, titleLines.length > 1 ? 23 : 31);

		pdf.setFont('helvetica', 'normal');
		pdf.setFontSize(9);
		pdf.setTextColor(...C_TERTIARY);
		pdf.text('大纲', ML, 57);

		let y = 88;
		let pageCount = 1;

		const addFooter = () => {
			pdf.setFont('helvetica', 'normal');
			pdf.setFontSize(8);
			pdf.setTextColor(...C_QUATERNARY);
			pdf.text('mindmapwizard.com', PW / 2, PH - 24, { align: 'center' });
		};

		const ensureSpace = (needed) => {
			if (y + needed > PH - MB) {
				addFooter();
				pdf.addPage('a4', 'portrait');
				pageCount++;
				y = MT;
			}
		};

		const cleanNotesText = (raw) =>
			raw
				.replace(/<!--MM_CITATIONS_DATA:[\s\S]*?-->/g, '')
				.replace(/<[^>]*>/g, '')
				.replace(/\*\*/g, '')
				.replace(/\*/g, '')
				.replace(/^#{1,6}\s+/gm, '')
				.trim();

		const parseLinkSegments = (rawText) => {
			const segs = [];
			const re = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g;
			let lastIdx = 0, m;
			while ((m = re.exec(rawText)) !== null) {
				if (m.index > lastIdx) segs.push({ type: 'text', content: rawText.slice(lastIdx, m.index) });
				segs.push({ type: 'link', text: m[1], url: m[2] });
				lastIdx = m.index + m[0].length;
			}
			if (lastIdx < rawText.length) segs.push({ type: 'text', content: rawText.slice(lastIdx) });
			if (segs.length === 1 && segs[0].type === 'text' && /^https?:\/\/\S+$/.test(segs[0].content.trim())) {
				const t = segs[0].content.trim();
				return [{ type: 'link', text: t, url: t }];
			}
			return segs;
		};

		const getVisibleText = (segs) => segs.map(s => s.type === 'link' ? s.text : s.content).join('');

		const renderLines = (vis, segs, textX, baseY, textW, fSize, lineH, normalColor) => {
			const lines = pdf.splitTextToSize(vis, textW);
			const hasLink = segs.some(s => s.type === 'link');

			if (!hasLink) {
				pdf.setTextColor(...normalColor);
				pdf.text(lines, textX, baseY);
				return lines.length;
			}

			const urlMap = [];
			for (const seg of segs) {
				const t = seg.type === 'link' ? seg.text : seg.content;
				const url = seg.type === 'link' ? seg.url : null;
				for (let i = 0; i < t.length; i++) urlMap.push(url);
			}

			let charIdx = 0;
			for (let li = 0; li < lines.length; li++) {
				const line = lines[li];
				const lineY = baseY + li * lineH;
				let x = textX;
				let runStart = 0;

				while (runStart < line.length) {
					const runUrl = charIdx + runStart < urlMap.length ? urlMap[charIdx + runStart] : null;
					let runEnd = runStart + 1;
					while (runEnd < line.length) {
						const nextUrl = charIdx + runEnd < urlMap.length ? urlMap[charIdx + runEnd] : null;
						if (nextUrl !== runUrl) break;
						runEnd++;
					}
					const runText = line.slice(runStart, runEnd);
					const w = pdf.getTextWidth(runText);
					if (runUrl) {
						pdf.setTextColor(0, 102, 204);
						pdf.text(runText, x, lineY);
						pdf.link(x, lineY - fSize * 0.85, w, fSize * 1.1, { url: runUrl });
					} else {
						pdf.setTextColor(...normalColor);
						pdf.text(runText, x, lineY);
					}
					x += w;
					runStart = runEnd;
				}

				charIdx += line.length;
				if (li < lines.length - 1) charIdx++;
			}

			pdf.setTextColor(...normalColor);
			return lines.length;
		};

		const renderNode = (node, level) => {
			if (!node || typeof node !== 'object') return;
			const text = String(node.content ?? '').trim();

			if (text) {
				if (window.ImageHandler?.isImageRef(text)) {
					const imgData = imageDataMap[text];
					if (imgData) {
						const indent = level >= 3 ? (level - 2) * INDENT : 0;
						const maxW = UW - indent;
						const maxH = 160;
						const aspect = imgData.width / imgData.height;
						let imgW = Math.min(maxW, imgData.width);
						let imgH = imgW / aspect;
						if (imgH > maxH) { imgH = maxH; imgW = imgH * aspect; }
						ensureSpace(imgH + 12);
						y += 6;
						pdf.addImage(imgData.dataUrl, 'JPEG', ML + indent, y, imgW, imgH);
						y += imgH + 6;
					}
				} else if (level === 2) {
					const fSize = 12.5;
					const lineH = fSize * 1.5;
					pdf.setFont('helvetica', 'bold');
					pdf.setFontSize(fSize);
					const segs = parseLinkSegments(text);
					const vis = getVisibleText(segs);
					const lines = pdf.splitTextToSize(vis, UW);
					const blockH = lines.length * lineH;

					ensureSpace(blockH + 30);
					y += 28;

					pdf.setDrawColor(...C_SEPARATOR);
					pdf.setLineWidth(0.5);
					pdf.line(ML, y - 8, ML + UW, y - 8);

					renderLines(vis, segs, ML, y + fSize * 0.82, UW, fSize, lineH, C_PRIMARY);
					y += blockH;

				} else {
					const indent = (level - 2) * INDENT;
					const fSize = level === 3 ? 10.5 : (level === 4 ? 10 : 9.5);
					const fStyle = level === 3 ? 'bold' : 'normal';
					const fColor = level === 3 ? C_SECONDARY : (level === 4 ? C_TERTIARY : C_QUATERNARY);
					const lineH = fSize * 1.45;
					const textX = ML + indent;
					const textW = UW - indent;

					pdf.setFont('helvetica', fStyle);
					pdf.setFontSize(fSize);
					const segs = parseLinkSegments(text);
					const vis = getVisibleText(segs);
					const lines = pdf.splitTextToSize(vis, textW);
					const blockH = lines.length * lineH;

					ensureSpace(blockH + (level === 3 ? 10 : 4));
					y += level === 3 ? 8 : 3;

					renderLines(vis, segs, textX, y + fSize * 0.82, textW, fSize, lineH, fColor);
					y += blockH;
				}
			}

			if (node.notes && typeof node.notes === 'string') {
				const notes = cleanNotesText(node.notes);
				if (notes) {
					const noteIndent = (level - 2) * INDENT;
					const noteFSize = 8.5;
					const noteLineH = noteFSize * 1.4;
					const noteSegs = parseLinkSegments(notes);
					const noteVis = getVisibleText(noteSegs);

					pdf.setFont('helvetica', 'normal');
					pdf.setFontSize(noteFSize);

					const noteLines = pdf.splitTextToSize(noteVis, UW - noteIndent);
					const noteBlockH = noteLines.length * noteLineH + 4;

					ensureSpace(noteBlockH);
					y += 3;
					renderLines(noteVis, noteSegs, ML + noteIndent, y + noteFSize * 0.82, UW - noteIndent, noteFSize, noteLineH, C_QUATERNARY);
					y += noteBlockH;
				}
			}

			if (Array.isArray(node.children) && node.children.length > 0) {
				const childrenStartY = y;
				const childrenStartPage = pageCount;

				for (const child of node.children) renderNode(child, level + 1);

				if (level + 1 >= 3 && y > childrenStartY && pageCount === childrenStartPage) {
					const guideX = ML + (level - 2) * INDENT + 5;
					pdf.setDrawColor(...C_GUIDE);
					pdf.setLineWidth(0.4);
					pdf.line(guideX, childrenStartY, guideX, y - 2);
				}
			}
		};

		if (Array.isArray(root.children)) {
			for (const child of root.children) renderNode(child, 2);
		}

		addFooter();
	},

	async downloadPDF(svgContent, width, height, topic, scaleFactor = 1) {
		const watermarkSVG = await this.loadWatermarkSVG();
		const watermarkedSVG = this.addWatermarkToSVG(svgContent, watermarkSVG, width, height);

		const container = document.createElement('div');
		container.innerHTML = watermarkedSVG;
		const svgEl = container.firstElementChild;
		const svgData = new XMLSerializer().serializeToString(svgEl);

		const outlineData = this.getOutlineData();
		const img = new Image();
		img.crossOrigin = 'Anonymous';

		await new Promise((resolve, reject) => {
			img.onload = async () => {
				try {
					const pdf = new jsPDF({
						orientation: width > height ? 'landscape' : 'portrait',
						unit: 'pt',
						format: 'letter',
					});

					const pdfW = pdf.internal.pageSize.getWidth();
					const pdfH = pdf.internal.pageSize.getHeight();

					const margin = 36;
					const maxW = pdfW - margin * 2;
					const maxH = pdfH - margin * 2;
					const aspect = width / height;

					let renderW = maxW;
					let renderH = renderW / aspect;
					if (renderH > maxH) {
						renderH = maxH;
						renderW = renderH * aspect;
					}

					const targetPxW = Math.max(Math.round(width * scaleFactor), 100);
					const targetPxH = Math.max(Math.round(height * scaleFactor), 100);

					const canvas = document.createElement('canvas');
					canvas.width = Math.max(1, targetPxW);
					canvas.height = Math.max(1, targetPxH);
					const ctx = canvas.getContext('2d');

					ctx.fillStyle = '#ffffff';
					ctx.fillRect(0, 0, canvas.width, canvas.height);

					ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

					const x = (pdfW - renderW) / 2;
					const y = (pdfH - renderH) / 2;

					pdf.addImage(
						canvas.toDataURL('image/jpeg', 0.92),
						'JPEG',
						x,
						y,
						renderW,
						renderH
					);

					if (outlineData) {
						await this.addOutlinePage(pdf, outlineData);
					}

					pdf.save(`${topic}.pdf`);
					canvas.remove();

					trackEvent('mm_downloaded', {
						download_format: 'pdf',
						watermark_inserted: 'false',
						quality_scale: scaleFactor
					});
					resolve();
				} catch (error) {
					reject(error);
				}
			};
			img.onerror = () => reject(new Error('渲染 PDF 图片失败。'));

			img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
		});
	},

	async downloadJPG(svg, topic) {
		const { svgContent, width, height } = this.getSVGData(svg, 24, true);

		const watermarkSVG = await this.loadWatermarkSVG();
		const watermarkedSVG = this.addWatermarkToSVG(svgContent, watermarkSVG, width, height);

		const tempSvg = document.createElement('div');
		tempSvg.innerHTML = watermarkedSVG;
		const svgElement = tempSvg.firstElementChild;
		const svgData = new XMLSerializer().serializeToString(svgElement);

		const img = new Image();
		img.crossOrigin = 'Anonymous';

		img.onload = () => {
			const maxSide = 3000;
			const aspect = width / height;
			let outW = width;
			let outH = height;
			if (Math.max(width, height) > maxSide) {
				if (width >= height) {
					outW = maxSide;
					outH = Math.round(maxSide / aspect);
				} else {
					outH = maxSide;
					outW = Math.round(maxSide * aspect);
				}
			}

			const canvas = document.createElement('canvas');
			canvas.width = Math.max(1, outW);
			canvas.height = Math.max(1, outH);
			const ctx = canvas.getContext('2d');

			ctx.fillStyle = '#ffffff';
			ctx.fillRect(0, 0, canvas.width, canvas.height);

			ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

			this.triggerDownload(
				this.dataURLToBlob(canvas.toDataURL('image/jpeg', 0.92)),
				`${topic}.jpg`,
			);
			canvas.remove();
		};

		img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
	},

	dataURLToBlob(dataURL) {
		const arr = dataURL.split(',');
		const mime = arr[0].match(/:(.*?);/)[1];
		const bstr = atob(arr[1]);
		let n = bstr.length;
		const u8arr = new Uint8Array(n);
		while (n--) {
			u8arr[n] = bstr.charCodeAt(n);
		}
		return new Blob([u8arr], {
			type: mime
		});
	},
};

window.jsPDF = window.jspdf.jsPDF;

async function downloadMindmap(format) {
	try {
		const {
			topic
		} = DownloadHandler.getMindmapElements();


		if (format === 'markdown') {
			DownloadHandler.downloadMarkdown(topic);
			return;
		}


		const svgWithSystemFont = await DownloadHandler.regenerateSVGForDownload();

		const {
			svgContent,
			width,
			height
		} = DownloadHandler.getSVGData(svgWithSystemFont, 24, true);

		switch (format) {
			case 'svg':
				await DownloadHandler.downloadSVG(svgContent, width, height, topic);
				break;
			case 'pdf':
				await DownloadHandler.downloadPDF(svgContent, width, height, topic);
				break;
			case 'jpg':
				await DownloadHandler.downloadJPG(svgWithSystemFont, topic);
				break;
			default:
				throw new Error(`Unsupported format: ${format}`);
		}

		document.getElementById('download-options-popup').style.display = 'none';
	} catch (error) {
		trackErrorEvent(`Download failed for format: ${format}. Reason: ${error.message}`);
		console.error('Download error:', error);
		alert(error.message);
	}
}

async function downloadAsImage() {
	const format = 'png';
	try {

		const svgWithSystemFont = await DownloadHandler.regenerateSVGForDownload();

		const { svgContent, width, height } = DownloadHandler.getSVGData(svgWithSystemFont, 24, true);

		const watermarkSVG = await DownloadHandler.loadWatermarkSVG();
		const watermarkedSVG = DownloadHandler.addWatermarkToSVG(svgContent, watermarkSVG, width, height);

		const img = new Image();
		img.crossOrigin = 'Anonymous';
		img.onload = function () {
			const maxSide = 3000;
			const aspect = width / height;
			let outW = width;
			let outH = height;
			if (Math.max(width, height) > maxSide) {
				if (width >= height) {
					outW = maxSide;
					outH = Math.round(maxSide / aspect);
				} else {
					outH = maxSide;
					outW = Math.round(maxSide * aspect);
				}
			}

			const canvas = document.createElement('canvas');
			canvas.width = Math.max(1, outW);
			canvas.height = Math.max(1, outH);

			const ctx = canvas.getContext('2d');

			ctx.fillStyle = '#ffffff';
			ctx.fillRect(0, 0, canvas.width, canvas.height);

			ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

			const url = canvas.toDataURL('image/png');
			const a = document.createElement('a');
			a.href = url;
			a.download = 'mindmap.png';
			a.click();

			trackEvent('mm_downloaded', {
				download_format: format,
				watermark_inserted: 'false'
			});
		};

		const svgBase64 = btoa(unescape(encodeURIComponent(watermarkedSVG)));
		img.src = `data:image/svg+xml;base64,${svgBase64}`;

		document.getElementById('download-options-popup').style.display = 'none';
	} catch (error) {
		trackErrorEvent(`Download as image (PNG) failed. Reason: ${error.message}`);
		console.error('Download as image error:', error);
		alert(error.message);
	}
}


window.addEventListener('load', () => {
	try {
		const historyKey = 'mindmap-history';
		const existingHistoryJSON = localStorage.getItem(historyKey);

		if (existingHistoryJSON) {
			let history = [];
			try { history = JSON.parse(existingHistoryJSON) || []; } catch { history = []; }
			let changed = false;

			const md2json = (md, fallbackTitle = '思维导图') => {
				try {
					const lines = String(md || '').split(/\r?\n/);
					let rootContent = fallbackTitle;
					let firstHeadingIndex = -1;
					for (let i = 0; i < lines.length; i++) {
						const m = lines[i].trim().match(/^(#{1,6})\s+(.*)$/);
						if (m) { rootContent = m[2].trim(); firstHeadingIndex = i; break; }
					}
					const root = { content: rootContent, children: [] };
					const stack = [{ level: 1, node: root }];

					lines.forEach((raw, index) => {
						const line = raw.trim();
						if (!line) return;
						if (index === firstHeadingIndex) return;

						const hm = line.match(/^(#{1,6})\s+(.*)$/);
						if (hm) {
							const lvl = hm[1].length;
							const text = hm[2].trim();
							const node = { content: text, children: [] };
							while (stack.length && stack[stack.length - 1].level >= lvl) stack.pop();
							const parent = stack[stack.length - 1]?.node || root;
							parent.children.push(node);
							stack.push({ level: lvl, node });
							return;
						}
						const bm = line.match(/^[-*+]\s+(.*)$/);
						if (bm) {
							const text = bm[1].trim();
							const node = { content: text, children: [] };
							const parent = stack[stack.length - 1]?.node || root;
							parent.children.push(node);
							stack.push({ level: stack[stack.length - 1].level, node, isBullet: true });
							return;
						}
						const node = { content: line, children: [] };
						const parent = stack[stack.length - 1]?.node || root;
						parent.children.push(node);
					});

					return JSON.stringify({
						"mm-settings": { "spacing": 30, "mm-link-width": 4, "border-radius": 4 },
						"mm-node": root
					}, null, 2);
				} catch {
					return JSON.stringify({
						"mm-settings": { "spacing": 30, "mm-link-width": 4, "border-radius": 4 },
						"mm-node": { "content": fallbackTitle, "children": [] }
					}, null, 2);
				}
			};

			const migrated = history.map((it) => {
				let mindmapStr = null;
				if (it && typeof it === 'object') {
					if (it.mindmap) {
						mindmapStr = typeof it.mindmap === 'string' ? it.mindmap : JSON.stringify(it.mindmap);
					} else if (it.mmjson) {
						mindmapStr = typeof it.mmjson === 'string' ? it.mmjson : JSON.stringify(it.mmjson);
						changed = true;
					} else if (it.markdown) {
						mindmapStr = md2json(it.markdown, (it.topic || '思维导图'));
						changed = true;
					} else if (it.topic) {
						mindmapStr = md2json(`# ${it.topic}`, it.topic);
						changed = true;
					}
				}
				const id = it.id ?? Date.now();
				const timestamp = it.timestamp || new Date().toISOString();
				return mindmapStr ? { id, timestamp, mindmap: mindmapStr } : { id, timestamp, mindmap: JSON.stringify({ "mm-settings": { "spacing": 30, "mm-link-width": 2.5, "border-radius": 4 }, "mm-node": { "content": "思维导图", "children": [] } }, null, 2) };
			});

			if (changed) {
				localStorage.setItem(historyKey, JSON.stringify(migrated));
			}
		}

		try {
			const pgRaw = localStorage.getItem('mindmap-playground');
			if (pgRaw) {
				const pg = JSON.parse(pgRaw);
				let mindmapStr = null;
				if (pg.mindmap) mindmapStr = typeof pg.mindmap === 'string' ? pg.mindmap : JSON.stringify(pg.mindmap);
				else if (pg.mmjson) mindmapStr = typeof pg.mmjson === 'string' ? pg.mmjson : JSON.stringify(pg.mmjson);
				else if (pg.markdown) mindmapStr = md2json(pg.markdown, (pg.topic || '思维导图'));
				else if (pg.topic) mindmapStr = md2json(`# ${pg.topic}`, pg.topic);
				if (mindmapStr) {
					const cleaned = { id: pg.id || Date.now(), timestamp: pg.timestamp || new Date().toISOString(), mindmap: mindmapStr };
					localStorage.setItem('mindmap-playground', JSON.stringify(cleaned));
				}
			}
		} catch { }


		try {
			const sampleMarkdown = "# Mind Map\n\n## Branch\n## Branch";
			const existingHistoryJSON2 = localStorage.getItem(historyKey);
			if (existingHistoryJSON2) {
				let history2 = JSON.parse(existingHistoryJSON2) || [];
				const cleaned = history2.filter(item => item.markdown !== sampleMarkdown);
				if (cleaned.length !== history2.length) {
					localStorage.setItem(historyKey, JSON.stringify(cleaned));
				}
			}
		} catch { }
	} catch (error) {
		trackErrorEvent(`History migration failed. Reason: ${error.message}`);
		console.error('Error migrating mind maps to new schema:', error);
	}
});

async function createLocalMindMapFromMarkdown(markdownInput) {
	try {
		hideHeader();
		const app = document.getElementById('app');
		if (app) app.style.display = 'none';

		document.getElementById('loading-animation').style.display = 'flex';

		const mmjson = window.markdownToMmJson(markdownInput);
		const mmjsonStr = JSON.stringify(mmjson, null, 2);

		let title = "思维导图";
		const firstHeader = markdownInput.split('\n').find(line => line.trim().startsWith('#'));
		if (firstHeader) {
			title = firstHeader.replace(/^#+\s*/, '').trim();
		}

		const newId = saveMindmapToHistory(mmjsonStr);

		window.currentMindmap = {
			id: newId,
			title: title,
			markdown: mmjsonStr
		};
		window.currentMindmapTitle = title;

		const url = new URL(window.location);
		if (url.searchParams.has('q')) {
			url.searchParams.delete('q');
		}
		url.searchParams.set('id', newId);
		window.history.replaceState({}, '', url.toString());

		await renderMindmap(markdownInput, { playPopAnimation: true });

		document.getElementById('loading-animation').style.display = 'none';
		document.getElementById('button-container').style.display = 'flex';
		document.getElementById('mindmap').style.display = 'block';

		if (typeof loadMindmapsLeftSidebar === 'function') {
			await loadMindmapsLeftSidebar(true);
		}

	} catch (error) {
		console.error('Failed to create local mind map:', error);
		const loadingAnimation = document.getElementById('loading-animation');
		if (loadingAnimation) loadingAnimation.style.display = 'none';
		const app = document.getElementById('app');
		if (app) app.style.display = '';
		const mindmap = document.getElementById('mindmap');
		if (mindmap) mindmap.style.display = '';
		const header = document.getElementById('header');
		if (header) header.style.display = '';
		showErrorPopup(error.message, "Error");
		throw error;
	}
}

function expandMindMapNode() {
	return expandMindMapNodeCore();
}

function resetMindMapHistory() {
    if (typeof HistoryManager !== 'undefined') {
        HistoryManager.undoStack = [];
        HistoryManager.redoStack = [];
        HistoryManager.updateButtons();
    }

    previousHierarchy = null;
    currentHierarchy = null;
    
    lastRenderedStyle = null;

    scale = 1;
    currentPoint = { x: 0, y: 0 };
    if (typeof updateTransform === 'function') {
        updateTransform();
    }

    window.__editingNodeId = null;
    if (typeof closeContextMenus === 'function') {
        closeContextMenus();
    }
    
    const activeEditor = document.querySelector('.node-edit-fo');
    if (activeEditor) {
        activeEditor.remove();
    }
};

function showLicensePopup() {
  const licensePopup = document.getElementById('licensePopup');
  const infoMenu = document.querySelector('.info-menu');
  
  if (licensePopup) {
    licensePopup.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
  
  if (infoMenu) {
    infoMenu.classList.remove('show');
  }
}

function closeLicensePopup() {
  const licensePopup = document.getElementById('licensePopup');
  
  if (licensePopup) {
    licensePopup.classList.remove('show');
    document.body.style.overflow = '';
  }
}

document.addEventListener('DOMContentLoaded', function() {
  const closeLicenseBtn = document.getElementById('closeLicensePopup');
  const licensePopup = document.getElementById('licensePopup');
  
  if (closeLicenseBtn) {
    closeLicenseBtn.addEventListener('click', closeLicensePopup);
  }
  
  if (licensePopup) {
    licensePopup.addEventListener('click', function(e) {
      if (e.target === licensePopup) {
        closeLicensePopup();
      }
    });
  }
});

window.showLicensePopup = showLicensePopup;
window.closeLicensePopup = closeLicensePopup;

document.addEventListener('DOMContentLoaded', () => {
    if (window.ChatManager) {
        window.chatManager = new window.ChatManager();
    }
});

