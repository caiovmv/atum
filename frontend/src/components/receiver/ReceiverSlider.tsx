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
    <div className={`receiver-hctrl ${className}`.trim()}>
      <span className="receiver-hctrl-label">{label}</span>
      <input
        type="range"
        className="receiver-hctrl-input"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={handleChange}
        aria-label={label}
      />
      <span className="receiver-hctrl-value">{displayValue ?? value}</span>
    </div>
  );
}
