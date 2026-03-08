import { useCallback } from 'react';

const BAND_LABELS = ['40', '80', '160', '315', '630', '1.25k', '2.5k', '5k', '10k', '20k'];
const MIN = -6;
const MAX = 6;

interface ParametricEQProps {
  gains: number[];
  overlay?: number[];
  onChange: (index: number, value: number) => void;
  onFlat: () => void;
  className?: string;
}

export function ParametricEQ({ gains, overlay, onChange, onFlat, className = '' }: ParametricEQProps) {
  const handleChange = useCallback(
    (bandIdx: number, e: React.ChangeEvent<HTMLInputElement>) => {
      onChange(bandIdx, parseFloat(e.target.value));
    },
    [onChange],
  );

  const isFlat = gains.every((g) => g === 0);

  return (
    <div className={`receiver-eq ${className}`.trim()}>
      <div className="receiver-eq-header">
        <span className="receiver-eq-label">PARAMETRIC EQ</span>
        <div className="receiver-eq-flat-wrap">
          <span className="receiver-eq-flat-label">FLAT</span>
          <button
            type="button"
            className={`receiver-eq-flat-btn ${isFlat ? 'receiver-toggle-on' : ''}`}
            onClick={onFlat}
          >
            <span className="receiver-toggle-indicator" />
          </button>
        </div>
      </div>
      <div className="receiver-eq-bands">
        <div className="receiver-eq-scale" aria-hidden>
          <span className="receiver-eq-scale-mark">+6</span>
          <span className="receiver-eq-scale-mark">0</span>
          <span className="receiver-eq-scale-mark">-6</span>
        </div>
        {BAND_LABELS.map((label, bandIdx) => {
          const gain = Math.round(gains[bandIdx] ?? 0);
          const ov = Math.round(overlay?.[bandIdx] ?? 0);
          const combined = Math.max(MIN, Math.min(MAX, gain + ov));
          const hasOverlay = ov !== 0;

          return (
            <div key={label} className="receiver-eq-band">
              <span className={`receiver-eq-db${hasOverlay ? ' receiver-eq-db--overlay' : ''}`}>
                {combined > 0 ? `+${combined}` : combined}
              </span>
              <div className="receiver-eq-slider-col">
                <input
                  type="range"
                  className="receiver-eq-vslider"
                  min={MIN}
                  max={MAX}
                  step={1}
                  value={gain}
                  onChange={(e) => handleChange(bandIdx, e)}
                  aria-label={`${label}Hz`}
                />
              </div>
              <span className="receiver-eq-freq">{label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
