import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDownloadsEvents } from '../contexts/DownloadsEventsContext';
import { useToast } from '../contexts/ToastContext';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { IoCheckmarkCircle, IoCloseCircleOutline, IoSearch, IoAdd } from 'react-icons/io5';
import { MediaCard } from '../components/MediaCard';
import { SearchResultCardSkeleton } from '../components/SearchResultCardSkeleton';
import { SearchFilesModal } from '../components/search/SearchFilesModal';
import { SearchAddModal } from '../components/search/SearchAddModal';
import { statusLabel } from '../utils/format';
import './Search.css';

const SEARCH_STORAGE_KEY = 'atum-search-state';
const PAGE_SIZE = 20;

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
  /** URL do arquivo .torrent (quando disponível; preferido ao magnet para "Ver arquivos") */
  torrent_url?: string | null;
  parsed_year?: number | null;
  parsed_video_quality?: string | null;
  parsed_audio_codec?: string | null;
  parsed_music_quality?: string | null;
  parsed_cleaned_title?: string | null;
}

interface FilterSuggestions {
  years: number[];
  genres: string[];
  qualities: string[];
}

interface StoredSearch {
  query: string;
  contentType: 'music' | 'movies' | 'tv';
  sortBy: 'seeders' | 'size';
  results: SearchResult[];
}

