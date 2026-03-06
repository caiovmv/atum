import { useCallback } from 'react';

interface ReceiverSliderProps {
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
  label: string;
  displayValue?: string;
  className?: string;
}

export function ReceiverSlider({
  value,
  min,
  max,
  step = 1,
  onChange,
  label,
  displayValue,
  className = '',
}: ReceiverSliderProps) {
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange(parseFloat(e.target.value));
    },
    [onChange],
  );

  return (
    <div className={`receiver-hslider ${className}`.trim()}>
      <div className="receiver-hslider-header">
        <span className="receiver-hslider-label">{label}</span>
        {displayValue != null && (
          <span className="receiver-hslider-value">{displayValue}</span>
        )}
      </div>
      <input
        type="range"
        className="receiver-hslider-input"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={handleChange}
        aria-label={label}
      />
    </div>
  );
}
