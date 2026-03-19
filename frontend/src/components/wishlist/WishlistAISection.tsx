import { IoSparkles } from 'react-icons/io5';
import type { AISuggestion } from '../../types/wishlist';

interface WishlistAISectionProps {
  aiLoading: boolean;
  aiOpen: boolean;
  aiSuggestions: AISuggestion[];
  onFetch: () => void;
  onAddSuggestion: (term: string) => void;
}

export function WishlistAISection({
  aiLoading,
  aiOpen,
  aiSuggestions,
  onFetch,
  onAddSuggestion,
}: WishlistAISectionProps) {
  return (
    <section className="atum-wishlist-ai" aria-labelledby="ai-heading">
      <div className="atum-wishlist-ai-header">
        <h2 id="ai-heading" className="atum-wishlist-section-title">
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
        <div className="atum-wishlist-ai-results">
          {aiLoading ? (
            <p className="atum-wishlist-ai-loading">Analisando sua biblioteca…</p>
          ) : aiSuggestions.length === 0 ? (
            <p className="atum-wishlist-ai-empty">Nenhuma sugestão. Adicione mais itens à biblioteca.</p>
          ) : (
            <div className="atum-wishlist-ai-cards">
              {aiSuggestions.map((s, i) => (
                <div key={i} className="atum-wishlist-ai-card">
                  <div className="atum-wishlist-ai-card-info">
                    <span className="atum-wishlist-ai-card-term">{s.term}</span>
                    <span className="atum-wishlist-ai-card-reason">{s.reason}</span>
                    <span className="atum-wishlist-ai-card-type">{s.content_type}</span>
                  </div>
                  <button
                    type="button"
                    className="atum-btn atum-btn-small atum-btn-primary"
                    onClick={() => onAddSuggestion(s.term)}
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
