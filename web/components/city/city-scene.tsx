"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { CityData } from "./types";

/* One InstancedMesh for standing buildings, one for ghosts of demolished ones.
   Colour and scale are driven per frame from the year value (motion value or slider). */
function Massing({ data, year }: { data: CityData; year: { get: () => number } }) {
  const solid = useRef<THREE.InstancedMesh>(null);
  const ghost = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const geometries = useMemo(() => data.buildings.map((b) => {
    const s = new THREE.Shape(b.ring.map(([x, y]) => new THREE.Vector2(x, y)));
    const g = new THREE.ExtrudeGeometry(s, { depth: 1, bevelEnabled: false });
    g.rotateX(-Math.PI / 2);
    return g;
  }), [data]);
  const merged = useMemo(() => {
    // Footprints differ per building, so instances share a unit box scaled to each
    // footprint's bounding box: cheap, thousands of draws collapse to one.
    return new THREE.BoxGeometry(1, 1, 1);
  }, []);
  const boxes = useMemo(() => data.buildings.map((b, i) => {
    geometries[i].computeBoundingBox();
    const bb = geometries[i].boundingBox!;
    return { cx: (bb.min.x + bb.max.x) / 2, cz: (bb.min.z + bb.max.z) / 2, w: Math.max(2, bb.max.x - bb.min.x), d: Math.max(2, bb.max.z - bb.min.z) };
  }), [data, geometries]);
  const sandstone = useMemo(() => new THREE.Color("#C1622E"), []);
  const plaster = useMemo(() => new THREE.Color("#E8DCC6"), []);
  const alarm = useMemo(() => new THREE.Color("#C4361F"), []);
  const indigo = useMemo(() => new THREE.Color("#23304A"), []);

  useFrame(() => {
    const y = year.get();
    if (!solid.current || !ghost.current) return;
    data.buildings.forEach((b, i) => {
      const box = boxes[i];
      const ch = b.change;
      let scaleY = b.h, visible = true, isGhost = false, color = b.core ? sandstone : plaster;
      if (ch) {
        const t = THREE.MathUtils.clamp((y - ch.from) / Math.max(1, ch.year - ch.from), 0, 1);
        if (ch.type === "NEW_CONSTRUCTION") { visible = t > 0; scaleY = Math.max(0.3, b.h * t); if (t > 0) color = alarm; }
        if (ch.type === "VERTICAL_ADDITION") { scaleY = b.h * (1 + 0.5 * t); if (t > 0.01) color = alarm; }
        if (ch.type === "DEMOLITION") { isGhost = t >= 1; scaleY = isGhost ? b.h : b.h * (1 - 0.6 * t); if (t > 0.01 && !isGhost) color = alarm; }
      }
      dummy.position.set(box.cx, visible ? scaleY / 2 : -5, box.cz);
      dummy.scale.set(box.w, visible ? scaleY : 0.001, box.d);
      dummy.updateMatrix();
      if (isGhost) {
        ghost.current!.setMatrixAt(i, dummy.matrix);
        dummy.scale.set(0.001, 0.001, 0.001); dummy.updateMatrix();
        solid.current!.setMatrixAt(i, dummy.matrix);
      } else {
        solid.current!.setMatrixAt(i, dummy.matrix);
        solid.current!.setColorAt(i, color);
        dummy.scale.set(0.001, 0.001, 0.001); dummy.updateMatrix();
        ghost.current!.setMatrixAt(i, dummy.matrix);
      }
      ghost.current!.setColorAt(i, indigo);
    });
    solid.current.instanceMatrix.needsUpdate = true;
    ghost.current.instanceMatrix.needsUpdate = true;
    if (solid.current.instanceColor) solid.current.instanceColor.needsUpdate = true;
    if (ghost.current.instanceColor) ghost.current.instanceColor.needsUpdate = true;
  });
  const n = data.buildings.length;
  return (
    <>
      <instancedMesh ref={solid} args={[merged, undefined, n]} castShadow receiveShadow>
        <meshStandardMaterial roughness={0.9} metalness={0} />
      </instancedMesh>
      <instancedMesh ref={ghost} args={[merged, undefined, n]}>
        <meshBasicMaterial wireframe transparent opacity={0.55} />
      </instancedMesh>
    </>
  );
}

function Outline({ rings, color, y = 0.2 }: { rings: [number, number][][]; color: string; y?: number }) {
  const lines = useMemo(() => rings.map((r) => new THREE.BufferGeometry().setFromPoints(r.map(([x, z]) => new THREE.Vector3(x, y, z)))), [rings, y]);
  return <>{lines.map((g, i) => <primitive key={i} object={new THREE.Line(g, new THREE.LineBasicMaterial({ color }))} />)}</>;
}

function Camera({ progress }: { progress: { get: () => number } }) {
  const { camera } = useThree();
  useFrame(() => {
    const p = progress.get();
    // Dolly from an oblique overview toward the core as the scrub advances.
    const r = 3200 - 2100 * p;
    const a = -0.9 + 0.5 * p;
    camera.position.set(Math.sin(a) * r, 1500 - 950 * p, Math.cos(a) * r);
    camera.lookAt(0, 0, 0);
  });
  return null;
}

export function CityScene({ data, year, progress, onContextLost }: { data: CityData; year: { get: () => number }; progress: { get: () => number }; onContextLost?: () => void }) {
  return (
    <Canvas shadows dpr={[1, 1.5]} camera={{ fov: 32, near: 10, far: 20000, position: [-2200, 1500, 2400] }}
      gl={{ antialias: true, powerPreference: "high-performance" }} frameloop="always" style={{ background: "transparent" }}
      onCreated={({ gl }) => gl.domElement.addEventListener("webglcontextlost", (e) => { e.preventDefault(); onContextLost?.(); })}>
      <hemisphereLight args={["#F2EBE0", "#23304A", 0.9]} />
      <directionalLight position={[-1500, 2500, 1200]} intensity={1.6} castShadow shadow-mapSize={[2048, 2048]} shadow-camera-left={-2500} shadow-camera-right={2500} shadow-camera-top={2500} shadow-camera-bottom={-2500} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow position={[0, -0.5, 0]}>
        <planeGeometry args={[9000, 9000]} />
        <meshStandardMaterial color="#D9CDB6" roughness={1} />
      </mesh>
      <Outline rings={data.core} color="#C4361F" y={1} />
      <Outline rings={data.buffer} color="#23304A" y={0.5} />
      <Massing data={data} year={year} />
      <Camera progress={progress} />
    </Canvas>
  );
}
