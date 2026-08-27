/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import HoloSphere from './components/HoloSphere';
import InfoPanel from './components/InfoPanel';
import { Network } from 'lucide-react';
import { nodes } from './data';

export default function App() {
  const [selectedNodeId, setSelectedNodeId] = useState<string>("TCM_ROOT");

  return (
    <div className="relative w-screen h-screen bg-[#010204] text-gray-50 overflow-hidden font-sans">
      {/* 3D Sphere Canvas */}
      <HoloSphere selectedId={selectedNodeId} onSelect={setSelectedNodeId} />

      {/* UI Overlay */}
      <div className="pointer-events-none absolute inset-0 z-50 flex flex-col justify-between p-8">
        
        {/* Header */}
        <header className="flex items-center gap-4 pointer-events-auto w-max">
          <div className="w-10 h-10 rounded-full border border-gray-700/50 flex items-center justify-center bg-gray-800/50 backdrop-blur-md">
            <Network className="text-gray-300" size={20} />
          </div>
          <div>
            <h1 className="text-lg font-medium tracking-wide text-gray-200">
              TCM Knowledge Graph
            </h1>
            <p className="text-[10px] tracking-wider text-gray-500 uppercase mt-0.5">
              1600+ Node Matrix
            </p>
          </div>
        </header>

        {/* Right Side: Information Panel */}
        <div className="absolute top-1/2 right-4 lg:right-12 transform -translate-y-1/2 pointer-events-none w-full max-w-sm lg:max-w-md">
          <InfoPanel selectedId={selectedNodeId} />
        </div>
      </div>
    </div>
  );
}

