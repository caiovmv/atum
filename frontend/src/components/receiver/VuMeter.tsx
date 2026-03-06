import { useEffect, useRef, useState } from 'react';
import { vuToNormalized } from '../../audio/analysis';

const SCALE_MARKS = [-20, -15, -10, -7, -5, -3, -1, 0, 1, 2, 3];
const SMOOTH = 0.055;

const VFD = '#00e5c8';
const VFD_DIM = 'rgba(0, 229, 200, 0.15)';
const VFD_SCALE = 'rgba(0, 229, 200, 0.5)';
const VFD_TEXT = 'rgba(0, 229, 200, 0.6)';

interface VuMeterProps {
  value: number;
  label?: string;
  className?: string;
}

export function VuMeter({ value, label = '', className = '' }: VuMeterProps) {
  const [display, setDisplay] = useState(0);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const targetNorm = vuToNormalized(value);
    let displayVal = display;
    const tick = () => {
      displayVal += (targetNorm - displayVal) * SMOOTH;
      setDisplay(displayVal);
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [value]);

  const angle = -90 + display * 180;

  return (
    <div className={`receiver-vu ${className}`.trim()} aria-hidden>
      {label && <span className="receiver-vu-label">{label}</span>}
      <svg viewBox="0 0 200 120" className="receiver-vu-svg">
        <defs />
        {/* Arc background (dim VFD) */}
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke={VFD_DIM}
          strokeWidth="8"
          strokeLinecap="round"
        />
        {/* Scale marks */}
        {SCALE_MARKS.map((vu) => {
          const t = vuToNormalized(vu);
          const a = -90 + t * 180;
          const rad = (a * Math.PI) / 180;
          const isZero = vu === 0;
          const isMajor = vu === -20 || vu === -10 || vu === -3 || vu === 0 || vu === 3;
          const tickLen = isZero ? 18 : isMajor ? 14 : 8;
          return (
            <g key={vu}>
              <line
                x1={100 + (80 - tickLen) * Math.sin(rad)}
                y1={100 - (80 - tickLen) * Math.cos(rad)}
                x2={100 + 80 * Math.sin(rad)}
                y2={100 - 80 * Math.cos(rad)}
                stroke={VFD_SCALE}
                strokeWidth={isZero ? 2 : isMajor ? 1.5 : 1}
              />
              <text
                x={100 + 92 * Math.sin(rad)}
                y={100 - 92 * Math.cos(rad)}
                textAnchor="middle"
                dominantBaseline="middle"
                className="receiver-vu-scale-text"
                fill={VFD_TEXT}
              >
                {vu > 0 ? `+${vu}` : vu}
              </text>
            </g>
          );
        })}
        {/* Needle glow (thicker translucent line behind) */}
        <g transform={`rotate(${angle} 100 100)`}>
          <line x1="100" y1="100" x2="100" y2="32" stroke={VFD} strokeWidth="10" strokeLinecap="round" opacity="0.12" />
          <line x1="100" y1="100" x2="100" y2="32" stroke={VFD} strokeWidth="6" strokeLinecap="round" opacity="0.2" />
          <line x1="100" y1="100" x2="100" y2="32" stroke={VFD} strokeWidth="2" strokeLinecap="round" />
        </g>
        {/* Pivot dot */}
        <circle cx="100" cy="100" r="3" fill={VFD} opacity="0.6" />
      </svg>
    </div>
  );
}
