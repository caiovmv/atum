/**
 * Extração de energia por faixa de frequência para visualizadores audiovisuais.
 * bass: ~20-200 Hz, mid: ~200-1200 Hz, treble: ~1.2k-11 kHz
 */

export interface AudioEnergy {
  bass: number;
  mid: number;
  treble: number;
  rms?: number;
}

/** Bins aproximados para fftSize 2048 @ 44.1kHz: bin = freq / (sampleRate/fftSize) */
const BASS_END = 20;
const MID_END = 120;
const TREBLE_END = 512;

/** Boost de sensibilidade: música típica tem valores baixos no FFT */
const SENSITIVITY = 2.5;
/** Curva para expandir a faixa dinâmica (valor^exp) */
const CURVE_EXP = 0.7;

function applyResponse(raw: number): number {
  const boosted = Math.min(1, raw * SENSITIVITY);
  return Math.pow(boosted, CURVE_EXP);
}

/**
 * Extrai energia normalizada (0-1) por faixa a partir do FFT.
 * Usa getByteFrequencyData do AnalyserNode.
 * Aplica boost e curva para resposta mais visível à música.
 */
export function extractAudioEnergy(
  analyser: AnalyserNode,
  freqBuf: Uint8Array
): AudioEnergy {
  analyser.getByteFrequencyData(freqBuf as Uint8Array<ArrayBuffer>);

  let bass = 0;
  let mid = 0;
  let treble = 0;

  const len = Math.min(freqBuf.length, TREBLE_END);

  for (let i = 0; i < len; i++) {
    const v = freqBuf[i] / 255;
    if (i < BASS_END) {
      bass += v;
    } else if (i < MID_END) {
      mid += v;
    } else {
      treble += v;
    }
  }

  return {
    bass: applyResponse(Math.min(1, bass / BASS_END)),
    mid: applyResponse(Math.min(1, mid / (MID_END - BASS_END))),
    treble: applyResponse(Math.min(1, treble / (TREBLE_END - MID_END))),
  };
}
