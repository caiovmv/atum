import { useEffect, useRef, useState, useCallback } from 'react';
import { IoEllipsisHorizontal } from 'react-icons/io5';
import { createAudioEngine } from '../../audio/audioEngine';
import { useMarquee } from '../../hooks/useMarquee';
import { loadDspState, saveDspState, applyDspToEngine } from '../../audio/dspPersist';
import { CoverImage } from '../CoverImage';
import { useNowPlaying } from '../../contexts/NowPlayingContext';
import './ReceiverMobile.css';

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, '0')}`;
}

interface ReceiverMobileProps {
  streamUrl: string;
  title: string;
  contentType?: string | null;
  itemId: number;
  isImport: boolean;
  hasPrev: boolean;
  hasNext: boolean;
  onBack?: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  onEngineReady: (engine: import('../../audio/audioEngine').AudioEngine | null) => void;
  onTimeUpdate?: (time: number) => void;
  onDurationChange?: (dur: number) => void;
  onPlayingChange?: (playing: boolean) => void;
  onMenuOpen: () => void;
  className?: string;
}

export function ReceiverMobile({
  streamUrl,
  title,
  contentType,
  itemId,
  isImport,
  hasPrev,
  hasNext,
  onBack,
  onPrev,
  onNext,
  onEngineReady,
  onTimeUpdate,
  onDurationChange,
  onPlayingChange,
  onMenuOpen,
  className = '',
}: ReceiverMobileProps) {
  const nowPlaying = useNowPlaying();
  const engineRef = useRef<ReturnType<typeof createAudioEngine> | null>(null);
  const [volume, setVolumeState] = useState(() => loadDspState().volume ?? 50);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const titleRef = useRef<HTMLParagraphElement>(null);
  const titleOverflows = useMarquee(titleRef, title);

  const [audioRetry, setAudioRetry] = useState(0);

  useEffect(() => {
    const el = nowPlaying.audioRef.current;
    if (!el || !streamUrl) {
      const id = setTimeout(() => setAudioRetry((r) => r + 1), 100);
      return () => clearTimeout(id);
    }

    el.crossOrigin = 'anonymous';
    el.src = streamUrl;

    const playWhenReady = () => {
      el.play().catch(() => {});
    };
    el.addEventListener('canplay', playWhenReady);
    playWhenReady();

    const engine = createAudioEngine(el);
    if (engine.ctx.state === 'suspended') engine.ctx.resume().catch(() => {});
    engineRef.current = engine;
    applyDspToEngine(engine, loadDspState());
    onEngineReady(engine);

    return () => {
      el.removeEventListener('canplay', playWhenReady);
      engine.dispose();
      engineRef.current = null;
      onEngineReady(null);
    };
  }, [streamUrl, onEngineReady, audioRetry]);

  useEffect(() => {
    const el = nowPlaying.audioRef.current;
    if (!el) return;

    const onTime = () => {
      const t = el.currentTime;
      setCurrentTime(t);
      onTimeUpdate?.(t);
    };
    const onDur = () => {
      const d = el.duration;
      if (Number.isFinite(d)) {
        setDuration(d);
        onDurationChange?.(d);
      }
    };
    const onPlay = () => {
      setIsPlaying(true);
      onPlayingChange?.(true);
    };
    const onPause = () => {
      setIsPlaying(false);
      onPlayingChange?.(false);
    };

    el.addEventListener('timeupdate', onTime);
    el.addEventListener('durationchange', onDur);
    el.addEventListener('play', onPlay);
    el.addEventListener('pause', onPause);
    onTime();
    onDur();

    return () => {
      el.removeEventListener('timeupdate', onTime);
      el.removeEventListener('durationchange', onDur);
      el.removeEventListener('play', onPlay);
      el.removeEventListener('pause', onPause);
    };
  }, [streamUrl, onTimeUpdate, onDurationChange, onPlayingChange]);

  const handlePlayPause = useCallback(() => {
    const el = nowPlaying.audioRef.current;
    if (!el) return;
    if (engineRef.current?.ctx.state === 'suspended') {
      engineRef.current.ctx.resume().catch(() => {});
    }
    if (el.paused) {
      el.play().catch(() => {});
    } else {
      el.pause();
    }
  }, [nowPlaying.audioRef]);

  const handleVolumeChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const v = Math.max(0, Math.min(100, Number(e.target.value) || 0));
      setVolumeState(v);
      saveDspState({ volume: v });
      const eng = engineRef.current;
      if (eng) {
        eng.volumeGain.gain.setTargetAtTime(v / 100, eng.ctx.currentTime, 0.01);
      }
    },
    []
  );

  return (
    <div className={`receiver-mobile receiver-layout-main ${className}`.trim()}>
      <div className="receiver-mobile-cover">
        <CoverImage
          contentType={(contentType as 'music' | 'movies' | 'tv') || 'music'}
          title={title}
          downloadId={isImport ? undefined : itemId}
          importId={isImport ? itemId : undefined}
          size="card"
        />
      </div>

      <div className="receiver-mobile-title-wrap">
        <p
          ref={titleRef}
          className={`receiver-mobile-title${titleOverflows ? ' receiver-mobile-title--marquee' : ' receiver-mobile-title--static'}`}
          title={title}
        >
          {titleOverflows ? (
            <>
              <span>{title}</span>
              <span aria-hidden>{title}</span>
            </>
          ) : (
            title
          )}
        </p>
      </div>
      <p className="receiver-mobile-time">
        {formatTime(currentTime)}
        {duration > 0 ? ` / ${formatTime(duration)}` : ''}
      </p>

      <div className="receiver-mobile-transport">
        {onBack && (
          <button
            type="button"
            className="receiver-mobile-transport-btn"
            onClick={onBack}
            aria-label="Voltar"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </button>
        )}
        <button
          type="button"
          className="receiver-mobile-transport-btn"
          onClick={onPrev}
          disabled={!hasPrev}
          aria-label="Anterior"
        >
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M6 6h2v12H6zm3.5 6 8.5 6V6z" />
          </svg>
        </button>
        <button
          type="button"
          className="receiver-mobile-transport-btn receiver-mobile-transport-btn--play"
          onClick={handlePlayPause}
          aria-label={isPlaying ? 'Pausar' : 'Reproduzir'}
        >
          {isPlaying ? (
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M6 4h4v16H6zm8 0h4v16h-4z" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>
        <button
          type="button"
          className="receiver-mobile-transport-btn"
          onClick={onNext}
          disabled={!hasNext}
          aria-label="Próxima"
        >
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M6 18l8.5-6L6 6zm9 0V6l4 6z" />
          </svg>
        </button>
      </div>

      <div className="receiver-mobile-volume">
        <label htmlFor="receiver-mobile-volume-input" className="receiver-mobile-volume-label">
          Volume
        </label>
        <input
          id="receiver-mobile-volume-input"
          type="range"
          min={0}
          max={100}
          value={volume}
          onChange={handleVolumeChange}
          className="receiver-mobile-volume-input"
          aria-label="Volume"
        />
      </div>

      <button
        type="button"
        className="receiver-mobile-menu-btn"
        onClick={onMenuOpen}
        aria-label="Menu"
      >
        <IoEllipsisHorizontal size={24} />
      </button>
    </div>
  );
}
