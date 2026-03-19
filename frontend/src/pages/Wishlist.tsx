import { EmptyState } from '../components/EmptyState';
import { SkeletonRow } from '../components/Skeleton';
import { WishlistAISection } from '../components/wishlist/WishlistAISection';
import { useWishlist } from '../hooks/useWishlist';
import './Wishlist.css';

export function Wishlist() {
  const wl = useWishlist();

  return (
    <div className="atum-page wishlist-page atum-wishlist">
      <h1 className="atum-wishlist-title">Wishlist</h1>
      <p className="atum-wishlist-desc">
        Termos salvos e/ou lista colada (um por linha). Use Buscar e adicionar aos downloads para enfileirar o melhor resultado de cada um.
      </p>

      <section className="atum-wishlist-form" aria-labelledby="add-term-heading">
        <h2 id="add-term-heading" className="atum-wishlist-section-title">Adicionar termo</h2>
        <form onSubmit={wl.handleAddTerm} className="atum-wishlist-add-form">
          <input
            type="text"
            value={wl.newTerm}
            onChange={(e) => wl.setNewTerm(e.target.value)}
            placeholder="Ex.: Artist - Album ou Nome do filme"
            className="atum-wishlist-input"
            aria-label="Novo termo"
          />
          <button type="submit" className="atum-btn atum-btn-primary">Adicionar</button>
        </form>
        {wl.addError && <p className="atum-wishlist-error" role="alert">{wl.addError}</p>}
      </section>

      {wl.fetchError && (
        <div className="atum-wishlist-error" role="alert">
          <span>{wl.fetchError}</span>{' '}
          <button type="button" className="atum-btn atum-btn-small" onClick={() => wl.refetchTerms()}>
            Tentar novamente
          </button>
        </div>
      )}

      <section className="atum-wishlist-terms" aria-labelledby="terms-heading">
        <h2 id="terms-heading" className="atum-wishlist-section-title">Termos salvos</h2>
        {wl.wishlistReconnecting && (
          <span className="atum-wishlist-reconnecting" aria-live="polite">Reconectando…</span>
        )}
        {wl.loading ? (
          <div className="atum-wishlist-skeleton" aria-busy="true">
            {Array.from({ length: 5 }, (_, i) => (
              <SkeletonRow key={i} />
            ))}
          </div>
        ) : wl.terms.length === 0 ? (
          <EmptyState
            title="Nenhum termo salvo"
            description="Adicione um termo acima ou use o campo de lote abaixo para buscar e adicionar aos downloads."
          />
        ) : (
          <ul className="atum-wishlist-list">
            {wl.terms.map((t) => (
              <li key={t.id} className="atum-wishlist-item">
                <span className="atum-wishlist-term-text">{t.term}</span>
                <button
                  type="button"
                  className="atum-btn atum-btn-small"
                  onClick={() => wl.handleRemove(t.id)}
                  aria-label={`Remover ${t.term}`}
                >
                  Remover
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <WishlistAISection
        aiLoading={wl.aiLoading}
        aiOpen={wl.aiOpen}
        aiSuggestions={wl.aiSuggestions}
        onFetch={wl.fetchAISuggestions}
        onAddSuggestion={wl.addSuggestionToWishlist}
      />

      <section className="atum-wishlist-batch" aria-labelledby="batch-heading">
        <h2 id="batch-heading" className="atum-wishlist-section-title">Colar lista (uma busca por linha)</h2>
        <textarea
          value={wl.pastedLines}
          onChange={(e) => wl.setPastedLines(e.target.value)}
          placeholder="Artist - Album"
          className="atum-wishlist-textarea"
          rows={6}
          aria-label="Linhas para busca em lote"
        />
      </section>

      <section className="atum-wishlist-run">
        <span className="atum-wishlist-label">Tipo de conteúdo:</span>
        <div className="atum-wishlist-pills" role="group" aria-label="Tipo de conteúdo">
          {(['music', 'movies', 'tv'] as const).map((t) => (
            <button
              key={t}
              type="button"
              className={`atum-wishlist-pill ${wl.contentType === t ? 'atum-wishlist-pill--active' : ''}`}
              onClick={() => wl.setContentType(t)}
              aria-pressed={wl.contentType === t}
            >
              {t === 'music' ? 'Música' : t === 'movies' ? 'Filmes' : 'Séries'}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="atum-btn atum-btn-primary atum-wishlist-run-btn"
          onClick={wl.handleRun}
          disabled={wl.running}
        >
          {wl.running ? 'Enviando…' : 'Buscar e adicionar aos downloads'}
        </button>
      </section>
    </div>
  );
}
