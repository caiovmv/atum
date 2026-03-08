interface ReceiverToggleProps {
  active: boolean;
  onToggle: () => void;
  label: string;
  className?: string;
}

export function ReceiverToggle({ active, onToggle, label, className = '' }: ReceiverToggleProps) {
  return (
    <div className={`receiver-toggle-wrap ${className}`.trim()}>
      <span className="receiver-toggle-label">{label}</span>
      <button
        type="button"
        className={`receiver-toggle ${active ? 'receiver-toggle-on' : ''}`}
        onClick={onToggle}
        aria-pressed={active}
        aria-label={label}
      >
        <span className="receiver-toggle-indicator" />
      </button>
    </div>
  );
}
