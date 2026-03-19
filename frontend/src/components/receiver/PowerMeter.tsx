import { useEffect, useRef, useState } from 'react';
import { dBFS_toNormalized } from '../../audio/analysis';

const SCALE_MARKS = [-60, -48, -36, -24, -18, -12, -6, -3, 0];
const SMOOTH = 0.2;
const PEAK_HOLD_DECAY = 1500;

const VFD = 'var(--atum-accent)';
const VFD_DIM = 'var(--atum-accent-dim)';
const VFD_SCALE = 'var(--atum-accent-scale)';
const VFD_TEXT = 'var(--atum-accent-text)';


interface PowerMeterProps {
  value: number;
  className?: string;
  showPeakHold?: boolean;
}

export function PowerMeter({ value, className = '', showPeakHold = true }: PowerMeterProps) {
  const [display, setDisplay] = useState(0);
  const [peakHold, setPeakHold] = useState(0);
  const peakHoldTimeRef = useRef(0);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const targetNorm = dBFS_toNormalized(value);
    let displayVal = display;
    let holdVal = peakHold;
    const tick = (now: number) => {
      displayVal += (targetNorm - displayVal) * SMOOTH;
      setDisplay(displayVal);

      if (showPeakHold) {
        if (targetNorm > holdVal) {
          holdVal = targetNorm;
          peakHoldTimeRef.current = now;
        } else if (now - peakHoldTimeRef.current > PEAK_HOLD_DECAY) {
          holdVal += (targetNorm - holdVal) * 0.02;
        }
        setPeakHold(holdVal);
      }

      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [value, showPeakHold]);

  const angle = -90 + display * 180;

  return (
    <div className={`receiver-power receiver-power-dial ${className}`.trim()} aria-hidden>
      <span className="receiver-power-label">POWER (dBFS)</span>
      <svg viewBox="0 0 200 120" className="receiver-power-svg">
        <defs>
          <radialGradient id="pwrGlow" cx="100" cy="100" r="110" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor={VFD} stopOpacity="0.14" />
            <stop offset="0.3" stopColor={VFD} stopOpacity="0.10" />
            <stop offset="0.55" stopColor={VFD} stopOpacity="0.05" />
            <stop offset="0.8" stopColor={VFD} stopOpacity="0.02" />
            <stop offset="1" stopColor={VFD} stopOpacity="0" />
          </radialGradient>
          <linearGradient id="pwrRef" x1="0.05" y1="0" x2="1.0" y2="0.92">
            <stop offset="0" stopColor="white" stopOpacity="0" />
            <stop offset="0.44" stopColor="white" stopOpacity="0" />
            <stop offset="0.50" stopColor="white" stopOpacity="0.04" />
            <stop offset="0.55" stopColor="white" stopOpacity="0.028" />
            <stop offset="0.62" stopColor="white" stopOpacity="0" />
            <stop offset="1" stopColor="white" stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* VFD backlight — base fill: display "on" */}
        <rect x="0" y="0" width="200" height="120" fill={VFD} opacity="0.04" rx="4" />
        {/* Hotspot — brighter at center-bottom */}
        <ellipse cx="100" cy="90" rx="110" ry="85" fill="url(#pwrGlow)" />
        {/* Secondary diffuse layer */}
        <ellipse cx="100" cy="80" rx="90" ry="65" fill={VFD} opacity="0.03" />
        {/* Brighter edge strip at bottom */}
        <path
          d="M 15 115 Q 100 108 185 115 L 185 113.5 Q 100 111 15 113.5 Z"
          fill={VFD}
          opacity="0.1"
        />
        {/* Arc background (dim VFD) */}
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke={VFD_DIM}
          strokeWidth="8"
          strokeLinecap="round"
        />
        {/* Scale marks */}
        {SCALE_MARKS.map((db) => {
          const t = dBFS_toNormalized(db);
          const a = -90 + t * 180;
          const rad = (a * Math.PI) / 180;
          const isZero = db === 0;
          const isMajor = db === -60 || db === -24 || db === -12 || db === 0;
          const tickLen = isZero ? 18 : isMajor ? 14 : 8;
          return (
            <g key={db}>
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
                className="receiver-power-scale-text"
                fill={VFD_TEXT}
              >
                {db}
              </text>
            </g>
          );
        })}
        {/* Peak hold mark with glow */}
        {showPeakHold && peakHold > 0.01 && (() => {
          const phAngle = -90 + peakHold * 180;
          const phRad = (phAngle * Math.PI) / 180;
          const cx = 100 + 80 * Math.sin(phRad);
          const cy = 100 - 80 * Math.cos(phRad);
          return (
            <>
              <circle cx={cx} cy={cy} r={8} fill={VFD} opacity="0.08" />
              <circle cx={cx} cy={cy} r={5} fill={VFD} opacity="0.15" />
              <circle cx={cx} cy={cy} r={3} fill="none" stroke={VFD} strokeWidth="1.5" />
            </>
          );
        })()}
        {/* Needle glow (thicker translucent line behind) */}
        <g transform={`rotate(${angle} 100 100)`}>
          <line x1="100" y1="100" x2="100" y2="32" stroke={VFD} strokeWidth="10" strokeLinecap="round" opacity="0.12" />
          <line x1="100" y1="100" x2="100" y2="32" stroke={VFD} strokeWidth="6" strokeLinecap="round" opacity="0.2" />
          <line x1="100" y1="100" x2="100" y2="32" stroke={VFD} strokeWidth="2" strokeLinecap="round" />
        </g>
        {/* Pivot dot */}
        <circle cx="100" cy="100" r="3" fill={VFD} opacity="0.6" />
        {/* Diagonal glass reflection — thin band */}
        <rect x="0" y="0" width="200" height="120" fill="url(#pwrRef)" />
      </svg>
    </div>
  );
}
