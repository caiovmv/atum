function iconSvg(d: string, w = 14, h = 12) {
  return (
    <svg className="receiver-transport-svg" viewBox={`0 0 ${w} ${h}`} width={w} height={h} fill="currentColor">
      <path d={d} />
    </svg>
  );
}

interface ReceiverTransportProps {
  onBack?: () => void;
  isPlaying: boolean | null;
  hasPrev: boolean;
  hasNext: boolean;
  shuffled: boolean;
  powerOn: boolean;
  onSeekBack: () => void;
  onSeekForward: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  onStop: () => void;
  onPlayPause: () => void;
  onToggleShuffle: () => void;
  onPowerToggle: () => void;
}

export function ReceiverTransport({
  onBack,
  isPlaying,
  hasPrev,
  hasNext,
  shuffled,
  powerOn,
  onSeekBack,
  onSeekForward,
  onPrev,
  onNext,
  onStop,
  onPlayPause,
  onToggleShuffle,
  onPowerToggle,
}: ReceiverTransportProps) {
  return (
    <div className="receiver-transport">
      {onBack && (
        <button type="button" className="receiver-transport-btn" onClick={onBack} aria-label="Voltar" title="Voltar">
          <svg className="receiver-transport-svg" viewBox="0 0 16 16" width={14} height={14} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10 3L5 8l5 5" />
          </svg>
        </button>
      )}
      <button type="button" className="receiver-transport-btn" onClick={onSeekBack} aria-label="Voltar 10s" title="-10s">
        {iconSvg('M1 1v10h1.5V6.5L7 10V6.5L11.5 10V2L7 5.5V2L2.5 5.5V1z')}
      </button>
      <button type="button" className={`receiver-transport-btn${!hasPrev ? ' receiver-transport-btn--disabled' : ''}`} onClick={onPrev} disabled={!hasPrev} aria-label="Anterior">
        {iconSvg('M1.5 1v10h1.5V1zM4 6l5 5V1z M9 6l5 5V1z')}
      </button>
      <button type="button" className="receiver-transport-btn" onClick={onStop} aria-label="Parar">
        {iconSvg('M2 2h10v8H2z')}
      </button>
      <button type="button" className={`receiver-transport-btn receiver-transport-btn--play${isPlaying ? ' receiver-transport-btn--active' : ''}`} onClick={onPlayPause} aria-label={isPlaying ? 'Pausar' : 'Reproduzir'}>
        {isPlaying ? iconSvg('M3 1h3v10H3zM8 1h3v10H8z') : iconSvg('M3 1v10l9-5z')}
      </button>
      <button type="button" className={`receiver-transport-btn${!hasNext ? ' receiver-transport-btn--disabled' : ''}`} onClick={onNext} disabled={!hasNext} aria-label="Próxima">
        {iconSvg('M0 1l5 5-5 5z M5 1l5 5-5 5z M11 1h1.5v10H11z')}
      </button>
      <button type="button" className="receiver-transport-btn" onClick={onSeekForward} aria-label="Avançar 10s" title="+10s">
        {iconSvg('M2.5 2v8L7 5.5V10l4.5-3.5V11H13.5V1H12V5.5L7 2v3.5L2.5 2z')}
      </button>
      <button type="button" className={`receiver-transport-btn${shuffled ? ' receiver-transport-btn--active' : ''}`} onClick={onToggleShuffle} aria-label={shuffled ? 'Desativar aleatório' : 'Ativar aleatório'} title="Aleatório">
        {iconSvg('M1 3h3l2 3-2 3H1V3zM8 3h3l2 3-2 3H8V3zM7 4l1.5 2L7 8M0 6h1M12 4l1 2-1 2')}
      </button>
      <button
        type="button"
        className={`receiver-transport-btn receiver-power-btn${powerOn ? ' receiver-transport-btn--active' : ''}`}
        aria-label={powerOn ? 'Desligar' : 'Ligar'}
        onClick={onPowerToggle}
      >
        <svg className="receiver-transport-svg receiver-power-icon" viewBox="0 0 14 14" width={14} height={14} fill="currentColor">
          <path d="M7 1v5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" fill="none" />
          <path d="M3.5 3.8A5 5 0 1 0 10.5 3.8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" fill="none" />
        </svg>
      </button>
    </div>
  );
}
