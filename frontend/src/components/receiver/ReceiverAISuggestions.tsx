interface ReceiverAISuggestionsProps {
  onRequestEQ: () => void;
  onSetInput: (v: string) => void;
  onRequestSmartQueue: () => void;
  hasApplyEQ: boolean;
  hasSmartQueue: boolean;
}

export function ReceiverAISuggestions({
  onRequestEQ,
  onSetInput,
  onRequestSmartQueue,
  hasApplyEQ,
  hasSmartQueue,
}: ReceiverAISuggestionsProps) {
  return (
    <div className="receiver-ai-empty">
      <p>Pergunte sobre a faixa, peça sugestões de EQ, ou explore artistas similares.</p>
      <div className="receiver-ai-suggestions">
        {hasApplyEQ && (
          <button type="button" onClick={onRequestEQ} className="receiver-ai-suggestion receiver-ai-suggestion--primary" aria-label="Aplicar Auto-EQ automaticamente">
            Auto-EQ
          </button>
        )}
        <button type="button" onClick={() => onSetInput('Sugira EQ para esta faixa')} className="receiver-ai-suggestion" aria-label="Pedir sugestão de EQ">
          Sugira EQ
        </button>
        <button type="button" onClick={() => onSetInput('Artistas similares')} className="receiver-ai-suggestion" aria-label="Buscar artistas similares">
          Similares
        </button>
        <button type="button" onClick={() => onSetInput('Sobre esta faixa')} className="receiver-ai-suggestion" aria-label="Informações sobre a faixa">
          Sobre a faixa
        </button>
        <button type="button" onClick={() => onSetInput('Aumente o volume para 85%')} className="receiver-ai-suggestion" aria-label="Ajustar volume para 85%">
          Volume 85%
        </button>
        <button type="button" onClick={() => onSetInput('Configure EQ ideal para esta faixa')} className="receiver-ai-suggestion" aria-label="Configurar EQ ideal">
          EQ ideal
        </button>
        {hasSmartQueue && (
          <button type="button" onClick={onRequestSmartQueue} className="receiver-ai-suggestion receiver-ai-suggestion--primary" aria-label="Montar fila inteligente">
            Smart Queue
          </button>
        )}
      </div>
    </div>
  );
}
