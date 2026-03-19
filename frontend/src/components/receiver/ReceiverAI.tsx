import { memo, useCallback, useEffect, useRef } from 'react';
import { IoSend, IoChatbubbleEllipses, IoMic, IoMicOff } from 'react-icons/io5';
import { ReceiverAISuggestions } from './ReceiverAISuggestions';
import { useReceiverAI } from '../../hooks/useReceiverAI';

export interface EQSuggestion {
  bass: number;
  mid: number;
  treble: number;
}

export interface SmartQueueResult {
  ids: number[];
  explanation: string;
}

export interface CreateCollectionPayload {
  name: string;
  kind: 'static' | 'dynamic_rules' | 'dynamic_ai';
  rules?: { kind: string; type: string; value: string }[];
  ai_prompt?: string;
  description?: string;
}

export type AgentAction =
  | { action: 'play' }
  | { action: 'pause' }
  | { action: 'stop' }
  | { action: 'next' }
  | { action: 'prev' }
  | { action: 'volume'; value: number }
  | { action: 'eq'; bass: number; mid: number; treble: number }
  | { action: 'navigate'; path: string }
  | { action: 'create_collection' } & CreateCollectionPayload;

const ACTION_RE = /\$\$ACTION:(.*?)\$\$/;

export function parseAction(text: string): { clean: string; action: AgentAction | null } {
  const match = text.match(ACTION_RE);
  if (!match) return { clean: text, action: null };
  const clean = text.replace(ACTION_RE, '').trim();
  try {
    const parsed = JSON.parse(match[1]) as AgentAction;
    if (parsed && typeof parsed.action === 'string') return { clean, action: parsed };
  } catch {
    /* invalid JSON */
  }
  return { clean, action: null };
}

interface ReceiverAIProps {
  trackTitle?: string;
  artist?: string;
  album?: string;
  codec?: string;
  bitrate?: string;
  volume?: number;
  bass?: number;
  mid?: number;
  treble?: number;
  onApplyEQ?: (eq: EQSuggestion) => void;
  onSmartQueue?: (result: SmartQueueResult) => void;
  onAction?: (action: AgentAction) => void;
}

export const ReceiverAI = memo(function ReceiverAI({
  trackTitle,
  artist,
  album,
  codec,
  bitrate,
  volume: currentVolume,
  bass: currentBass,
  mid: currentMid,
  treble: currentTreble,
  onApplyEQ,
  onSmartQueue,
  onAction,
}: ReceiverAIProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const ai = useReceiverAI({
    trackTitle,
    artist,
    album,
    codec,
    bitrate,
    volume: currentVolume,
    bass: currentBass,
    mid: currentMid,
    treble: currentTreble,
    onApplyEQ,
    onSmartQueue,
    onAction,
  });

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [ai.messages.length]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        ai.send();
      }
    },
    [ai.send]
  );

  return (
    <div className="receiver-ai">
      <div className="receiver-ai-header">
        <IoChatbubbleEllipses size={14} />
        <span>AI ASSISTANT</span>
        {trackTitle && (
          <span className="receiver-ai-ctx">
            ► {trackTitle}
            {artist ? ` · ${artist}` : ''}
          </span>
        )}
      </div>

      <div className="receiver-ai-messages" ref={listRef}>
        {ai.messages.length === 0 && !ai.loading && (
          <ReceiverAISuggestions
            onRequestEQ={ai.requestEQ}
            onSetInput={ai.setInput}
            onRequestSmartQueue={() => ai.requestSmartQueue('Monte uma fila com mood similar à faixa atual')}
            hasApplyEQ={!!onApplyEQ}
            hasSmartQueue={!!onSmartQueue}
          />
        )}

        {ai.messages.map((msg, i) => (
          <div
            key={i}
            className={`receiver-ai-msg receiver-ai-msg--${msg.role}${msg.isStep ? ' receiver-ai-msg--step' : ''}`}
          >
            <span className="receiver-ai-msg-role">
              {msg.role === 'user' ? 'YOU' : msg.isStep ? '▸' : 'AI'}
            </span>
            <span className="receiver-ai-msg-text">{msg.content}</span>
          </div>
        ))}

        {ai.loading && (
          <div className="receiver-ai-msg receiver-ai-msg--assistant">
            <span className="receiver-ai-msg-role">AI</span>
            <span className="receiver-ai-typing">
              <span />
              <span />
              <span />
            </span>
          </div>
        )}

        {ai.error && <div className="receiver-ai-error">{ai.error}</div>}
      </div>

      <div className="receiver-ai-input-row">
        {ai.hasSpeech && (
          <button
            type="button"
            className={`receiver-ai-voice${ai.listening ? ' receiver-ai-voice--active' : ''}`}
            onClick={ai.toggleVoice}
            aria-label={ai.listening ? 'Parar gravação' : 'Gravar voz'}
            aria-pressed={ai.listening}
          >
            {ai.listening ? <IoMicOff size={14} /> : <IoMic size={14} />}
          </button>
        )}
        <input
          ref={ai.inputRef}
          type="text"
          className="receiver-ai-input"
          value={ai.input}
          onChange={(e) => ai.setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={ai.listening ? 'Ouvindo…' : 'Mensagem…'}
          disabled={ai.loading}
          autoComplete="off"
          spellCheck={false}
        />
        <button
          type="button"
          className="receiver-ai-send"
          onClick={ai.send}
          disabled={!ai.input.trim() || ai.loading}
          aria-label="Enviar"
        >
          <IoSend size={14} />
        </button>
      </div>
    </div>
  );
});
