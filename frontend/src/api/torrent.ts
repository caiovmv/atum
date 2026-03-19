/**
 * API de metadados de torrent.
 */
import { apiJson } from './client';

export interface TorrentFile {
  index: number;
  path: string;
  size: number;
}

export interface TorrentMetadata {
  name?: string;
  files: TorrentFile[];
}

export async function getTorrentMetadata(body: {
  magnet?: string | null;
  torrent_url?: string | null;
}): Promise<TorrentMetadata> {
  const data = await apiJson<{ name?: string; files?: TorrentFile[] }>('/api/torrent/metadata', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ magnet: body.magnet ?? null, torrent_url: body.torrent_url ?? null }),
  });
  return {
    name: data?.name,
    files: Array.isArray(data?.files) ? data.files : [],
  };
}
