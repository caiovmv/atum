import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useWavesurfer } from '@wavesurfer/react';
import { createAudioEngine, type AudioEngine } from '../../audio/audioEngine';
import {
  computeRMS_dBFS,
  dBFS_to_VU,
  computePeak_dBFS,
  computeFFT,
  computeStreamingSignal,
  computeLoudnessBoost,
  detectQuality,
  inferQualityMeta,
  type QualityMeta,
} from '../../audio/analysis';
import { VuMeter } from './VuMeter';
import { PowerMeter } from './PowerMeter';
import { Spectrum } from './Spectrum';
import { ParametricEQ } from './ParametricEQ';
import { ReceiverSlider } from './ReceiverSlider';
import { ReceiverToggle } from './ReceiverToggle';
import { StreamingSignal } from './StreamingSignal';
import { QualityTune } from './QualityTune';
import '../../styles/receiver.css';

const VFD_COLOR = '#00e5c8';
const NUM_EQ_BANDS = 10;
const INITIAL_EQ = new Array(NUM_EQ_BANDS).fill(0);

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

interface ReceiverPanelProps {
  streamUrl: string;
  title: string;
  fileName?: string;
  contentType?: string | null;
  onNext?: () => void;
  hasNext?: boolean;
  className?: string;
}

export function ReceiverPanel({
  streamUrl,
  title,
  fileName = '',
  contentType = null,
  onNext,
  hasNext,
  className = '',
}: ReceiverPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<AudioEngine | null>(null);
  const [engineReady, setEngineReady] = useState(false);

  // Meter state (L/R independentes)
  const [vuValueL, setVuValueL] = useState(-20);
  const [vuValueR, setVuValueR] = useState(-20);
  const [peakValue, setPeakValue] = useState(-60);
  const [fftData, setFftData] = useState<Uint8Array>(new Uint8Array(0));
  const [sampleRate, setSampleRate] = useState(44100);
  const [streamSignal, setStreamSignal] = useState(1);
  const [qualityMeta, setQualityMeta] = useState<QualityMeta | null>(null);

  // DSP control state
  const [volume, setVolume] = useState(80);
  const [balance, setBalance] = useState(0);
  const [eqGains, setEqGains] = useState<number[]>(INITIAL_EQ);
  const [bass, setBass] = useState(0);
  const [mid, setMid] = useState(0);
  const [treble, setTreble] = useState(0);
  const [loudness, setLoudness] = useState(false);
  const [att, setAtt] = useState(false);

  const { wavesurfer, isReady, isPlaying, currentTime } = useWavesurfer({
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

  const resumeAndPlay = useCallback(() => {
    if (!wavesurfer) return;
    const media = wavesurfer.getMediaElement();
    if (!media || !engineRef.current) return;
    if (engineRef.current.ctx.state === 'suspended') {
      engineRef.current.ctx.resume();
    }
    wavesurfer.playPause();
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
      engineRef.current = null;
      setEngineReady(false);
    };
  }, [isReady, wavesurfer, contentType, fileName]);

  // Analysis loop (L/R independentes)
  useEffect(() => {
    if (!isReady || !wavesurfer || !engineReady) return;
    const media = wavesurfer.getMediaElement();
    if (!media) return;
    let raf = 0;
    const tick = () => {
      const engine = engineRef.current;
      if (!engine?.analyser) { raf = requestAnimationFrame(tick); return; }
      setVuValueL(dBFS_to_VU(computeRMS_dBFS(engine.analyserL)));
      setVuValueR(dBFS_to_VU(computeRMS_dBFS(engine.analyserR)));
      setPeakValue(computePeak_dBFS(engine.analyser));
      setFftData(computeFFT(engine.analyser));
      setStreamSignal(computeStreamingSignal(media));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [isReady, wavesurfer, engineReady]);

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

  const loudnessOverlay = useMemo(() => {
    if (!loudness) return undefined;
    const { bassBoost, trebleBoost } = computeLoudnessBoost(volume, att, qualityMeta?.codec);
    return [
      bassBoost,
      bassBoost,
      Math.round(bassBoost * 0.5),
      0, 0, 0, 0,
      Math.round(trebleBoost * 0.3),
      Math.round(trebleBoost * 0.8),
      trebleBoost,
    ];
  }, [loudness, volume, att, qualityMeta]);

  const qualityScore = detectQuality(qualityMeta);
  const qualityLabel = qualityMeta?.codec
    ? qualityMeta.bitrate
      ? `${qualityMeta.codec} ${qualityMeta.bitrate}`
      : qualityMeta.codec
    : '';

  const formatTime = (s: number) => {
    if (!isFinite(s) || s < 0) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  const duration = wavesurfer?.getDuration() ?? 0;

  return (
    <div className={`receiver-panel ${className}`.trim()}>
      <div className="receiver-row-meters">
        <div className="receiver-meters-lr">
          <VuMeter value={vuValueL} label="dBLevel L" />
          <VuMeter value={vuValueR} label="dBLevel R" />
        </div>
        <PowerMeter value={peakValue} />
      </div>

      <Spectrum data={fftData} sampleRate={sampleRate} />

      <ParametricEQ gains={eqGains} overlay={loudnessOverlay} onChange={handleEqChange} onFlat={handleEqFlat} />

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
            min={-12}
            max={12}
            onChange={handleBass}
            label="BASS"
            displayValue={toneDisplay(bass)}
          />
          <ReceiverSlider
            value={mid}
            min={-12}
            max={12}
            onChange={handleMid}
            label="MID"
            displayValue={toneDisplay(mid)}
          />
          <ReceiverSlider
            value={treble}
            min={-12}
            max={12}
            onChange={handleTreble}
            label="TREBLE"
            displayValue={toneDisplay(treble)}
          />
        </div>
        <div className="receiver-controls-cluster">
          <ReceiverToggle active={loudness} onToggle={() => setLoudness((p) => !p)} label="LOUDNESS" />
          <ReceiverToggle active={att} onToggle={() => setAtt((p) => !p)} label="ATT -20dB" />
        </div>
      </div>

      <div className="receiver-row-info">
        <span className="receiver-title">{title || '—'}</span>
        <span className="receiver-time">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>

      <div className="receiver-row-signals">
        <StreamingSignal value={streamSignal} />
        <QualityTune value={qualityScore} label={qualityLabel} />
      </div>

      <div className="receiver-waveform-wrap" ref={containerRef} />

      <div className="receiver-play-row">
        <button type="button" className="receiver-play-btn" onClick={resumeAndPlay} aria-label={isPlaying ? 'Pausar' : 'Reproduzir'}>
          {isPlaying ? 'Pausar' : 'Reproduzir'}
        </button>
      </div>

      {hasNext && onNext && (
        <div className="receiver-next-row">
          <button type="button" className="atum-player-next-btn" onClick={onNext}>
            Próximo
          </button>
        </div>
      )}
    </div>
  );
}
