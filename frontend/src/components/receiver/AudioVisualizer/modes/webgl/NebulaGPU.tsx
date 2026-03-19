import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Points, PointMaterial } from '@react-three/drei';
import * as THREE from 'three';
import { useAudioEnergyContext } from '../../AudioEnergyContext';
import { ACCENT_HEX } from '../../../../../utils/theme';

const COUNT = 100000;

export function NebulaGPU() {
  const ref = useRef<THREE.Points>(null);
  const getAudio = useAudioEnergyContext();

  const positions = useMemo(() => {
    const arr = new Float32Array(COUNT * 3);
    for (let i = 0; i < arr.length; i++) {
      arr[i] = (Math.random() - 0.5) * 50;
    }
    return arr;
  }, []);

  useFrame(() => {
    if (!ref.current) return;
    const { bass, mid, treble } = getAudio();
    ref.current.rotation.x += 0.002 + bass * 0.04;
    ref.current.rotation.y += 0.002 + mid * 0.04;
    const mat = ref.current.material as THREE.PointsMaterial;
    if (mat) mat.size = 0.02 + treble * 0.08;
  });

  return (
    <Points ref={ref} positions={positions} stride={3} frustumCulled={false}>
      <PointMaterial
        transparent
        size={0.04}
        sizeAttenuation
        depthWrite={false}
        color={ACCENT_HEX}
      />
    </Points>
  );
}
