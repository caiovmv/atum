import { useEffect, useRef, useState, useCallback, useMemo, type UIEvent } from 'react';
import { useWavesurfer } from '@wavesurfer/react';
import { createAudioEngine, type AudioEngine } from '../../audio/audioEngine';
import {
  computeRMS_dBFS,
  dBFS_to_VU,
  computePeak_dBFS,
  computeFFT,
  computeLoudnessBoost,
  inferQualityMeta,
  type QualityMeta,
} from '../../audio/analysis';
import { VuMeter } from './VuMeter';
import { PowerMeter } from './PowerMeter';
import { Spectrum } from './Spectrum';
import { ParametricEQ } from './ParametricEQ';
import { ReceiverSlider } from './ReceiverSlider';
import { ReceiverToggle } from './ReceiverToggle';
import { SmartEQ } from './SmartEQ';
import '../../styles/receiver.css';
import '../../styles/smarteq.css';

const VFD_COLOR = '#00e5c8';
const NUM_EQ_BANDS = 10;
const INITIAL_EQ = new Array(NUM_EQ_BANDS).fill(0);
const LS_KEY = 'receiver-dsp-state';

interface DspPersist {
  volume: number;
  balance: number;
  eqGains: number[];
  bass: number;
  mid: number;
  treble: number;
  loudness: boolean;
  att: boolean;
}

function loadDspState(): Partial<DspPersist> {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Partial<DspPersist>;
  } catch { return {}; }
}

function saveDspState(s: DspPersist): void {
  try { localStorage.setItem(LS_KEY, JSON.stringify(s)); } catch { /* quota */ }
}

const BASS_BANDS = [0, 1, 2];
const MID_BANDS = [3, 4, 5, 6];
const TREBLE_BANDS = [7, 8, 9];

function balanceDisplay(v: number): string {
  if (v === 0) return 'C';
  return v < 0 ? `L${Math.abs(v)}` : `R${v}`;
}

