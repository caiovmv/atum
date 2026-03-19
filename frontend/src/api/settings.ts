import { apiGet, apiJson, evictCache } from './client';

export interface SettingsData {
  [key: string]: unknown;
}

export interface EnrichmentStats {
  total: number;
  enriched: number;
  errors: number;
  pending: number;
}

export async function getSettings(
  options?: { staleMs?: number; signal?: AbortSignal }
): Promise<SettingsData> {
  const data = await apiGet<SettingsData>('/api/settings', { staleMs: 60_000, ...options });
  return data ?? {};
}

export async function getEnrichmentStats(
  options?: { staleMs?: number; signal?: AbortSignal }
): Promise<EnrichmentStats | null> {
  try {
    return await apiGet<EnrichmentStats>('/api/settings/enrichment-stats', { staleMs: 120_000, ...options });
  } catch {
    return null;
  }
}

export async function saveSettings(settings: Record<string, unknown>): Promise<SettingsData> {
  const data = await apiJson<SettingsData>('/api/settings', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ settings }),
  });
  evictCache('/api/settings');
  return data ?? {};
}

export async function testConnection(
  service: string,
  params: Record<string, string>
): Promise<{ ok: boolean; message?: string; error?: string }> {
  return apiJson<{ ok: boolean; message?: string; error?: string }>('/api/settings/test-connection', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service, ...params }),
  });
}

export interface ReorganizeResult {
  processed: number;
  skipped?: number;
  errors?: number;
  cleaned?: number;
  dry_run?: boolean;
  details?: string[];
}

export async function reorganizeLibrary(dryRun = false): Promise<ReorganizeResult> {
  const params = dryRun ? '?dry_run=true' : '';
  return apiJson<ReorganizeResult>(`/api/settings/reorganize-library${params}`, { method: 'POST' });
}
