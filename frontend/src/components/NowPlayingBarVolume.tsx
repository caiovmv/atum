import { useEffect, useRef, useCallback } from 'react';
import { IoVolumeHigh, IoVolumeMedium, IoVolumeMute } from 'react-icons/io5';

function VolumeIcon({ volume }: { volume: number }) {
  if (volume === 0) return <IoVolumeMute size={16} />;
  if (volume < 50) return <IoVolumeMedium size={16} />;
  return <IoVolumeHigh size={16} />;
}

interface NowPlayingBarVolumeProps {
  volume: number;
  onVolumeChange: (vol: number) => void;
  open: boolean;
  onToggle: () => void;
  onClose: () => void;
}

export function NowPlayingBarVolume({
  volume,
  onVolumeChange,
  open,
  onToggle,
  onClose,
}: NowPlayingBarVolumeProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('pointerdown', handleClick);
    return () => document.removeEventListener('pointerdown', handleClick);
  }, [open, onClose]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => onVolumeChange(Number(e.target.value)),
    [onVolumeChange]
  );

  return (
    <div className="now-playing-bar-volume-wrap" ref={ref}>
      <button
        type="button"
        className="now-playing-bar-btn"
        onClick={onToggle}
        aria-label={`Volume: ${volume}%`}
      >
        <VolumeIcon volume={volume} />
      </button>
      {open && (
        <div className="now-playing-bar-volume-popup">
          <input
            type="range"
            className="now-playing-bar-volume-slider"
            min={0}
            max={100}
            step={1}
            value={volume}
            onChange={handleChange}
            aria-label="Volume"
          />
          <span className="now-playing-bar-volume-label">{volume}</span>
        </div>
      )}
    </div>
  );
}
