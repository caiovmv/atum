import { useState, useEffect, useCallback, useMemo } from 'react';
import { useDownloadsEvents } from '../contexts/DownloadsEventsContext';
import { useToast } from '../contexts/ToastContext';
import { getDownloads, startDownload, stopDownload, deleteDownload, retryDownload } from '../api/downloads';

export interface DownloadRow {
  id: number;
  status: string;
  name?: string;
  save_path?: string;
  content_type?: string;
  progress?: number;
  num_seeds?: number;
  num_peers?: number;
  num_leechers?: number | null;
  total_bytes?: number;
  downloaded_bytes?: number;
  download_speed_bps?: number;
  eta_seconds?: number;
  error_message?: string | null;
}

export function useDownloads() {
  const { downloads: contextDownloads, lastUpdated: contextLastUpdated, refetch: contextRefetch, reconnecting } = useDownloadsEvents();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [removeModalId, setRemoveModalId] = useState<number | null>(null);
  const { showToast } = useToast();

  const rows = useMemo(
    () => (statusFilter ? contextDownloads.filter((d) => d.status === statusFilter) : contextDownloads) as DownloadRow[],
    [contextDownloads, statusFilter]
  );

  const statusCounts = useMemo(
    () => ({
      queued: contextDownloads.filter((d) => d.status === 'queued').length,
      downloading: contextDownloads.filter((d) => d.status === 'downloading').length,
      paused: contextDownloads.filter((d) => d.status === 'paused').length,
      completed: contextDownloads.filter((d) => d.status === 'completed').length,
      failed: contextDownloads.filter((d) => d.status === 'failed').length,
    }),
    [contextDownloads]
  );

  const fetchDownloads = useCallback(
    async (signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        await getDownloads(statusFilter || undefined, { signal });
        if (!signal?.aborted) contextRefetch();
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Erro ao carregar');
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [statusFilter, contextRefetch]
  );

  useEffect(() => {
    const controller = new AbortController();
    fetchDownloads(controller.signal);
    return () => controller.abort();
  }, [fetchDownloads]);

  const showToastMessage = (msg: string) => showToast(msg, 4000);

  const handleStart = useCallback(
    async (id: number) => {
      try {
        await startDownload(id);
        fetchDownloads();
      } catch {
        showToastMessage('Falha ao iniciar. Tente novamente.');
      }
    },
    [fetchDownloads, showToastMessage]
  );

  const handleStop = useCallback(
    async (id: number) => {
      try {
        await stopDownload(id);
        fetchDownloads();
      } catch {
        showToastMessage('Falha ao parar. Tente novamente.');
      }
    },
    [fetchDownloads, showToastMessage]
  );

  const handleRemove = useCallback(
    async (id: number) => {
      setRemoveModalId(null);
      try {
        await deleteDownload(id);
        fetchDownloads();
      } catch {
        showToastMessage('Falha ao remover. Tente novamente.');
      }
    },
    [fetchDownloads, showToastMessage]
  );

  const handleRetry = useCallback(
    async (id: number) => {
      try {
        await retryDownload(id);
        showToastMessage('Download re-enfileirado.');
        fetchDownloads();
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Falha ao tentar novamente.';
        try {
          const parsed = JSON.parse(msg) as { detail?: string };
          showToastMessage(parsed.detail || msg);
        } catch {
          showToastMessage(msg);
        }
      }
    },
    [fetchDownloads, showToastMessage]
  );

  return {
    rows,
    loading,
    error,
    statusFilter,
    setStatusFilter,
    statusCounts,
    lastUpdated: contextLastUpdated,
    reconnecting,
    removeModalId,
    setRemoveModalId,
    fetchDownloads,
    contextRefetch,
    handleStart,
    handleStop,
    handleRemove,
    handleRetry,
  };
}