function toneDisplay(v: number): string {
  if (v === 0) return '0';
  return v > 0 ? `+${v}` : `${v}`;
}

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, '0')}`;
}

interface ReceiverPanelProps {
  streamUrl: string;
  title: string;
  fileName?: string;
  contentType?: string | null;
  onNext?: () => void;
  onPrev?: () => void;
  hasNext?: boolean;
  hasPrev?: boolean;
  className?: string;
}

export function ReceiverPanel({
  streamUrl,
  title,
  fileName = '',
  contentType = null,
  onNext,
  onPrev,
  hasNext,
  hasPrev,
  className = '',
}: ReceiverPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<AudioEngine | null>(null);
  const [engineReady, setEngineReady] = useState(false);

  // Meter state (consolidated for fewer re-renders)
  const [meterState, setMeterState] = useState<{ vuL: number; vuR: number; peak: number; fft: Uint8Array }>({
    vuL: -20,
    vuR: -20,
    peak: -60,
    fft: new Uint8Array(0),
  });
  const [sampleRate, setSampleRate] = useState(44100);
  const [qualityMeta, setQualityMeta] = useState<QualityMeta | null>(null);
  const analysisBuffers = useRef<{ timeL: Float32Array | null; timeR: Float32Array | null; timeMono: Float32Array | null; freq: Uint8Array | null }>({ timeL: null, timeR: null, timeMono: null, freq: null });

  // DSP control state (restored from localStorage)
  const savedDsp = useRef(loadDspState()).current;
  const [volume, setVolume] = useState(savedDsp.volume ?? 80);
  const [balance, setBalance] = useState(savedDsp.balance ?? 0);
  const [eqGains, setEqGains] = useState<number[]>(savedDsp.eqGains ?? INITIAL_EQ);
  const [bass, setBass] = useState(savedDsp.bass ?? 0);
  const [mid, setMid] = useState(savedDsp.mid ?? 0);
  const [treble, setTreble] = useState(savedDsp.treble ?? 0);
  const [loudness, setLoudness] = useState(savedDsp.loudness ?? false);
  const [att, setAtt] = useState(savedDsp.att ?? false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showWaveform, setShowWaveform] = useState(false);
  const [smartEqActive, setSmartEqActive] = useState(false);
  const [smartEqPreview, setSmartEqPreview] = useState<number[] | null>(null);
  const [powerOn, setPowerOn] = useState(true);
  const [activeStack, setActiveStack] = useState(0);
  const swipeRef = useRef<HTMLDivElement>(null);

  const STACK_COUNT = 5;

  const handleSwipeScroll = useCallback((e: UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    if (!el || el.scrollWidth <= el.clientWidth) return;
    const idx = Math.round(el.scrollLeft / el.clientWidth);
    setActiveStack(Math.max(0, Math.min(STACK_COUNT - 1, idx)));
  }, []);

  const { wavesurfer, isReady, isPlaying } = useWavesurfer({
    container: containerRef,
    url: streamUrl,
    waveColor: VFD_COLOR,
    progressColor: 'rgba(255,255,255,0.4)',
    height: 72,
    barWidth: 2,
    barGap: 1,
    barRadius: 1,
    normalize: true,
  });

  useEffect(() => {
    if (!wavesurfer) return;
    const onTime = (t: number) => setCurrentTime(t);
    const onReady = () => setDuration(wavesurfer.getDuration());
    wavesurfer.on('timeupdate', onTime);
    wavesurfer.on('ready', onReady);
    return () => {
      wavesurfer.un('timeupdate', onTime);
      wavesurfer.un('ready', onReady);
    };
  }, [wavesurfer]);

  const resumeAndPlay = useCallback(() => {
    if (!wavesurfer) return;
    const media = wavesurfer.getMediaElement();
    if (!media || !engineRef.current) return;
    if (engineRef.current.ctx.state === 'suspended') {
      engineRef.current.ctx.resume();
    }
    wavesurfer.playPause();
  }, [wavesurfer]);

  const handleStop = useCallback(() => {
    if (!wavesurfer) return;
    wavesurfer.stop();
  }, [wavesurfer]);

  const handleSeekBack = useCallback(() => {
    if (!wavesurfer) return;
    wavesurfer.skip(-10);
  }, [wavesurfer]);

  const handleSeekForward = useCallback(() => {
    if (!wavesurfer) return;
    wavesurfer.skip(10);
  }, [wavesurfer]);

  // Initialize audio engine (reutiliza se já existir no elemento)
  useEffect(() => {
    if (!isReady || !wavesurfer) return;
    const media = wavesurfer.getMediaElement();
    if (!media) return;
    media.crossOrigin = 'anonymous';
    const engine = createAudioEngine(media);
    engineRef.current = engine;
    if (engine.ctx.state === 'suspended') engine.ctx.resume();
    setSampleRate(engine.ctx.sampleRate);
    setQualityMeta(inferQualityMeta(contentType, fileName));
    setEngineReady(true);
    return () => {
      engine.dispose();
      engineRef.current = null;
      setEngineReady(false);
    };
  }, [isReady, wavesurfer, contentType, fileName]);

  // Analysis loop (~30fps, consolidated state, reused buffers)
  useEffect(() => {
    if (!isReady || !wavesurfer || !engineReady) return;
    const media = wavesurfer.getMediaElement();
    if (!media) return;
    let raf = 0;
    let frame = 0;
    const tick = () => {
      frame++;
      const engine = engineRef.current;
      if (!engine?.analyser) { raf = requestAnimationFrame(tick); return; }
      if (frame % 2 === 0) {
        const bufs = analysisBuffers.current;
        if (!bufs.timeL || bufs.timeL.length !== engine.analyserL.fftSize)
          bufs.timeL = new Float32Array(engine.analyserL.fftSize);
        if (!bufs.timeR || bufs.timeR.length !== engine.analyserR.fftSize)
          bufs.timeR = new Float32Array(engine.analyserR.fftSize);
        if (!bufs.timeMono || bufs.timeMono.length !== engine.analyser.fftSize)
          bufs.timeMono = new Float32Array(engine.analyser.fftSize);
        if (!bufs.freq || bufs.freq.length !== engine.analyser.frequencyBinCount)
          bufs.freq = new Uint8Array(engine.analyser.frequencyBinCount);

        const vuL = dBFS_to_VU(computeRMS_dBFS(engine.analyserL, bufs.timeL));
        const vuR = dBFS_to_VU(computeRMS_dBFS(engine.analyserR, bufs.timeR));
        const peak = computePeak_dBFS(engine.analyser, bufs.timeMono);
        computeFFT(engine.analyser, bufs.freq);
        setMeterState({ vuL, vuR, peak, fft: bufs.freq });
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [isReady, wavesurfer, engineReady]);

  // Persist DSP state to localStorage
  useEffect(() => {
    saveDspState({ volume, balance, eqGains, bass, mid, treble, loudness, att });
  }, [volume, balance, eqGains, bass, mid, treble, loudness, att]);

  // Sync Volume
  useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;
    const p = engine.volumeGain.gain;
    const t = engine.ctx.currentTime;
    p.cancelScheduledValues(t);
    p.setValueAtTime(p.value, t);
    p.setTargetAtTime(volume / 100, t, 0.01);
  }, [volume, engineReady]);

  // Sync Balance
  useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;
    const p = engine.panner.pan;
    const t = engine.ctx.currentTime;
    p.cancelScheduledValues(t);
    p.setValueAtTime(p.value, t);
    p.setTargetAtTime(balance / 50, t, 0.01);
  }, [balance, engineReady]);

  // Sync EQ bands
  useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;
    const t = engine.ctx.currentTime;
    eqGains.forEach((g, i) => {
      if (engine.eqBands[i]) {
        const p = engine.eqBands[i].gain;
        p.cancelScheduledValues(t);
        p.setValueAtTime(p.value, t);
        p.setTargetAtTime(g, t, 0.01);
      }
    });
  }, [eqGains, engineReady]);

  // Sync Loudness (volume-aware + codec-aware)
  useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;
    const t = engine.ctx.currentTime;
    const lo = engine.loudnessLow.gain;
    const hi = engine.loudnessHigh.gain;
    lo.cancelScheduledValues(t);
    hi.cancelScheduledValues(t);
    lo.setValueAtTime(lo.value, t);
    hi.setValueAtTime(hi.value, t);
    if (loudness) {
      const { bassBoost, trebleBoost } = computeLoudnessBoost(
        volume, att, qualityMeta?.codec
      );
      lo.setTargetAtTime(bassBoost, t, 0.02);
      hi.setTargetAtTime(trebleBoost, t, 0.02);
    } else {
      lo.setTargetAtTime(0, t, 0.02);
      hi.setTargetAtTime(0, t, 0.02);
    }
  }, [loudness, volume, att, qualityMeta, engineReady]);

  // Sync ATT
  useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;
    const p = engine.attGain.gain;
    const t = engine.ctx.currentTime;
    p.cancelScheduledValues(t);
    p.setValueAtTime(p.value, t);
    p.setTargetAtTime(att ? 0.1 : 1.0, t, 0.02);
  }, [att, engineReady]);

  const handleEqChange = useCallback((index: number, value: number) => {
    setEqGains((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  }, []);

  const handleEqFlat = useCallback(() => {
    setEqGains(new Array(NUM_EQ_BANDS).fill(0));
    setBass(0);
    setMid(0);
    setTreble(0);
  }, []);

  const applyTone = useCallback((bands: number[], value: number) => {
    setEqGains((prev) => {
      const next = [...prev];
      for (const i of bands) next[i] = value;
      return next;
    });
  }, []);

  const handleBass = useCallback((v: number) => {
    const rounded = Math.round(v);
    setBass(rounded);
    applyTone(BASS_BANDS, rounded);
  }, [applyTone]);

  const handleMid = useCallback((v: number) => {
    const rounded = Math.round(v);
    setMid(rounded);
    applyTone(MID_BANDS, rounded);
  }, [applyTone]);

  const handleTreble = useCallback((v: number) => {
    const rounded = Math.round(v);
    setTreble(rounded);
    applyTone(TREBLE_BANDS, rounded);
  }, [applyTone]);

  const handleSmartEqCorrection = useCallback((gains: number[]) => {
    setEqGains(gains);
    setBass(0);
    setMid(0);
    setTreble(0);
  }, []);

  const handleSmartEqPreset = useCallback((gains: number[]) => {
    setEqGains(gains);
    setBass(0);
    setMid(0);
    setTreble(0);
  }, []);

  const handleSmartEqPreview = useCallback((gains: number[] | null) => {
    setSmartEqPreview(gains);
  }, []);

  const loudnessOverlay = useMemo(() => {
    if (!loudness) return undefined;
    const { bassBoost, trebleBoost } = computeLoudnessBoost(volume, att, qualityMeta?.codec);
    const clamp6 = (v: number) => Math.round(Math.max(-6, Math.min(6, v)));
    return [
      clamp6(bassBoost),
      clamp6(bassBoost),
      clamp6(bassBoost * 0.5),
      0, 0, 0, 0,
      clamp6(trebleBoost * 0.3),
      clamp6(trebleBoost * 0.8),
      clamp6(trebleBoost),
    ];
  }, [loudness, volume, att, qualityMeta]);

  const iconSvg = (d: string, w = 14, h = 12) => (
    <svg className="receiver-transport-svg" viewBox={`0 0 ${w} ${h}`} width={w} height={h} fill="currentColor">
      <path d={d} />
    </svg>
  );

  return (
    <div className={`receiver-panel ${className}`.trim()}>
      <div className="receiver-swipe-container" ref={swipeRef} onScroll={handleSwipeScroll}>
      {/* Stack 1: Header */}
      <div className="receiver-header">
        <div className="receiver-brand-group">
          <span className="receiver-brand">ATUM</span>
          <span className="receiver-model">SRX-900</span>
        </div>
        <div className="receiver-header-display">
          <span className="receiver-header-title">{title}</span>
          <span className="receiver-header-time">
            {formatTime(currentTime)}{duration > 0 ? ` / ${formatTime(duration)}` : ''}
          </span>
        </div>
        <div className="receiver-transport">
          <button type="button" className="receiver-transport-btn" onClick={handleSeekBack} aria-label="Voltar 10s" title="-10s">
            {iconSvg('M1 1v10h1.5V6.5L7 10V6.5L11.5 10V2L7 5.5V2L2.5 5.5V1z')}
          </button>
          <button type="button" className={`receiver-transport-btn${!hasPrev ? ' receiver-transport-btn--disabled' : ''}`} onClick={onPrev} disabled={!hasPrev} aria-label="Anterior">
            {iconSvg('M1.5 1v10h1.5V1zM4 6l5 5V1z M9 6l5 5V1z')}
          </button>
          <button type="button" className="receiver-transport-btn" onClick={handleStop} aria-label="Parar">
            {iconSvg('M2 2h10v8H2z')}
          </button>
          <button type="button" className={`receiver-transport-btn receiver-transport-btn--play${isPlaying ? ' receiver-transport-btn--active' : ''}`} onClick={resumeAndPlay} aria-label={isPlaying ? 'Pausar' : 'Reproduzir'}>
            {isPlaying
              ? iconSvg('M3 1h3v10H3zM8 1h3v10H8z')
              : iconSvg('M3 1v10l9-5z')
            }
          </button>
          <button type="button" className={`receiver-transport-btn${!hasNext ? ' receiver-transport-btn--disabled' : ''}`} onClick={onNext} disabled={!hasNext} aria-label="Próxima">
            {iconSvg('M0 1l5 5-5 5z M5 1l5 5-5 5z M11 1h1.5v10H11z')}
          </button>
          <button type="button" className="receiver-transport-btn" onClick={handleSeekForward} aria-label="Avançar 10s" title="+10s">
            {iconSvg('M2.5 2v8L7 5.5V10l4.5-3.5V11H13.5V1H12V5.5L7 2v3.5L2.5 2z')}
          </button>
        </div>
        <button
          type="button"
          className={`receiver-transport-btn receiver-power-btn${powerOn ? ' receiver-transport-btn--active' : ''}`}
          aria-label={powerOn ? 'Desligar' : 'Ligar'}
          onClick={() => {
            const next = !powerOn;
            setPowerOn(next);
            const engine = engineRef.current;
            if (engine) {
              if (next) {
                engine.ctx.resume();
              } else {
                engine.ctx.suspend();
                if (wavesurfer && isPlaying) wavesurfer.pause();
              }
            }
          }}
        >
          <svg className="receiver-transport-svg receiver-power-icon" viewBox="0 0 14 14" width={14} height={14} fill="currentColor">
            <path d="M7 1v5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" fill="none" />
            <path d="M3.5 3.8A5 5 0 1 0 10.5 3.8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" fill="none" />
          </svg>
        </button>
      </div>

      <div className="receiver-bezel" />

      {/* Stack 2: Meters */}
      <div className="receiver-stack-meters">
        <div className="receiver-stack-glass">
          <div className="receiver-row-meters">
            <div className="receiver-meters-lr">
              <VuMeter value={meterState.vuL} label="dBLevel L" meterIndex={0} />
              <VuMeter value={meterState.vuR} label="dBLevel R" meterIndex={1} />
            </div>
            <PowerMeter value={meterState.peak} />
          </div>
        </div>
      </div>

      <div className="receiver-bezel" />

      {/* Stack 3: Spectrum + Waveform */}
      <div className="receiver-stack-spectrum">
        <div className="receiver-stack-glass">
          <Spectrum data={meterState.fft} sampleRate={sampleRate} />
          <div
            className={`receiver-waveform-wrap${showWaveform ? '' : ' receiver-waveform-wrap--hidden'}`}
            ref={containerRef}
          />
          <button
            type="button"
            className={`receiver-waveform-toggle${showWaveform ? ' receiver-waveform-toggle--active' : ''}`}
            onClick={() => setShowWaveform((p) => !p)}
          >
            <span className="receiver-toggle-indicator" />
            <span className="receiver-waveform-toggle-label">WAVEFORM</span>
          </button>
        </div>
      </div>

      <div className="receiver-bezel" />

      {/* Stack 4: Parametric EQ */}
      <div className="receiver-stack-eq">
        <ParametricEQ gains={eqGains} overlay={smartEqPreview ?? loudnessOverlay} onChange={handleEqChange} onFlat={handleEqFlat} />
      </div>

      <div className="receiver-bezel" />

      {/* Stack 5: Controls */}
      <div className="receiver-stack-controls">
        <div className="receiver-controls-row">
          <div className="receiver-controls-cluster receiver-controls-cluster--sliders">
            <ReceiverSlider
              value={volume}
              min={0}
              max={100}
              onChange={setVolume}
              label="VOLUME"
              displayValue={`${Math.round(volume)}%`}
            />
            <ReceiverSlider
              value={balance}
              min={-50}
              max={50}
              onChange={(v) => setBalance(Math.round(v))}
              label="BALANCE"
              displayValue={balanceDisplay(Math.round(balance))}
            />
          </div>
          <div className="receiver-controls-cluster receiver-controls-cluster--sliders">
            <ReceiverSlider
              value={bass}
              min={-6}
              max={6}
              onChange={handleBass}
              label="BASS"
              displayValue={toneDisplay(bass)}
            />
            <ReceiverSlider
              value={mid}
              min={-6}
              max={6}
              onChange={handleMid}
              label="MID"
              displayValue={toneDisplay(mid)}
            />
            <ReceiverSlider
              value={treble}
              min={-6}
              max={6}
              onChange={handleTreble}
              label="TREBLE"
              displayValue={toneDisplay(treble)}
            />
          </div>
          <div className="receiver-controls-cluster">
            <ReceiverToggle active={loudness} onToggle={() => setLoudness((p) => !p)} label="LOUDNESS" />
            <ReceiverToggle active={att} onToggle={() => setAtt((p) => !p)} label="ATT -20dB" />
            <ReceiverToggle active={smartEqActive} onToggle={() => setSmartEqActive((p) => !p)} label="SMART EQ" />
          </div>
        </div>
        <div className={`smarteq-panel-wrap${smartEqActive ? ' smarteq-panel-wrap--open' : ''}`}>
          <SmartEQ
            fftData={meterState.fft}
            sampleRate={sampleRate}
            audioCtx={engineRef.current?.ctx ?? null}
            onApplyCorrection={handleSmartEqCorrection}
            onApplyPreset={handleSmartEqPreset}
            onCorrectionPreview={handleSmartEqPreview}
            active={smartEqActive}
          />
        </div>
      </div>
      </div>{/* end swipe-container */}

      {/* Dots VFD — visible only on mobile */}
      <div className="receiver-dots">
        {Array.from({ length: STACK_COUNT }, (_, i) => (
          <span key={i} className={`receiver-dot${i === activeStack ? ' receiver-dot--active' : ''}`} />
        ))}
      </div>
    </div>
  );
}
