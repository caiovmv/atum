import { useEffect, useRef, useState, useCallback, useMemo, type UIEvent } from 'react';
import type WaveSurfer from 'wavesurfer.js';
import { createAudioEngine, type AudioEngine } from '../audio/audioEngine';
import {
  computeRMS_dBFS,
  dBFS_to_VU,
  computePeak_dBFS,
  computeFFT,
  computeLoudnessBoost,
  inferQualityMeta,
  type QualityMeta,
} from '../audio/analysis';
import { loadDspState, saveDspState } from '../audio/dspPersist';
import { createPlaylist } from '../api/playlists';
import { getSettings } from '../api/settings';
import { chat } from '../api/chat';
import type { EQSuggestion, AgentAction } from '../components/receiver/ReceiverAI';

const NUM_EQ_BANDS = 10;
const INITIAL_EQ = new Array(NUM_EQ_BANDS).fill(0);
const BASS_BANDS = [0, 1, 2];
const MID_BANDS = [3, 4, 5, 6];
const TREBLE_BANDS = [7, 8, 9];
const STACK_COUNT = 6;

interface UseReceiverPanelProps {
  streamUrl?: string;
  title: string;
  fileName?: string;
  contentType?: string | null;
  artist?: string;
  album?: string;
  coverUrl?: string;
  onNext?: () => void;
  onPrev?: () => void;
  onTimeUpdate?: (time: number) => void;
  onDurationChange?: (dur: number) => void;
  onPlayingChange?: (playing: boolean) => void;
  onEngineReady?: (engine: AudioEngine | null) => void;
  onNavigate?: (path: string) => void;
  wavesurfer: WaveSurfer | null;
  isReady: boolean;
  isPlaying: boolean | null;
}

