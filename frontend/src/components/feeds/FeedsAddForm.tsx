type ContentType = 'music' | 'movies' | 'tv';

interface FeedsAddFormProps {
  newUrl: string;
  setNewUrl: (v: string) => void;
  contentType: ContentType;
  setContentType: (t: ContentType) => void;
  adding: boolean;
  addError: string | null;
  onAddFeed: (e: React.FormEvent) => void;
}

export function FeedsAddForm({
  newUrl,
  setNewUrl,
  contentType,
  setContentType,
  adding,
  addError,
  onAddFeed,
}: FeedsAddFormProps) {
  return (
    <section className="atum-feeds-form" aria-labelledby="add-feed-heading">
      <h2 id="add-feed-heading" className="atum-feeds-section-title">Adicionar feed</h2>
      <form onSubmit={onAddFeed} className="atum-feeds-add-form">
        <input
          type="url"
          value={newUrl}
          onChange={(e) => setNewUrl(e.target.value)}
          placeholder="https://…"
          className="atum-feeds-input"
          aria-label="URL do feed RSS"
        />
        <div className="atum-feeds-pills" role="group" aria-label="Tipo de conteúdo">
          {(['music', 'movies', 'tv'] as const).map((t) => (
            <button
              key={t}
              type="button"
              className={`atum-feeds-pill ${contentType === t ? 'atum-feeds-pill--active' : ''}`}
              onClick={() => setContentType(t)}
              aria-pressed={contentType === t}
            >
              {t === 'music' ? 'Música' : t === 'movies' ? 'Filmes' : 'Séries'}
            </button>
          ))}
        </div>
        <button type="submit" className="atum-btn atum-btn-primary" disabled={adding}>
          {adding ? 'Adicionando…' : 'Adicionar'}
        </button>
      </form>
      {addError && <p className="atum-feeds-error" role="alert">{addError}</p>}
    </section>
  );
}
