import { apiGet, apiJson } from './client';

export interface Download {
  id: number;
  status: string;
  name?: string;
  progress?: number;
  content_type?: string;
  [key: string]: unknown;
}

export async function getDownloads(
  status?: string,
  options?: { signal?: AbortSignal; staleMs?: number }
): Promise<Download[]> {
  const url = status ? `/api/downloads?status=${encodeURIComponent(status)}` : '/api/downloads';
  try {
    const data = await apiGet<Download[]>(url, { staleMs: 5000, ...options });
    return Array.isArray(data) ? data : [];
  } catch (e) {
    if (e instanceof Error && e.message.includes('503')) {
      throw new Error('Runner não configurado. Inicie: dl-torrent runner');
    }
    throw e;
  }
}

export async function startDownload(id: number): Promise<void> {
  await apiJson<unknown>(`/api/downloads/${id}/start`, { method: 'POST' });
}

export async function stopDownload(id: number): Promise<void> {
  await apiJson<unknown>(`/api/downloads/${id}/stop`, { method: 'POST' });
}

export async function deleteDownload(id: number): Promise<void> {
  await apiJson<unknown>(`/api/downloads/${id}`, { method: 'DELETE' });
}

export async function retryDownload(id: number): Promise<void> {
  await apiJson<unknown>(`/api/downloads/${id}/retry`, { method: 'POST' });
}

export interface CreateDownloadBody {
  magnet?: string | null;
  torrent_url?: string | null;
  name?: string | null;
  content_type?: string;
  start_now?: boolean;
  save_path?: string | null;
  excluded_file_indices?: number[];
  torrent_files?: Array<{ index: number; path: string; size: number }>;
}

export async function createDownload(body: CreateDownloadBody): Promise<Download> {
  const res = await apiJson<Download>('/api/downloads', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res;
}
