(function () {
	const LLM_MESSAGES_URL = '/api/llm/messages';
	const LLM_RUNTIME_URL = '/api/llm/runtime';
	const FALLBACK_MODEL_LABEL = '平台配置模型';

	function authHeaders() {
		const token = localStorage.getItem('authToken')
			|| (localStorage.getItem('codexPreviewAuth') === '1' ? 'codex-preview-token' : '');
		return token ? { Authorization: `Bearer ${token}` } : {};
	}

	function messageText(content) {
		if (typeof content === 'string') return content;
		if (!Array.isArray(content)) return '';
		return content
			.map(part => typeof part === 'string' ? part : (part?.text || part?.content || ''))
			.filter(Boolean)
			.join('\n');
	}

	function knowledgeQueryFromPayload(payload) {
		const messages = Array.isArray(payload?.messages) ? payload.messages : [];
		return messages
			.filter(message => message?.role !== 'system')
			.map(message => messageText(message?.content))
			.filter(Boolean)
			.slice(-2)
			.join('\n')
			.slice(0, 1600);
	}

	async function enrichWithCourseKnowledge(payload, signal) {
		const query = knowledgeQueryFromPayload(payload);
		if (!query) return payload;
		try {
			const response = await fetch('/api/knowledge/retrieve', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', ...authHeaders() },
				credentials: 'include',
				body: JSON.stringify({ query, topK: 6 }),
				signal
			});
			if (!response.ok) return payload;
			const result = await response.json();
			const knowledge = result?.data;
			if (!knowledge?.grounded || !knowledge?.context) return payload;
			window.lastMindmapKnowledgeSources = knowledge.citations || [];
			return {
				...payload,
				messages: [
					{
						role: 'system',
						content: `以下内容来自嵌智学航本地课程知识库。生成导图时必须优先依据这些片段，关键节点使用 [KB1]、[KB2] 标注来源；资料没有支持的具体硬件参数不得编造。\n\n${knowledge.context}`
					},
					...(payload.messages || [])
				]
			};
		} catch (error) {
			if (error?.name !== 'AbortError') console.warn('Course knowledge retrieval skipped:', error);
			return payload;
		}
	}

	async function loadLlmRuntime() {
		try {
			const response = await fetch(LLM_RUNTIME_URL, {
				headers: authHeaders(),
				credentials: 'include'
			});
			if (!response.ok) throw new Error(`Runtime request failed: ${response.status}`);
			const result = await response.json();
			const runtime = result?.data || {};
			window.LLM_RUNTIME = runtime;
			window.API_MODEL = runtime.model || FALLBACK_MODEL_LABEL;
			window.dispatchEvent(new CustomEvent('llm-runtime-ready', { detail: runtime }));
			return runtime;
		} catch (error) {
			console.warn('Unable to load model runtime:', error);
			return { model: window.API_MODEL || FALLBACK_MODEL_LABEL, protocol: 'auto' };
		}
	}

	async function callLlmChatCompletion(payload, _browserApiKey, options = {}) {
		const groundedPayload = await enrichWithCourseKnowledge(payload, options.signal);
		return fetch(LLM_MESSAGES_URL, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', ...authHeaders() },
			credentials: 'include',
			body: JSON.stringify({ ...groundedPayload, stream: false }),
			signal: options.signal
		});
	}

	window.API_BASE_URL = LLM_MESSAGES_URL;
	window.API_AUTH_TOKEN = '';
	window.API_MODEL = FALLBACK_MODEL_LABEL;
	window.callLlmMessages = callLlmChatCompletion;
	window.callLlmChatCompletion = callLlmChatCompletion;
	window.loadLlmRuntime = loadLlmRuntime;
	window.getLlmAuthHeaders = authHeaders;

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', loadLlmRuntime, { once: true });
	} else {
		loadLlmRuntime();
	}
})();
