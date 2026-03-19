import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
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

  varying vec2 vUv;

  float mandelbulb(vec3 p) {
    float power = 8.0 + bass * 6.0;
    vec3 z = p;
    float dr = 1.0;
    float r = 0.0;

    for (int i = 0; i < 8; i++) {
      r = length(z);
      if (r > 2.0) break;

      float theta = acos(z.z / r);
      float phi = atan(z.y, z.x);
      dr = pow(r, power - 1.0) * power * dr + 1.0;
      float zr = pow(r, power);
      theta *= power;
      phi *= power;
      z = zr * vec3(sin(theta) * cos(phi), sin(phi) * sin(theta), cos(theta));
      z += p;
    }
    return 0.5 * log(r) * r / dr;
  }

  void main() {
    vec2 uv = vUv * 2.0 - 1.0;
    uv.x *= 1.5;

    vec3 ro = vec3(0, 0, -3.0 + sin(time * 0.3) * 0.5);
    vec3 rd = normalize(vec3(uv, 1.5));

    float t = 0.0;
    for (int i = 0; i < 64; i++) {
      vec3 p = ro + rd * t;
      float d = mandelbulb(p);
      t += d * 0.5;
      if (d < 0.001 || t > 20.0) break;
    }

    float fog = 1.0 / (1.0 + t * 0.1);
    vec3 col = vec3(
      fog * (0.5 + treble * 0.5),
      fog * (0.3 + mid * 0.4),
      fog * (0.6 + bass * 0.3)
    );

    gl_FragColor = vec4(col, 1.0);
  }
`;

export function FractalRaymarch() {
  const meshRef = useRef<THREE.Mesh>(null);
  const getAudio = useAudioEnergyContext();

  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        uniforms: {
          time: { value: 0 },
          bass: { value: 0 },
          mid: { value: 0 },
          treble: { value: 0 },
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
  });

  return (
    <mesh ref={meshRef} material={material}>
      <planeGeometry args={[4, 4]} />
    </mesh>
  );
}
