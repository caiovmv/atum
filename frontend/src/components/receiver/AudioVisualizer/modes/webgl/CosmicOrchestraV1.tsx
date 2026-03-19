import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Points, PointMaterial } from '@react-three/drei';
import * as THREE from 'three';
import { useAudioEnergyContext } from '../../AudioEnergyContext';
import { ACCENT_HEX } from '../../../../../utils/theme';

const STAR_COUNT = 100000;

interface MassiveBody {
  pos: THREE.Vector3;
  vel: THREE.Vector3;
}

export function CosmicOrchestraV1() {
  const nebulaRef = useRef<THREE.Points>(null);
  const getAudio = useAudioEnergyContext();

  const starPositions = useMemo(() => {
    const arr = new Float32Array(STAR_COUNT * 3);
    for (let i = 0; i < arr.length; i++) {
      arr[i] = (Math.random() - 0.5) * 200;
    }
    return arr;
  }, []);

  const bodies = useMemo<MassiveBody[]>(
    () => [
      { pos: new THREE.Vector3(-15, 0, 0), vel: new THREE.Vector3(0, 0, 0) },
      { pos: new THREE.Vector3(15, 0, 0), vel: new THREE.Vector3(0, 0, 0) },
      { pos: new THREE.Vector3(0, 15, 0), vel: new THREE.Vector3(0, 0, 0) },
      { pos: new THREE.Vector3(0, -10, 5), vel: new THREE.Vector3(0, 0, 0) },
    ],
    []
  );

  useFrame(() => {
    const { bass, mid, treble } = getAudio();

    if (nebulaRef.current) {
      nebulaRef.current.rotation.y += 0.001 + mid * 0.035;
      nebulaRef.current.rotation.x += 0.0005;
      const mat = nebulaRef.current.material as THREE.PointsMaterial;
      if (mat) mat.size = 0.015 + treble * 0.08;
    }

    const G = 0.0015 + bass * 0.08;

    for (const a of bodies) {
      for (const b of bodies) {
        if (a === b) continue;
        const dir = b.pos.clone().sub(a.pos);
        const dist = dir.length() + 0.1;
        const force = G / (dist * dist);
        dir.normalize().multiplyScalar(force);
        a.vel.add(dir);
      }
      a.pos.add(a.vel);
    }
  });

  return (
    <>
      <Points
        ref={nebulaRef}
        positions={starPositions}
        stride={3}
        frustumCulled={false}
      >
        <PointMaterial
          transparent
          size={0.03}
          sizeAttenuation
          depthWrite={false}
          color={ACCENT_HEX}
        />
      </Points>
      {bodies.map((b, i) => (
        <mesh key={i} position={b.pos}>
          <sphereGeometry args={[0.8, 24, 24]} />
          <meshStandardMaterial
            emissive={ACCENT_HEX}
            emissiveIntensity={0.8}
            color="#0a1a18"
          />
        </mesh>
      ))}
    </>
  );
}
