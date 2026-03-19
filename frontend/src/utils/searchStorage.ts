/** Utilitários para busca: storage, labels, helpers */

import type { SearchResult } from '../types/search';

export const SEARCH_STORAGE_KEY = 'atum-search-state';

export const INDEXER_LABELS: Record<string, string> = {
  '1337x': '1337x',
  tpb: 'TPB',
  yts: 'YTS',
  eztv: 'EZTV',
  nyaa: 'NYAA',
  limetorrents: 'Limetorrents',
  iptorrents: 'IPTorrents',
};

/** Ordem fixa das fontes no filtro (mesma ordem que a API usa por padrão). */
export const INDEXER_ORDER = ['1337x', 'tpb', 'yts', 'eztv', 'nyaa', 'limetorrents', 'iptorrents'];

export interface StoredSearch {
  query: string;
  contentType: 'music' | 'movies' | 'tv';
  sortBy: 'seeders' | 'size';
  results: SearchResult[];
}

export function loadStoredSearch(): Partial<StoredSearch> | null {
  try {
    const raw = sessionStorage.getItem(SEARCH_STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as StoredSearch;
    if (!data || !Array.isArray(data.results)) return null;
    return {
      query: data.query ?? '',
      contentType: data.contentType ?? 'music',
      sortBy: data.sortBy ?? 'seeders',
      results: data.results,
    };
  } catch {
    return null;
  }
}

export function saveStoredSearch(state: StoredSearch) {
  try {
    sessionStorage.setItem(SEARCH_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // ignore
  }
}

export function indexerLabel(indexer: string | undefined): string {
  if (!indexer) return '—';
  const s = indexer.toLowerCase();
  return INDEXER_LABELS[s] ?? indexer;
}

export function titleMatchesQuery(title: string, searchQuery: string): boolean {
  const words = searchQuery.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return true;
  const t = title.toLowerCase();
  return words.every((w) => t.includes(w));
}

export function normalizeMagnet(m: string | null | undefined): string {
  return (m || '').trim();
}
