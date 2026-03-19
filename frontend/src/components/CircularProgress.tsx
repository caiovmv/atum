import { memo } from 'react';
import './CircularProgress.css';

interface CircularProgressProps {
  percent: number;
  size?: number;
  strokeWidth?: number;
  label?: string;
}

export const CircularProgress = memo(function CircularProgress({
  percent,
  size = 64,
  strokeWidth = 4,
  label,
}: CircularProgressProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.min(100, Math.max(0, percent));
  const offset = circumference - (clamped / 100) * circumference;

  return (
    <div className="circular-progress" style={{ width: size, height: size }}>
      <svg
        viewBox={`0 0 ${size} ${size}`}
        width={size}
        height={size}
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ?? `${clamped.toFixed(2)}%`}
      >
        <circle
          className="circular-progress-track"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
        />
        <circle
          className="circular-progress-fill"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <span className="circular-progress-text">{clamped.toFixed(2)}%</span>
    </div>
  );
});
