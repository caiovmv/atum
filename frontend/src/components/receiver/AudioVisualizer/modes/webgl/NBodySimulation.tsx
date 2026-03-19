import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Points, PointMaterial } from '@react-three/drei';
import * as THREE from 'three';
import { useAudioEnergyContext } from '../../AudioEnergyContext';
import { ACCENT_HEX } from '../../../../../utils/theme';

const BODY_COUNT = 500;

interface Body {
  pos: THREE.Vector3;
  vel: THREE.Vector3;
}

export function NBodySimulation() {
  const meshRef = useRef<THREE.Points>(null);
  const getAudio = useAudioEnergyContext();

  const { bodies, positions } = useMemo(() => {
    const bodies: Body[] = [];
    const positions = new Float32Array(BODY_COUNT * 3);
    for (let i = 0; i < BODY_COUNT; i++) {
      bodies.push({
        pos: new THREE.Vector3(
          (Math.random() - 0.5) * 40,
          (Math.random() - 0.5) * 40,
          (Math.random() - 0.5) * 40
        ),
        vel: new THREE.Vector3(0, 0, 0),
      });
      positions[i * 3] = bodies[i].pos.x;
      positions[i * 3 + 1] = bodies[i].pos.y;
      positions[i * 3 + 2] = bodies[i].pos.z;
    }
    return { bodies, positions };
  }, []);

  useFrame(() => {
    const { bass } = getAudio();
    const G = 0.0008 + bass * 0.04;

    for (let i = 0; i < bodies.length; i++) {
      const a = bodies[i];
      for (let j = 0; j < bodies.length; j++) {
        if (i === j) continue;
        const b = bodies[j];
        const dir = b.pos.clone().sub(a.pos);
        const dist = dir.length() + 0.1;
        const force = G / (dist * dist);
        dir.normalize().multiplyScalar(force);
        a.vel.add(dir);
      }
      a.pos.add(a.vel);
    }

    if (meshRef.current) {
      const posAttr = meshRef.current.geometry.attributes
        .position as THREE.BufferAttribute;
      for (let i = 0; i < bodies.length; i++) {
        const p = bodies[i].pos;
        posAttr.setXYZ(i, p.x, p.y, p.z);
      }
      posAttr.needsUpdate = true;
    }
  });

  return (
    <Points ref={meshRef} positions={positions} stride={3} frustumCulled={false}>
      <PointMaterial
        transparent
        size={0.15}
        sizeAttenuation
        depthWrite={false}
        color={ACCENT_HEX}
      />
    </Points>
  );
}
