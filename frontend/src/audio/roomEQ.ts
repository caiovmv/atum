/**
 * Room EQ: mede a resposta acustica da sala usando microfone e sinal
 * de teste (pink noise), calcula correcao inversa para as 10 bandas do EQ.
 *
 * Fluxo: gerar pink noise → tocar nas caixas → capturar mic → FFT → correcao.
 */

import { extractBandEnergies, EQ_BANDS } from './spectralEQ';

export interface RoomMeasurement {
  measured: number[];
  correction: number[];
  timestamp: number;
}

export type RoomEQPhase = 'idle' | 'requesting-mic' | 'measuring' | 'done' | 'error';

/**
 * Gera um AudioBuffer com pink noise via Web Worker (off main thread).
 * Fallback síncrono se Workers não estiverem disponíveis.
 */
export async function generatePinkNoise(ctx: AudioContext, durationSec: number): Promise<AudioBuffer> {
  const length = Math.ceil(ctx.sampleRate * durationSec);

  try {
    const worker = new Worker(new URL('./pinkNoise.worker.ts', import.meta.url), { type: 'module' });
    const samples = await new Promise<Float32Array>((resolve, reject) => {
      worker.onmessage = (e: MessageEvent<ArrayBuffer>) => {
        resolve(new Float32Array(e.data));
        worker.terminate();
      };
      worker.onerror = (err) => {
        worker.terminate();
        reject(err);
      };
      worker.postMessage({ length });
    });
    const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
    buffer.getChannelData(0).set(samples);
    return buffer;
  } catch {
    return generatePinkNoiseFallback(ctx, length);
  }
}

function generatePinkNoiseFallback(ctx: AudioContext, length: number): AudioBuffer {
  const buffer = ctx.createBuffer(1, length, ctx.sampleRate);
  const data = buffer.getChannelData(0);

  let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
  for (let i = 0; i < length; i++) {
    const white = Math.random() * 2 - 1;
    b0 = 0.99886 * b0 + white * 0.0555179;
    b1 = 0.99332 * b1 + white * 0.0750759;
    b2 = 0.96900 * b2 + white * 0.1538520;
    b3 = 0.86650 * b3 + white * 0.3104856;
    b4 = 0.55000 * b4 + white * 0.5329522;
    b5 = -0.7616 * b5 - white * 0.0168980;
    const pink = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362;
    b6 = white * 0.115926;
    data[i] = pink * 0.11;
  }
  return buffer;
}

/**
 * Solicita acesso ao microfone do usuario.
 */
export async function requestMicrophone(): Promise<MediaStream> {
  return navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
    },
  });
}

/**
 * Executa a medicao completa da sala:
 * 1. Solicita mic
 * 2. Toca pink noise
 * 3. Captura FFT do mic em multiplas amostras
 * 4. Calcula correcao inversa
 *
 * Retorna um objeto com callbacks para controle.
 */
export class RoomEQSession {
  private ctx: AudioContext;
  private micStream: MediaStream | null = null;
  private micSource: MediaStreamAudioSourceNode | null = null;
  private micAnalyser: AnalyserNode | null = null;
  private noiseSource: AudioBufferSourceNode | null = null;
  private noiseGain: GainNode | null = null;
  private snapshots: number[][] = [];
  private rafId = 0;
  private targetSnapshots = 150; // ~5s at 30fps

  phase: RoomEQPhase = 'idle';
  progress = 0;
  result: RoomMeasurement | null = null;
  error: string | null = null;

  private onUpdate: () => void;

  constructor(ctx: AudioContext, onUpdate: () => void) {
    this.ctx = ctx;
    this.onUpdate = onUpdate;
  }

  async start(volume = 0.3): Promise<void> {
    this.phase = 'requesting-mic';
    this.error = null;
    this.result = null;
    this.progress = 0;
    this.snapshots = [];
    this.onUpdate();

    try {
      this.micStream = await requestMicrophone();
    } catch (err) {
      this.phase = 'error';
      this.error = 'Acesso ao microfone negado';
      this.onUpdate();
      return;
    }

    this.micSource = this.ctx.createMediaStreamSource(this.micStream);
    this.micAnalyser = this.ctx.createAnalyser();
    this.micAnalyser.fftSize = 8192;
    this.micAnalyser.smoothingTimeConstant = 0.4;
    this.micSource.connect(this.micAnalyser);

    const pinkBuffer = await generatePinkNoise(this.ctx, 6);
    this.noiseGain = this.ctx.createGain();
    this.noiseGain.gain.value = volume;
    this.noiseSource = this.ctx.createBufferSource();
    this.noiseSource.buffer = pinkBuffer;
    this.noiseSource.loop = true;
    this.noiseSource.connect(this.noiseGain);
    this.noiseGain.connect(this.ctx.destination);
    this.noiseSource.start();

    this.phase = 'measuring';
    this.onUpdate();

    // Wait 0.5s for pink noise to stabilize before measuring
    setTimeout(() => this.collectLoop(), 500);
  }

  private collectLoop(): void {
    if (this.phase !== 'measuring' || !this.micAnalyser) return;

    const data = new Uint8Array(this.micAnalyser.frequencyBinCount);
    this.micAnalyser.getByteFrequencyData(data);
    const energies = extractBandEnergies(data, this.ctx.sampleRate);
    this.snapshots.push(energies);
    this.progress = Math.min(1, this.snapshots.length / this.targetSnapshots);
    this.onUpdate();

    if (this.snapshots.length >= this.targetSnapshots) {
      this.finish();
      return;
    }

    this.rafId = requestAnimationFrame(() => this.collectLoop());
  }

  stop(): void {
    if (this.snapshots.length >= 30) {
      this.finish();
    } else {
      this.cleanup();
      this.phase = 'idle';
      this.onUpdate();
    }
  }

  private finish(): void {
    this.cleanup();

    const numBands = EQ_BANDS.length;
    const avg = new Array(numBands).fill(0);
    for (const snap of this.snapshots) {
      for (let i = 0; i < numBands; i++) avg[i] += snap[i];
    }
    for (let i = 0; i < numBands; i++) avg[i] /= this.snapshots.length;

    // Flat target: all bands should have equal energy.
    // Pink noise has equal energy per octave, so a flat room should read ~equal.
    const mean = avg.reduce((s, v) => s + v, 0) / numBands;
    const correction = avg.map((v) => {
      const delta = mean - v; // inverse: if band is loud, cut it
      return Math.max(-6, Math.min(6, Math.round(delta)));
    });

    this.result = { measured: avg, correction, timestamp: Date.now() };
    this.phase = 'done';
    this.onUpdate();
  }

  private cleanup(): void {
    cancelAnimationFrame(this.rafId);
    try { this.noiseSource?.stop(); } catch { /* already stopped */ }
    this.noiseSource?.disconnect();
    this.noiseGain?.disconnect();
    this.micSource?.disconnect();
    this.micAnalyser?.disconnect();
    if (this.micStream) {
      for (const track of this.micStream.getTracks()) track.stop();
    }
    this.micStream = null;
    this.micSource = null;
    this.micAnalyser = null;
    this.noiseSource = null;
    this.noiseGain = null;
  }

  dispose(): void {
    this.cleanup();
    this.phase = 'idle';
  }
}
