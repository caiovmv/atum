import { useRef, useMemo, useEffect, useState } from 'react';
import { useWavesurfer } from '@wavesurfer/react';
import { useMediaSession } from '../../hooks/useMediaSession';
import { useCrossfade } from '../../hooks/useCrossfade';
import { useNowPlaying } from '../../contexts/NowPlayingContext';
import { ReceiverAI, type SmartQueueResult } from './ReceiverAI';
import { ParametricEQ } from './ParametricEQ';
import { ReceiverHeader } from './ReceiverHeader';
import { ReceiverStackControls } from './ReceiverStackControls';
import { ReceiverStackMeters } from './ReceiverStackMeters';
import { ReceiverStackSpectrum } from './ReceiverStackSpectrum';
import { ReceiverDots } from './ReceiverDots';
import { ReceiverAIFab } from './ReceiverAIFab';
import { ReceiverProactivePill } from './ReceiverProactivePill';
import { useReceiverPanel } from '../../hooks/useReceiverPanel';
import '../../styles/receiver.css';
import '../../styles/smarteq.css';
import '../../styles/receiver-ai.css';

const VFD_COLOR = 'var(--atum-accent)';

interface ReceiverPanelProps {
  streamUrl: string;
  title: string;
  fileName?: string;
  contentType?: string | null;
  artist?: string;
  album?: string;
  coverUrl?: string;
  onBack?: () => void;
  onNext?: () => void;
  onPrev?: () => void;
  hasNext?: boolean;
  hasPrev?: boolean;
  className?: string;
  onSmartQueue?: (result: SmartQueueResult) => void;
  onNavigate?: (path: string) => void;
  onTimeUpdate?: (time: number) => void;
  onDurationChange?: (dur: number) => void;
  onPlayingChange?: (playing: boolean) => void;
  onEngineReady?: (engine: import('../../audio/audioEngine').AudioEngine | null) => void;
  audioRef?: React.RefObject<HTMLAudioElement | null>;
}

