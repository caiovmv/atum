import { apiGet } from './client';

export async function getCover(params: {
  content_type?: string;
  title?: string;
  size?: 'small' | 'large';
  download_id?: number;
  import_id?: number;
}, options?: { staleMs?: number; signal?: AbortSignal }): Promise<{ url?: string | null } | null> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== '' && v !== null) {
      searchParams.set(k, String(v));
    }
  });
  try {
    return await apiGet<{ url?: string | null }>(`/api/cover?${searchParams}`, { staleMs: 300_000, ...options });
  } catch {
    return null;
  }
}
