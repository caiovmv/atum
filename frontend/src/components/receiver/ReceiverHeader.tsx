import { useRef } from 'react';
import { useMarquee } from '../../hooks/useMarquee';
import { ReceiverTransport } from './ReceiverTransport';

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, '0')}`;
}

interface ReceiverHeaderProps {
  title: string;
  currentTime: number;
  duration: number;
  isPlaying: boolean | null;
  hasPrev: boolean;
  hasNext: boolean;
  shuffled: boolean;
  powerOn: boolean;
  onBack?: () => void;
  onSeekBack: () => void;
  onSeekForward: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  onStop: () => void;
  onPlayPause: () => void;
  onToggleShuffle: () => void;
  onPowerToggle: () => void;
}

export function ReceiverHeader({
  title,
  currentTime,
  duration,
  isPlaying,
  hasPrev,
  hasNext,
  shuffled,
  powerOn,
  onBack,
  onSeekBack,
  onSeekForward,
  onPrev,
  onNext,
  onStop,
  onPlayPause,
  onToggleShuffle,
  onPowerToggle,
}: ReceiverHeaderProps) {
  const titleRef = useRef<HTMLSpanElement>(null);
  const titleOverflows = useMarquee(titleRef, title);

  return (
    <div className="receiver-header">
      <div className="receiver-brand-group">
        <span className="receiver-brand">ATUM</span>
        <span className="receiver-model">SRX-900</span>
      </div>
      <div className="receiver-header-display">
        <span ref={titleRef} className={`receiver-header-title${titleOverflows ? ' receiver-header-title--marquee' : ''}`}>
          {titleOverflows ? <><span>{title}</span><span aria-hidden>{title}</span></> : title}
        </span>
        <span className="receiver-header-time">
          {formatTime(currentTime)}{duration > 0 ? ` / ${formatTime(duration)}` : ''}
        </span>
      </div>
      <ReceiverTransport
        onBack={onBack}
        isPlaying={isPlaying}
        hasPrev={hasPrev}
        hasNext={hasNext}
        shuffled={shuffled}
        powerOn={powerOn}
        onSeekBack={onSeekBack}
        onSeekForward={onSeekForward}
        onPrev={onPrev}
        onNext={onNext}
        onStop={onStop}
        onPlayPause={onPlayPause}
        onToggleShuffle={onToggleShuffle}
        onPowerToggle={onPowerToggle}
      />
    </div>
  );
}
