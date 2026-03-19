import type { RoomEQPhase } from '../../audio/roomEQ';

interface SmartEQRoomEQProps {
  roomPhase: RoomEQPhase;
  roomProgress: number;
  roomResult: number[] | null;
  roomError: string | null;
  onStart: () => void;
  onStop: () => void;
  onApply: () => void;
  onRetry: () => void;
}

export function SmartEQRoomEQ({
  roomPhase,
  roomProgress,
  roomResult,
  roomError,
  onStart,
  onStop,
  onApply,
  onRetry,
}: SmartEQRoomEQProps) {
  return (
    <div className="smarteq-wizard">
      <div className="smarteq-row">
        <span className="smarteq-label">ROOM EQ</span>
        {roomPhase === 'idle' && (
          <button type="button" className="smarteq-btn" onClick={onStart}>
            <span className="smarteq-btn-indicator" />
            <span className="smarteq-btn-text">CALIBRATE</span>
          </button>
        )}
        {roomPhase === 'requesting-mic' && (
          <span className="smarteq-ref-status">Aguardando permissao do microfone...</span>
        )}
        {roomPhase === 'measuring' && (
          <>
            <button type="button" className="smarteq-btn smarteq-btn--active" onClick={onStop}>
              <span className="smarteq-btn-indicator smarteq-btn-indicator--pulse" />
              <span className="smarteq-btn-text">MEASURING {Math.round(roomProgress * 100)}%</span>
            </button>
            <div className="smarteq-progress smarteq-progress--flex">
              <div className="smarteq-progress-fill" style={{ width: `${roomProgress * 100}%` }} />
            </div>
          </>
        )}
        {roomPhase === 'done' && (
          <>
            <button type="button" className="smarteq-btn smarteq-btn--apply" onClick={onApply}>
              <span className="smarteq-btn-indicator smarteq-btn-indicator--ready" />
              <span className="smarteq-btn-text">APPLY ROOM EQ</span>
            </button>
            <button type="button" className="smarteq-btn" onClick={onRetry}>
              <span className="smarteq-btn-text">RETRY</span>
            </button>
          </>
        )}
        {roomPhase === 'error' && (
          <>
            <span className="smarteq-result-val smarteq-result-val--neg smarteq-error-text">
              {roomError}
            </span>
            <button type="button" className="smarteq-btn" onClick={onStart}>
              <span className="smarteq-btn-text">RETRY</span>
            </button>
          </>
        )}
      </div>

      {roomPhase === 'idle' && (
        <div className="smarteq-wizard-step">
          Posicione o microfone na posicao de escuta.
          O sistema tocara <strong>pink noise</strong> por ~5s e medira a resposta da sala.
        </div>
      )}

      {roomPhase === 'done' && roomResult && (
        <div className="smarteq-result">
          {roomResult.map((g, i) => (
            <div key={i} className="smarteq-result-band">
              <span className={`smarteq-result-val${g > 0 ? ' smarteq-result-val--pos' : g < 0 ? ' smarteq-result-val--neg' : ''}`}>
                {g > 0 ? `+${g}` : g}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
