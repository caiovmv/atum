import { apiGet, apiJson, apiFormData } from './client';

export interface Playlist {
  id: number;
  name: string;
  cover_path?: string;
  system_kind?: string;
  kind: string;
  description?: string;
  track_count: number;
  created_at: string;
}

export interface PlaylistTrack {
  id: number;
  source: string;
  item_id: number;
  file_index: number;
  file_name?: string;
  item_name?: string;
  artist?: string;
  position: number;
  play_count?: number;
  cover_path_small?: string;
}

export interface PlaylistData extends Playlist {
  rules?: { kind: string; type: string; value: string }[];
  ai_prompt?: string;
  ai_notes?: string;
  tracks: PlaylistTrack[];
}

export async function getPlaylists(
  kind?: string,
  options?: { signal?: AbortSignal }
): Promise<Playlist[]> {
  const url = kind ? `/api/playlists?kind=${encodeURIComponent(kind)}` : '/api/playlists';
  const data = await apiGet<Playlist[]>(url, options);
  return Array.isArray(data) ? data : [];
}

export async function createPlaylist(body: {
  name: string;
  kind?: string;
  rules?: unknown;
  ai_prompt?: string;
  description?: string;
}): Promise<Playlist> {
  return apiJson<Playlist>('/api/playlists', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function getPlaylist(
  id: string,
  options?: { signal?: AbortSignal }
): Promise<PlaylistData> {
  return apiGet<PlaylistData>(`/api/playlists/${id}`, options);
}

export async function updatePlaylist(
  id: number,
  body: { name?: string; description?: string | null; ai_prompt?: string | null }
): Promise<PlaylistData> {
  return apiJson<PlaylistData>(`/api/playlists/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function deletePlaylist(id: number): Promise<void> {
  await apiJson<unknown>(`/api/playlists/${id}`, { method: 'DELETE' });
}

export async function removeTrackFromPlaylist(playlistId: number, trackId: number): Promise<void> {
  await apiJson<unknown>(`/api/playlists/${playlistId}/tracks/${trackId}`, { method: 'DELETE' });
}

export async function uploadPlaylistCover(playlistId: number, file: File): Promise<void> {
  const formData = new FormData();
  formData.append('file', file);
  await apiFormData(`/api/playlists/${playlistId}/cover`, formData);
}

export async function generatePlaylist(id: number): Promise<{ count?: number; tracks?: unknown[] }> {
  return apiJson<{ count?: number; tracks?: unknown[] }>(`/api/playlists/${id}/generate`, { method: 'POST' });
}

export interface AddTrackPayload {
  source: string;
  item_id: number;
  file_index: number;
  file_name?: string;
}

export async function addTrackToPlaylist(playlistId: number, tracks: AddTrackPayload[]): Promise<void> {
  await apiJson<unknown>(`/api/playlists/${playlistId}/tracks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tracks }),
  });
}

export interface AddFromQueuePayload {
  id: number;
  source?: string;
  file_index?: number;
  file_name?: string;
}

export async function addFromQueue(name: string, tracks: AddFromQueuePayload[]): Promise<{ id?: number }> {
  return apiJson<{ id?: number }>('/api/playlists/from-queue', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, tracks }),
  });
}

export async function resetPlayCount(): Promise<{ reset?: number }> {
  return apiJson<{ reset?: number }>('/api/playlists/play-count/reset', { method: 'POST' });
}

export async function incrementPlayCount(body: {
  source: string;
  item_id: number;
  file_index?: number;
}): Promise<{ play_count?: number }> {
  return apiJson<{ play_count?: number }>('/api/playlists/play-count/increment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...body, file_index: body.file_index ?? 0 }),
  });
}

export async function toggleFavorite(body: {
  source: string;
  item_id: number;
  file_index?: number;
  file_name?: string;
}): Promise<{ favorited: boolean }> {
  return apiJson<{ favorited: boolean }>('/api/playlists/favorites/toggle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...body, file_index: body.file_index ?? 0 }),
  });
}
