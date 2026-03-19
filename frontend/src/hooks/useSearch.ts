import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useDebouncedValue } from './useDebouncedValue';
import { getIndexerStatus, getFilterSuggestions, searchTorrents } from '../api/search';
import {
  SEARCH_STORAGE_KEY,
  loadStoredSearch,
  saveStoredSearch,
  INDEXER_ORDER,
  titleMatchesQuery,
} from '../utils/searchStorage';
import type { SearchResult, FilterSuggestions } from '../types/search';

const PAGE_SIZE = 20;

export function useSearch() {
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
  const [indexerProgress, setIndexerProgress] = useState<Record<string, 'pending' | 'loading' | 'done' | 'error'>>({});
  const [indexerCounts, setIndexerCounts] = useState<Record<string, number>>({});
  const [indexersReconnecting, setIndexersReconnecting] = useState(false);
  const searchAbortRef = useRef<AbortController | null>(null);
  const indexersSseRef = useRef<EventSource | null>(null);
  const indexersReconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
    getIndexerStatus({ signal: controller.signal })
      .then((status) => {
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

  const toggleSource = useCallback((key: string) => {
    setPage(1);
    setSourceFilter((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next.size ? next : new Set(enabledIndexers);
    });
  }, [enabledIndexers]);

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
    getFilterSuggestions(
      { content_type: contentType, q: debouncedQuery.trim() },
      { signal: controller.signal }
    )
      .then(setFilterSuggestions)
      .catch((err) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        if (import.meta.env.DEV) console.warn('[Search] filter suggestions fetch failed', err);
      });
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
      const params = { ...baseParams, indexers: indexer };
      searchTorrents(params, { signal })
        .then((data) => {
          if (signal.aborted) return;
          setIndexerProgress((p) => ({ ...p, [indexer]: 'done' }));
          setIndexerCounts((c) => ({ ...c, [indexer]: data.length }));
          setResults((prev) => mergeAndSort(prev, data, sortBy));
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

  const clearFilters = useCallback(() => {
    setYearFilter('');
    setGenreFilter('');
    setQualityFilter('');
    setAudioFilter('');
    setNameFilter('');
    setSourceFilter(new Set(enabledIndexers));
    setPage(1);
  }, [enabledIndexers]);

  const newSearch = useCallback(() => {
    setResults([]);
    setQuery('');
    setPage(1);
    setIndexerProgress({});
    setIndexerCounts({});
    setError(null);
    try {
      sessionStorage.removeItem(SEARCH_STORAGE_KEY);
    } catch {
      // ignore
    }
  }, []);

  return {
    query,
    setQuery,
    contentType,
    setContentType,
    sortBy,
    setSortBy,
    results,
    setResults,
    page,
    setPage,
    loading,
    error,
    indexerStatus,
    sourceFilter,
    setSourceFilter,
    nameFilter,
    setNameFilter,
    onlyRelevant,
    setOnlyRelevant,
    clientSort,
    setClientSort,
    filterSuggestions,
    yearFilter,
    setYearFilter,
    genreFilter,
    setGenreFilter,
    qualityFilter,
    setQualityFilter,
    audioFilter,
    setAudioFilter,
    indexerProgress,
    indexerCounts,
    indexersReconnecting,
    enabledIndexers,
    allIndexersForFilter,
    filteredResults,
    pageResults,
    totalPages,
    start,
    toggleSource,
    handleSearch,
    clearFilters,
    newSearch,
  };
}
