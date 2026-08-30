import React, { useMemo, useState } from 'react';
import {
  ChevronRight,
  Compass,
  Crosshair,
  Menu,
  Network,
  RotateCcw,
  Search,
  X,
} from 'lucide-react';
import HoloSphere from './components/HoloSphere';
import InfoPanel from './components/InfoPanel';
import { nodes } from '../wu-xing-holo-core-original/src/data';

type GraphNode = (typeof nodes)[number];

const levelName: Record<string, string> = {
  root: '知识总览',
  main: '主要知识',
  subtopic: '子主题',
  knowledge_point: '具体知识点',
};

export default function App() {
  const [selectedNodeId, setSelectedNodeId] = useState('TCM_ROOT');
  const [activeDomain, setActiveDomain] = useState('');
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [focusToken, setFocusToken] = useState(0);

  const nodeById = useMemo(() => new Map(nodes.map(node => [node.id, node])), []);
  const domains = useMemo(() => {
    const grouped = new Map<string, { name: string; color: string; topics: GraphNode[] }>();
    nodes.filter(node => node.level === 'main').forEach(node => {
      const current = grouped.get(node.domain) || { name: node.domain, color: node.color, topics: [] };
      current.topics.push(node);
      grouped.set(node.domain, current);
    });
    return [...grouped.values()];
  }, []);

  const selectedNode = nodeById.get(selectedNodeId) || nodeById.get('TCM_ROOT');
  const selectedTopic = selectedNode?.level === 'main'
    ? selectedNode
    : nodes.find(node => node.level === 'main' && node.id === selectedNode?.parent)
      || nodes.find(node => node.level === 'main' && node.id === nodes.find(parent => parent.id === selectedNode?.parent)?.parent)
      || (selectedNode?.level === 'root' ? undefined : undefined);
  const subtopics = selectedTopic ? nodes.filter(node => node.parent === selectedTopic.id) : [];
  const selectedSubtopic = selectedNode?.level === 'subtopic'
    ? selectedNode
    : selectedNode?.level === 'knowledge_point'
      ? (selectedNode.parent ? nodeById.get(selectedNode.parent) : undefined)
      : undefined;
  const points = selectedSubtopic ? nodes.filter(node => node.parent === selectedSubtopic.id) : [];
  const searchResults = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase();
    if (!query) return [];
    return nodes.filter(node => [
      node.title,
      node.domain,
      node.explanation,
      node.summary,
      ...(node.keywords || []),
      ...(node.tags || []),
    ].some(value => String(value || '').toLocaleLowerCase().includes(query))).slice(0, 40);
  }, [searchQuery]);

  function topicFor(node: GraphNode | undefined) {
    let current = node;
    while (current && current.level !== 'main' && current.parent) current = nodeById.get(current.parent);
    return current?.level === 'main' ? current : undefined;
  }

  function selectNode(id: string, openPanel = true) {
    const node = nodeById.get(id);
    if (!node) return;
    setSelectedNodeId(id);
    setActiveDomain(node.level === 'root' ? '' : node.domain);
    setPanelOpen(openPanel);
    setFocusToken(value => value + 1);
    const topic = topicFor(node);
    if (topic) setActiveDomain(topic.domain);
  }

  function selectDomain(domain: string) {
    setActiveDomain(domain);
    setSelectedNodeId('TCM_ROOT');
    setPanelOpen(false);
    setNavigationOpen(true);
    setFocusToken(value => value + 1);
  }

  function selectFromNavigation(id: string, openPanel = false) {
    // Keep navigation context visible while opening a node detail panel.
    if (openPanel) setNavigationOpen(true);
    selectNode(id, openPanel);
  }

  function resetView() {
    selectNode('TCM_ROOT', false);
    setActiveDomain('');
    setNavigationOpen(false);
  }

  function labelFor(node: GraphNode) {
    if (!selectedTopic) return node.title;
    return node.title.replace(`${selectedTopic.title}·`, '');
  }

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-[#070b12] font-sans text-slate-100">
      <HoloSphere
        selectedId={selectedNodeId}
        activeDomain={activeDomain || undefined}
        onSelect={(id) => selectNode(id, true)}
        focusToken={focusToken}
      />

      <div className="pointer-events-none absolute inset-0" style={{ zIndex: 30, pointerEvents: 'none' }}>
        <header className="pointer-events-auto absolute left-4 top-4 flex items-center gap-3 sm:left-7 sm:top-6" style={{ pointerEvents: 'auto', zIndex: 40 }}>
          <div className="grid h-10 w-10 place-items-center border border-slate-700/70 bg-slate-950/80 text-slate-200 shadow-lg backdrop-blur">
            <Network size={19} />
          </div>
          <div>
            <h1 className="text-base font-semibold tracking-[0.08em] text-slate-100 sm:text-lg">中医药知识星图</h1>
            <p className="mt-0.5 text-[10px] tracking-[0.14em] text-slate-500">1601 节点 · 可旋转、缩放、平移</p>
          </div>
        </header>

        <button
          type="button"
          title={navigationOpen ? '关闭星图导航' : '打开星图导航'}
          aria-label={navigationOpen ? '关闭星图导航' : '打开星图导航'}
          onClick={() => setNavigationOpen(value => !value)}
          className="pointer-events-auto absolute right-4 top-4 grid h-10 w-10 place-items-center border border-slate-700/70 bg-slate-950/85 text-slate-300 shadow-lg backdrop-blur transition hover:border-cyan-300/60 hover:text-cyan-200 md:hidden"
          style={{ pointerEvents: 'auto', zIndex: 45 }}
        >
          {navigationOpen ? <X size={18} /> : <Menu size={18} />}
        </button>

        <aside style={{ pointerEvents: 'auto', zIndex: 45 }} className={[
          'pointer-events-auto absolute left-3 right-3 top-[4.5rem] max-h-[calc(100dvh-6rem)] overflow-hidden border border-slate-700/70 bg-[#0b111b]/95 shadow-2xl backdrop-blur-xl transition duration-200 sm:left-6 sm:right-auto sm:top-24 sm:w-[360px] md:opacity-100 md:translate-y-0 md:pointer-events-auto',
          navigationOpen ? 'translate-y-0 opacity-100' : '-translate-y-3 opacity-0 !pointer-events-none md:!pointer-events-auto md:opacity-100 md:translate-y-0',
        ].join(' ')}>
          <div className="flex items-center gap-3 border-b border-slate-700/70 px-4 py-3">
            <div className="flex items-center gap-2 text-[11px] font-semibold tracking-[0.16em] text-cyan-200">
              <Compass size={15} />
              <span>星图导航</span>
            </div>
            <label className="flex min-w-0 flex-1 items-center gap-1.5 border border-slate-700/80 bg-slate-950/60 px-2 py-1.5 text-slate-300 focus-within:border-cyan-300/70">
              <Search size={13} className="shrink-0 text-slate-500" />
              <input
                value={searchQuery}
                onChange={event => setSearchQuery(event.target.value)}
                placeholder="搜索"
                aria-label="搜索知识点、主题或知识域"
                className="min-w-0 flex-1 bg-transparent text-[10px] text-slate-100 outline-none placeholder:text-slate-600"
              />
              {searchQuery && (
                <button type="button" title="清空搜索" aria-label="清空搜索" onClick={() => setSearchQuery('')} className="grid h-5 w-5 shrink-0 place-items-center text-slate-500 hover:text-cyan-200">
                  <X size={13} />
                </button>
              )}
            </label>
            <button type="button" title="回到全局视角" aria-label="回到全局视角" onClick={resetView} className="grid h-7 w-7 place-items-center border border-slate-700 text-slate-400 transition hover:border-cyan-300/60 hover:text-cyan-200">
              <RotateCcw size={14} />
            </button>
          </div>

          <div className="max-h-[calc(100dvh-9.5rem)] overflow-y-auto p-3 custom-scrollbar">
            {searchQuery.trim() ? (
              <div>
                <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-[0.18em] text-slate-500">
                  <span>搜索结果</span>
                  <span>{searchResults.length}{searchResults.length === 40 ? '+' : ''}</span>
                </div>
                <div className="grid gap-1.5">
                  {searchResults.map(result => (
                    <button
                      key={result.id}
                      type="button"
                      data-search-result={result.id}
                      onClick={() => selectFromNavigation(result.id, true)}
                      className="flex min-w-0 items-start gap-2 border border-slate-700/70 px-2.5 py-2 text-left transition hover:border-cyan-300/60 hover:bg-cyan-300/10"
                    >
                      <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: result.color }} />
                      <span className="min-w-0">
                        <span className="block truncate text-[11px] text-slate-200">{result.title}</span>
                        <span className="mt-0.5 block truncate text-[9px] text-slate-500">{result.domain} · {levelName[result.level]}</span>
                      </span>
                    </button>
                  ))}
                  {searchResults.length === 0 && <div className="border border-dashed border-slate-700 px-3 py-5 text-center text-[11px] text-slate-500">未找到匹配条目</div>}
                </div>
              </div>
            ) : (
              <>
            <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-slate-500">知识域</div>
            <div className="grid grid-cols-2 gap-2">
              {domains.map(domain => (
                <button
                  key={domain.name}
                  type="button"
                  aria-pressed={activeDomain === domain.name}
                  onClick={() => selectDomain(domain.name)}
                  className={[
                    'flex min-w-0 items-center gap-2 border px-2.5 py-2 text-left text-[10px] transition',
                    activeDomain === domain.name
                      ? 'border-cyan-300/70 bg-cyan-300/10 text-cyan-100'
                      : 'border-slate-700/80 bg-slate-900/60 text-slate-300 hover:border-slate-500 hover:text-white',
                  ].join(' ')}
                >
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: domain.color }} />
                  <span className="min-w-0 flex-1 truncate">{domain.name}</span>
                  <span className="text-[9px] text-slate-500">{domain.topics.length}</span>
                </button>
              ))}
            </div>

            {activeDomain && (
              <div className="mt-4 border-t border-slate-700/70 pt-3">
                <div className="mb-2 flex items-center gap-1 text-[10px] font-semibold text-cyan-200">
                  <ChevronRight size={13} />
                  <span>{activeDomain} · 主题</span>
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {(domains.find(domain => domain.name === activeDomain)?.topics || []).map(topic => (
                    <button
                      key={topic.id}
                      type="button"
                      aria-current={selectedTopic?.id === topic.id ? 'page' : undefined}
                      onClick={() => selectFromNavigation(topic.id, true)}
                      className={[
                        'min-w-0 border px-2 py-1.5 text-left text-[10px] transition',
                        selectedTopic?.id === topic.id
                          ? 'border-cyan-200/70 bg-cyan-300/10 text-cyan-100'
                          : 'border-slate-700/70 text-slate-400 hover:border-slate-500 hover:text-slate-100',
                      ].join(' ')}
                    >
                      <span className="block truncate">{topic.title}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {selectedTopic && (
              <div className="mt-4 border-t border-slate-700/70 pt-3">
                <div className="mb-2 flex items-center gap-1 text-[10px] font-semibold text-slate-300">
                  <ChevronRight size={13} />
                  <span>{selectedTopic.title} · 子主题</span>
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {subtopics.map(subtopic => (
                    <button
                      key={subtopic.id}
                      type="button"
                      aria-current={selectedSubtopic?.id === subtopic.id ? 'page' : undefined}
                      onClick={() => selectFromNavigation(subtopic.id, true)}
                      className={[
                        'min-w-0 border px-2 py-1.5 text-left text-[10px] transition',
                        selectedSubtopic?.id === subtopic.id
                          ? 'border-emerald-300/70 bg-emerald-300/10 text-emerald-100'
                          : 'border-slate-700/70 text-slate-500 hover:border-slate-500 hover:text-slate-100',
                      ].join(' ')}
                    >
                      <span className="block truncate">{labelFor(subtopic)}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {selectedSubtopic && (
              <div className="mt-4 border-t border-slate-700/70 pt-3">
                <div className="mb-2 flex items-center gap-1 text-[10px] font-semibold text-slate-300">
                  <ChevronRight size={13} />
                  <span>{selectedSubtopic.title} · 具体知识点</span>
                </div>
                <div className="grid grid-cols-1 gap-1.5">
                  {points.map(point => (
                    <button
                      key={point.id}
                      type="button"
                      aria-current={selectedNodeId === point.id ? 'page' : undefined}
                      onClick={() => selectFromNavigation(point.id, true)}
                      className={[
                        'min-w-0 border px-2 py-1.5 text-left text-[10px] transition',
                        selectedNodeId === point.id
                          ? 'border-cyan-200/70 bg-cyan-300/10 text-cyan-100'
                          : 'border-slate-700/70 text-slate-500 hover:border-slate-500 hover:text-slate-100',
                      ].join(' ')}
                    >
                      <span className="block truncate">{labelFor(point)}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

              </>
            )}
            {panelOpen && selectedNode && (
              <div className="mt-4 md:hidden">
                <InfoPanel selected={selectedNode} levelName={levelName[selectedNode.level] || ''} onClose={() => setPanelOpen(false)} embedded />
              </div>
            )}
          </div>
        </aside>

        <div className="pointer-events-auto absolute bottom-4 left-4 flex items-center gap-2 sm:bottom-6 sm:left-7" style={{ pointerEvents: 'auto', zIndex: 40 }}>
          <button type="button" title="重置视角" aria-label="重置视角" onClick={resetView} className="grid h-9 w-9 place-items-center border border-slate-700/70 bg-slate-950/80 text-slate-300 backdrop-blur transition hover:border-cyan-300/60 hover:text-cyan-200">
            <RotateCcw size={15} />
          </button>
          <button type="button" title="聚焦当前节点" aria-label="聚焦当前节点" onClick={() => selectNode(selectedNodeId, false)} className="grid h-9 w-9 place-items-center border border-slate-700/70 bg-slate-950/80 text-slate-300 backdrop-blur transition hover:border-cyan-300/60 hover:text-cyan-200">
            <Crosshair size={15} />
          </button>
          <span className="hidden border-l border-slate-700/70 pl-3 text-[10px] tracking-wide text-slate-500 sm:inline">
            拖拽旋转 · 滚轮缩放 · 右键平移
          </span>
        </div>

        {panelOpen && selectedNode && (
          <div className="pointer-events-auto absolute right-6 top-1/2 hidden w-[340px] -translate-y-1/2 md:block" style={{ pointerEvents: 'auto', zIndex: 45 }}>
            <InfoPanel selected={selectedNode} levelName={levelName[selectedNode.level] || ''} onClose={() => setPanelOpen(false)} />
          </div>
        )}
      </div>
    </main>
  );
}
