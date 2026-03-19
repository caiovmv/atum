import { apiGet, apiJson, evictCache } from './client';
import type { LibraryItem } from '../types/library';

export interface LibraryParams {
  content_type?: string;
  limit?: number;
  offset?: number;
  search?: string;
  q?: string;
  artist?: string;
  album?: string;
  genre?: string;
  tag?: string[];
  mood?: string;
  sub_genre?: string;
  descriptor?: string;
  folder_path?: string;
  year?: number;
  quality?: string;
  audio?: string;
}

export interface LibraryFolder {
  path: string;
  name: string;
  count: number;
}

export async function getLibrary(
  params: LibraryParams,
  options?: { staleMs?: number; signal?: AbortSignal }
): Promise<LibraryItem[]> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== '' && v !== null) {
      if (Array.isArray(v)) {
        v.forEach((x) => searchParams.append(k, String(x)));
      } else {
        searchParams.set(k, String(v));
      }
    }
  });
  const data = await apiGet<LibraryItem[]>(`/api/library?${searchParams}`, options);
  return Array.isArray(data) ? data : [];
}

export interface LibraryItemDetail {
  id: number;
  name?: string;
  content_type?: string;
  source?: string;
  [key: string]: unknown;
}

export interface LibraryItemDetailFull extends LibraryItemDetail {
  folder_stats?: { path: string; parent: string; created_at: number; modified_at: number };
  files?: { files?: LibraryFile[] };
  metadata_json?: Record<string, unknown>;
  cover_source?: string;
  user_edited_at?: string;
}

export interface LibraryFile {
  index: number;
  name: string;
  size: number;
}

export async function getLibraryItem(
  id: number,
  isImport: boolean,
  options?: { signal?: AbortSignal }
): Promise<LibraryItemDetail> {
  const url = isImport ? `/api/library/imported/${id}` : `/api/library/${id}`;
  return apiGet<LibraryItemDetail>(url, options);
}

export async function getLibraryItemFiles(
  id: number,
  isImport: boolean,
  options?: { signal?: AbortSignal }
): Promise<{ files: LibraryFile[] }> {
  const url = isImport ? `/api/library/imported/${id}/files` : `/api/library/${id}/files`;
  const data = await apiGet<{ files?: LibraryFile[] }>(url, options);
  return { files: Array.isArray(data?.files) ? data.files : [] };
}

export async function getLibraryItemDetail(
  importId: number,
  options?: { signal?: AbortSignal }
): Promise<LibraryItemDetailFull> {
  return apiGet<LibraryItemDetailFull>(`/api/library/imported/${importId}/detail`, options);
}

export async function getLibraryFacets(
  contentType: string,
  options?: { staleMs?: number; signal?: AbortSignal }
): Promise<Record<string, string[]>> {
  return apiGet<Record<string, string[]>>(
    `/api/library/facets?content_type=${encodeURIComponent(contentType)}`,
    { staleMs: 300_000, ...options }
  );
}

export async function getLibraryFolders(
  contentType: string,
  options?: { staleMs?: number; signal?: AbortSignal }
): Promise<LibraryFolder[]> {
  const data = await apiGet<{ folders?: LibraryFolder[] }>(
    `/api/library/folders?content_type=${encodeURIComponent(contentType)}`,
    { staleMs: 60_000, ...options }
  );
  return Array.isArray(data?.folders) ? data.folders : [];
}

export interface AutocompleteSuggestion {
  type: 'artist' | 'album' | 'title' | 'genre';
  value: string;
  count?: number;
}

export async function getLibraryAutocomplete(
  q: string,
  contentType: string,
  options?: { limit?: number; signal?: AbortSignal }
): Promise<AutocompleteSuggestion[]> {
  if (!q.trim()) return [];
  const params = new URLSearchParams({
    q: q.trim(),
    content_type: contentType,
    limit: String(options?.limit ?? 10),
  });
  const data = await apiGet<{ suggestions?: AutocompleteSuggestion[] }>(
    `/api/library/autocomplete?${params}`,
    { ...options }
  );
  return Array.isArray(data?.suggestions) ? data.suggestions : [];
}

export async function refreshCover(
  itemId: number,
  isImport: boolean,
  query?: string
): Promise<{ ok: boolean; message?: string }> {
  const url = isImport
    ? `/api/library/imported/${itemId}/refresh-cover`
    : `/api/library/${itemId}/refresh-cover`;
  try {
    const data = await apiJson<{ ok?: boolean; message?: string }>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query || undefined }),
    });
    return {
      ok: data?.ok ?? false,
      message: data?.ok ? 'Capa atualizada com sucesso!' : (data?.message || 'Nenhuma capa encontrada para esse termo.'),
    };
  } catch {
    return { ok: false, message: 'Erro ao buscar capa.' };
  }
}

export async function updateImportedItem(
  id: number,
  body: { name?: string; year?: number; artist?: string; album?: string; genre?: string; tags?: string[] }
): Promise<LibraryItem> {
  return apiJson<LibraryItem>(`/api/library/imported/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function uploadImportedCover(
  importId: number,
  file: File
): Promise<{ ok: boolean; cover_path_small?: string; cover_path_large?: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`/api/library/imported/${importId}/cover-upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Erro ao enviar capa.');
  }
  return res.json();
}

export { evictCache };
