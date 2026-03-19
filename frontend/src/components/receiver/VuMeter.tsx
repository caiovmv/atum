import { useEffect, useRef, useState } from 'react';
import { vuToNormalized } from '../../audio/analysis';

const SCALE_MARKS = [-20, -15, -10, -7, -5, -3, -1, 0, 1, 2, 3];

const ATTACK_MS = 300;
const DECAY_MS = 1500;

const VFD = 'var(--atum-accent)';
const VFD_DIM = 'var(--atum-accent-dim)';
const VFD_SCALE = 'var(--atum-accent-scale)';
const VFD_TEXT = 'var(--atum-accent-text)';

interface VuMeterProps {
  value: number;
  label?: string;
  /** 0 = left meter, 1 = right meter — shifts reflection subtly */
  meterIndex?: number;
  className?: string;
}

export function VuMeter({ value, label = '', meterIndex = 0, className = '' }: VuMeterProps) {
  const [display, setDisplay] = useState(0);
  const rafRef = useRef<number>(0);
  const prevTimeRef = useRef<number>(0);

  useEffect(() => {
    const targetNorm = vuToNormalized(value);
    let displayVal = display;
    const tick = (now: number) => {
      const dt = prevTimeRef.current ? now - prevTimeRef.current : 16;
      prevTimeRef.current = now;
      const rising = targetNorm > displayVal;
      const tau = rising ? ATTACK_MS : DECAY_MS;
      const alpha = 1 - Math.exp(-dt / tau);
      displayVal += (targetNorm - displayVal) * alpha;
      setDisplay(displayVal);
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [value]);

  const angle = -90 + display * 180;

  const uid = `vu${meterIndex}`;
  const refStart = meterIndex === 0 ? 0.40 : 0.44;
  const refPeak = meterIndex === 0 ? 0.48 : 0.51;
  const refEnd = meterIndex === 0 ? 0.56 : 0.58;
  const refFade = meterIndex === 0 ? 0.62 : 0.65;
  const refOpacity = meterIndex === 0 ? 0.055 : 0.045;
  const refX2 = meterIndex === 0 ? 0.95 : 1.0;
  const refY2 = meterIndex === 0 ? 1.0 : 0.92;

  return (
    <div className={`receiver-vu ${className}`.trim()} aria-hidden>
      {label && <span className="receiver-vu-label">{label}</span>}
      <svg viewBox="0 0 200 120" className="receiver-vu-svg">
        <defs>
          <radialGradient id={`${uid}Glow`} cx="100" cy="100" r="110" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor={VFD} stopOpacity="0.14" />
            <stop offset="0.3" stopColor={VFD} stopOpacity="0.10" />
            <stop offset="0.55" stopColor={VFD} stopOpacity="0.05" />
            <stop offset="0.8" stopColor={VFD} stopOpacity="0.02" />
            <stop offset="1" stopColor={VFD} stopOpacity="0" />
          </radialGradient>
          <linearGradient id={`${uid}Ref`} x1="0" y1="0.05" x2={refX2} y2={refY2}>
            <stop offset="0" stopColor="white" stopOpacity="0" />
            <stop offset={refStart} stopColor="white" stopOpacity="0" />
            <stop offset={refPeak} stopColor="white" stopOpacity={refOpacity} />
            <stop offset={refEnd} stopColor="white" stopOpacity={refOpacity * 0.7} />
            <stop offset={refFade} stopColor="white" stopOpacity="0" />
            <stop offset="1" stopColor="white" stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* VFD backlight — base fill: display "on" */}
        <rect x="0" y="0" width="200" height="120" fill={VFD} opacity="0.04" rx="4" />
        {/* Hotspot — brighter at center-bottom */}
        <ellipse cx="100" cy="90" rx="110" ry="85" fill={`url(#${uid}Glow)`} />
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
        {/* Diagonal glass reflection — thin band */}
        <rect x="0" y="0" width="200" height="120" fill={`url(#${uid}Ref)`} />
      </svg>
    </div>
  );
}
