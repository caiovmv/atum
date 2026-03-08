/**
 * Funções de análise de áudio para o receiver: RMS (VU), pico dBFS,
 * FFT, buffer do stream e heurística de qualidade.
 *
 * VU: escala -40 a +3 VU, relação 0 VU ≈ -18 dBFS (NAB).
 * Power/Peak: escala -60 a 0 dBFS (padrão digital).
 */

/** Escala VU (loudness médio): -20 a +3. Centro visual: -3 VU. */
export const VU_MIN = -20;
export const VU_MAX = 3;
/** Ponto central do dial VU (0.5 normalizado). */
export const VU_CENTER = -3;

/** Escala dBFS do Power Meter (pico): -60 a 0. Centro visual: -12 dBFS. */
export const DBFS_MIN = -60;
export const DBFS_MAX = 0;
/** Ponto central do dial Power (0.5 normalizado). */
export const DBFS_CENTER = -12;

/** RMS → dBFS (full scale digital). Retorna valor em dB, tipicamente -Infinity a 0. */
export function computeRMS_dBFS(analyser: AnalyserNode, buf?: Float32Array): number {
  const buffer = (buf ?? new Float32Array(analyser.fftSize)) as Float32Array<ArrayBuffer>;
  analyser.getFloatTimeDomainData(buffer);
  let sum = 0;
  for (let i = 0; i < buffer.length; i++) {
    sum += buffer[i] * buffer[i];
  }
  const rms = Math.sqrt(sum / buffer.length);
  const dbFS = 20 * Math.log10(rms);
  return isFinite(dbFS) ? dbFS : DBFS_MIN;
}

/**
 * Converte dBFS para VU (0 VU ≈ -18 dBFS).
 * VU = dBFS + 18, limitado a [-20, +3].
 */
export function dBFS_to_VU(dBFS: number): number {
  const vu = dBFS + 18;
  return Math.max(VU_MIN, Math.min(VU_MAX, vu));
}

/**
 * Converte VU para posição normalizada 0–1.
 * Mapeamento não-linear (piecewise): VU_CENTER (-3) fica no centro (0.5).
 *   -20 → 0,  -3 → 0.5,  +3 → 1
 */
export function vuToNormalized(vu: number): number {
  const clamped = Math.max(VU_MIN, Math.min(VU_MAX, vu));
  if (clamped <= VU_CENTER) {
    return ((clamped - VU_MIN) / (VU_CENTER - VU_MIN)) * 0.5;
  }
  return 0.5 + ((clamped - VU_CENTER) / (VU_MAX - VU_CENTER)) * 0.5;
}

/** Pico no time domain → dBFS para Power Meter (-60 a 0). */
export function computePeak_dBFS(analyser: AnalyserNode, buf?: Float32Array): number {
  const buffer = (buf ?? new Float32Array(analyser.fftSize)) as Float32Array<ArrayBuffer>;
  analyser.getFloatTimeDomainData(buffer);
  let peak = 0;
  for (let i = 0; i < buffer.length; i++) {
    peak = Math.max(peak, Math.abs(buffer[i]));
  }
  const dbFS = peak > 0 ? 20 * Math.log10(peak) : DBFS_MIN;
  return Math.max(DBFS_MIN, Math.min(DBFS_MAX, isFinite(dbFS) ? dbFS : DBFS_MIN));
}

/**
 * Converte dBFS para posição normalizada 0–1 (Power Meter).
 * Mapeamento não-linear (piecewise): DBFS_CENTER (-12) fica no centro (0.5).
 *   -60 → 0,  -12 → 0.5,  0 → 1
 */
export function dBFS_toNormalized(dBFS: number): number {
  const clamped = Math.max(DBFS_MIN, Math.min(DBFS_MAX, dBFS));
  if (clamped <= DBFS_CENTER) {
    return ((clamped - DBFS_MIN) / (DBFS_CENTER - DBFS_MIN)) * 0.5;
  }
  return 0.5 + ((clamped - DBFS_CENTER) / (DBFS_MAX - DBFS_CENTER)) * 0.5;
}

/** FFT para spectrum analyzer (byte frequency data). */
export function computeFFT(analyser: AnalyserNode, buf?: Uint8Array): Uint8Array {
  const data = (buf ?? new Uint8Array(analyser.frequencyBinCount)) as Uint8Array<ArrayBuffer>;
  analyser.getByteFrequencyData(data);
  return data;
}

export interface QualityMeta {
  codec?: string;
  bitrate?: number;
  sampleRate?: number;
}

/**
 * Loudness inteligente Hi-Fi: boost de graves/agudos proporcional ao volume
 * efetivo (slider * ATT) com compensação por codec.
 */
export function computeLoudnessBoost(
  volumePercent: number,
  attOn: boolean,
  codec: string | undefined
): { bassBoost: number; trebleBoost: number } {
  const effectiveVolume = (volumePercent / 100) * (attOn ? 0.1 : 1.0);
  const volumeFactor = Math.max(0, 1 - effectiveVolume);

  const maxBass = 10;
  const maxTreble = 6;

  let codecMul = 1.0;
  const c = (codec || '').toUpperCase();
  if (c === 'FLAC' || c === 'ALAC') codecMul = 0.8;
  else if (c === 'MP3')             codecMul = 1.2;
  else if (c === 'AAC')             codecMul = 1.1;

  return {
    bassBoost:   Math.round(maxBass * volumeFactor * codecMul * 10) / 10,
    trebleBoost: Math.round(maxTreble * volumeFactor * codecMul * 10) / 10,
  };
}

/** Inferir meta a partir de Content-Type ou nome de arquivo (heurística). */
export function inferQualityMeta(contentType: string | null, fileName: string): QualityMeta | null {
  const name = (fileName || '').toLowerCase();
  const type = (contentType || '').toLowerCase();

  if (type.includes('flac') || name.endsWith('.flac')) {
    return { codec: 'FLAC', sampleRate: 44100 };
  }
  if (type.includes('mp3') || name.endsWith('.mp3')) {
    return { codec: 'MP3', bitrate: 320 };
  }
  if (name.endsWith('.m4a') || name.endsWith('.alac')) {
    return { codec: 'ALAC' };
  }
  if (type.includes('aac')) return { codec: 'AAC' };
  return null;
}
