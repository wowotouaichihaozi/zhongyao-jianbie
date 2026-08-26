import { motion, AnimatePresence } from 'motion/react';
import React from 'react';
import { nodes } from '../data';

interface InfoPanelProps {
  selectedId: string;
}

export default function InfoPanel({ selectedId }: InfoPanelProps) {
  const data = nodes.find((el) => el.id === selectedId);

  if (!data) return null;

  const parent = nodes.find((n) => n.id === data.parent);
  const children = nodes.filter((n) => n.parent === data.id);
  const keywords = data.keywords || data.tags;

  const getLevelName = (level: string) => {
    switch (level) {
      case 'root': return '知识总览';
      case 'main': return '主要知识';
      case 'subtopic': return '子知识';
      case 'knowledge_point': return '具体知识点';
      default: return '';
    }
  };

  const getParentTitle = (title: string) => {
    return title.replace(/·/g, ' ＞ ');
  };

  // Special handling for ROOT node
  if (data.id === 'TCM_ROOT') {
    return (
      <div className="relative w-full flex flex-col justify-center font-sans max-h-[80vh]">
        <div className="relative bg-gray-900/80 border border-gray-700/50 backdrop-blur-xl p-8 rounded-2xl shadow-2xl pointer-events-auto flex flex-col">
          <AnimatePresence mode="wait">
            <motion.div
              key="root"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              className="flex flex-col h-full"
            >
              <h2 className="text-3xl font-bold text-gray-100 tracking-wider mb-2">中医药知识库</h2>
              <div className="text-sm tracking-widest text-emerald-400/90 mb-6">知识总览</div>

              <div className="flex flex-col gap-4 text-sm text-gray-300">
                <div className="flex items-center gap-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-red-400"></div>
                  <span>10 个知识领域</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-green-400"></div>
                  <span>100 个主要知识点</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-400"></div>
                  <span>500 个二级知识点</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-yellow-400"></div>
                  <span>1000 个三级知识点</span>
                </div>
              </div>

              <div className="mt-8 pt-5 border-t border-gray-800">
                <div className="text-xs text-gray-500 mb-3 tracking-widest">包含领域：</div>
                <div className="flex flex-wrap gap-2">
                  {["基础理论", "藏象与生命物质", "经络与腧穴", "四诊与辨证", "病因病机", "中药学", "方剂学", "常见证候与病证", "经典与学术", "治则养生与综合"].map(d => (
                    <span key={d} className="px-2 py-1 bg-gray-800/80 text-gray-400 text-[11px] rounded border border-gray-700/50">{d}</span>
                  ))}
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    );
  }

  // Normal nodes
  return (
    <div className="relative w-full flex flex-col justify-center font-sans max-h-[85vh]">
      <div className="relative bg-gray-900/80 border border-gray-700/50 backdrop-blur-xl p-6 lg:p-8 rounded-2xl shadow-2xl pointer-events-auto flex flex-col overflow-hidden max-h-full">
        <AnimatePresence mode="wait">
          <motion.div
            key={data.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col h-full overflow-hidden"
          >
            {/* Header */}
            <div className="shrink-0 mb-5">
              <h2 className="text-2xl lg:text-3xl font-bold leading-snug tracking-wide text-gray-100 mb-4">
                {data.title}
              </h2>
              <div className="flex flex-wrap items-center gap-3">
                <div className="inline-flex items-center gap-2 px-2.5 py-1 bg-gray-800/60 border border-gray-700/50 rounded-md text-xs tracking-wider text-gray-300">
                  <span className="w-2 h-2 rounded-full shadow-[0_0_8px_rgba(255,255,255,0.5)]" style={{ backgroundColor: data.color }}></span>
                  {data.domain}
                </div>
                <div className="text-xs text-gray-500 tracking-widest">
                  {getLevelName(data.level)}
                </div>
              </div>
            </div>

            {/* Content (Scrollable) */}
            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-6">
              <div className="text-gray-300 leading-loose tracking-wide text-sm lg:text-[15px] text-justify whitespace-pre-wrap">
                {data.explanation || data.summary}
              </div>

              {keywords && keywords.length > 0 && (
                <div className="pt-2">
                  <div className="flex flex-wrap gap-2 text-xs">
                    {keywords.map((kw, i) => (
                      <span key={i} className="px-2 py-1 text-emerald-400/90 bg-emerald-400/10 border border-emerald-400/20 rounded">
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            {(parent || (children && children.length > 0)) && (
              <div className="shrink-0 mt-5 pt-4 border-t border-gray-800/80 space-y-2">
                {parent && (
                  <div className="text-xs text-gray-500 tracking-wide">
                    所属知识：<span className="text-gray-300 ml-1">{getParentTitle(parent.title)}</span>
                  </div>
                )}
                {children && children.length > 0 && (
                  <div className="text-xs text-gray-500 tracking-wide">
                    下级知识：<span className="text-gray-300 ml-1">{children.length} 个</span>
                  </div>
                )}
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

