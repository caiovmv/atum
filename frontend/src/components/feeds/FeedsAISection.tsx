import { IoSparkles } from 'react-icons/io5';
import type { AIFeedSuggestion } from '../../types/feeds';

interface FeedsAISectionProps {
  aiOpen: boolean;
  aiLoading: boolean;
  aiSuggestions: AIFeedSuggestion[];
  onFetch: () => void;
  onAddSuggested: (url: string, contentType: string) => void;
}

export function FeedsAISection({
  aiOpen,
  aiLoading,
  aiSuggestions,
  onFetch,
  onAddSuggested,
}: FeedsAISectionProps) {
  return (
    <section className="atum-feeds-ai" aria-labelledby="ai-feeds-heading">
      <div className="atum-feeds-ai-header">
        <h2 id="ai-feeds-heading" className="atum-feeds-section-title">
          <IoSparkles size={16} /> Sugestões AI
        </h2>
        <button
          type="button"
          className="atum-btn atum-btn-primary atum-btn-small"
          onClick={onFetch}
          disabled={aiLoading}
        >
          {aiLoading ? 'Analisando…' : aiOpen ? 'Atualizar' : 'Descobrir'}
        </button>
      </div>
      {aiOpen && (
        <div className="atum-feeds-ai-results">
          {aiLoading ? (
            <p className="atum-feeds-ai-loading">Analisando sua biblioteca…</p>
          ) : aiSuggestions.length === 0 ? (
            <p className="atum-feeds-ai-empty">Nenhuma sugestão de feed.</p>
          ) : (
            <div className="atum-feeds-ai-cards">
              {aiSuggestions.map((s, i) => (
                <div key={i} className="atum-feeds-ai-card">
                  <div className="atum-feeds-ai-card-info">
                    <span className="atum-feeds-ai-card-title">{s.title}</span>
                    <span className="atum-feeds-ai-card-url">{s.url}</span>
                    <span className="atum-feeds-ai-card-reason">{s.reason}</span>
                    <span className="atum-feeds-ai-card-type">{s.content_type}</span>
                  </div>
                  <button
                    type="button"
                    className="atum-btn atum-btn-small atum-btn-primary"
                    onClick={() => onAddSuggested(s.url, s.content_type)}
                  >
                    Adicionar
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
