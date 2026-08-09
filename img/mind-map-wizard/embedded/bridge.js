(function () {
  'use strict';

  const MESSAGE_SCOPE = 'xz-mindmap-wizard';
  let engineReady = false;
  let currentContent = '';
  let currentTitle = '思维导图';

  window.MMW_READONLY = true;
  window.MMW_EMBEDDED = true;
  window.openNotesDrawer = window.openNotesDrawer || function () {};
  window.defaultMmSettings = function () {
    return {
      spacing: 34,
      'border-radius': 6,
      'branch-alignment': 'auto',
      style: '1'
    };
  };

  function post(type, payload) {
    if (window.parent === window) return;
    window.parent.postMessage({ scope: MESSAGE_SCOPE, type, ...(payload || {}) }, window.location.origin);
  }

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      const script = document.createElement('script');
      script.src = src;
      script.async = false;
      script.onload = resolve;
      script.onerror = function () {
        reject(new Error('导图引擎文件加载失败：' + src));
      };
      document.head.appendChild(script);
    });
  }

  function markdownToJson(markdown) {
    const lines = String(markdown || '').replace(/\r/g, '').split('\n');
    let rootTitle = currentTitle;
    let rootIndex = -1;
    let rootLevel = 1;

    for (let index = 0; index < lines.length; index += 1) {
      const match = lines[index].trim().match(/^(#{1,6})\s+(.+)$/);
      if (!match) continue;
      rootTitle = match[2].trim() || currentTitle;
      rootIndex = index;
      rootLevel = match[1].length;
      break;
    }

    const root = { content: rootTitle, children: [] };
    const stack = [{ kind: 'heading', level: rootLevel, node: root }];

    lines.forEach(function (rawLine, index) {
      const line = rawLine.trim();
      if (!line || index === rootIndex || /^```/.test(line)) return;

      const heading = line.match(/^(#{1,6})\s+(.+)$/);
      if (heading) {
        const level = heading[1].length;
        const node = { content: heading[2].trim(), children: [] };
        while (stack.length > 1 && (stack[stack.length - 1].kind === 'list' || stack[stack.length - 1].level >= level)) {
          stack.pop();
        }
        stack[stack.length - 1].node.children.push(node);
        stack.push({ kind: 'heading', level, node });
        return;
      }

      const listItem = rawLine.match(/^(\s*)(?:[-*+]|\d+\.)\s+(.+)$/);
      if (listItem) {
        const indent = Math.floor(listItem[1].replace(/\t/g, '    ').length / 2);
        const node = { content: listItem[2].trim(), children: [] };
        while (stack.length > 1 && stack[stack.length - 1].kind === 'list' && stack[stack.length - 1].indent >= indent) {
          stack.pop();
        }
        const last = stack[stack.length - 1];
        const parent = last.kind === 'list' && indent > last.indent ? last.node : last.node;
        parent.children.push(node);
        stack.push({ kind: 'list', indent, node });
        return;
      }

      stack[stack.length - 1].node.children.push({ content: line, children: [] });
    });

    return {
      'mm-settings': window.defaultMmSettings(),
      'mm-node': root
    };
  }

  function parseContent(content) {
    const source = String(content || '').trim();
    if (!source) throw new Error('没有可渲染的思维导图内容');
    if (source.startsWith('{')) {
      try {
        const parsed = JSON.parse(source);
        if (parsed && parsed['mm-node']) return parsed;
        if (parsed && typeof parsed.markdown === 'string') return markdownToJson(parsed.markdown);
      } catch (_error) {
        // Treat malformed JSON-looking model output as Markdown below.
      }
    }
    return markdownToJson(source);
  }

  function render(content, title) {
    if (!engineReady) return;
    currentContent = String(content || currentContent || '').trim();
    currentTitle = String(title || currentTitle || '思维导图').trim();
    const data = parseContent(currentContent);
    data['mm-settings'] = { ...window.defaultMmSettings(), ...(data['mm-settings'] || {}) };

    const editor = document.getElementById('json-editor');
    editor.value = JSON.stringify(data, null, 2);
    window.updateMindMap();

    window.requestAnimationFrame(function () {
      if (typeof window.fitToScreen === 'function') window.fitToScreen();
      if (window.innerWidth < 640 && typeof window.zoomMindMap === 'function') window.zoomMindMap(1.7);
      const svg = document.querySelector('#svg-output svg');
      const nodeCount = svg ? svg.querySelectorAll('.mm-node').length : 0;
      if (!svg || nodeCount === 0) {
        post('error', { message: '导图引擎没有生成有效 SVG 节点' });
        return;
      }
      post('rendered', { nodeCount });
    });
  }

  function exportSvg() {
    const svg = document.querySelector('#svg-output svg');
    if (!svg) throw new Error('当前没有可导出的思维导图');
    const clone = svg.cloneNode(true);
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    const xml = new XMLSerializer().serializeToString(clone);
    post('export', { filename: currentTitle + '.svg', content: xml });
  }

  function runControl(action) {
    if (action === 'zoom-in' && typeof window.zoomMindMap === 'function') window.zoomMindMap(1.2);
    if (action === 'zoom-out' && typeof window.zoomMindMap === 'function') window.zoomMindMap(1 / 1.2);
    if (action === 'fit' && typeof window.fitToScreen === 'function') window.fitToScreen();
    if (action === 'reset') render(currentContent, currentTitle);
    if (action === 'export') exportSvg();
  }

  window.addEventListener('message', function (event) {
    if (event.source !== window.parent || event.origin !== window.location.origin) return;
    const message = event.data || {};
    if (message.scope !== MESSAGE_SCOPE) return;
    try {
      if (message.type === 'render') render(message.content, message.title);
      if (message.type === 'control') runControl(message.action);
    } catch (error) {
      post('error', { message: error && error.message ? error.message : '思维导图渲染失败' });
    }
  });

  async function boot() {
    try {
      await loadScript('./renderer.js');
      await loadScript('./interaction.js');
      engineReady = typeof window.updateMindMap === 'function';
      if (!engineReady) throw new Error('导图引擎初始化失败');
      post('ready');
    } catch (error) {
      const container = document.getElementById('mindmap');
      container.innerHTML = '<div class="engine-error">思维导图引擎加载失败</div>';
      post('error', { message: error && error.message ? error.message : '导图引擎加载失败' });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
