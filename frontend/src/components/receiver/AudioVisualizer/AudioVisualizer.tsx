import { useRef, useEffect } from 'react';
import { useAudioEnergy } from './useAudioEnergy';
import { createRenderLoop } from './renderLoop';
import {
  createThreeBody,
  createFractal,
  createParticleNebula,
  createOscilloscopeTunnel,
  createCosmicVU,
} from './modes/canvas';

export type CanvasVisualizerMode =
  | 'threebody'
  | 'fractal'
  | 'nebula'
  | 'tunnel'
  | 'vu';

interface AudioVisualizerProps {
  mode: CanvasVisualizerMode;
  analyser: AnalyserNode | null;
  width: number;
  height: number;
  className?: string;
}

export function AudioVisualizer({
  mode,
  analyser,
  width,
  height,
  className = '',
}: AudioVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const getAudioEnergy = useAudioEnergy(analyser);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !analyser) return;

    const ctx = canvas.getContext('2d', { willReadFrequently: false });
    if (!ctx) return;

    canvas.width = width;
    canvas.height = height;

    let visual: { draw: (a: { bass: number; mid: number; treble: number }) => void };

    switch (mode) {
      case 'threebody':
        visual = createThreeBody(ctx, width, height);
        break;
      case 'fractal':
        visual = createFractal(ctx, width, height);
        break;
      case 'nebula':
        visual = createParticleNebula(ctx, width, height);
        break;
      case 'tunnel':
        visual = createOscilloscopeTunnel(ctx, width, height);
        break;
      case 'vu':
        visual = createCosmicVU(ctx, width, height);
        break;
      default:
        visual = createThreeBody(ctx, width, height);
    }

    const stop = createRenderLoop(getAudioEnergy, visual.draw);
    return stop;
  }, [mode, analyser, width, height, getAudioEnergy]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className={className}
      style={{ display: 'block', width: '100%', height: '100%' }}
      aria-hidden
    />
  );
}
