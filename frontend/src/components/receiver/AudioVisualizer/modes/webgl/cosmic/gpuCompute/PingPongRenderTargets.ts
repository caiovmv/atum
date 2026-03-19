import * as THREE from 'three';

const SIZE = 256; // 256x256 = 65k particles

export function createPingPongTargets(_gl: THREE.WebGLRenderer): {
  positionA: THREE.WebGLRenderTarget;
  positionB: THREE.WebGLRenderTarget;
  velocityA: THREE.WebGLRenderTarget;
  velocityB: THREE.WebGLRenderTarget;
  size: number;
  particleCount: number;
  initPositionTexture: () => THREE.DataTexture;
  initVelocityTexture: () => THREE.DataTexture;
} {
  const positionA = new THREE.WebGLRenderTarget(SIZE, SIZE, {
    format: THREE.RGBAFormat,
    type: THREE.FloatType,
    minFilter: THREE.NearestFilter,
    magFilter: THREE.NearestFilter,
    wrapS: THREE.ClampToEdgeWrapping,
    wrapT: THREE.ClampToEdgeWrapping,
  });

  const positionB = new THREE.WebGLRenderTarget(SIZE, SIZE, {
    format: THREE.RGBAFormat,
    type: THREE.FloatType,
    minFilter: THREE.NearestFilter,
    magFilter: THREE.NearestFilter,
    wrapS: THREE.ClampToEdgeWrapping,
    wrapT: THREE.ClampToEdgeWrapping,
  });

  const velocityA = new THREE.WebGLRenderTarget(SIZE, SIZE, {
    format: THREE.RGBAFormat,
    type: THREE.FloatType,
    minFilter: THREE.NearestFilter,
    magFilter: THREE.NearestFilter,
    wrapS: THREE.ClampToEdgeWrapping,
    wrapT: THREE.ClampToEdgeWrapping,
  });

  const velocityB = new THREE.WebGLRenderTarget(SIZE, SIZE, {
    format: THREE.RGBAFormat,
    type: THREE.FloatType,
    minFilter: THREE.NearestFilter,
    magFilter: THREE.NearestFilter,
    wrapS: THREE.ClampToEdgeWrapping,
    wrapT: THREE.ClampToEdgeWrapping,
  });

  function initPositionTexture() {
    const data = new Float32Array(SIZE * SIZE * 4);
    for (let i = 0; i < SIZE * SIZE; i++) {
      data[i * 4] = (Math.random() - 0.5) * 60;
      data[i * 4 + 1] = (Math.random() - 0.5) * 60;
      data[i * 4 + 2] = (Math.random() - 0.5) * 60;
      data[i * 4 + 3] = 1;
    }
    const tex = new THREE.DataTexture(data, SIZE, SIZE, THREE.RGBAFormat, THREE.FloatType);
    tex.needsUpdate = true;
    return tex;
  }

  function initVelocityTexture() {
    const data = new Float32Array(SIZE * SIZE * 4);
    for (let i = 0; i < SIZE * SIZE; i++) {
      data[i * 4] = (Math.random() - 0.5) * 0.1;
      data[i * 4 + 1] = (Math.random() - 0.5) * 0.1;
      data[i * 4 + 2] = (Math.random() - 0.5) * 0.1;
      data[i * 4 + 3] = 0;
    }
    const tex = new THREE.DataTexture(data, SIZE, SIZE, THREE.RGBAFormat, THREE.FloatType);
    tex.needsUpdate = true;
    return tex;
  }

  return {
    positionA,
    positionB,
    velocityA,
    velocityB,
    size: SIZE,
    particleCount: SIZE * SIZE,
    initPositionTexture,
    initVelocityTexture,
  };
}
