import { IoChatbubbleEllipses } from 'react-icons/io5';
import { ReceiverAI, type EQSuggestion, type SmartQueueResult, type AgentAction } from './ReceiverAI';

interface ReceiverAIFabProps {
  open: boolean;
  onToggle: () => void;
  onClose: () => void;
  overlayRef: React.RefObject<HTMLDivElement | null>;
  fabRef: React.RefObject<HTMLButtonElement | null>;
  trackTitle?: string;
  artist?: string;
  album?: string;
  codec?: string;
  bitrate?: string;
  volume: number;
  bass: number;
  mid: number;
  treble: number;
  onApplyEQ?: (eq: EQSuggestion) => void;
  onSmartQueue?: (result: SmartQueueResult) => void;
  onAction?: (action: AgentAction) => void;
}

export function ReceiverAIFab({
  open,
  onToggle,
  onClose,
  overlayRef,
  fabRef,
  trackTitle,
  artist,
  album,
  codec,
  bitrate,
  volume,
  bass,
  mid,
  treble,
  onApplyEQ,
  onSmartQueue,
  onAction,
}: ReceiverAIFabProps) {
  return (
    <>
      <button
        ref={fabRef}
        type="button"
        className={`receiver-ai-fab${open ? ' receiver-ai-fab--active' : ''}`}
        onClick={onToggle}
        aria-label="Assistente AI"
      >
        <IoChatbubbleEllipses size={20} />
      </button>

      {open && (
        <div ref={overlayRef} className="receiver-ai-overlay" role="dialog" aria-modal="true" aria-label="Assistente AI">
          <div className="receiver-ai-overlay-header">
            <span>AI ASSISTANT</span>
            <button type="button" className="receiver-ai-overlay-close" onClick={onClose} aria-label="Fechar">×</button>
          </div>
          <ReceiverAI
            trackTitle={trackTitle}
            artist={artist}
            album={album}
            codec={codec}
            bitrate={bitrate}
            volume={volume}
            bass={bass}
            mid={mid}
            treble={treble}
            onApplyEQ={onApplyEQ}
            onSmartQueue={onSmartQueue}
            onAction={onAction}
          />
        </div>
      )}
    </>
  );
}
