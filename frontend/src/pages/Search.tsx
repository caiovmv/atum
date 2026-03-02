import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { CoverImage } from '../components/CoverImage';
import './Search.css';

const SEARCH_STORAGE_KEY = 'atum-search-state';
const PAGE_SIZE = 20;
const SOURCES = ['1337x', 'tpb', 'tg'] as const;
type SourceKey = (typeof SOURCES)[number];

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

function indexerLabel(indexer: string | undefined): string {
  if (!indexer) return '—';
  const s = indexer.toLowerCase();
  if (s === '1337x') return '1337x';
  if (s === 'tpb') return 'TPB';
  if (s === 'tg') return 'TorrentGalaxy';
  return indexer;
}

function indexerToKey(indexer: string | undefined): SourceKey | null {
  if (!indexer) return null;
  const s = indexer.toLowerCase();
  if (s === '1337x') return '1337x';
  if (s === 'tpb') return 'tpb';
  if (s === 'tg') return 'tg';
  return null;
}

function titleMatchesQuery(title: string, searchQuery: string): boolean {
  const words = searchQuery.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return true;
  const t = title.toLowerCase();
  return words.every((w) => t.includes(w));
}

export function Search() {
  const [query, setQuery] = useState('');
  const [contentType, setContentType] = useState<'music' | 'movies' | 'tv'>('music');
  const [sortBy, setSortBy] = useState<'seeders' | 'size'>('seeders');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState<number[]>([]);
  const [sourceFilter, setSourceFilter] = useState<Set<SourceKey>>(new Set(SOURCES));
  const [nameFilter, setNameFilter] = useState('');
  const [onlyRelevant, setOnlyRelevant] = useState(true);
  const [clientSort, setClientSort] = useState<'seeders' | 'size' | 'quality'>('seeders');
  const [filterSuggestions, setFilterSuggestions] = useState<FilterSuggestions>({ years: [], genres: [], qualities: [] });
  const [yearFilter, setYearFilter] = useState<number | ''>('');
  const [genreFilter, setGenreFilter] = useState('');
  const [qualityFilter, setQualityFilter] = useState('');
  const [audioFilter, setAudioFilter] = useState('');
  const [toast, setToast] = useState<string | null>(null);
  const navigate = useNavigate();
  const searchAbortRef = useRef<AbortController | null>(null);

  const filteredResults = useMemo(() => {
    let list = results.map((r, i) => ({ r, originalIndex: i }));
    const q = query.trim();
    if (onlyRelevant && q) {
      list = list.filter(({ r }) => titleMatchesQuery(r.title, q));
    }
    const src = sourceFilter;
    if (src.size < SOURCES.length) {
      list = list.filter(({ r }) => {
        const k = indexerToKey(r.indexer);
        return k != null && src.has(k);
      });
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

  function toggleSource(key: SourceKey) {
    setPage(1);
    setSourceFilter((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next.size ? next : new Set(SOURCES);
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
    if (!query.trim() || results.length === 0) return;
    const params = new URLSearchParams({ q: query.trim(), content_type: contentType });
    fetch(`/api/search-filter-suggestions?${params}`)
      .then((res) => (res.ok ? res.json() : { years: [], genres: [], qualities: [] }))
      .then((data: FilterSuggestions) => setFilterSuggestions(data))
      .catch(() => {});
  }, [query, contentType, results.length]);

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    searchAbortRef.current?.abort();
    searchAbortRef.current = new AbortController();
    const signal = searchAbortRef.current.signal;
    setLoading(true);
    setError(null);
    setYearFilter('');
    setGenreFilter('');
    setQualityFilter('');
    setAudioFilter('');
    const params = new URLSearchParams({
      q: query.trim(),
      limit: '1000',
      sort_by: sortBy,
      content_type: contentType,
      music_category_only: contentType === 'music' ? 'true' : 'false',
    });
    fetch(`/api/search?${params}`, { signal })
      .then((res) => {
        if (!res.ok) throw new Error(res.statusText);
        return res.json();
      })
      .then((data) => {
        if (signal.aborted) return;
        setResults(data);
        setPage(1);
        saveStoredSearch({ query: query.trim(), contentType, sortBy, results: data });
      })
      .catch((err) => {
        if (err?.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Erro na busca');
        setResults([]);
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false);
      });
  }, [query, sortBy, contentType]);

  useEffect(() => {
    return () => { searchAbortRef.current?.abort(); };
  }, []);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 4000);
  }

  async function addToQueue(indices: number[]) {
    if (results.length === 0) return;
    setAdding(indices);
    try {
      const res = await fetch('/api/add-from-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          limit: 1000,
          sort_by: sortBy,
          content_type: contentType,
          music_category_only: contentType === 'music',
          indices,
          start_now: true,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      if (data.errors?.length) {
        showToast('Alguns falharam: ' + data.errors.join('; '));
      }
      if (data.added?.length) {
        navigate('/downloads');
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Erro ao adicionar');
    } finally {
      setAdding([]);
    }
  }

  return (
    <div className="atum-page search-page">
      <h1 className="atum-page-title">Busca</h1>
      {toast && (
        <div className="search-toast" role="alert" aria-live="polite">
          {toast}
          <button type="button" className="search-toast-dismiss" onClick={() => setToast(null)} aria-label="Fechar">×</button>
        </div>
      )}
      <form onSubmit={handleSearch} className="search-form" role="search" aria-label="Buscar torrents">
        <input
          type="text"
          placeholder="Artista, álbum, filme, série…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="search-input"
          aria-describedby={error ? 'search-error' : undefined}
          aria-busy={loading}
        />
        <select value={contentType} onChange={(e) => setContentType(e.target.value as 'music' | 'movies' | 'tv')}>
          <option value="music">Música</option>
          <option value="movies">Filmes</option>
          <option value="tv">Séries</option>
        </select>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value as 'seeders' | 'size')}>
          <option value="seeders">Seeders</option>
          <option value="size">Tamanho</option>
        </select>
        <button type="submit" className="primary" disabled={loading} aria-busy={loading}>
          {loading ? 'Buscando…' : 'Buscar'}
        </button>
      </form>
      {error && <p id="search-error" className="search-error" role="alert">{error}</p>}
      <section className="results-section" aria-live="polite" aria-busy={loading}>
        {results.length > 0 && (
          <>
            <div className="results-filters">
              <div className="filter-row">
                <span className="filter-label">Fonte:</span>
                {SOURCES.map((key) => (
                  <label key={key} className="filter-check">
                    <input
                      type="checkbox"
                      checked={sourceFilter.has(key)}
                      onChange={() => toggleSource(key)}
                    />
                    {indexerLabel(key)}
                  </label>
                ))}
              </div>
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
              <div className="filter-row">
                <span className="filter-label">Ordenar:</span>
                <select value={clientSort} onChange={(e) => { setClientSort(e.target.value as typeof clientSort); setPage(1); }}>
                  <option value="seeders">Se/Le</option>
                  <option value="size">Tamanho</option>
                  <option value="quality">Qualidade</option>
                </select>
              </div>
            </div>
            <p className="results-meta">
              {filteredResults.length} resultado(s){filteredResults.length !== results.length && ` (de ${results.length})`}
              <button type="button" className="clear-search-btn" onClick={() => { setYearFilter(''); setGenreFilter(''); setQualityFilter(''); setAudioFilter(''); setNameFilter(''); setSourceFilter(new Set(SOURCES)); setPage(1); }}>
                Limpar filtros
              </button>
              <button type="button" className="clear-search-btn" onClick={() => { setResults([]); setQuery(''); setPage(1); try { sessionStorage.removeItem(SEARCH_STORAGE_KEY); } catch { /* ignore */ } }}>
                Nova busca
              </button>
            </p>
          </>
        )}
        {results.length > 0 && filteredResults.length === 0 && (
          <p className="search-empty" role="status">Nenhum resultado para &quot;{query.trim()}&quot; com os filtros atuais. Tente limpar filtros ou alterar a busca.</p>
        )}
        <div className="results-grid">
          {pageResults.map(({ r, originalIndex }, idx) => (
            <div key={`${r.indexer}-${r.torrent_id}-${start + idx}`} className="result-card">
              {(contentType === 'movies' || contentType === 'tv') ? (
                <button
                  type="button"
                  className="result-card-clickable"
                  onClick={() => navigate('/detail', {
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
                  })}
                  aria-label={`Ver detalhes de ${r.title}`}
                >
                  <CoverImage contentType={contentType} title={r.title} size="card" />
                  <span className="result-source">{indexerLabel(r.indexer)}</span>
                  <div className="result-title">{r.title}</div>
                </button>
              ) : (
                <>
                  <CoverImage contentType={contentType} title={r.title} size="card" />
                  <span className="result-source">{indexerLabel(r.indexer)}</span>
                  <div className="result-title">{r.title}</div>
                </>
              )}
              <div className="result-meta">
                <span>{r.quality_label}</span>
                {r.parsed_year != null && <span>{r.parsed_year}</span>}
                {r.parsed_audio_codec && <span>{r.parsed_audio_codec}</span>}
                {r.parsed_music_quality && <span>{r.parsed_music_quality}</span>}
                <span>Se: {r.seeders} Le: {r.leechers}</span>
                <span>{r.size}</span>
              </div>
              <button
                type="button"
                className="primary add-btn"
                disabled={adding.includes(originalIndex)}
                onClick={() => addToQueue([originalIndex])}
                aria-label={adding.includes(originalIndex) ? 'Adicionando à fila…' : `Adicionar ${r.title} à fila`}
              >
                {adding.includes(originalIndex) ? '…' : 'Adicionar'}
              </button>
            </div>
          ))}
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
    </div>
  );
}
