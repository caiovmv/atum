interface QualityTuneProps {
  value: number; // 0–1 quality score
  label?: string; // e.g. "FLAC", "MP3 320"
  className?: string;
}

export function QualityTune({ value, label = '', className = '' }: QualityTuneProps) {
  const pct = Math.round(value * 100);
  return (
    <div className={`receiver-quality ${className}`.trim()} aria-hidden>
      <span className="receiver-quality-label">QUALITY</span>
      <div className="receiver-quality-track">
        <div
          className="receiver-quality-fill"
          style={{ width: `${pct}%` }}
        />
      </div>
      {label && <span className="receiver-quality-value">{label}</span>}
    </div>
  );
}