function loadStoredSearch(): Partial<StoredSearch> | null {
  try {
    const raw = sessionStorage.getItem(SEARCH_STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as StoredSearch;
    if (!data || !Array.isArray(data.results)) return null;
    return { query: data.query ?? '', contentType: data.contentType ?? 'music', sortBy: data.sortBy ?? 'seeders', results: data.results };
  } catch {
    return null;
  }
}

function saveStoredSearch(state: StoredSearch) {
  try {
    sessionStorage.setItem(SEARCH_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // ignore
  }
}

const INDEXER_LABELS: Record<string, string> = {
  '1337x': '1337x',
  tpb: 'TPB',
  yts: 'YTS',
  eztv: 'EZTV',
  nyaa: 'NYAA',
  limetorrents: 'Limetorrents',
  iptorrents: 'IPTorrents',
};

/** Ordem fixa das fontes no filtro (mesma ordem que a API usa por padrão). */
const INDEXER_ORDER = ['1337x', 'tpb', 'yts', 'eztv', 'nyaa', 'limetorrents', 'iptorrents'];

function indexerLabel(indexer: string | undefined): string {
  if (!indexer) return '—';
  const s = indexer.toLowerCase();
  return INDEXER_LABELS[s] ?? indexer;
}

function titleMatchesQuery(title: string, searchQuery: string): boolean {
  const words = searchQuery.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return true;
  const t = title.toLowerCase();
  return words.every((w) => t.includes(w));
}

function normalizeMagnet(m: string | null | undefined): string {
  return (m || '').trim();
}

export function Search() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebouncedValue(query, 400);
  const [contentType, setContentType] = useState<'music' | 'movies' | 'tv'>('music');
  const [sortBy, setSortBy] = useState<'seeders' | 'size'>('seeders');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [indexerStatus, setIndexerStatus] = useState<Record<string, boolean>>({});
  const [sourceFilter, setSourceFilter] = useState<Set<string>>(new Set());
  const [nameFilter, setNameFilter] = useState('');
  const [onlyRelevant, setOnlyRelevant] = useState(true);
  const [clientSort, setClientSort] = useState<'seeders' | 'size' | 'quality'>('seeders');
  const [filterSuggestions, setFilterSuggestions] = useState<FilterSuggestions>({ years: [], genres: [], qualities: [] });
  const [yearFilter, setYearFilter] = useState<number | ''>('');
  const [genreFilter, setGenreFilter] = useState('');
  const [qualityFilter, setQualityFilter] = useState('');
  const [audioFilter, setAudioFilter] = useState('');
  const { showToast } = useToast();
  const [filesModalResult, setFilesModalResult] = useState<SearchResult | null>(null);
  const [addModalResult, setAddModalResult] = useState<SearchResult | null>(null);
  const { downloads: contextDownloads } = useDownloadsEvents();
  const downloads = useMemo(
    () =>
      contextDownloads.map((d) => ({
        id: d.id,
        magnet: d.magnet,
        status: (d.status ?? 'queued') as string,
        progress: d.progress,
      })),
    [contextDownloads]
  );
  const [indexerProgress, setIndexerProgress] = useState<Record<string, 'pending' | 'loading' | 'done' | 'error'>>({});
  const [indexerCounts, setIndexerCounts] = useState<Record<string, number>>({});
  const navigate = useNavigate();
  const searchAbortRef = useRef<AbortController | null>(null);

  const enabledIndexers = useMemo(
    () => Object.entries(indexerStatus).filter(([, ok]) => ok).map(([name]) => name),
    [indexerStatus]
  );
  const allIndexersForFilter = useMemo(() => {
    const keys = Object.keys(indexerStatus);
    return keys.slice().sort((a, b) => {
      const ia = INDEXER_ORDER.indexOf(a);
      const ib = INDEXER_ORDER.indexOf(b);
      if (ia !== -1 && ib !== -1) return ia - ib;
      if (ia !== -1) return -1;
      if (ib !== -1) return 1;
      return a.localeCompare(b);
    });
  }, [indexerStatus]);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/indexers/status', { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : {}))
      .then((status: Record<string, boolean>) => {
        setIndexerStatus(status);
        setSourceFilter((prev) => {
          const enabled = Object.entries(status).filter(([, ok]) => ok).map(([name]) => name);
          if (enabled.length === 0) return prev;
          if (prev.size === 0) return new Set(enabled);
          return new Set(enabled.filter((e) => prev.has(e)));
        });
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setIndexerStatus({});
      });
    return () => controller.abort();
  }, []);

  const indexersSseRef = useRef<EventSource | null>(null);
  const [indexersReconnecting, setIndexersReconnecting] = useState(false);
  const indexersReconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    let disposed = false;
    const open = () => {
      if (disposed || indexersSseRef.current) return;
      const es = new EventSource('/api/indexers/events');
      es.onmessage = (event) => {
        setIndexersReconnecting(false);
        try {
          const status = JSON.parse(event.data);
          if (status && typeof status === 'object') setIndexerStatus(status);
        } catch {
          // ignore
        }
      };
      es.onerror = () => {
        setIndexersReconnecting(true);
        es.close();
        indexersSseRef.current = null;
        if (!disposed) {
          indexersReconnectRef.current = setTimeout(() => {
            indexersReconnectRef.current = null;
            if (document.visibilityState === 'visible') open();
          }, 5000);
        }
      };
      indexersSseRef.current = es;
    };
    const close = () => {
      if (indexersSseRef.current) {
        indexersSseRef.current.close();
        indexersSseRef.current = null;
      }
      if (indexersReconnectRef.current) {
        clearTimeout(indexersReconnectRef.current);
        indexersReconnectRef.current = null;
      }
    };
    const onVisibility = () => {
      if (document.visibilityState === 'visible') open();
      else close();
    };
    if (document.visibilityState === 'visible') open();
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      disposed = true;
      document.removeEventListener('visibilitychange', onVisibility);
      close();
    };
  }, []);

  async function ensureMagnetOrTorrentUrl(r: SearchResult): Promise<SearchResult | null> {
    if (r.magnet || r.torrent_url) return r;
    if (!r.indexer || !r.torrent_id) return null;
    try {
      const res = await fetch('/api/search/resolve-magnet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ indexer: r.indexer, torrent_id: r.torrent_id }),
      });
      const data = await res.json().catch(() => null);
      if (data?.magnet) return { ...r, magnet: data.magnet };
    } catch { /* ignore */ }
    return null;
  }

  async function openModal(r: SearchResult, setter: (v: SearchResult | null) => void) {
    const resolved = await ensureMagnetOrTorrentUrl(r);
    if (!resolved || (!resolved.magnet && !resolved.torrent_url)) {
      showToastMessage('Este resultado não possui magnet nem link do .torrent.');
      return;
    }
    setter(resolved);
  }

  const filteredResults = useMemo(() => {
    let list = results.map((r, i) => ({ r, originalIndex: i }));
    const q = query.trim();
    if (onlyRelevant && q) {
      list = list.filter(({ r }) => titleMatchesQuery(r.title, q));
    }
    const src = sourceFilter;
    if (src.size > 0) {
      list = list.filter(({ r }) => src.has(r.indexer?.toLowerCase() ?? ''));
    }
    const name = nameFilter.trim().toLowerCase();
    if (name) {
      list = list.filter(({ r }) => r.title.toLowerCase().includes(name));
    }
    if (yearFilter !== '') {
      const y = Number(yearFilter);
      list = list.filter(({ r }) => r.parsed_year != null && r.parsed_year === y);
    }
    if (genreFilter) {
      const g = genreFilter.toLowerCase();
      list = list.filter(({ r }) => r.title.toLowerCase().includes(g));
    }
    if (qualityFilter) {
      const qf = qualityFilter.toLowerCase();
      list = list.filter(({ r }) => {
        const ql = (r.quality_label || '').toLowerCase();
        const pq = (r.parsed_video_quality || r.parsed_music_quality || '').toLowerCase();
        return ql.includes(qf) || pq.includes(qf);
      });
    }
    if (audioFilter) {
      list = list.filter(({ r }) => (r.parsed_audio_codec || '').toLowerCase() === audioFilter.toLowerCase());
    }
    const sorted = [...list].sort((a, b) => {
      if (clientSort === 'seeders') {
        const se = b.r.seeders - a.r.seeders;
        if (se !== 0) return se;
        return b.r.leechers - a.r.leechers;
      }
      if (clientSort === 'size') return b.r.size_bytes - a.r.size_bytes;
      return (a.r.quality_label || '').localeCompare(b.r.quality_label || '');
    });
    return sorted;
  }, [results, query, onlyRelevant, sourceFilter, nameFilter, yearFilter, genreFilter, qualityFilter, audioFilter, clientSort]);

  const totalPages = Math.max(1, Math.ceil(filteredResults.length / PAGE_SIZE));
  const start = (page - 1) * PAGE_SIZE;
  const pageResults = filteredResults.slice(start, start + PAGE_SIZE);

  function toggleSource(key: string) {
    setPage(1);
    setSourceFilter((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next.size ? next : new Set(enabledIndexers);
    });
  }

  useEffect(() => {
    const stored = loadStoredSearch();
    if (stored && stored.results?.length) {
      if (stored.query != null) setQuery(stored.query);
      if (stored.contentType) setContentType(stored.contentType);
      if (stored.sortBy) setSortBy(stored.sortBy);
      setResults(stored.results);
      setPage(1);
    }
  }, []);

  useEffect(() => {
    if (!debouncedQuery.trim() || results.length === 0) return;
    const controller = new AbortController();
    const params = new URLSearchParams({ q: debouncedQuery.trim(), content_type: contentType });
    fetch(`/api/search-filter-suggestions?${params}`, { signal: controller.signal })
      .then((res) => (res.ok ? res.json() : { years: [], genres: [], qualities: [] }))
      .then((data: FilterSuggestions) => setFilterSuggestions(data))
      .catch(() => {});
    return () => controller.abort();
  }, [debouncedQuery, contentType, results.length]);

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    searchAbortRef.current?.abort();
    searchAbortRef.current = new AbortController();
    const signal = searchAbortRef.current.signal;
    const indexersToRequest = sourceFilter.size > 0
      ? Array.from(sourceFilter).filter((i) => indexerStatus[i] !== false)
      : enabledIndexers;
    if (indexersToRequest.length === 0) return;

    setLoading(true);
    setError(null);
    setResults([]);
    setYearFilter('');
    setGenreFilter('');
    setQualityFilter('');
    setAudioFilter('');
    const progressInit: Record<string, 'loading'> = {};
    indexersToRequest.forEach((i) => { progressInit[i] = 'loading'; });
    setIndexerProgress(progressInit);
    setIndexerCounts({});

    const baseParams = {
      q: query.trim(),
      limit: '1000',
      sort_by: sortBy,
      content_type: contentType,
      music_category_only: contentType === 'music' ? 'true' : 'false',
    };

    function mergeAndSort(prev: SearchResult[], next: SearchResult[], by: 'seeders' | 'size'): SearchResult[] {
      const seen = new Set(prev.map((x) => `${x.indexer}-${x.torrent_id}`));
      const combined = [...prev];
      for (const r of next) {
        const key = `${r.indexer}-${r.torrent_id}`;
        if (!seen.has(key)) {
          seen.add(key);
          combined.push(r);
        }
      }
      if (by === 'seeders') {
        combined.sort((a, b) => (b.seeders ?? 0) - (a.seeders ?? 0));
      } else {
        combined.sort((a, b) => (b.size_bytes ?? 0) - (a.size_bytes ?? 0));
      }
      return combined;
    }

    let completed = 0;
    const total = indexersToRequest.length;

    indexersToRequest.forEach((indexer) => {
      const params = new URLSearchParams({ ...baseParams, indexers: indexer });
      fetch(`/api/search?${params}`, { signal })
        .then((res) => {
          if (!res.ok) throw new Error(res.statusText);
          return res.json();
        })
        .then((data: SearchResult[]) => {
          if (signal.aborted) return;
          setIndexerProgress((p) => ({ ...p, [indexer]: 'done' }));
          setIndexerCounts((c) => ({ ...c, [indexer]: Array.isArray(data) ? data.length : 0 }));
          setResults((prev) => mergeAndSort(prev, Array.isArray(data) ? data : [], sortBy));
          completed += 1;
          if (completed === total) {
            setLoading(false);
            setPage(1);
            setResults((final) => {
              saveStoredSearch({ query: query.trim(), contentType, sortBy, results: final });
              return final;
            });
          }
        })
        .catch((err) => {
          if (err?.name === 'AbortError') return;
          setIndexerProgress((p) => ({ ...p, [indexer]: 'error' }));
          setIndexerCounts((c) => ({ ...c, [indexer]: 0 }));
          completed += 1;
          if (completed === total) {
            setLoading(false);
            setResults((r) => {
              if (r.length === 0) setError('Nenhum indexador respondeu. Tente novamente.');
              else saveStoredSearch({ query: query.trim(), contentType, sortBy, results: r });
              return r;
            });
          }
        });
    });
  }, [query, sortBy, contentType, sourceFilter, enabledIndexers, indexerStatus]);

  useEffect(() => {
    return () => { searchAbortRef.current?.abort(); };
  }, []);

  const showToastMessage = (msg: string) => showToast(msg, 4000);

  return (
    <div className="atum-page search-page">
      <h1 className="atum-page-title">Busca</h1>
      {indexersReconnecting && <span className="search-reconnecting" aria-live="polite">Reconectando indexadores…</span>}
      <form onSubmit={handleSearch} className="search-hero" role="search" aria-label="Buscar torrents">
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
      {error && <p id="search-error" className="search-error" role="alert">{error}</p>}
      {Object.keys(indexerProgress).length > 0 && (
        <div className="search-progress-wrap search-progress-wrap--compact" role="status" aria-live="polite" aria-label="Progresso da busca por indexador">
          <div className="search-progress-bar-wrap">
            <div
              className="search-progress-bar-fill"
              style={{
                width: `${(Object.values(indexerProgress).filter((s) => s === 'done' || s === 'error').length / Object.keys(indexerProgress).length) * 100}%`,
              }}
            />
            <span className="search-progress-bar-label">
              {Object.values(indexerProgress).filter((s) => s === 'done' || s === 'error').length} / {Object.keys(indexerProgress).length}
            </span>
          </div>
          <div className="search-progress-indexers">
            {INDEXER_ORDER.filter((key) => key in indexerProgress).map((key) => {
              const status = indexerProgress[key];
              const count = indexerCounts[key] ?? 0;
              return (
                <span key={key} className={`search-progress-indexer search-progress-indexer--${status}`} title={status === 'loading' ? 'Buscando…' : status === 'done' ? `${count} resultado(s)` : 'Falha'}>
                  {status === 'loading' && <span className="search-progress-spinner" aria-hidden />}
                  {status === 'done' && <IoCheckmarkCircle className="search-progress-icon" aria-hidden />}
                  {status === 'error' && <IoCloseCircleOutline className="search-progress-icon search-progress-icon--error" aria-hidden />}
                  <span className="search-progress-indexer-name">{indexerLabel(key)}</span>
                  {status === 'done' && count >= 0 && <span className="search-progress-count">{count}</span>}
                </span>
              );
            })}
          </div>
        </div>
      )}
      <section className="results-section" aria-live="polite" aria-busy={loading}>
        {results.length > 0 && (
          <>
            <div className="results-filters">
              {allIndexersForFilter.length > 0 && (
                <div className="filter-row filter-row--chips">
                  <span className="filter-label">Fonte:</span>
                  <div className="filter-chips">
                    {allIndexersForFilter.map((key) => {
                      const enabled = indexerStatus[key] !== false;
                      const active = sourceFilter.has(key);
                      return (
                        <button
                          key={key}
                          type="button"
                          className={`search-pill search-pill--chip ${active ? 'search-pill--active' : ''} ${!enabled ? 'search-pill--disabled' : ''}`}
                          onClick={() => enabled && toggleSource(key)}
                          disabled={!enabled}
                          title={!enabled ? 'Fonte desativada' : undefined}
                        >
                          {indexerLabel(key)}{!enabled ? ' (indisponível)' : ''}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
              <div className="filter-row">
                <span className="filter-label">Ano:</span>
                <select
                  value={yearFilter}
                  onChange={(e) => { setYearFilter(e.target.value === '' ? '' : Number(e.target.value)); setPage(1); }}
                  className="filter-select"
                >
                  <option value="">Todos</option>
                  {filterSuggestions.years.map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                  {filterSuggestions.years.length === 0 && results
                    .map((r) => r.parsed_year)
                    .filter((y): y is number => typeof y === 'number')
                    .filter((y, i, arr) => arr.indexOf(y) === i)
                    .sort((a, b) => b - a)
                    .map((y) => (
                      <option key={y} value={y}>{y}</option>
                    ))}
                </select>
                <span className="filter-label">Gênero:</span>
                <select
                  value={genreFilter}
                  onChange={(e) => { setGenreFilter(e.target.value); setPage(1); }}
                  className="filter-select"
                >
                  <option value="">Todos</option>
                  {filterSuggestions.genres.map((g) => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
                <span className="filter-label">Qualidade:</span>
                <select
                  value={qualityFilter}
                  onChange={(e) => { setQualityFilter(e.target.value); setPage(1); }}
                  className="filter-select"
                >
                  <option value="">Todas</option>
                  {filterSuggestions.qualities.map((q) => (
                    <option key={q} value={q}>{q}</option>
                  ))}
                </select>
                <span className="filter-label">Áudio:</span>
                <select
                  value={audioFilter}
                  onChange={(e) => { setAudioFilter(e.target.value); setPage(1); }}
                  className="filter-select"
                >
                  <option value="">Todos</option>
                  {results
                    .map((r) => r.parsed_audio_codec)
                    .filter((a): a is string => typeof a === 'string' && a.length > 0)
                    .filter((a, i, arr) => arr.indexOf(a) === i)
                    .sort((a, b) => a.localeCompare(b))
                    .map((codec) => (
                      <option key={codec} value={codec}>{codec}</option>
                    ))}
                </select>
              </div>
              <div className="filter-row">
                <span className="filter-label">Nome:</span>
                <input
                  type="text"
                  placeholder="Filtrar pelo título…"
                  value={nameFilter}
                  onChange={(e) => { setNameFilter(e.target.value); setPage(1); }}
                  className="filter-name-input"
                />
                <label className="filter-check">
                  <input
                    type="checkbox"
                    checked={onlyRelevant}
                    onChange={(e) => { setOnlyRelevant(e.target.checked); setPage(1); }}
                  />
                  Só títulos relacionados à busca
                </label>
              </div>
              <div className="filter-row filter-row--pills">
                <span className="filter-label">Ordenar:</span>
                <div className="filter-chips">
                  <button type="button" className={`search-pill search-pill--chip ${clientSort === 'seeders' ? 'search-pill--active' : ''}`} onClick={() => { setClientSort('seeders'); setPage(1); }} aria-pressed={clientSort === 'seeders'}>Se/Le</button>
                  <button type="button" className={`search-pill search-pill--chip ${clientSort === 'size' ? 'search-pill--active' : ''}`} onClick={() => { setClientSort('size'); setPage(1); }} aria-pressed={clientSort === 'size'}>Tamanho</button>
                  <button type="button" className={`search-pill search-pill--chip ${clientSort === 'quality' ? 'search-pill--active' : ''}`} onClick={() => { setClientSort('quality'); setPage(1); }} aria-pressed={clientSort === 'quality'}>Qualidade</button>
                </div>
              </div>
            </div>
            <p className="results-meta">
              {filteredResults.length} resultado(s){filteredResults.length !== results.length && ` (de ${results.length})`}
              <button type="button" className="clear-search-btn" onClick={() => { setYearFilter(''); setGenreFilter(''); setQualityFilter(''); setAudioFilter(''); setNameFilter(''); setSourceFilter(new Set(enabledIndexers)); setPage(1); }}>
                Limpar filtros
              </button>
              <button type="button" className="clear-search-btn" onClick={() => { setResults([]); setQuery(''); setPage(1); setIndexerProgress({}); setIndexerCounts({}); setError(null); try { sessionStorage.removeItem(SEARCH_STORAGE_KEY); } catch { /* ignore */ } }}>
                Nova busca
              </button>
            </p>
          </>
        )}
        {results.length > 0 && filteredResults.length === 0 && (
          <p className="search-empty" role="status">Nenhum resultado para &quot;{query.trim()}&quot; com os filtros atuais. Tente limpar filtros ou alterar a busca.</p>
        )}
        <div className="results-grid">
          {loading && results.length === 0
            ? Array.from({ length: 10 }, (_, i) => <SearchResultCardSkeleton key={`skeleton-${i}`} />)
            : pageResults.map(({ r, originalIndex }, idx) => {
            const match = r.magnet ? downloads.find((d) => normalizeMagnet(d.magnet) === normalizeMagnet(r.magnet)) : null;
            const overlay = match
              ? {
                  type: (match.progress != null ? 'progress' : 'status') as 'progress' | 'status',
                  label: statusLabel(match.status),
                  percent: match.progress,
                }
              : undefined;
            return (
            <MediaCard
              key={`${r.indexer}-${r.torrent_id}-${start + idx}`}
              cover={{ contentType, title: r.title }}
              coverShape={contentType === 'music' ? 'square' : 'poster'}
              title={r.title}
              source={indexerLabel(r.indexer)}
              meta={[
                r.quality_label,
                r.parsed_year != null ? String(r.parsed_year) : '',
                r.parsed_audio_codec ?? '',
                r.parsed_music_quality ?? '',
                `Se: ${r.seeders} Le: ${r.leechers}`,
                r.size,
              ].filter(Boolean)}
              showSeLe={true}
              overlay={overlay}
              primaryAction={
                <button
                  type="button"
                  className="media-card-play-btn"
                  onClick={(e) => { e.stopPropagation(); openModal(r, setAddModalResult); }}
                  aria-label={`Adicionar ${r.title} à fila`}
                >
                  <IoAdd size={24} />
                </button>
              }
              actions={
                <div className="result-card-actions" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    className="secondary add-btn"
                    onClick={() => openModal(r, setFilesModalResult)}
                    aria-label="Ver lista de arquivos do torrent"
                  >
                    Ver arquivos
                  </button>
                  <button
                    type="button"
                    className="primary add-btn"
                    onClick={() => openModal(r, setAddModalResult)}
                    aria-label={`Adicionar ${r.title} à fila`}
                  >
                    Adicionar
                  </button>
                  {(contentType === 'movies' || contentType === 'tv') && (
                    <button
                      type="button"
                      className="secondary add-btn"
                      onClick={() =>
                        navigate('/detail', {
                          state: {
                            result: r,
                            searchParams: {
                              query,
                              limit: 1000,
                              sort_by: sortBy,
                              content_type: contentType,
                              music_category_only: false,
                            },
                            originalIndex,
                          },
                        })
                      }
                      aria-label={`Ver detalhes de ${r.title}`}
                    >
                      Detalhes
                    </button>
                  )}
                </div>
              }
              onClick={() => openModal(r, setFilesModalResult)}
              clickAriaLabel={`Ver lista de arquivos de ${r.title} (${indexerLabel(r.indexer)})`}
            />
          );
          }) }
        </div>
        {filteredResults.length > PAGE_SIZE && (
          <nav className="pagination" aria-label="Paginação dos resultados">
            <span className="pagination-info">
              Página {page} de {totalPages} ({filteredResults.length} resultado(s))
            </span>
            <div className="pagination-buttons">
              <button type="button" disabled={page <= 1} onClick={() => setPage(1)} aria-label="Primeira página">«</button>
              <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Anterior</button>
              <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Próxima</button>
              <button type="button" disabled={page >= totalPages} onClick={() => setPage(totalPages)} aria-label="Última página">»</button>
            </div>
          </nav>
        )}
      </section>

      {filesModalResult && (
        <SearchFilesModal
          result={filesModalResult}
          onClose={() => setFilesModalResult(null)}
          onAddToQueue={() => setAddModalResult(filesModalResult)}
        />
      )}

      {addModalResult && (
        <SearchAddModal
          result={addModalResult}
          contentType={contentType}
          onClose={() => setAddModalResult(null)}
        />
      )}
    </div>
  );
}
