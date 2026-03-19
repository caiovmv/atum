import { memo, useEffect, useRef, useState } from 'react';
import type { AudioEngine } from '../audio/audioEngine';
import './MiniVU.css';

const BARS = 5;
const MIN_HEIGHT_PX = 3;
const MAX_HEIGHT_PX = 16;
const SENSITIVITY = 3.5;
const CURVE_EXP = 0.65;

/** Bins para fftSize 2048: 0-20, 20-50, 50-120, 120-250, 250-512 */
const BAND_RANGES: [number, number][] = [
  [0, 20],
  [20, 50],
  [50, 120],
  [120, 250],
  [250, 512],
];

function extractBandEnergies(freqBuf: Uint8Array<ArrayBufferLike>): number[] {
  const energies: number[] = [];
  for (const [start, end] of BAND_RANGES) {
    let sum = 0;
    const count = Math.min(end, freqBuf.length) - start;
    if (count <= 0) {
      energies.push(0);
      continue;
    }
    for (let i = start; i < Math.min(end, freqBuf.length); i++) {
      sum += freqBuf[i] / 255;
    }
    const avg = sum / count;
    const boosted = Math.min(1, avg * SENSITIVITY);
    energies.push(Math.pow(boosted, CURVE_EXP));
  }
  return energies;
}

interface MiniVUProps {
  engine: AudioEngine | null;
  isPlaying: boolean;
}

export const MiniVU = memo(function MiniVU({ engine, isPlaying }: MiniVUProps) {
  const [bars, setBars] = useState<number[]>(() => new Array(BARS).fill(0));
  const freqBufRef = useRef<Uint8Array | null>(null);
  const barsRef = useRef<number[]>(new Array(BARS).fill(0));

  useEffect(() => {
    if (!engine || !isPlaying) {
      setBars(new Array(BARS).fill(0));
      return;
    }

    if (engine.ctx.state === 'suspended') {
      engine.ctx.resume().catch(() => {});
    }

    const analyser = engine.analyserVisualizer ?? engine.analyser;
    if (!freqBufRef.current || freqBufRef.current.length !== analyser.frequencyBinCount) {
      freqBufRef.current = new Uint8Array(analyser.frequencyBinCount);
    }
    const freqBuf = freqBufRef.current;

    let raf = 0;
    let frame = 0;

    const tick = () => {
      frame++;
      if (frame % 2 === 0) {
        analyser.getByteFrequencyData(freqBuf as Uint8Array<ArrayBuffer>);
        const energies = extractBandEnergies(freqBuf);
        const prev = barsRef.current;
        const next: number[] = [];
        for (let i = 0; i < BARS; i++) {
          const target = energies[i];
          const alpha = 0.35;
          next[i] = prev[i] + (target - prev[i]) * alpha;
        }
        barsRef.current = next;
        setBars(next);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [engine, isPlaying]);

  const hasActiveEngine = engine && isPlaying;

  return (
    <div className={`mini-vu${hasActiveEngine ? ' mini-vu--active' : ''}`} aria-hidden>
      {Array.from({ length: BARS }, (_, i) => {
        const norm = hasActiveEngine ? bars[i] ?? 0 : 0;
        const heightPx = MIN_HEIGHT_PX + norm * (MAX_HEIGHT_PX - MIN_HEIGHT_PX);
        return (
          <span
            key={i}
            className="mini-vu-bar"
            style={{ height: `${heightPx}px` }}
          />
        );
      })}
    </div>
  );
});
