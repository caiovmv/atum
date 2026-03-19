import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useAudioEnergyContext } from '../../AudioEnergyContext';
import { ACCENT_HEX } from '../../../../../utils/theme';

/** Cores do Cosmic VU: bass, mid, treble */
const BASS_COLOR = new THREE.Color('#e53935');
const MID_COLOR = new THREE.Color('#ff9800');
const TREBLE_COLOR = new THREE.Color(ACCENT_HEX);

/** Galáxia espiral: ~150k estrelas em distribuição espiral */
const STAR_COUNT = 150000;

function spiralGalaxyData(): { positions: Float32Array; colors: Float32Array } {
  const positions = new Float32Array(STAR_COUNT * 3);
  const colors = new Float32Array(STAR_COUNT * 3);
  const colorSets = [BASS_COLOR, MID_COLOR, TREBLE_COLOR, BASS_COLOR];

  for (let i = 0; i < STAR_COUNT; i++) {
    const r = Math.pow(Math.random(), 0.5) * 80;
    const theta = Math.random() * Math.PI * 2;
    const arm = Math.floor(Math.random() * 4);
    const armOffset = (arm / 4) * Math.PI * 2 + theta * 0.15;
    const spiral = armOffset + r * 0.08;
    const x = Math.cos(theta + spiral) * r * (0.8 + Math.random() * 0.4);
    const y = (Math.random() - 0.5) * 8;
    const z = Math.sin(theta + spiral) * r * (0.8 + Math.random() * 0.4);
    positions[i * 3] = x;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = z;

    const c = colorSets[arm];
    colors[i * 3] = c.r;
    colors[i * 3 + 1] = c.g;
    colors[i * 3 + 2] = c.b;
  }
  return { positions, colors };
}

const galaxyVertexShader = /* glsl */ `
  attribute vec3 color;
  uniform float pointSize;
  varying vec3 vColor;
  void main() {
    vColor = color;
    vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mvPos;
    gl_PointSize = pointSize * (300.0 / -mvPos.z);
  }
`;

const galaxyFragmentShader = /* glsl */ `
  uniform float bass;
  uniform float mid;
  uniform float treble;

  varying vec3 vColor;

  void main() {
    float intensity = 0.5 + bass * 0.3 + mid * 0.3 + treble * 0.3;
    gl_FragColor = vec4(vColor * intensity, 0.9);
  }
`;

export function CosmicOrchestraV2() {
  const galaxyRef = useRef<THREE.Points>(null);
  const blackHoleRef = useRef<THREE.Mesh>(null);
  const getAudio = useAudioEnergyContext();

  const { positions, colors } = useMemo(spiralGalaxyData, []);

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    return geo;
  }, [positions, colors]);

  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: galaxyVertexShader,
        fragmentShader: galaxyFragmentShader,
        uniforms: {
          bass: { value: 0 },
          mid: { value: 0 },
          treble: { value: 0 },
          pointSize: { value: 0.02 },
        },
        transparent: true,
        depthWrite: false,
        vertexColors: true,
      }),
    []
  );

  useFrame(() => {
    const { bass, mid, treble } = getAudio();

    if (galaxyRef.current) {
      galaxyRef.current.rotation.y += 0.0015 + mid * 0.03;
      const mat = galaxyRef.current.material as THREE.ShaderMaterial;
      if (mat?.uniforms?.pointSize) mat.uniforms.pointSize.value = 0.012 + treble * 0.06;
    }

    if (material.uniforms) {
      material.uniforms.bass.value = bass;
      material.uniforms.mid.value = mid;
      material.uniforms.treble.value = treble;
    }

    if (blackHoleRef.current) {
      const scale = 1.2 + bass * 3;
      blackHoleRef.current.scale.setScalar(scale);
    }
  });

  return (
    <>
      <points ref={galaxyRef} geometry={geometry} material={material} frustumCulled={false} />
      <mesh ref={blackHoleRef} position={[0, 0, 0]}>
        <sphereGeometry args={[2, 32, 32]} />
        <meshBasicMaterial color="#000" />
      </mesh>
      <pointLight position={[0, 0, 0]} intensity={0.5} color={ACCENT_HEX} />
    </>
  );
}
