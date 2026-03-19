import { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useReceiverEngine } from '../../../contexts/ReceiverEngineContext';
import { useAudioEnergy } from './useAudioEnergy';
import { AudioVisualizer, type CanvasVisualizerMode } from './AudioVisualizer';
import {
  AudioVisualizerWebGL,
  type WebGLVisualizerMode,
} from './AudioVisualizerWebGL';
import './AudioVisualizer.css';

type VisualizerMode = CanvasVisualizerMode | WebGLVisualizerMode;

const CANVAS_MODES: { id: CanvasVisualizerMode; label: string }[] = [
  { id: 'threebody', label: '3 Corpos' },
  { id: 'fractal', label: 'Fractal' },
  { id: 'nebula', label: 'Nebulosa' },
  { id: 'tunnel', label: 'Túnel' },
  { id: 'vu', label: 'Cosmic VU' },
];

const WEBGL_MODES: { id: WebGLVisualizerMode; label: string }[] = [
  { id: 'nebula-gpu', label: 'Nebulosa GPU' },
  { id: 'fractal-gpu', label: 'Fractal GPU' },
  { id: 'fractal-ray', label: 'Fractal 3D' },
  { id: 'nbody', label: 'N-Body' },
  { id: 'orchestra-v1', label: 'Orchestra v1' },
  { id: 'orchestra-v2', label: 'Orchestra v2' },
  { id: 'orchestra-v3', label: 'Orchestra v3' },
];

const ALL_MODES = [...CANVAS_MODES, ...WEBGL_MODES];

interface AudioVisualizerOverlayProps {
  onClose: () => void;
}

const isWebGLMode = (m: VisualizerMode): m is WebGLVisualizerMode =>
  WEBGL_MODES.some((x) => x.id === m);

export function AudioVisualizerOverlay({ onClose }: AudioVisualizerOverlayProps) {
  const [mode, setMode] = useState<VisualizerMode>('threebody');
  const [size, setSize] = useState({ w: 800, h: 600 });
  const containerRef = useRef<HTMLDivElement>(null);
  const engine = useReceiverEngine();
  const analyser = engine?.analyserVisualizer ?? engine?.analyser ?? null;
  const getAudioEnergy = useAudioEnergy(analyser);

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setSize({ w: rect.width, h: rect.height });
      }
    };

    updateSize();
    const ro = new ResizeObserver(updateSize);
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose]
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const content = (
    <div
      className="audio-visualizer-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Visualizador de áudio"
    >
      <div className="audio-visualizer-backdrop" onClick={onClose} />
      <div className="audio-visualizer-content">
        <div className="audio-visualizer-header">
          <div className="audio-visualizer-modes">
            {ALL_MODES.map((m) => (
              <button
                key={m.id}
                type="button"
                className={`audio-visualizer-mode-btn${mode === m.id ? ' audio-visualizer-mode-btn--active' : ''}`}
                onClick={() => setMode(m.id)}
              >
                {m.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="audio-visualizer-close"
            onClick={onClose}
            aria-label="Fechar visualizador"
          >
            ×
          </button>
        </div>
        <div ref={containerRef} className="audio-visualizer-canvas-wrap">
          {analyser ? (
            isWebGLMode(mode) ? (
              <AudioVisualizerWebGL
                mode={mode}
                getAudioEnergy={getAudioEnergy}
                width={size.w}
                height={size.h}
              />
            ) : (
              <AudioVisualizer
                mode={mode}
                analyser={analyser}
                width={size.w}
                height={size.h}
              />
            )
          ) : (
            <div className="audio-visualizer-empty">
              Áudio não disponível. Inicie a reprodução no receiver.
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return createPortal(content, document.body);
}
