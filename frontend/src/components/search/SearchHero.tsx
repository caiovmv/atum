import { IoSearch } from 'react-icons/io5';

interface SearchHeroProps {
  query: string;
  setQuery: (v: string) => void;
  contentType: 'music' | 'movies' | 'tv';
  setContentType: (t: 'music' | 'movies' | 'tv') => void;
  sortBy: 'seeders' | 'size';
  setSortBy: (s: 'seeders' | 'size') => void;
  loading: boolean;
  error: string | null;
  onSubmit: (e: React.FormEvent) => void;
}

export function SearchHero({
  query,
  setQuery,
  contentType,
  setContentType,
  sortBy,
  setSortBy,
  loading,
  error,
  onSubmit,
}: SearchHeroProps) {
  return (
    <form onSubmit={onSubmit} className="search-hero" role="search" aria-label="Buscar torrents">
      <div className="search-hero-input-wrap">
        <IoSearch className="search-hero-icon" aria-hidden />
        <input
          type="text"
          placeholder="O que você quer ouvir ou assistir?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="search-hero-input"
          aria-describedby={error ? 'search-error' : undefined}
          aria-busy={loading}
        />
      </div>
      <div className="search-hero-pills">
        <span className="search-hero-pills-label">Tipo:</span>
        {(['music', 'movies', 'tv'] as const).map((t) => (
          <button
            key={t}
            type="button"
            className={`search-pill ${contentType === t ? 'search-pill--active' : ''}`}
            onClick={() => setContentType(t)}
            aria-pressed={contentType === t}
          >
            {t === 'music' ? 'Música' : t === 'movies' ? 'Filmes' : 'Séries'}
          </button>
        ))}
        <span className="search-hero-pills-label">Ordenar:</span>
        <button
          type="button"
          className={`search-pill ${sortBy === 'seeders' ? 'search-pill--active' : ''}`}
          onClick={() => setSortBy('seeders')}
          aria-pressed={sortBy === 'seeders'}
        >
          Seeders
        </button>
        <button
          type="button"
          className={`search-pill ${sortBy === 'size' ? 'search-pill--active' : ''}`}
          onClick={() => setSortBy('size')}
          aria-pressed={sortBy === 'size'}
        >
          Tamanho
        </button>
      </div>
      <button type="submit" className="search-hero-submit primary" disabled={loading} aria-busy={loading}>
        {loading ? 'Buscando…' : 'Buscar'}
      </button>
    </form>
  );
}
