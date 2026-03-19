import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../contexts/ToastContext';
import { useFetch } from './useFetch';
import { getWishlist, addWishlistTerm, removeWishlistTerm, runWishlist } from '../api/wishlist';
import { getAIRecommendations } from '../api/ai';
import { evictCache } from '../api/client';
import type { AISuggestion } from '../types/wishlist';

export type ContentType = 'music' | 'movies' | 'tv';

export function useWishlist() {
  const [pastedLines, setPastedLines] = useState('');
  const [contentType, setContentType] = useState<ContentType>('music');
  const [newTerm, setNewTerm] = useState('');
  const [running, setRunning] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [aiSuggestions, setAiSuggestions] = useState<AISuggestion[]>([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiOpen, setAiOpen] = useState(false);
  const [wishlistReconnecting, setWishlistReconnecting] = useState(false);
  const { showToast } = useToast();
  const navigate = useNavigate();

  const { data: termsData, loading, error: fetchError, refetch: refetchTerms } = useFetch(
    (signal) => getWishlist({ signal }),
    []
  );
  const terms = termsData ?? [];

  const refetchTermsRef = useRef(refetchTerms);
  refetchTermsRef.current = refetchTerms;

  const wishlistSseRef = useRef<EventSource | null>(null);
  const wishlistReconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let disposed = false;
    const open = () => {
      if (disposed || wishlistSseRef.current) return;
      const es = new EventSource('/api/wishlist/events');
      es.onmessage = () => {
        setWishlistReconnecting(false);
        evictCache('/api/wishlist');
        refetchTermsRef.current();
      };
      es.onerror = () => {
        setWishlistReconnecting(true);
        es.close();
        wishlistSseRef.current = null;
        if (!disposed) {
          wishlistReconnectRef.current = setTimeout(() => {
            wishlistReconnectRef.current = null;
            if (document.visibilityState === 'visible') open();
          }, 5000);
        }
      };
      wishlistSseRef.current = es;
    };
    const close = () => {
      if (wishlistSseRef.current) {
        wishlistSseRef.current.close();
        wishlistSseRef.current = null;
      }
      if (wishlistReconnectRef.current) {
        clearTimeout(wishlistReconnectRef.current);
        wishlistReconnectRef.current = null;
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

  const showToastMessage = useCallback((msg: string) => showToast(msg, 4000), [showToast]);

  const fetchAISuggestions = useCallback(async () => {
    setAiLoading(true);
    setAiOpen(true);
    try {
      const data = await getAIRecommendations('wishlist', 10);
      setAiSuggestions(data.wishlist_suggestions || []);
    } catch {
      showToast('Erro ao buscar sugestões AI', 4000);
      setAiSuggestions([]);
    } finally {
      setAiLoading(false);
    }
  }, [showToast]);

  const addSuggestionToWishlist = useCallback(async (term: string) => {
    try {
      await addWishlistTerm(term);
      refetchTerms();
      showToast(`"${term}" adicionado à wishlist`, 3000);
      setAiSuggestions((prev) => prev.filter((s) => s.term !== term));
    } catch {
      if (import.meta.env.DEV) console.warn('addSuggestionToWishlist failed');
    }
  }, [refetchTerms, showToast]);

  const handleAddTerm = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const term = newTerm.trim();
      if (!term) return;
      setAddError(null);
      try {
        await addWishlistTerm(term);
        setNewTerm('');
        refetchTerms();
        showToastMessage('Termo adicionado.');
      } catch (err) {
        setAddError(err instanceof Error ? err.message : 'Erro');
      }
    },
    [newTerm, refetchTerms, showToastMessage]
  );

  const handleRemove = useCallback(
    async (id: number) => {
      try {
        await removeWishlistTerm(id);
        refetchTerms();
        showToastMessage('Termo removido.');
      } catch {
        if (import.meta.env.DEV) console.warn('handleRemove failed');
      }
    },
    [refetchTerms, showToastMessage]
  );

  const handleRun = useCallback(async () => {
    const lines = pastedLines
      .split(/\n/)
      .map((l) => l.trim())
      .filter(Boolean);
    const termIds = terms.map((t) => t.id);
    if (termIds.length === 0 && lines.length === 0) {
      showToastMessage('Adicione termos à lista ou cole linhas no campo de lote.');
      return;
    }
    setRunning(true);
    try {
      const data = await runWishlist({
        term_ids: termIds.length ? termIds : undefined,
        lines: lines.length ? lines : undefined,
        content_type: contentType,
        start_now: true,
      });
      const ok = data.ok ?? 0;
      const fail = data.fail ?? 0;
      if (ok > 0) showToastMessage(`${ok} item(ns) adicionado(s) aos downloads.`);
      if (fail > 0) showToastMessage((ok > 0 ? ' ' : '') + `${fail} falha(s).`);
      if (ok > 0) navigate('/downloads');
    } catch (err) {
      showToastMessage(err instanceof Error ? err.message : 'Erro de rede');
    } finally {
      setRunning(false);
    }
  }, [pastedLines, terms, contentType, showToastMessage, navigate]);

  return {
    pastedLines,
    setPastedLines,
    contentType,
    setContentType,
    newTerm,
    setNewTerm,
    running,
    addError,
    aiSuggestions,
    aiLoading,
    aiOpen,
    terms,
    loading,
    fetchError,
    wishlistReconnecting,
    refetchTerms,
    fetchAISuggestions,
    addSuggestionToWishlist,
    handleAddTerm,
    handleRemove,
    handleRun,
  };
}
