import { apiGet, apiJson } from './client';

export interface TmdbDetail {
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

export async function getTmdbDetail(
  title: string,
  contentType: 'movies' | 'tv',
  options?: { staleMs?: number; signal?: AbortSignal }
): Promise<TmdbDetail> {
  const params = new URLSearchParams({ title, content_type: contentType });
  return apiGet<TmdbDetail>(`/api/tmdb-detail?${params}`, { staleMs: 600_000, ...options });
}

export interface AddFromSearchParams {
  query: string;
  limit: number;
  sort_by: string;
  content_type: 'music' | 'movies' | 'tv';
  music_category_only: boolean;
  indices: number[];
  start_now?: boolean;
}

export interface AddFromSearchResult {
  added?: unknown[];
  errors?: string[];
}

export async function addFromSearch(params: AddFromSearchParams): Promise<AddFromSearchResult> {
  return apiJson<AddFromSearchResult>('/api/add-from-search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...params, start_now: params.start_now ?? true }),
  });
}