export function useReceiverPanel({
  title,
  fileName = '',
  contentType = null,
  artist,
  album,
  onNext,
  onPrev,
  onTimeUpdate,
  onDurationChange,
  onPlayingChange,
  onEngineReady,
  onNavigate,
  wavesurfer,
  isReady,
  isPlaying,
}: UseReceiverPanelProps) {
  const engineRef = useRef<AudioEngine | null>(null);
  const [engineReady, setEngineReady] = useState(false);
  const [meterState, setMeterState] = useState<{ vuL: number; vuR: number; peak: number; fft: Uint8Array }>({
    vuL: -20,
    vuR: -20,
    peak: -60,
    fft: new Uint8Array(0),
  });
  const [sampleRate, setSampleRate] = useState(44100);
  const [qualityMeta, setQualityMeta] = useState<QualityMeta | null>(null);
  const analysisBuffers = useRef<{
    timeL: Float32Array | null;
    timeR: Float32Array | null;
    timeMono: Float32Array | null;
    freq: Uint8Array | null;
  }>({ timeL: null, timeR: null, timeMono: null, freq: null });

  const savedDsp = useRef(loadDspState()).current;
  const [volume, setVolume] = useState(savedDsp.volume ?? 50);
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
  const [scrollFraction, setScrollFraction] = useState(0);
  const [proactivePill, setProactivePill] = useState<string | null>(null);
  const proactivePillTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const [aiAvailable, setAiAvailable] = useState<boolean | null>(null);

  const handleSwipeScroll = useCallback((e: UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    if (!el || el.scrollWidth <= el.clientWidth) return;
    const frac = el.scrollLeft / el.clientWidth;
    setScrollFraction(frac);
    const idx = Math.max(0, Math.min(STACK_COUNT - 1, Math.round(frac)));
    setActiveStack((prev) => {
      if (prev !== idx) {
        try {
          navigator.vibrate?.(8);
        } catch {
          /* no vibration support */
        }
      }
      return idx;
    });
  }, []);

  useEffect(() => {
    if (!wavesurfer) return;
    const onTime = (t: number) => {
      setCurrentTime(t);
      onTimeUpdate?.(t);
    };
    const onReady = () => {
      const d = wavesurfer.getDuration();
      setDuration(d);
      onDurationChange?.(d);
    };
    wavesurfer.on('timeupdate', onTime);
    wavesurfer.on('ready', onReady);
    return () => {
      wavesurfer.un('timeupdate', onTime);
      wavesurfer.un('ready', onReady);
    };
  }, [wavesurfer, onTimeUpdate, onDurationChange]);

  useEffect(() => {
    if (isPlaying != null) onPlayingChange?.(isPlaying);
  }, [isPlaying, onPlayingChange]);

  useEffect(() => {
    getSettings()
      .then((d) => setAiAvailable(!!(d?.ai_provider && d?.ai_model)))
      .catch(() => setAiAvailable(false));
  }, []);

  useEffect(() => {
    if (!title || aiAvailable === false || aiAvailable === null) return;
    clearTimeout(proactivePillTimer.current);
    const ctrl = new AbortController();
    const timer = setTimeout(() => {
      chat(
        {
          messages: [
            {
              role: 'user',
              content: `Sobre "${title}"${artist ? ` de ${artist}` : ''}: dê UMA dica útil em até 12 palavras. Pode ser: sugestão de EQ para o gênero, curiosidade sobre a produção/gravação, ou artista similar. Se possível, seja específico (ex: "Grave marcante — tente Bass +3 para sentir o kick"). Responda SOMENTE a frase, sem aspas, sem pontuação final.`,
            },
          ],
          context: {
            track: title,
            artist,
            album,
            codec: qualityMeta?.codec,
            bitrate: qualityMeta?.bitrate != null ? `${qualityMeta.bitrate} kbps` : undefined,
          },
        },
        { signal: ctrl.signal }
      )
        .then((d) => {
          if (d?.content) {
            setProactivePill(d.content.slice(0, 80));
            proactivePillTimer.current = setTimeout(() => setProactivePill(null), 8000);
          }
        })
        .catch((e) => {
          if (e instanceof Error && e.message.includes('503')) setAiAvailable(false);
          else if (import.meta.env.DEV) console.warn('[ReceiverPanel] proactive pill fetch failed', e);
        });
    }, 2500);
    return () => {
      clearTimeout(timer);
      clearTimeout(proactivePillTimer.current);
      ctrl.abort();
    };
  }, [title, artist, album, aiAvailable, qualityMeta]);

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
    onEngineReady?.(engine);
    return () => {
      engine.dispose();
      engineRef.current = null;
      setEngineReady(false);
      onEngineReady?.(null);
    };
  }, [isReady, wavesurfer, contentType, fileName, onEngineReady]);

  useEffect(() => {
    if (!isReady || !wavesurfer || !engineReady) return;
    const media = wavesurfer.getMediaElement();
    if (!media) return;
    let raf = 0;
    let frame = 0;
    const tick = () => {
      frame++;
      const engine = engineRef.current;
      if (!engine?.analyser) {
        raf = requestAnimationFrame(tick);
        return;
      }
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
        setMeterState({ vuL, vuR, peak, fft: new Uint8Array(bufs.freq) });
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [isReady, wavesurfer, engineReady]);

  useEffect(() => {
    saveDspState({ volume, balance, eqGains, bass, mid, treble, loudness, att });
  }, [volume, balance, eqGains, bass, mid, treble, loudness, att]);

  useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;
    const p = engine.volumeGain.gain;
    const t = engine.ctx.currentTime;
    p.cancelScheduledValues(t);
    p.setValueAtTime(p.value, t);
    p.setTargetAtTime(volume / 100, t, 0.01);
  }, [volume, engineReady]);

  useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;
    const p = engine.panner.pan;
    const t = engine.ctx.currentTime;
    p.cancelScheduledValues(t);
    p.setValueAtTime(p.value, t);
    p.setTargetAtTime(balance / 50, t, 0.01);
  }, [balance, engineReady]);

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
      const { bassBoost, trebleBoost } = computeLoudnessBoost(volume, att, qualityMeta?.codec);
      lo.setTargetAtTime(bassBoost, t, 0.02);
      hi.setTargetAtTime(trebleBoost, t, 0.02);
    } else {
      lo.setTargetAtTime(0, t, 0.02);
      hi.setTargetAtTime(0, t, 0.02);
    }
  }, [loudness, volume, att, qualityMeta, engineReady]);

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

  const handleBass = useCallback(
    (v: number) => {
      const rounded = Math.round(v);
      setBass(rounded);
      applyTone(BASS_BANDS, rounded);
    },
    [applyTone]
  );

  const handleMid = useCallback(
    (v: number) => {
      const rounded = Math.round(v);
      setMid(rounded);
      applyTone(MID_BANDS, rounded);
    },
    [applyTone]
  );

  const handleTreble = useCallback(
    (v: number) => {
      const rounded = Math.round(v);
      setTreble(rounded);
      applyTone(TREBLE_BANDS, rounded);
    },
    [applyTone]
  );

  const handleApplyAIEQ = useCallback(
    (eq: EQSuggestion) => {
      handleBass(eq.bass);
      handleMid(eq.mid);
      handleTreble(eq.treble);
    },
    [handleBass, handleMid, handleTreble]
  );

  const actionDepsRef = useRef({
    resumeAndPlay,
    wavesurfer,
    isPlaying,
    handleStop,
    onNext,
    onPrev,
    handleApplyAIEQ,
  });
  useEffect(() => {
    actionDepsRef.current = {
      resumeAndPlay,
      wavesurfer,
      isPlaying,
      handleStop,
      onNext,
      onPrev,
      handleApplyAIEQ,
    };
  });

  const handleAgentAction = useCallback(
    (action: AgentAction) => {
      const d = actionDepsRef.current;
      switch (action.action) {
        case 'play':
          d.resumeAndPlay();
          break;
        case 'pause':
          if (d.wavesurfer && d.isPlaying) d.wavesurfer.pause();
          break;
        case 'stop':
          d.handleStop();
          break;
        case 'next':
          d.onNext?.();
          break;
        case 'prev':
          d.onPrev?.();
          break;
        case 'volume': {
          const v = typeof action.value === 'number' ? action.value : 80;
          setVolume(Math.max(0, Math.min(100, v)));
          break;
        }
        case 'eq':
          d.handleApplyAIEQ({
            bass: action.bass ?? 0,
            mid: action.mid ?? 0,
            treble: action.treble ?? 0,
          });
          break;
        case 'navigate':
          onNavigate?.(action.path);
          break;
        case 'create_collection':
          if ('name' in action && action.name) {
            createPlaylist({
              name: action.name,
              kind: action.kind || 'static',
              rules: action.rules,
              ai_prompt: action.ai_prompt,
              description: action.description,
            }).catch((e) => {
              if (import.meta.env.DEV) console.warn('[ReceiverPanel] create_collection failed', e);
            });
          }
          break;
        default:
          break;
      }
    },
    [onNavigate]
  );

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
      0,
      0,
      0,
      0,
      clamp6(trebleBoost * 0.3),
      clamp6(trebleBoost * 0.8),
      clamp6(trebleBoost),
    ];
  }, [loudness, volume, att, qualityMeta]);

  const handlePowerToggle = useCallback(() => {
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
  }, [powerOn, wavesurfer, isPlaying]);

  return {
    engineRef,
    meterState,
    sampleRate,
    qualityMeta,
    volume,
    setVolume,
    balance,
    setBalance,
    eqGains,
    bass,
    mid,
    treble,
    loudness,
    setLoudness,
    att,
    setAtt,
    currentTime,
    duration,
    showWaveform,
    setShowWaveform,
    smartEqActive,
    setSmartEqActive,
    smartEqPreview,
    powerOn,
    activeStack,
    scrollFraction,
    proactivePill,
    setProactivePill,
    handleSwipeScroll,
    resumeAndPlay,
    handleStop,
    handleSeekBack,
    handleSeekForward,
    handleEqChange,
    handleEqFlat,
    handleBass,
    handleMid,
    handleTreble,
    handleApplyAIEQ,
    handleAgentAction,
    handleSmartEqCorrection,
    handleSmartEqPreset,
    handleSmartEqPreview,
    handlePowerToggle,
    loudnessOverlay,
  };
}
