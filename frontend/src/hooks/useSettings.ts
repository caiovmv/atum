import { useState, useEffect, useCallback } from 'react';
import { useFetch } from './useFetch';
import { getSettings, getEnrichmentStats, saveSettings, testConnection, reorganizeLibrary } from '../api/settings';
import type { SettingsData, EnrichmentStats } from '../api/settings';

export interface TestResult {
  ok: boolean;
  message?: string;
  error?: string;
}

export interface ReorganizeResult {
  processed: number;
  skipped: number;
  errors: number;
  dry_run: boolean;
  details: string[];
}

export function useSettings() {
  const { data: fetchData, loading, error: fetchError, refetch } = useFetch(
    async (signal) => {
      const [settingsData, statsData] = await Promise.all([
        getSettings({ signal }),
        getEnrichmentStats({ signal }),
      ]);
      return { settings: settingsData, enrichmentStats: statsData };
    },
    []
  );
  const [settings, setSettings] = useState<SettingsData>({});
  const [enrichmentStats, setEnrichmentStats] = useState<EnrichmentStats | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [dirty, setDirty] = useState<SettingsData>({});
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [testing, setTesting] = useState<Record<string, boolean>>({});
  const [reorganizing, setReorganizing] = useState(false);
  const [reorganizeResult, setReorganizeResult] = useState<ReorganizeResult | null>(null);

  useEffect(() => {
    if (fetchData) {
      setSettings(fetchData.settings ?? {});
      setEnrichmentStats(fetchData.enrichmentStats ?? null);
    }
  }, [fetchData]);

  const val = useCallback((key: string): string => {
    if (key in dirty) return String(dirty[key] ?? '');
    return String(settings[key] ?? '');
  }, [dirty, settings]);

  const boolVal = useCallback((key: string): boolean => {
    if (key in dirty) return Boolean(dirty[key]);
    return Boolean(settings[key]);
  }, [dirty, settings]);

  const set = useCallback((key: string, value: unknown) => {
    setDirty((prev) => ({ ...prev, [key]: value }));
  }, []);

  const save = useCallback(async () => {
    if (Object.keys(dirty).length === 0) return;
    setSaving(true);
    try {
      const data = await saveSettings(dirty);
      setSettings(data);
      setDirty({});
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch {
      if (import.meta.env.DEV) console.warn('[Settings] save failed');
    } finally {
      setSaving(false);
    }
  }, [dirty]);

  const handleTestConnection = useCallback(async (service: string, params: Record<string, string>) => {
    setTesting((prev) => ({ ...prev, [service]: true }));
    setTestResults((prev) => {
      const copy = { ...prev };
      delete copy[service];
      return copy;
    });
    try {
      const data = await testConnection(service, params);
      setTestResults((prev) => ({ ...prev, [service]: data }));
    } catch {
      setTestResults((prev) => ({ ...prev, [service]: { ok: false, error: 'Erro de rede' } }));
    } finally {
      setTesting((prev) => ({ ...prev, [service]: false }));
    }
  }, []);

  const handleReorganize = useCallback(async (dryRun: boolean) => {
    setReorganizing(true);
    setReorganizeResult(null);
    try {
      const data = await reorganizeLibrary(dryRun);
      setReorganizeResult(data as ReorganizeResult);
    } catch {
      if (import.meta.env.DEV) console.warn('[Settings] reorganize failed');
    } finally {
      setReorganizing(false);
    }
  }, []);

  const hasDirty = Object.keys(dirty).length > 0;

  const discard = useCallback(() => {
    setDirty({});
    refetch();
  }, [refetch]);

  return {
    settings,
    loading,
    fetchError,
    refetch,
    val,
    boolVal,
    set,
    save,
    saving,
    saved,
    dirty,
    hasDirty,
    testResults,
    testing,
    handleTestConnection,
    enrichmentStats,
    reorganizing,
    reorganizeResult,
    handleReorganize,
    discard,
  };
}
