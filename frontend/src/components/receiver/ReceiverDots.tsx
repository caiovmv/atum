const STACK_LABELS = ['SRX', 'METERS', 'SPECTRUM', 'EQ', 'CTRL', 'AI'] as const;

interface ReceiverDotsProps {
  scrollFraction: number;
  activeStack: number;
  swipeRef: React.RefObject<HTMLDivElement | null>;
}

export function ReceiverDots({ scrollFraction, activeStack, swipeRef }: ReceiverDotsProps) {
  return (
    <div className="receiver-dots">
      {STACK_LABELS.map((label, i) => {
        const dist = Math.abs(scrollFraction - i);
        const glow = Math.max(0, 1 - dist);
        return (
          <button
            key={label}
            type="button"
            className={`receiver-dot${i === activeStack ? ' receiver-dot--active' : ''}`}
            onClick={() => {
              const el = swipeRef.current;
              if (el) el.scrollTo({ left: i * el.clientWidth, behavior: 'smooth' });
            }}
            aria-label={label}
            style={{ '--dot-glow': glow } as React.CSSProperties}
          >
            <span className="receiver-dot-pip" />
            <span className="receiver-dot-label">{label}</span>
          </button>
        );
      })}
    </div>
  );
}
