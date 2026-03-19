import { useRef, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useAudioEnergyContext } from '../../../AudioEnergyContext';
import { createPingPongTargets } from './gpuCompute/PingPongRenderTargets';
import {
  simulationVertexShader,
  velocityFragmentShader,
  positionFragmentShader,
} from './gpuCompute/simulationShader';
import {
  particleVertexShader,
  particleFragmentShader,
} from './gpuCompute/renderShader';

const SIM_SIZE = 256;

export function CosmicOrchestraV3() {
  const getAudio = useAudioEnergyContext();
  const { gl } = useThree();

  const state = useRef<{
    targets: ReturnType<typeof createPingPongTargets> | null;
    simScene: THREE.Scene | null;
    simCamera: THREE.OrthographicCamera | null;
    posQuad: THREE.Mesh | null;
    velQuad: THREE.Mesh | null;
    particlePoints: THREE.Points | null;
    readPos: THREE.WebGLRenderTarget;
    readVel: THREE.WebGLRenderTarget;
    writePos: THREE.WebGLRenderTarget;
    writeVel: THREE.WebGLRenderTarget;
    posMaterial: THREE.ShaderMaterial | null;
    velMaterial: THREE.ShaderMaterial | null;
    particleMaterial: THREE.ShaderMaterial | null;
    particleGeometry: THREE.BufferGeometry | null;
  } | null>(null);

  useEffect(() => {
    const targets = createPingPongTargets(gl);
    const resolution = new THREE.Vector2(SIM_SIZE, SIM_SIZE);
    const simCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    const copyFrag = /* glsl */ `
      uniform sampler2D uTex;
      varying vec2 vUv;
      void main() { gl_FragColor = texture2D(uTex, vUv); }
    `;
    const copyVert = /* glsl */ `
      varying vec2 vUv;
      void main() { vUv = uv; gl_Position = vec4(position, 1.0); }
    `;
    const copyMat = new THREE.ShaderMaterial({
      vertexShader: copyVert,
      fragmentShader: copyFrag,
      uniforms: { uTex: { value: null as THREE.Texture | null } },
    });
    const copyScene = new THREE.Scene();
    const copyQuad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), copyMat);
    copyScene.add(copyQuad);

    copyMat.uniforms.uTex.value = targets.initPositionTexture();
    gl.setRenderTarget(targets.positionA);
    gl.render(copyScene, simCamera);
    copyMat.uniforms.uTex.value = targets.initVelocityTexture();
    gl.setRenderTarget(targets.velocityA);
    gl.render(copyScene, simCamera);
    gl.setRenderTarget(null);
    copyMat.dispose();

    const posSimMaterial = new THREE.ShaderMaterial({
      vertexShader: simulationVertexShader,
      fragmentShader: positionFragmentShader,
      uniforms: {
        positionTex: { value: targets.positionA.texture },
        velocityTex: { value: targets.velocityA.texture },
        resolution: { value: resolution },
      },
    });

    const velSimMaterial = new THREE.ShaderMaterial({
      vertexShader: simulationVertexShader,
      fragmentShader: velocityFragmentShader,
      uniforms: {
        positionTex: { value: targets.positionA.texture },
        velocityTex: { value: targets.velocityA.texture },
        bass: { value: 0 },
        mid: { value: 0 },
        resolution: { value: resolution },
      },
    });

    const posGeo = new THREE.PlaneGeometry(2, 2);
    const posQuad = new THREE.Mesh(posGeo, posSimMaterial);
    const velQuad = new THREE.Mesh(posGeo, velSimMaterial);

    const simScene = new THREE.Scene();
    simScene.add(posQuad);
    simScene.add(velQuad);

    const refs = new Float32Array(SIM_SIZE * SIM_SIZE * 2);
    for (let i = 0; i < SIM_SIZE * SIM_SIZE; i++) {
      refs[i * 2] = (i % SIM_SIZE) / SIM_SIZE;
      refs[i * 2 + 1] = Math.floor(i / SIM_SIZE) / SIM_SIZE;
    }
    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute(
      'reference',
      new THREE.BufferAttribute(refs, 2)
    );
    particleGeometry.setDrawRange(0, SIM_SIZE * SIM_SIZE);

    const particleMaterial = new THREE.ShaderMaterial({
      vertexShader: particleVertexShader,
      fragmentShader: particleFragmentShader,
      uniforms: {
        positionTex: { value: targets.positionA.texture },
        size: { value: 2 },
        bass: { value: 0 },
        mid: { value: 0 },
        treble: { value: 0 },
      },
      transparent: true,
      depthWrite: false,
    });

    const particlePoints = new THREE.Points(particleGeometry, particleMaterial);

    state.current = {
      targets,
      simScene,
      simCamera,
      posQuad,
      velQuad,
      particlePoints,
      readPos: targets.positionA,
      readVel: targets.velocityA,
      writePos: targets.positionB,
      writeVel: targets.velocityB,
      posMaterial: posSimMaterial,
      velMaterial: velSimMaterial,
      particleMaterial,
      particleGeometry,
    };

    return () => {
      targets.positionA.dispose();
      targets.positionB.dispose();
      targets.velocityA.dispose();
      targets.velocityB.dispose();
      posSimMaterial.dispose();
      velSimMaterial.dispose();
      particleMaterial.dispose();
      particleGeometry.dispose();
      state.current = null;
    };
  }, [gl]);

  useFrame(() => {
    const s = state.current;
    if (!s) return;

    const { bass, mid, treble } = getAudio();

    s.velMaterial!.uniforms.bass.value = bass;
    s.velMaterial!.uniforms.mid.value = mid;
    s.particleMaterial!.uniforms.size.value = 1.2 + treble * 3;
    s.particleMaterial!.uniforms.bass.value = bass;
    s.particleMaterial!.uniforms.mid.value = mid;
    s.particleMaterial!.uniforms.treble.value = treble;

    s.velMaterial!.uniforms.positionTex.value = s.readPos.texture;
    s.velMaterial!.uniforms.velocityTex.value = s.readVel.texture;
    s.velQuad!.material = s.velMaterial!;
    s.velQuad!.visible = true;
    s.posQuad!.visible = false;

    gl.setRenderTarget(s.writeVel);
    gl.render(s.simScene!, s.simCamera!);

    s.posMaterial!.uniforms.positionTex.value = s.readPos.texture;
    s.posMaterial!.uniforms.velocityTex.value = s.writeVel.texture;
    s.posQuad!.material = s.posMaterial!;
    s.posQuad!.visible = true;
    s.velQuad!.visible = false;

    gl.setRenderTarget(s.writePos);
    gl.render(s.simScene!, s.simCamera!);

    const tmpPos = s.readPos;
    s.readPos = s.writePos;
    s.writePos = tmpPos;
    const tmpVel = s.readVel;
    s.readVel = s.writeVel;
    s.writeVel = tmpVel;

    s.particleMaterial!.uniforms.positionTex.value = s.readPos.texture;
    gl.setRenderTarget(null);
  });

  if (!state.current?.particlePoints) return null;

  return <primitive object={state.current.particlePoints} />;
}