export function ReceiverPanel({
  streamUrl,
  title,
  fileName = '',
  contentType = null,
  artist,
  album,
  coverUrl,
  onBack,
  onNext,
  onPrev,
  hasNext,
  hasPrev,
  className = '',
  onSmartQueue,
  onNavigate,
  onTimeUpdate,
  onDurationChange,
  onPlayingChange,
  onEngineReady,
  audioRef: sharedAudioRef,
}: ReceiverPanelProps) {
  const { shuffled, toggleShuffle } = useNowPlaying();
  const containerRef = useRef<HTMLDivElement>(null);
  const swipeRef = useRef<HTMLDivElement>(null);
  const [aiFabOpen, setAiFabOpen] = useState(false);
  const aiFabRef = useRef<HTMLButtonElement>(null);
  const aiOverlayRef = useRef<HTMLDivElement>(null);

  const wavesurferOptions = useMemo(() => {
    const opts: Parameters<typeof useWavesurfer>[0] = {
      container: containerRef,
      url: streamUrl,
      autoplay: true,
      waveColor: VFD_COLOR,
      progressColor: 'rgba(255,255,255,0.4)',
      height: 72,
      barWidth: 2,
      barGap: 1,
      barRadius: 1,
      normalize: true,
    };
    if (sharedAudioRef?.current) {
      opts.media = sharedAudioRef.current;
    }
    return opts;
  }, [streamUrl, sharedAudioRef]);

  const { wavesurfer, isReady, isPlaying } = useWavesurfer(wavesurferOptions);

  const rp = useReceiverPanel({
    streamUrl,
    title,
    fileName,
    contentType,
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
  });

  useMediaSession({
    title,
    artist,
    album,
    coverUrl,
    isPlaying: isPlaying ?? false,
    currentTime: rp.currentTime,
    duration: rp.duration,
    onPlay: rp.resumeAndPlay,
    onPause: rp.resumeAndPlay,
    onSeekBackward: rp.handleSeekBack,
    onSeekForward: rp.handleSeekForward,
    onPreviousTrack: onPrev,
    onNextTrack: onNext,
    hasPrev,
    hasNext,
  });

  useCrossfade(rp.engineRef.current, streamUrl, rp.volume, isPlaying ?? false);

  useEffect(() => {
    if (aiFabOpen) {
      requestAnimationFrame(() => {
        const input = aiOverlayRef.current?.querySelector<HTMLInputElement>('.receiver-ai-input');
        input?.focus();
      });
    } else {
      aiFabRef.current?.focus();
    }
  }, [aiFabOpen]);

  return (
    <div className={`receiver-panel ${className}`.trim()}>
      <div className="receiver-swipe-container" ref={swipeRef} onScroll={rp.handleSwipeScroll}>
        <ReceiverHeader
          title={title}
          currentTime={rp.currentTime}
          duration={rp.duration}
          isPlaying={isPlaying}
          hasPrev={hasPrev ?? false}
          hasNext={hasNext ?? false}
          shuffled={shuffled}
          powerOn={rp.powerOn}
          onBack={onBack}
          onSeekBack={rp.handleSeekBack}
          onSeekForward={rp.handleSeekForward}
          onPrev={onPrev}
          onNext={onNext}
          onStop={rp.handleStop}
          onPlayPause={rp.resumeAndPlay}
          onToggleShuffle={toggleShuffle}
          onPowerToggle={rp.handlePowerToggle}
        />

        <div className="receiver-bezel" />

        <ReceiverStackMeters
          vuL={rp.meterState.vuL}
          vuR={rp.meterState.vuR}
          peak={rp.meterState.peak}
        />

        <div className="receiver-bezel" />

        <ReceiverStackSpectrum
          fftData={rp.meterState.fft}
          sampleRate={rp.sampleRate}
          showWaveform={rp.showWaveform}
          containerRef={containerRef}
          onToggleWaveform={() => rp.setShowWaveform((p) => !p)}
        />

        <div className="receiver-bezel" />

        <div className="receiver-stack-eq">
          <ParametricEQ
            gains={rp.eqGains}
            overlay={rp.smartEqPreview ?? rp.loudnessOverlay}
            onChange={rp.handleEqChange}
            onFlat={rp.handleEqFlat}
          />
        </div>

        <div className="receiver-bezel" />

        <ReceiverStackControls
          volume={rp.volume}
          setVolume={rp.setVolume}
          balance={rp.balance}
          setBalance={rp.setBalance}
          bass={rp.bass}
          mid={rp.mid}
          treble={rp.treble}
          onBass={rp.handleBass}
          onMid={rp.handleMid}
          onTreble={rp.handleTreble}
          loudness={rp.loudness}
          setLoudness={rp.setLoudness}
          att={rp.att}
          setAtt={rp.setAtt}
          smartEqActive={rp.smartEqActive}
          setSmartEqActive={rp.setSmartEqActive}
          fftData={rp.meterState.fft}
          sampleRate={rp.sampleRate}
          audioCtx={rp.engineRef.current?.ctx ?? null}
          onApplyCorrection={rp.handleSmartEqCorrection}
          onApplyPreset={rp.handleSmartEqPreset}
          onCorrectionPreview={rp.handleSmartEqPreview}
        />

        <div className="receiver-bezel" />

        <div className="receiver-stack-ai">
          <ReceiverAI
            trackTitle={title}
            artist={artist}
            album={album}
            codec={rp.qualityMeta?.codec}
            bitrate={rp.qualityMeta?.bitrate != null ? `${rp.qualityMeta.bitrate} kbps` : undefined}
            volume={rp.volume}
            bass={rp.bass}
            mid={rp.mid}
            treble={rp.treble}
            onApplyEQ={rp.handleApplyAIEQ}
            onSmartQueue={onSmartQueue}
            onAction={rp.handleAgentAction}
          />
        </div>
      </div>

      <ReceiverDots scrollFraction={rp.scrollFraction} activeStack={rp.activeStack} swipeRef={swipeRef} />

      {rp.proactivePill && (
        <ReceiverProactivePill text={rp.proactivePill} onDismiss={() => rp.setProactivePill(null)} />
      )}

      {rp.activeStack !== 5 && (
        <ReceiverAIFab
          open={aiFabOpen}
          onToggle={() => setAiFabOpen((p) => !p)}
          onClose={() => setAiFabOpen(false)}
          overlayRef={aiOverlayRef}
          fabRef={aiFabRef}
          trackTitle={title}
          artist={artist}
          album={album}
          codec={rp.qualityMeta?.codec}
          bitrate={rp.qualityMeta?.bitrate != null ? `${rp.qualityMeta.bitrate} kbps` : undefined}
          volume={rp.volume}
          bass={rp.bass}
          mid={rp.mid}
          treble={rp.treble}
          onApplyEQ={rp.handleApplyAIEQ}
          onSmartQueue={onSmartQueue}
          onAction={rp.handleAgentAction}
        />
      )}
    </div>
  );
}
