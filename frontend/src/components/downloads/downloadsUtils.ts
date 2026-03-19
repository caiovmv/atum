import type { DownloadRow } from '../../hooks/useDownloads';

export function formatBytes(bytes?: number): string {
  if (bytes == null || bytes <= 0) return '—';
  if (bytes >= 1_073_741_824) return `${(bytes / 1_073_741_824).toFixed(1)} GB`;
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
}

export function formatSpeed(bps?: number): string {
  if (!bps) return '';
  if (bps >= 1_048_576) return `${(bps / 1_048_576).toFixed(1)} MB/s`;
  return `${(bps / 1024).toFixed(0)} KB/s`;
}

export function formatEta(seconds?: number): string {
  if (!seconds || seconds <= 0) return '';
  if (seconds >= 3600) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  if (seconds >= 60) return `${Math.floor(seconds / 60)}m`;
  return `${seconds}s`;
}

export function resolveContentType(row: DownloadRow): 'music' | 'movies' | 'tv' | 'concerts' {
  const t = row.content_type;
  if (t === 'music' || t === 'movies' || t === 'tv' || t === 'concerts') return t;
  return 'movies';
}
