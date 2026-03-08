/**
 * Spectral EQ: analisa o espectro do audio tocando, compara com
 * target curves profissionais, e calcula correcao por banda.
 *
 * Bandas: 40, 80, 160, 315, 630, 1250, 2500, 5000, 10000, 20000 Hz
 * (mesmas 10 bandas do ParametricEQ e do Spectrum Analyzer).
 */

export const EQ_BANDS: [number, number, string][] = [
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

export interface TargetCurve {
  name: string;
  label: string;
  gains: number[];
}

export interface SpectralSnapshot {
  bandEnergies: number[];
  timestamp: number;
}

export interface SpectralResult {
  measured: number[];
  correction: number[];
  target: TargetCurve;
}

// ─── Target Curves ───

export const TARGET_CURVES: TargetCurve[] = [
  {
    name: 'flat',
    label: 'FLAT (STUDIO)',
    gains: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  },
  {
    name: 'harman',
    label: 'HARMAN CURVE',
    //       40   80  160  315  630 1.25k 2.5k  5k  10k  20k
    gains: [+3, +2, +1,   0,   0,   0,  -1,  -1,  -2,  -3],
  },
  {
    name: 'bk-house',
    label: 'B&K HOUSE',
    gains: [+2, +2, +1, +1,   0,   0,  -1,  -1,  -2,  -3],
  },
  {
    name: 'listening-room',
    label: 'LISTENING ROOM',
    gains: [+1, +1,   0,   0,   0,  -1,  -1,  -2,  -1,   0],
  },
  {
    name: 'late-night',
    label: 'LATE NIGHT',
    gains: [-3, -2,   0,  +1,  +1,  +1,  +1,   0,  -1,  -2],
  },
  {
    name: 'vocal-clarity',
    label: 'VOCAL CLARITY',
    gains: [ 0, -1,  -2,  -2,   0,  +1,  +2,  +1,   0,   0],
  },
  {
    name: 'warm-vintage',
    label: 'WARM VINTAGE',
    gains: [+2, +2, +1,   0,   0,   0,  -1,  -1,  -2,  -2],
  },
  {
    name: 'bright-airy',
    label: 'BRIGHT / AIRY',
    gains: [ 0,  0,   0,  -1,  -1,   0,   0,  +1,  +2,  +2],
  },
  // Genre-aware
  {
    name: 'rock',
    label: 'ROCK / METAL',
    gains: [+1, +2, +1,  -1,  -1,   0,  +1,  +2,  +1,   0],
  },
  {
    name: 'edm',
    label: 'EDM / ELETRONICA',
    gains: [+3, +3, +1,  -2,  -1,   0,   0,  +1,  +2,  +1],
  },
  {
    name: 'jazz',
    label: 'JAZZ / CLASSICO',
    gains: [ 0,  0,   0,   0,   0,   0,  -1,   0,  +1,  +1],
  },
  {
    name: 'hiphop',
    label: 'HIP-HOP / R&B',
    gains: [+3, +3, +1,  -1,   0,   0,  +1,  +1,   0,   0],
  },
  {
    name: 'pop',
    label: 'POP',
    gains: [+1, +1,   0,   0,  -1,   0,  +1,  +2,  +1,   0],
  },
];

// ─── Spectral Analysis ───

function freqToBin(freq: number, fftSize: number, sampleRate: number): number {
  return Math.round(freq / (sampleRate / fftSize));
}

/**
 * Extrai energia media por banda a partir de dados FFT (Uint8Array do analyser).
 * getByteFrequencyData retorna valores já em escala dB, mapeados linearmente
 * de [minDecibels..maxDecibels] para [0..255]. Convertemos de volta para dB.
 * Retorna 10 valores em dB relativos.
 */
export function extractBandEnergies(
  data: Uint8Array,
  sampleRate: number,
  minDecibels = -100,
  maxDecibels = -30,
): number[] {
  if (!data.length) return new Array(EQ_BANDS.length).fill(-60);
  const fftSize = data.length * 2;
  const dbRange = maxDecibels - minDecibels;
  return EQ_BANDS.map(([lo, hi]) => {
    const binLo = Math.max(0, freqToBin(lo, fftSize, sampleRate));
    const binHi = Math.min(data.length - 1, freqToBin(hi, fftSize, sampleRate));
    if (binHi <= binLo) return -60;
    let sum = 0;
    for (let j = binLo; j <= binHi; j++) sum += data[j];
    const avg = sum / (binHi - binLo + 1);
    const dB = minDecibels + (avg / 255) * dbRange;
    return Math.max(-60, dB);
  });
}

/**
 * Acumula snapshots e retorna a media por banda (janela movel).
 */
export function averageSnapshots(snapshots: SpectralSnapshot[]): number[] {
  if (snapshots.length === 0) return new Array(EQ_BANDS.length).fill(-60);
  const numBands = EQ_BANDS.length;
  const avg = new Array(numBands).fill(0);
  for (const snap of snapshots) {
    for (let i = 0; i < numBands; i++) {
      avg[i] += snap.bandEnergies[i];
    }
  }
  for (let i = 0; i < numBands; i++) {
    avg[i] /= snapshots.length;
  }
  return avg;
}

/**
 * Calcula a correcao EQ: target - measured, normalizado e clampado a [-6, +6].
 *
 * O raciocinio: se a banda de 80Hz esta 4 dB acima da media relativa
 * ao target, cortamos 4 dB nessa banda. Se esta 3 dB abaixo, levantamos 3 dB.
 */
export function computeSpectralCorrection(
  measured: number[],
  target: TargetCurve,
): number[] {
  const numBands = EQ_BANDS.length;

  const measuredMean = measured.reduce((s, v) => s + v, 0) / numBands;
  const targetMean = target.gains.reduce((s, v) => s + v, 0) / numBands;

  return target.gains.map((tg, i) => {
    const measuredNorm = measured[i] - measuredMean;
    const targetNorm = tg - targetMean;
    const delta = targetNorm - measuredNorm;
    return Math.max(-6, Math.min(6, Math.round(delta)));
  });
}

/**
 * Snapshot collector: acumula amostras ao longo do tempo
 * e calcula a correcao quando solicitado.
 */
export class SpectralAnalyzer {
  private snapshots: SpectralSnapshot[] = [];
  private maxSnapshots = 150; // ~5s at 30fps

  addSnapshot(fftData: Uint8Array, sampleRate: number): void {
    const bandEnergies = extractBandEnergies(fftData, sampleRate);
    this.snapshots.push({ bandEnergies, timestamp: Date.now() });
    if (this.snapshots.length > this.maxSnapshots) {
      this.snapshots.shift();
    }
  }

  getAveragedEnergies(): number[] {
    return averageSnapshots(this.snapshots);
  }

  computeCorrection(target: TargetCurve): SpectralResult {
    const measured = this.getAveragedEnergies();
    const correction = computeSpectralCorrection(measured, target);
    return { measured, correction, target };
  }

  get snapshotCount(): number {
    return this.snapshots.length;
  }

  get isReady(): boolean {
    return this.snapshots.length >= 30; // ~1s of data
  }

  captureAsReference(name: string): ReferenceTrack {
    return captureReferenceProfile(this.snapshots, name);
  }

  reset(): void {
    this.snapshots = [];
  }
}

// ─── Reference Track Matching ───

const REF_TRACK_KEY = 'smarteq-reference-tracks';

export interface ReferenceTrack {
  name: string;
  gains: number[];
  capturedAt: number;
}

/**
 * Captura o perfil espectral medio a partir de snapshots acumulados
 * e converte em uma TargetCurve (ganhos relativos ao flat).
 */
export function captureReferenceProfile(
  snapshots: SpectralSnapshot[],
  name: string,
): ReferenceTrack {
  const averaged = averageSnapshots(snapshots);
  const mean = averaged.reduce((s, v) => s + v, 0) / averaged.length;
  const gains = averaged.map((v) => {
    const relative = v - mean;
    return Math.max(-6, Math.min(6, Math.round(relative)));
  });
  return { name, gains, capturedAt: Date.now() };
}

export function referenceToTargetCurve(ref: ReferenceTrack): TargetCurve {
  return { name: `ref-${ref.capturedAt}`, label: `REF: ${ref.name}`, gains: ref.gains };
}

export function saveReferenceTrack(track: ReferenceTrack): void {
  try {
    const existing = loadReferenceTrackList();
    existing.push(track);
    if (existing.length > 10) existing.shift();
    localStorage.setItem(REF_TRACK_KEY, JSON.stringify(existing));
  } catch { /* quota */ }
}

export function loadReferenceTrackList(): ReferenceTrack[] {
  try {
    const raw = localStorage.getItem(REF_TRACK_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as ReferenceTrack[];
  } catch { return []; }
}

export function deleteReferenceTrack(capturedAt: number): void {
  try {
    const existing = loadReferenceTrackList().filter((t) => t.capturedAt !== capturedAt);
    localStorage.setItem(REF_TRACK_KEY, JSON.stringify(existing));
  } catch { /* quota */ }
}
