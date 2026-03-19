/**
 * Persistência e aplicação de estado DSP (volume, EQ, loudness, etc.) no AudioEngine.
 */
import type { AudioEngine } from './audioEngine';
import { computeLoudnessBoost } from './analysis';

export interface DspPersist {
  volume: number;
  balance: number;
  eqGains: number[];
  bass: number;
  mid: number;
  treble: number;
  loudness: boolean;
  att: boolean;
}

const STORAGE_KEY = 'receiver-dsp-state';

export function loadDspState(): Partial<DspPersist> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Partial<DspPersist>;
  } catch {
    return {};
  }
}

export function saveDspState(partial: Partial<DspPersist>): void {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const dsp = raw ? (JSON.parse(raw) as Partial<DspPersist>) : {};
    Object.assign(dsp, partial);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(dsp));
  } catch {
    /* quota or parse error */
  }
}

export function applyDspToEngine(engine: AudioEngine, dsp: Partial<DspPersist>): void {
  const t = engine.ctx.currentTime;
  const vol = dsp.volume ?? 50;
  const att = dsp.att ?? false;

  engine.volumeGain.gain.setTargetAtTime(vol / 100, t, 0.01);
  engine.attGain.gain.setTargetAtTime(att ? 0.1 : 1.0, t, 0.01);
  engine.panner.pan.setTargetAtTime((dsp.balance ?? 0) / 50, t, 0.01);

  const eqGains = dsp.eqGains ?? [];
  engine.eqBands.forEach((band, i) => {
    band.gain.setTargetAtTime(eqGains[i] ?? 0, t, 0.01);
  });

  if (dsp.loudness) {
    const { bassBoost, trebleBoost } = computeLoudnessBoost(vol, att, undefined);
    engine.loudnessLow.gain.setTargetAtTime(bassBoost, t, 0.02);
    engine.loudnessHigh.gain.setTargetAtTime(trebleBoost, t, 0.02);
  } else {
    engine.loudnessLow.gain.setTargetAtTime(0, t, 0.02);
    engine.loudnessHigh.gain.setTargetAtTime(0, t, 0.02);
  }
}
