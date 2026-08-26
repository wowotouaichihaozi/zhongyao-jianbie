import React, { useRef, useMemo, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html, Stars, Instances, Instance, Billboard } from '@react-three/drei';
import * as THREE from 'three';
import { nodes, edges, GraphNode } from '../data';

const glowMaterial = new THREE.ShaderMaterial({
  uniforms: { color: { value: new THREE.Color() } },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform vec3 color;
    varying vec2 vUv;
    void main() {
      float d = distance(vUv, vec2(0.5));
      float alpha = smoothstep(0.5, 0.0, d);
      gl_FragColor = vec4(color, alpha * 0.35); // Subtle soft glow
    }
  `,
  transparent: true,
  depthWrite: false,
  blending: THREE.AdditiveBlending,
});

function GlowBlob({ position, color, size }: { position: [number,number,number], color: string, size: number }) {
  const mat = useMemo(() => glowMaterial.clone(), []);
  useEffect(() => {
    mat.uniforms.color.value.set(color);
  }, [color, mat]);
  return (
    <Billboard position={position}>
      <mesh material={mat}>
        <planeGeometry args={[size, size]} />
      </mesh>
    </Billboard>
  );
}

function NetworkEdges() {
  const edgePositions = useMemo(() => {
    // 1600 edges, each with 2 vertices, each with x,y,z (6 floats per edge)
    const positions = new Float32Array(edges.length * 6);
    let idx = 0;
    
    // Quick lookup map for performance
    const nodeMap = new Map(nodes.map(n => [n.id, n]));

    edges.forEach((edge) => {
      const source = nodeMap.get(edge.source);
      const target = nodeMap.get(edge.target);
      if (source && target) {
        positions[idx++] = source.x;
        positions[idx++] = source.y;
        positions[idx++] = source.z;
        positions[idx++] = target.x;
        positions[idx++] = target.y;
        positions[idx++] = target.z;
      }
    });
    return positions;
  }, []);

  return (
    <lineSegments>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" array={edgePositions} count={edges.length * 2} itemSize={3} />
      </bufferGeometry>
      <lineBasicMaterial color="#ffffff" transparent opacity={0.15} blending={THREE.AdditiveBlending} />
    </lineSegments>
  );
}

function HTMLOverlays({ selectedId }: { selectedId: string }) {
  const activeNodes = useMemo(() => {
    const selected = nodes.find(n => n.id === selectedId);
    if (!selected) return [];
    
    // Show label for selected, its parent, and its children
    const parent = nodes.find(n => n.id === selected.parent);
    const children = nodes.filter(n => n.parent === selected.id);
    
    return [selected, parent, ...children].filter(Boolean) as GraphNode[];
  }, [selectedId]);

  return (
    <>
      {activeNodes.map(node => {
        const isMain = node.id === selectedId;
        return (
          <Html key={`html-${node.id}`} position={[node.x, node.y, node.z]} center distanceFactor={15} zIndexRange={[100, 0]}>
            <div className={`whitespace-nowrap transition-all duration-300 ${isMain ? 'scale-110 opacity-100' : 'scale-90 opacity-70 hover:opacity-100 hover:scale-100'}`}>
              <div 
                className="px-2 py-1 rounded bg-black/60 backdrop-blur-sm border shadow-lg flex items-center gap-2 pointer-events-none"
                style={{ borderColor: isMain ? `rgba(255,255,255,0.4)` : `rgba(255,255,255,0.1)`, boxShadow: isMain ? `0 0 15px rgba(255,255,255,0.2)` : 'none' }}
              >
                <div className="w-1.5 h-1.5 rounded-full bg-white" />
                <span className="text-gray-100 text-[10px] tracking-wider font-medium">{node.title}</span>
              </div>
            </div>
          </Html>
        );
      })}
    </>
  );
}

export default function HoloSphere({ selectedId, onSelect }: { selectedId: string, onSelect: (id: string) => void }) {
  return (
    <div className="absolute inset-0 w-full h-full cursor-move z-10 bg-[#020306]">
      <Canvas camera={{ position: [-8, 2, 22], fov: 50 }} gl={{ antialias: true, alpha: false }}>
        <color attach="background" args={['#020306']} />
        <ambientLight intensity={0.8} />
        
        {/* Deep Space Soft Aurora Nebula Glows */}
        <GlowBlob position={[-20, 15, -30]} color="#0a2240" size={60} />
        <GlowBlob position={[25, -15, -25]} color="#061228" size={70} />
        <GlowBlob position={[-20, -20, 25]} color="#061830" size={60} />
        <GlowBlob position={[20, 20, 30]} color="#0a1a3a" size={70} />

        {/* Render 1600 edges */}
        <NetworkEdges />

        {/* Render 1601 nodes efficiently using Instances */}
        <Instances range={nodes.length} limit={nodes.length}>
          <sphereGeometry args={[0.08, 12, 12]} />
          <meshBasicMaterial toneMapped={false} transparent opacity={0.7} />
          {nodes.map((node) => {
            const isSelected = selectedId === node.id;
            const scale = isSelected ? 1.5 : 1.0;

            return (
              <Instance
                key={node.id}
                position={[node.x, node.y, node.z]}
                color="#ffffff"
                scale={scale}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelect(node.id);
                }}
                onPointerOver={(e) => {
                  e.stopPropagation();
                  document.body.style.cursor = 'pointer';
                }}
                onPointerOut={(e) => {
                  document.body.style.cursor = 'move';
                }}
              />
            );
          })}
        </Instances>

        {/* HTML Labels for active subset */}
        <HTMLOverlays selectedId={selectedId} />

        <Stars radius={30} depth={50} count={3000} factor={4} saturation={0} fade speed={1} />

        <OrbitControls 
          enablePan={true} 
          enableZoom={true} 
          minDistance={2}
          maxDistance={40}
          autoRotate={true}
          autoRotateSpeed={0.06}
          target={[-4, 0, 0]}
        />
      </Canvas>
      
      {/* Interaction Hint */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 text-gray-400 text-[10px] tracking-widest pointer-events-none flex items-center gap-3 bg-black/40 px-4 py-2 rounded-full border border-gray-800/50 backdrop-blur-md">
        <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-ping"></span>
        Drag to Rotate • Right-Click to Pan • Scroll to Zoom
      </div>
    </div>
  );
}
