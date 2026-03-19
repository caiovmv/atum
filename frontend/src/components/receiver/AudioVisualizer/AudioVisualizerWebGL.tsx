import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { AudioEnergyProvider } from './AudioEnergyContext';
import { NebulaGPU } from './modes/webgl/NebulaGPU';
import { FractalRaymarch } from './modes/webgl/FractalRaymarch';
import { Mandelbrot2D } from './modes/webgl/Mandelbrot2D';
import { NBodySimulation } from './modes/webgl/NBodySimulation';
import { CosmicOrchestraV1 } from './modes/webgl/CosmicOrchestraV1';
import { CosmicOrchestraV2 } from './modes/webgl/CosmicOrchestraV2';
import { CosmicOrchestraV3 } from './modes/webgl/cosmic/CosmicOrchestraV3';

export type WebGLVisualizerMode =
  | 'nebula-gpu'
  | 'fractal-gpu'
  | 'fractal-ray'
  | 'nbody'
  | 'orchestra-v1'
  | 'orchestra-v2'
  | 'orchestra-v3';

interface AudioVisualizerWebGLProps {
  mode: WebGLVisualizerMode;
  getAudioEnergy: () => { bass: number; mid: number; treble: number };
  width: number;
  height: number;
  className?: string;
}

function Scene({ mode }: { mode: WebGLVisualizerMode }) {
  return (
    <>
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      {mode === 'nebula-gpu' && <NebulaGPU />}
      {mode === 'fractal-gpu' && <Mandelbrot2D />}
      {mode === 'fractal-ray' && <FractalRaymarch />}
      {mode === 'nbody' && <NBodySimulation />}
      {mode === 'orchestra-v1' && <CosmicOrchestraV1 />}
      {mode === 'orchestra-v2' && <CosmicOrchestraV2 />}
      {mode === 'orchestra-v3' && <CosmicOrchestraV3 />}
      {mode !== 'fractal-ray' && mode !== 'fractal-gpu' && (
        <OrbitControls
          enableZoom
          enablePan
          minDistance={20}
          maxDistance={120}
        />
      )}
    </>
  );
}

export function AudioVisualizerWebGL({
  mode,
  getAudioEnergy,
  width,
  height,
  className = '',
}: AudioVisualizerWebGLProps) {
  return (
    <div
      className={className}
      style={{
        width,
        height,
        background: '#000',
      }}
    >
      <Canvas
        camera={{ position: [0, 0, 50], fov: 60 }}
        gl={{ antialias: true, alpha: false }}
      >
        <AudioEnergyProvider getAudioEnergy={getAudioEnergy}>
          <Scene mode={mode} />
        </AudioEnergyProvider>
      </Canvas>
    </div>
  );
}
