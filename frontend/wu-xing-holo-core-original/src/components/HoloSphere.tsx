import React, { useRef, useMemo, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
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

const nodeById = new Map(nodes.map(node => [node.id, node]));

const neutralTint = new THREE.Color('#f2f5f7');
function domainTint(color: string, neutralMix = 0.72) {
  return new THREE.Color(color || '#ffffff').lerp(neutralTint, neutralMix).getHexString();
}

function focusedNodeIds(selectedId: string, activeDomain?: string) {
  if (selectedId === 'TCM_ROOT' && !activeDomain) return null;
  const focused = new Set<string>();
  if (selectedId === 'TCM_ROOT' && activeDomain) {
    nodes.forEach(node => {
      if (node.id === 'TCM_ROOT' || node.domain === activeDomain) focused.add(node.id);
    });
    return focused;
  }

  const selected = nodeById.get(selectedId);
  if (!selected) return focused;
  focused.add(selected.id);
  let parent = selected.parent ? nodeById.get(selected.parent) : undefined;
  while (parent) {
    focused.add(parent.id);
    parent = parent.parent ? nodeById.get(parent.parent) : undefined;
  }
  nodes.forEach(node => {
    let current = node.parent ? nodeById.get(node.parent) : undefined;
    while (current) {
      if (current.id === selected.id) {
        focused.add(node.id);
        break;
      }
      current = current.parent ? nodeById.get(current.parent) : undefined;
    }
  });
  if (selected.level === 'knowledge_point' && selected.parent) {
    nodes.forEach(node => {
      if (node.level === 'knowledge_point' && node.parent === selected.parent) focused.add(node.id);
    });
  }
  return focused;
}

function NetworkEdges({ selectedId, activeDomain }: { selectedId: string; activeDomain?: string }) {
  const edgeGroups = useMemo(() => {
    const nodeMap = nodeById;
    const focused = focusedNodeIds(selectedId, activeDomain);
    const groups = new Map<string, { normal: number[]; active: number[] }>();
    const appendEdge = (target: number[], source: GraphNode, destination: GraphNode) => {
      target.push(source.x, source.y, source.z, destination.x, destination.y, destination.z);
    };
    edges.forEach((edge) => {
      const source = nodeMap.get(edge.source);
      const target = nodeMap.get(edge.target);
      if (!source || !target) return;
      const color = target.level === 'main' ? target.color : source.color;
      const key = domainTint(color, focused ? 0.66 : 0.78);
      const group = groups.get(key) || { normal: [], active: [] };
      if (!focused) appendEdge(group.normal, source, target);
      else if (focused.has(source.id) && focused.has(target.id)) appendEdge(group.active, source, target);
      groups.set(key, group);
    });
    return [...groups.entries()];
  }, [activeDomain, selectedId]);

  return (
    <>
      {edgeGroups.map(([color, group]) => (
        <React.Fragment key={`domain-edges-${color}-${selectedId}-${activeDomain || 'all'}`}>
          {group.normal.length > 0 && (
            <lineSegments key={`normal-edges-${selectedId}-${activeDomain || 'all'}-${color}`} frustumCulled={false} renderOrder={-1}>
              <bufferGeometry key={`normal-geometry-${selectedId}-${activeDomain || 'all'}-${color}`}>
                <bufferAttribute attach="attributes-position" array={new Float32Array(group.normal)} count={group.normal.length / 3} itemSize={3} />
              </bufferGeometry>
              <lineBasicMaterial color={`#${color}`} transparent opacity={0.17} blending={THREE.NormalBlending} depthWrite={false} />
            </lineSegments>
          )}
          {group.active.length > 0 && (
            <lineSegments key={`active-edges-${selectedId}-${activeDomain || 'all'}-${color}`} frustumCulled={false} renderOrder={0}>
              <bufferGeometry key={`active-geometry-${selectedId}-${activeDomain || 'all'}-${color}`}>
                <bufferAttribute attach="attributes-position" array={new Float32Array(group.active)} count={group.active.length / 3} itemSize={3} />
              </bufferGeometry>
              <lineBasicMaterial color={`#${color}`} transparent opacity={0.4} blending={THREE.NormalBlending} depthWrite={false} />
            </lineSegments>
          )}
        </React.Fragment>
      ))}
    </>
  );
}

function HTMLOverlays({ selectedId, activeDomain }: { selectedId: string; activeDomain?: string }) {
  const activeNodes = useMemo(() => {
    const selected = nodes.find(n => n.id === selectedId);
    if (!selected) return [];
    if (selectedId === 'TCM_ROOT' && activeDomain) {
      return nodes.filter(node => node.level === 'main' && node.domain === activeDomain);
    }

    const parent = nodes.find(n => n.id === selected.parent);
    const children = nodes.filter(n => n.parent === selected.id);
    return [selected, parent, ...children].filter(Boolean) as GraphNode[];
  }, [activeDomain, selectedId]);

  return (
    <>
      {activeNodes.map(node => {
        const isMain = node.id === selectedId;
        return (
          <Html key={`html-${node.id}`} position={[node.x, node.y, node.z]} center={false} distanceFactor={15} pointerEvents="none" zIndexRange={[100, 0]}>
            <span data-selected-node-anchor={isMain ? node.id : undefined} className="absolute h-px w-px opacity-0" aria-hidden="true" />
            <div className={`relative -translate-y-1/2 translate-x-5 whitespace-nowrap transition-all duration-300 ${isMain ? 'scale-110 opacity-100' : 'scale-90 opacity-70 hover:opacity-100 hover:scale-100'}`}>
              <div
                data-selected-node-label={isMain ? node.id : undefined}
                data-active-domain-label={selectedId === 'TCM_ROOT' && activeDomain ? activeDomain : undefined}
                className="relative px-2 py-1 rounded bg-black/45 backdrop-blur-sm border shadow-lg flex items-center gap-2 pointer-events-none"
                style={{ borderColor: isMain ? `rgba(255,255,255,0.4)` : `rgba(255,255,255,0.1)`, boxShadow: isMain ? `0 0 15px rgba(255,255,255,0.2)` : 'none' }}
              >
                <span className="text-gray-100 text-[10px] tracking-wider font-medium">{node.title}</span>
              </div>
            </div>
          </Html>
        );
      })}
    </>
  );
}

function FocusCamera({ selectedId, activeDomain, focusToken = 0 }: { selectedId: string; activeDomain?: string; focusToken?: number }) {
  const { camera } = useThree();
  const controls = useRef<any>(null);
  const startCamera = useRef(new THREE.Vector3());
  const destination = useRef(new THREE.Vector3());
  const startTarget = useRef(new THREE.Vector3());
  const target = useRef(new THREE.Vector3(-4, 0, 0));
  const pendingFocus = useRef(true);
  const animating = useRef(false);
  const progress = useRef(0);
  const selected = useMemo(() => nodes.find(node => node.id === selectedId), [selectedId]);
  const domainTarget = useMemo(() => {
    const domainNodes = nodes.filter(node => node.level === 'main' && node.domain === activeDomain);
    if (!domainNodes.length) return null;
    const center = domainNodes.reduce((sum, node) => sum.add(new THREE.Vector3(node.x, node.y, node.z)), new THREE.Vector3());
    return center.multiplyScalar(1 / domainNodes.length);
  }, [activeDomain]);

  useEffect(() => {
    pendingFocus.current = true;
  }, [activeDomain, focusToken, selectedId]);

  useFrame(() => {
    const orbit = controls.current;
    if (!orbit) return;

    if (pendingFocus.current) {
      const isDomainFocus = selectedId === 'TCM_ROOT' && Boolean(domainTarget);
      const isOverview = !isDomainFocus && (selectedId === 'TCM_ROOT' || !selected);
      if (isDomainFocus) target.current.copy(domainTarget as THREE.Vector3);
      else if (isOverview) target.current.set(-4, 0, 0);
      else target.current.set(selected?.x || 0, selected?.y || 0, selected?.z || 0);

      const direction = camera.position.clone().sub(orbit.target);
      if (direction.lengthSq() < 0.001) direction.set(-4, 2, 22);
      direction.normalize();
      const desiredDistance = isOverview ? 22.45 : isDomainFocus ? 13.5 : 9.5;
      const focusDistance = desiredDistance;
      startCamera.current.copy(camera.position);
      startTarget.current.copy(orbit.target);
      destination.current.copy(target.current).addScaledVector(direction, focusDistance);
      progress.current = 0;
      pendingFocus.current = false;
      animating.current = true;
      orbit.autoRotate = false;
    }

    if (animating.current) {
      progress.current = Math.min(1, progress.current + 0.08);
      const eased = progress.current * progress.current * (3 - 2 * progress.current);
      camera.position.lerpVectors(startCamera.current, destination.current, eased);
      orbit.target.lerpVectors(startTarget.current, target.current, eased);
      if (progress.current >= 1) {
        animating.current = false;
        orbit.autoRotate = true;
      }
    }

    orbit.update();
  });

  return (
    <OrbitControls
      ref={controls}
      enablePan={true}
      enableZoom={true}
      minDistance={2}
      maxDistance={40}
      autoRotate={true}
      autoRotateSpeed={0.06}
      target={[-4, 0, 0]}
      onStart={() => {
        pendingFocus.current = false;
        animating.current = false;
        if (controls.current) controls.current.autoRotate = true;
      }}
    />
  );
}

export default function HoloSphere({ selectedId, activeDomain, onSelect, focusToken }: { selectedId: string; activeDomain?: string; onSelect: (id: string) => void; focusToken?: number }) {
  const focused = focusedNodeIds(selectedId, activeDomain);
  const activeNodes = focused ? nodes.filter(node => focused.has(node.id)) : nodes;
  const dimmedNodes = focused ? nodes.filter(node => !focused.has(node.id)) : [];

  function renderNode(node: GraphNode, dimmed = false) {
    const isSelected = selectedId === node.id;
    const scale = dimmed ? 0.68 : isSelected ? 1.55 : node.level === 'root' ? 1.2 : 1.08;
    const color = node.level === 'root'
      ? '#ffffff'
      : domainTint(node.color, dimmed ? 0.9 : isSelected ? 0.54 : 0.72);
    return (
      <Instance
        key={node.id}
        position={[node.x, node.y, node.z]}
        color={dimmed ? `#${color}` : `#${color}`}
        scale={scale}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(node.id);
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          document.body.style.cursor = 'pointer';
        }}
        onPointerOut={() => {
          document.body.style.cursor = 'move';
        }}
      />
    );
  }

  return (
    <div
      className="absolute inset-0 w-full h-full cursor-move z-10 bg-[#020306]"
      data-selected-node-id={selectedId}
      data-active-domain={activeDomain || undefined}
    >
      <Canvas camera={{ position: [-8, 2, 22], fov: 50 }} gl={{ antialias: true, alpha: false }}>
        <color attach="background" args={['#020306']} />
        <ambientLight intensity={0.8} />
        
        {/* Deep Space Soft Aurora Nebula Glows */}
        <GlowBlob position={[-20, 15, -30]} color="#0a2240" size={60} />
        <GlowBlob position={[25, -15, -25]} color="#061228" size={70} />
        <GlowBlob position={[-20, -20, 25]} color="#061830" size={60} />
        <GlowBlob position={[20, 20, 30]} color="#0a1a3a" size={70} />

        {/* Render 1600 edges */}
        <NetworkEdges selectedId={selectedId} activeDomain={activeDomain} />

        {/* Render focused nodes above a subdued background constellation. */}
        <Instances key={`active-${selectedId}-${activeDomain || 'all'}`} range={activeNodes.length} limit={activeNodes.length}>
          <sphereGeometry args={[0.08, 12, 12]} />
          <meshBasicMaterial toneMapped={false} transparent opacity={0.82} />
          {activeNodes.map(node => renderNode(node))}
        </Instances>
        {dimmedNodes.length > 0 && (
          <Instances key={`dimmed-${selectedId}-${activeDomain || 'all'}`} range={dimmedNodes.length} limit={dimmedNodes.length}>
            <sphereGeometry args={[0.08, 12, 12]} />
            <meshBasicMaterial toneMapped={false} transparent opacity={0.24} />
            {dimmedNodes.map(node => renderNode(node, true))}
          </Instances>
        )}

        {/* HTML Labels for active subset */}
        <HTMLOverlays selectedId={selectedId} activeDomain={activeDomain} />

        <Stars radius={30} depth={50} count={3000} factor={4} saturation={0} fade speed={1} />

        <FocusCamera selectedId={selectedId} activeDomain={activeDomain} focusToken={focusToken} />
      </Canvas>
      
      {/* Interaction Hint */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 text-gray-400 text-[10px] tracking-widest pointer-events-none flex items-center gap-3 bg-black/40 px-4 py-2 rounded-full border border-gray-800/50 backdrop-blur-md">
        <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-ping"></span>
        Drag to Rotate • Right-Click to Pan • Scroll to Zoom
      </div>
    </div>
  );
}
