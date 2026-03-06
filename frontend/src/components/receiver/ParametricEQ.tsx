import { useCallback } from 'react';

const BAND_LABELS = ['40', '80', '160', '315', '630', '1.25k', '2.5k', '5k', '10k', '20k'];
const SEGMENTS = 12;
const HALF = SEGMENTS / 2;

interface ParametricEQProps {
  gains: number[];
  overlay?: number[];
  onChange: (index: number, value: number) => void;
  onFlat: () => void;
  className?: string;
}

export function ParametricEQ({ gains, overlay, onChange, onFlat, className = '' }: ParametricEQProps) {
  const handleSegClick = useCallback(
    (bandIdx: number, segIdx: number) => {
      const db = segIdx - HALF;
      const current = Math.round(gains[bandIdx] ?? 0);
      onChange(bandIdx, db === current ? 0 : db);
    },
    [gains, onChange],
  );

  const isFlat = gains.every((g) => g === 0);

  return (
    <div className={`receiver-eq ${className}`.trim()}>
      <div className="receiver-eq-header">
        <span className="receiver-eq-label">PARAMETRIC EQ</span>
        <button
          type="button"
          className={`receiver-toggle receiver-eq-flat-btn ${isFlat ? 'receiver-toggle-on' : ''}`}
          onClick={onFlat}
        >
          <span className="receiver-toggle-indicator" />
          <span className="receiver-toggle-label">FLAT</span>
        </button>
      </div>
      <div className="receiver-eq-bands">
        {BAND_LABELS.map((label, bandIdx) => {
          const gain = Math.round(gains[bandIdx] ?? 0);
          const ov = Math.round(overlay?.[bandIdx] ?? 0);
          const combined = Math.max(-HALF, Math.min(HALF, gain + ov));
          return (
            <div key={label} className="receiver-eq-band">
              <span className="receiver-eq-db">
                {combined > 0 ? `+${combined}` : combined}
              </span>
              <div className="receiver-eq-segments">
                {Array.from({ length: SEGMENTS }, (_, s) => {
                  const segIdx = SEGMENTS - 1 - s;
                  const dbVal = segIdx - HALF;

                  let litUser = false;
                  if (gain > 0 && dbVal > 0 && dbVal <= gain) litUser = true;
                  if (gain < 0 && dbVal < 0 && dbVal >= gain) litUser = true;

                  let litLoudness = false;
                  if (!litUser && ov !== 0) {
                    if (combined > 0 && dbVal > 0 && dbVal <= combined) litLoudness = true;
                    if (combined < 0 && dbVal < 0 && dbVal >= combined) litLoudness = true;
                  }

                  const isCenter = segIdx === HALF;
                  return (
                    <div
                      key={s}
                      className={
                        'receiver-eq-seg' +
                        (litUser ? ' receiver-eq-seg-lit' : '') +
                        (litLoudness ? ' receiver-eq-seg-loudness' : '') +
                        (isCenter ? ' receiver-eq-seg-center' : '')
                      }
                      onClick={() => handleSegClick(bandIdx, segIdx)}
                      role="button"
                      tabIndex={-1}
                      aria-label={`${label}Hz ${dbVal > 0 ? '+' : ''}${dbVal}dB`}
                    />
                  );
                })}
              </div>
              <span className="receiver-eq-freq">{label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
