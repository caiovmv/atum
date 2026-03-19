/**
 * Web Audio API engine: grafo DSP completo estilo receiver vintage.
 *
 * Source → ATT → Volume → EQ (10 bands) → Loudness (low+high shelf)
 *        → Balance (StereoPanner) → Splitter → analyserL (ch0)
 *                                             → analyserR (ch1)
 *                                 → analyser (stereo, FFT) → Destination
 */

const EQ_FREQUENCIES = [40, 80, 160, 315, 630, 1250, 2500, 5000, 10000, 20000];

export interface AudioEngine {
  ctx: AudioContext;
  analyser: AnalyserNode;
  /** Analyser com smoothing baixo para visualizador (resposta mais rápida) */
  analyserVisualizer: AnalyserNode;
  analyserL: AnalyserNode;
  analyserR: AnalyserNode;
  attGain: GainNode;
  volumeGain: GainNode;
  eqBands: BiquadFilterNode[];
  loudnessLow: BiquadFilterNode;
  loudnessHigh: BiquadFilterNode;
  panner: StereoPannerNode;
  dispose(): void;
}

const ENGINE_KEY = '__receiverEngine';

/**
 * Cria (ou reutiliza) o engine de audio para o elemento.
 * createMediaElementSource so pode ser chamado UMA VEZ por elemento,
 * entao guardamos o engine no proprio elemento para reuso seguro.
 */
export function createAudioEngine(audioElement: HTMLAudioElement): AudioEngine {
  const existing = (audioElement as unknown as Record<string, unknown>)[ENGINE_KEY] as AudioEngine | undefined;
  if (existing) {
    if (existing.ctx.state === 'suspended') existing.ctx.resume();
    return existing;
  }

  if (!audioElement.crossOrigin) audioElement.crossOrigin = 'anonymous';

  const ctx = new AudioContext();
  const source = ctx.createMediaElementSource(audioElement);

  const attGain = ctx.createGain();
  attGain.gain.value = 1.0;

  const volumeGain = ctx.createGain();
  volumeGain.gain.value = 1.0;

  const eqBands: BiquadFilterNode[] = EQ_FREQUENCIES.map((freq) => {
    const f = ctx.createBiquadFilter();
    f.type = 'peaking';
    f.frequency.value = freq;
    f.Q.value = 1.4;
    f.gain.value = 0;
    return f;
  });

  const loudnessLow = ctx.createBiquadFilter();
  loudnessLow.type = 'lowshelf';
  loudnessLow.frequency.value = 100;
  loudnessLow.gain.value = 0;

  const loudnessHigh = ctx.createBiquadFilter();
  loudnessHigh.type = 'highshelf';
  loudnessHigh.frequency.value = 10000;
  loudnessHigh.gain.value = 0;

  const panner = ctx.createStereoPanner();
  panner.pan.value = 0;

  const analyser = ctx.createAnalyser();
  analyser.fftSize = 2048;
  analyser.smoothingTimeConstant = 0.6;

  const analyserVisualizer = ctx.createAnalyser();
  analyserVisualizer.fftSize = 2048;
  analyserVisualizer.smoothingTimeConstant = 0.2;

  const analyserL = ctx.createAnalyser();
  analyserL.fftSize = 2048;
  analyserL.smoothingTimeConstant = 0.6;

  const analyserR = ctx.createAnalyser();
  analyserR.fftSize = 2048;
  analyserR.smoothingTimeConstant = 0.6;

  const splitter = ctx.createChannelSplitter(2);

  // Wire: Source → ATT → Volume → EQ chain → Loudness → Balance
  source.connect(attGain);
  attGain.connect(volumeGain);

  let prev: AudioNode = volumeGain;
  for (const band of eqBands) {
    prev.connect(band);
    prev = band;
  }

  prev.connect(loudnessLow);
  loudnessLow.connect(loudnessHigh);
  loudnessHigh.connect(panner);

  // Balance → stereo analyser (FFT/Spectrum) → analyserVisualizer → output
  panner.connect(analyser);
  analyser.connect(analyserVisualizer);
  analyserVisualizer.connect(ctx.destination);

  // Balance → splitter → per-channel analysers (VU L/R)
  panner.connect(splitter);
  splitter.connect(analyserL, 0);
  splitter.connect(analyserR, 1);

  const engine: AudioEngine = {
    ctx, analyser, analyserVisualizer, analyserL, analyserR,
    attGain, volumeGain, eqBands, loudnessLow, loudnessHigh, panner,
    dispose() {
      // No-op: engine persiste no elemento <audio> e é reutilizado via ENGINE_KEY.
      // createMediaElementSource só pode ser chamado UMA VEZ por elemento,
      // então o grafo de nós é preservado intacto entre trocas de faixa.
    },
  };
  (audioElement as unknown as Record<string, unknown>)[ENGINE_KEY] = engine;

  return engine;
}
