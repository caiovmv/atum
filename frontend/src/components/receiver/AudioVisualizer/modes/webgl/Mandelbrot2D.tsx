import { useRef, useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useAudioEnergyContext } from '../../AudioEnergyContext';

const vertexShader = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const fragmentShader = /* glsl */ `
  uniform float time;
  uniform float bass;
  uniform float mid;
  uniform float treble;
  uniform vec2 resolution;

  varying vec2 vUv;

  vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
  }

  void main() {
    float zoom = 1.1 + treble * 0.8;
    float offsetX = sin(time * 0.2 + bass * 4.0) * 0.15;
    float offsetY = cos(time * 0.2 + mid * 4.0) * 0.15;

    float baseScale = min(resolution.x, resolution.y) / 2.5;
    float scale = baseScale / zoom;
    float aspect = resolution.x / resolution.y;
    float scaleX = aspect >= 1.0 ? scale : scale * aspect;
    float scaleY = aspect >= 1.0 ? scale / aspect : scale;

    float cr = (vUv.x - 0.5) * resolution.x / scaleX + offsetX;
    float ci = (vUv.y - 0.5) * resolution.y / scaleY + offsetY;

    float zr = 0.0;
    float zi = 0.0;
    int iterCount = 0;
    const int maxIter = 80;

    for (int j = 0; j < maxIter; j++) {
      float zr2 = zr * zr;
      float zi2 = zi * zi;
      if (zr2 + zi2 > 4.0) {
        iterCount = j + 1;
        break;
      }
      float newZr = zr2 - zi2 + cr;
      float newZi = 2.0 * zr * zi + ci;
      zr = newZr;
      zi = newZi;
      iterCount = j + 1;
    }

    float t = float(iterCount) / float(maxIter);
    float hue = mod(t * 360.0 + time * 20.0, 360.0) / 360.0;
    vec3 col = hsv2rgb(vec3(hue, 0.8, 1.0));

    gl_FragColor = vec4(col, 1.0);
  }
`;

export function Mandelbrot2D() {
  const meshRef = useRef<THREE.Mesh>(null);
  const getAudio = useAudioEnergyContext();
  const { size } = useThree();

  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: {
          time: { value: 0 },
          bass: { value: 0 },
          mid: { value: 0 },
          treble: { value: 0 },
          resolution: { value: new THREE.Vector2(1, 1) },
        },
        vertexShader,
        fragmentShader,
      }),
    []
  );

  useFrame((state) => {
    const { bass, mid, treble } = getAudio();
    material.uniforms.time.value = state.clock.elapsedTime;
    material.uniforms.bass.value = bass;
    material.uniforms.mid.value = mid;
    material.uniforms.treble.value = treble;
    material.uniforms.resolution.value.set(size.width, size.height);
  });

  return (
    <mesh ref={meshRef} material={material}>
      <planeGeometry args={[4, 4]} />
    </mesh>
  );
}
