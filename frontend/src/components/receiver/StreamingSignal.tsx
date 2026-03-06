interface StreamingSignalProps {
  value: number; // 0–1 buffer ratio
  className?: string;
}

export function StreamingSignal({ value, className = '' }: StreamingSignalProps) {
  const pct = Math.round(value * 100);
  return (
    <div className={`receiver-streaming ${className}`.trim()} aria-hidden>
      <span className="receiver-streaming-label">STREAM</span>
      <div className="receiver-streaming-track">
        <div
          className="receiver-streaming-fill"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="receiver-streaming-value">{pct}%</span>
    </div>
  );
}
