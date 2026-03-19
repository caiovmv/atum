import { IoChatbubbleEllipses } from 'react-icons/io5';

interface ReceiverProactivePillProps {
  text: string;
  onDismiss: () => void;
}

export function ReceiverProactivePill({ text, onDismiss }: ReceiverProactivePillProps) {
  return (
    <div
      className="receiver-proactive-pill"
      onClick={onDismiss}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onDismiss();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label={`Dica AI: ${text}. Pressione para fechar.`}
    >
      <IoChatbubbleEllipses size={12} />
      <span>{text}</span>
    </div>
  );
}
