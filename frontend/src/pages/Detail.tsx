import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import './Detail.css';

interface SearchResult {
  title: string;
  quality_label: string;
  seeders: number;
  leechers: number;
  size: string;
  size_bytes: number;
  torrent_id: string;
  indexer: string;
  magnet: string | null;
}

interface SearchParams {
  query: string;
  limit: number;
  sort_by: string;
  content_type: 'music' | 'movies' | 'tv';
  music_category_only: boolean;
}

interface DetailState {
  result: SearchResult;
  searchParams: SearchParams;
  originalIndex: number;
}

interface TmdbDetail {
  id: number;
  title: string;
  overview: string;
  genres: string[];
  runtime?: number;
  release_date?: string | null;
  first_air_date?: string | null;
  number_of_seasons?: number;
  number_of_episodes?: number;
  vote_average?: number;
  poster_url: string | null;
  backdrop_url: string | null;
}

function indexerLabel(indexer: string): string {
  const s = indexer.toLowerCase();
  if (s === '1337x') return '1337x';
  if (s === 'tpb') return 'TPB';
  if (s === 'tg') return 'TorrentGalaxy';
  return indexer;
}

export function Detail() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as DetailState | null;

  const [tmdb, setTmdb] = useState<TmdbDetail | null>(null);
  const [tmdbLoading, setTmdbLoading] = useState(true);
  const [tmdbError, setTmdbError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    if (!state?.result) return;
    const { result, searchParams } = state;
    const contentType = searchParams.content_type;
    if (contentType !== 'movies' && contentType !== 'tv') {
      setTmdbLoading(false);
      return;
    }
    setTmdbLoading(true);
    setTmdbError(null);
    const params = new URLSearchParams({
      title: result.title,
      content_type: contentType,
    });
    fetch(`/api/tmdb-detail?${params}`)
      .then((r) => {
        if (!r.ok) throw new Error(r.status === 404 ? 'Não encontrado no TMDB' : r.statusText);
        return r.json();
      })
      .then((data) => setTmdb(data))
      .catch((err) => setTmdbError(err instanceof Error ? err.message : 'Erro'))
      .finally(() => setTmdbLoading(false));
  }, [state?.result?.title, state?.searchParams?.content_type]);

  const handleAddToDownloads = async () => {
    if (!state) return;
    setAdding(true);
    try {
      const res = await fetch('/api/add-from-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: state.searchParams.query.trim(),
          limit: state.searchParams.limit,
          sort_by: state.searchParams.sort_by,
          content_type: state.searchParams.content_type,
          music_category_only: state.searchParams.music_category_only,
          indices: [state.originalIndex],
          start_now: true,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      if (data.errors?.length) {
        alert('Falha: ' + data.errors.join('; '));
      } else if (data.added?.length) {
        navigate('/downloads');
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Erro ao adicionar');
    } finally {
      setAdding(false);
    }
  };

  const NavBlock = () => (
    <nav className="detail-nav">
      <button type="button" className="detail-nav-btn back" onClick={() => navigate(-1)} aria-label="Voltar">
        ← Voltar
      </button>
      <button
        type="button"
        className="detail-nav-btn primary add"
        onClick={handleAddToDownloads}
        disabled={adding}
        aria-label="Adicionar aos downloads"
      >
        {adding ? '…' : '+ Adicionar aos downloads'}
      </button>
    </nav>
  );

  if (!state?.result) {
    return (
      <div className="atum-page detail-page">
        <p className="detail-message">Volte à busca e clique em um resultado para ver os detalhes.</p>
        <Link to="/" className="detail-back-link">← Voltar à busca</Link>
      </div>
    );
  }

  const { result, searchParams } = state;
  const contentType = searchParams.content_type;
  const isMovieOrTv = contentType === 'movies' || contentType === 'tv';

  return (
    <div className="atum-page detail-page">
      <header className="detail-header">
        <NavBlock />
      </header>

      <main className="detail-main">
        {isMovieOrTv && tmdbLoading && <p className="detail-loading">Carregando detalhes…</p>}
        {isMovieOrTv && tmdbError && <p className="detail-error">{tmdbError}</p>}

        {isMovieOrTv && tmdb && (
          <div className="detail-tmdb">
            {tmdb.backdrop_url && (
              <div className="detail-backdrop" style={{ backgroundImage: `url(${tmdb.backdrop_url})` }} />
            )}
            <div className="detail-tmdb-content">
              <div className="detail-poster-wrap">
                {tmdb.poster_url && (
                  <img src={tmdb.poster_url} alt="" className="detail-poster" />
                )}
              </div>
              <div className="detail-meta-wrap">
                <h1 className="detail-title">{tmdb.title}</h1>
                {tmdb.vote_average != null && (
                  <p className="detail-vote">Nota: {tmdb.vote_average.toFixed(1)}</p>
                )}
                {tmdb.genres?.length > 0 && (
                  <p className="detail-genres">{tmdb.genres.join(' · ')}</p>
                )}
                {contentType === 'movies' && tmdb.runtime != null && (
                  <p className="detail-runtime">{tmdb.runtime} min</p>
                )}
                {contentType === 'tv' && (
                  <p className="detail-runtime">
                    {tmdb.number_of_seasons != null && `${tmdb.number_of_seasons} temporada(s)`}
                    {tmdb.number_of_episodes != null && ` · ${tmdb.number_of_episodes} episódios`}
                  </p>
                )}
                {(tmdb.release_date || tmdb.first_air_date) && (
                  <p className="detail-date">{tmdb.release_date || tmdb.first_air_date}</p>
                )}
                {tmdb.overview && (
                  <div className="detail-overview">
                    <h2>Sinopse</h2>
                    <p>{tmdb.overview}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <section className="detail-torrent">
          <h2>Torrent</h2>
          <p className="detail-torrent-title">{result.title}</p>
          <div className="detail-torrent-meta">
            <span>{result.quality_label}</span>
            <span>Se: {result.seeders} Le: {result.leechers}</span>
            <span>{result.size}</span>
            <span>{indexerLabel(result.indexer)}</span>
          </div>
        </section>
      </main>

      <footer className="detail-footer">
        <NavBlock />
      </footer>
    </div>
  );
}
