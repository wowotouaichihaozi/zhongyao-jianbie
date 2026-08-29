import React from 'react';
import { ChevronRight, X } from 'lucide-react';
import { nodes } from '../../wu-xing-holo-core-original/src/data';

type Props = {
  selected: any;
  levelName: string;
  onClose: () => void;
  embedded?: boolean;
};

export default function InfoPanel({ selected, levelName, onClose, embedded = false }: Props) {
  const parent = selected.parent ? nodes.find(node => node.id === selected.parent) : null;
  const childrenCount = nodes.filter(node => node.parent === selected.id).length;
  const keywords = selected.keywords || selected.tags || [];
  const content = String(selected.explanation || selected.summary || '').trim();
  const lineage: string[] = [];
  let ancestor = parent;
  while (ancestor) {
    lineage.unshift(ancestor.title);
    ancestor = ancestor.parent ? nodes.find(node => node.id === ancestor?.parent) : null;
  }

  return (
    <section data-knowledge-status={content ? 'available' : 'missing'} className={[
      'text-slate-100',
      embedded
        ? 'border-t border-slate-700/70 bg-transparent'
        : 'max-h-[76vh] overflow-hidden border border-slate-700/80 bg-[#0b111b]/96 shadow-2xl backdrop-blur-xl',
    ].join(' ')}>
      <div className="flex items-start justify-between gap-4 border-b border-slate-700/70 px-5 py-4">
        <div className="min-w-0">
          <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-cyan-200">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: selected.color }} />
            <span>{levelName}</span>
          </div>
          <h2 className="break-words text-xl font-semibold leading-tight tracking-wide text-slate-50">{selected.title}</h2>
          <div className="mt-2 text-[10px] text-slate-500">{selected.domain}</div>
        </div>
        <button type="button" title="关闭详情" aria-label="关闭详情" onClick={onClose} className="grid h-8 w-8 shrink-0 place-items-center border border-slate-700 text-slate-400 transition hover:border-cyan-300/60 hover:text-cyan-200">
          <X size={15} />
        </button>
      </div>

      <div className={embedded ? 'px-5 py-4' : 'max-h-[calc(76vh-94px)] overflow-y-auto px-5 py-4 custom-scrollbar'}>
        <div className="grid grid-cols-2 gap-3 border-b border-slate-700/70 pb-4 text-[10px]">
          <div>
            <div className="text-slate-500">知识条目</div>
            <div className="mt-1 font-medium text-slate-300">{selected.id}</div>
          </div>
          <div>
            <div className="text-slate-500">内容状态</div>
            <div className={`mt-1 font-medium ${content ? 'text-emerald-300' : 'text-amber-300'}`}>
              {content ? '已收录学习说明' : '待补充说明'}
            </div>
          </div>
        </div>

        {lineage.length > 0 && (
          <div className="mt-4 text-[10px] leading-5 text-slate-500">
            所属路径：<span className="text-slate-300">{lineage.join(' ＞ ')}</span>
          </div>
        )}

        <p className="mt-4 text-sm leading-7 text-slate-300">{content || '当前条目暂未提供可展示的学习说明。'}</p>

        {keywords.length > 0 && (
          <div className="mt-5 border-t border-slate-700/70 pt-4">
            <div className="mb-2 text-[10px] uppercase tracking-[0.16em] text-slate-500">关键词</div>
            <div className="grid gap-1.5">
              {keywords.map((keyword: string) => (
                <div key={keyword} className="flex items-center gap-2 text-[11px] text-slate-300">
                  <ChevronRight size={12} className="text-cyan-300" />
                  <span>{keyword}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-5 grid grid-cols-2 gap-3 border-t border-slate-700/70 pt-4 text-[10px]">
          <div>
            <div className="text-slate-500">所属节点</div>
            <div className="mt-1 truncate text-slate-300">{parent?.title || '知识库根节点'}</div>
          </div>
          <div>
            <div className="text-slate-500">下级节点</div>
            <div className="mt-1 text-slate-300">{childrenCount || '无下级节点'}</div>
          </div>
        </div>
      </div>
    </section>
  );
}
