import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useToast } from '../contexts/ToastContext';
import { getTmdbDetail, addFromSearch } from '../api/detail';
import { Skeleton } from '../components/Skeleton';
import type { TmdbDetail } from '../api/detail';
import type { SearchResult } from '../types/search';
import './Detail.css';

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

const INDEXER_LABELS: Record<string, string> = {
  '1337x': '1337x', tpb: 'TPB', yts: 'YTS', eztv: 'EZTV', nyaa: 'NYAA',
  limetorrents: 'Limetorrents', iptorrents: 'IPTorrents',
};
function indexerLabel(indexer: string): string {
  return INDEXER_LABELS[indexer?.toLowerCase() ?? ''] ?? indexer ?? '—';
}

export function Detail() {
  const location = useLocation();
  const navigate = useNavigate();
  const { showToast } = useToast();
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
    const controller = new AbortController();
    setTmdbLoading(true);
    setTmdbError(null);
    getTmdbDetail(result.title, contentType, { signal: controller.signal })
      .then(setTmdb)
      .catch((err) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setTmdbError(err instanceof Error ? err.message : 'Erro');
      })
      .finally(() => setTmdbLoading(false));
    return () => controller.abort();
  }, [state?.result?.title, state?.searchParams?.content_type]);

  const handleAddToDownloads = async () => {
    if (!state) return;
    setAdding(true);
    try {
      const data = await addFromSearch({
        ...state.searchParams,
        query: state.searchParams.query.trim(),
        indices: [state.originalIndex],
        start_now: true,
      });
      if (data.errors?.length) {
        showToast('Falha: ' + data.errors.join('; '), 6000);
      } else if (data.added?.length) {
        navigate('/downloads');
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Erro ao adicionar', 4000);
    } finally {
      setAdding(false);
    }
  };

  const navBlock = (
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
        <Link to="/search" className="detail-back-link">← Voltar à busca</Link>
      </div>
    );
  }

  const { result, searchParams } = state;
  const contentType = searchParams.content_type;
  const isMovieOrTv = contentType === 'movies' || contentType === 'tv';

  return (
    <div className="atum-page detail-page">
      <header className="detail-header">
        {navBlock}
      </header>

      <main className="detail-main">
        {isMovieOrTv && tmdbLoading && (
            <div className="detail-tmdb-skeleton" aria-busy="true">
              <div className="detail-tmdb-skeleton-content">
                <Skeleton width="120px" height="180px" borderRadius="8px" />
                <div className="detail-tmdb-skeleton-meta">
                  <Skeleton width="80%" height="1.5rem" borderRadius="4px" />
                  <Skeleton width="60%" height="0.9rem" borderRadius="4px" className="detail-tmdb-skeleton-line" />
                  <Skeleton width="40%" height="0.9rem" borderRadius="4px" />
                </div>
              </div>
            </div>
          )}
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
        {navBlock}
      </footer>
    </div>
  );
}
