interface ReceiverToggleProps {
  active: boolean;
  onToggle: () => void;
  label: string;
  className?: string;
}

export function ReceiverToggle({ active, onToggle, label, className = '' }: ReceiverToggleProps) {
  return (
    <button
      type="button"
      className={`receiver-toggle ${active ? 'receiver-toggle-on' : ''} ${className}`.trim()}
      onClick={onToggle}
      aria-pressed={active}
    >
      <span className="receiver-toggle-indicator" />
      <span className="receiver-toggle-label">{label}</span>
    </button>
  );
}
