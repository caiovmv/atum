import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../contexts/ToastContext';
import { useFetch } from './useFetch';
import { getFeeds, getPending, addFeed, removeFeed, pollFeeds, addPendingToDownloads } from '../api/feeds';
import { getAIRecommendations } from '../api/ai';
import { evictCache } from '../api/client';
import type { AIFeedSuggestion } from '../types/feeds';

type ContentType = 'music' | 'movies' | 'tv';

export function useFeeds() {
  const [newUrl, setNewUrl] = useState('');
  const [contentType, setContentType] = useState<ContentType>('music');
  const [polling, setPolling] = useState(false);
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [selectedPending, setSelectedPending] = useState<Set<number>>(new Set());
  const [organize, setOrganize] = useState(false);
  const [addToDownloadsRunning, setAddToDownloadsRunning] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState<AIFeedSuggestion[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiOpen, setAiOpen] = useState(false);
  const [feedsReconnecting, setFeedsReconnecting] = useState(false);

  const navigate = useNavigate();
  const { showToast } = useToast();

  const { data: feedsData, loading, error: fetchError, refetch: refetchFeeds } = useFetch(
    (signal) => getFeeds({ signal }),
    []
  );
  const { data: pendingData, loading: pendingLoading, refetch: refetchPending } = useFetch(
    (signal) => getPending({ signal }),
    []
  );

  const feeds = feedsData ?? [];
  const pending = pendingData ?? [];

  const refetchPendingRef = useRef(refetchPending);
  refetchPendingRef.current = refetchPending;

  useEffect(() => {
    setSelectedPending(new Set());
  }, [pendingData]);

  const feedsSseRef = useRef<EventSource | null>(null);
  const feedsReconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let disposed = false;
    const open = () => {
      if (disposed || feedsSseRef.current) return;
      const es = new EventSource('/api/feeds/events');
      es.onmessage = () => {
        setFeedsReconnecting(false);
        evictCache('/api/feeds');
        refetchPendingRef.current();
      };
      es.onerror = () => {
        setFeedsReconnecting(true);
        es.close();
        feedsSseRef.current = null;
        if (!disposed) {
          feedsReconnectRef.current = setTimeout(() => {
            feedsReconnectRef.current = null;
            if (document.visibilityState === 'visible') open();
          }, 5000);
        }
      };
      feedsSseRef.current = es;
    };
    const close = () => {
      if (feedsSseRef.current) {
        feedsSseRef.current.close();
        feedsSseRef.current = null;
      }
      if (feedsReconnectRef.current) {
        clearTimeout(feedsReconnectRef.current);
        feedsReconnectRef.current = null;
      }
    };
    const onVisibility = () => {
      if (document.visibilityState === 'visible') open();
      else close();
    };
    if (document.visibilityState === 'visible') open();
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      disposed = true;
      document.removeEventListener('visibilitychange', onVisibility);
      close();
    };
  }, []);

  const showToastMessage = (msg: string) => showToast(msg, 4000);

  const fetchAIFeedSuggestions = useCallback(async () => {
    setAiLoading(true);
    setAiOpen(true);
    try {
      const data = await getAIRecommendations('feeds', 5);
      setAiSuggestions(data.feed_suggestions || []);
    } catch {
      showToast('Erro ao buscar sugestões AI', 4000);
      setAiSuggestions([]);
    } finally {
      setAiLoading(false);
    }
  }, [showToast]);

  const addSuggestedFeed = useCallback(
    async (url: string, ct: string) => {
      try {
        await addFeed(url, ct || 'music');
        refetchFeeds();
        showToast('Feed adicionado', 3000);
        setAiSuggestions((prev) => prev.filter((s) => s.url !== url));
      } catch {
        if (import.meta.env.DEV) console.warn('addSuggestedFeed failed');
      }
    },
    [refetchFeeds, showToast]
  );

  const handleAddFeed = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const url = newUrl.trim();
      if (!url) return;
      setAddError(null);
      setAdding(true);
      try {
        await addFeed(url, contentType);
        setNewUrl('');
        refetchFeeds();
        showToastMessage('Feed adicionado.');
      } catch (err) {
        setAddError(err instanceof Error ? err.message : 'Erro');
      } finally {
        setAdding(false);
      }
    },
    [newUrl, contentType, refetchFeeds, showToastMessage]
  );

  const handleRemoveFeed = useCallback(
    async (id: number) => {
      try {
        await removeFeed(id);
        refetchFeeds();
        refetchPending();
        showToastMessage('Feed removido.');
      } catch {
        if (import.meta.env.DEV) console.warn('handleRemoveFeed failed');
      }
    },
    [refetchFeeds, refetchPending, showToastMessage]
  );

  const handlePoll = useCallback(async () => {
    setPolling(true);
    try {
      const data = await pollFeeds();
      const saved = data.saved ?? 0;
      if (saved > 0) {
        showToastMessage(`${saved} novo(s) item(ns) em pendentes.`);
        refetchPending();
      } else if ((data.errors ?? []).length > 0) {
        showToastMessage((data.errors ?? [])[0] || 'Nenhuma novidade.');
      } else {
        showToastMessage('Nenhuma novidade.');
      }
    } catch (err) {
      showToastMessage(err instanceof Error ? err.message : 'Erro de rede');
    } finally {
      setPolling(false);
    }
  }, [showToastMessage, refetchPending]);

  const togglePending = useCallback((id: number) => {
    setSelectedPending((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const selectAllPending = useCallback(() => {
    setSelectedPending((prev) => {
      if (prev.size === pending.length) return new Set();
      return new Set(pending.map((p) => p.id));
    });
  }, [pending]);

  const handleAddToDownloads = useCallback(async () => {
    const ids = Array.from(selectedPending);
    if (ids.length === 0) {
      showToastMessage('Selecione pelo menos um item.');
      return;
    }
    setAddToDownloadsRunning(true);
    try {
      const data = await addPendingToDownloads(ids, organize);
      const ok = data.ok ?? 0;
      const fail = data.fail ?? 0;
      if (ok > 0) {
        showToastMessage(`${ok} item(ns) adicionado(s) aos downloads.`);
        refetchPending();
        navigate('/downloads');
      }
      if (fail > 0) showToastMessage((ok > 0 ? ' ' : '') + `${fail} falha(s).`);
    } catch (err) {
      showToastMessage(err instanceof Error ? err.message : 'Erro de rede');
    } finally {
      setAddToDownloadsRunning(false);
    }
  }, [selectedPending, organize, showToastMessage, refetchPending, navigate]);

  return {
    newUrl,
    setNewUrl,
    contentType,
    setContentType,
    adding,
    addError,
    handleAddFeed,
    feeds,
    loading,
    fetchError,
    refetchFeeds,
    refetchPending,
    handleRemoveFeed,
    polling,
    handlePoll,
    aiSuggestions,
    aiLoading,
    aiOpen,
    fetchAIFeedSuggestions,
    addSuggestedFeed,
    selectedPending,
    togglePending,
    selectAllPending,
    organize,
    setOrganize,
    addToDownloadsRunning,
    handleAddToDownloads,
    pending,
    pendingLoading,
    feedsReconnecting,
  };
}
