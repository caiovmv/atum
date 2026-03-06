import { useEffect, useRef, useState } from 'react';

/**
 * 10 bandas logarítmicas (padrão equalizador vintage).
 * Cada entrada: [freqMin, freqMax, label].
 */
const BANDS: [number, number, string][] = [
  [20, 60, '40'],
  [60, 120, '80'],
  [120, 240, '160'],
  [240, 470, '315'],
  [470, 940, '630'],
  [940, 1870, '1.25k'],
  [1870, 3750, '2.5k'],
  [3750, 7500, '5k'],
  [7500, 15000, '10k'],
  [15000, 22050, '20k'],
];

const SEGMENTS = 12;
const SMOOTH = 0.35;
const SAMPLE_RATE = 44100;

function freqToBin(freq: number, fftSize: number, sampleRate: number): number {
  return Math.round(freq / (sampleRate / fftSize));
}

interface SpectrumProps {
  data: Uint8Array;
  sampleRate?: number;
  className?: string;
}

export function Spectrum({ data, sampleRate = SAMPLE_RATE, className = '' }: SpectrumProps) {
  const prevRef = useRef<number[]>(new Array(BANDS.length).fill(0));
  const [bars, setBars] = useState<number[]>(new Array(BANDS.length).fill(0));

  useEffect(() => {
    if (!data.length) return;
    const fftSize = data.length * 2;
    const next: number[] = BANDS.map(([lo, hi]) => {
      const binLo = Math.max(0, freqToBin(lo, fftSize, sampleRate));
      const binHi = Math.min(data.length - 1, freqToBin(hi, fftSize, sampleRate));
      if (binHi <= binLo) return 0;
      let sum = 0;
      for (let j = binLo; j <= binHi; j++) sum += data[j];
      return (sum / (binHi - binLo + 1)) / 255;
    });
    const smoothed = prevRef.current.map((prev, i) => prev + (next[i] - prev) * SMOOTH);
    prevRef.current = smoothed;
    setBars(smoothed);
  }, [data, sampleRate]);

  return (
    <div className={`receiver-spectrum ${className}`.trim()} aria-hidden>
      <span className="receiver-spectrum-label">SPECTRUM ANALYZER</span>
      <div className="receiver-spectrum-display">
        {bars.map((h, i) => {
          const litCount = Math.round(h * SEGMENTS);
          return (
            <div key={i} className="receiver-spectrum-col">
              <div className="receiver-spectrum-segments">
                {Array.from({ length: SEGMENTS }, (_, s) => {
                  const segIdx = SEGMENTS - 1 - s;
                  const lit = segIdx < litCount;
                  return (
                    <div
                      key={s}
                      className={`receiver-spectrum-seg ${lit ? 'receiver-spectrum-seg-lit' : ''}`}
                    />
                  );
                })}
              </div>
              <span className="receiver-spectrum-freq">{BANDS[i][2]}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
