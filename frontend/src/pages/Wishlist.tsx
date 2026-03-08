import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../contexts/ToastContext';
import { EmptyState } from '../components/EmptyState';
import './Wishlist.css';

type ContentType = 'music' | 'movies' | 'tv';

interface WishlistTerm {
  id: number;
  term: string;
  created_at?: string;
}

export function Wishlist() {
  const [terms, setTerms] = useState<WishlistTerm[]>([]);
  const [pastedLines, setPastedLines] = useState('');
  const [contentType, setContentType] = useState<ContentType>('music');
  const [newTerm, setNewTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const { showToast } = useToast();
  const [addError, setAddError] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchTerms = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/wishlist');
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setTerms(Array.isArray(data) ? data : []);
    } catch (err) {
      setTerms([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    fetch('/api/wishlist', { signal: controller.signal })
      .then((res) => (res.ok ? res.json() : Promise.reject(res)))
      .then((data) => setTerms(Array.isArray(data) ? data : []))
      .catch((err) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setTerms([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const wishlistSseRef = useRef<EventSource | null>(null);
  const [wishlistReconnecting, setWishlistReconnecting] = useState(false);
  const wishlistReconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fetchTermsRef = useRef(fetchTerms);
  fetchTermsRef.current = fetchTerms;
  useEffect(() => {
    let disposed = false;
    const open = () => {
      if (disposed || wishlistSseRef.current) return;
      const es = new EventSource('/api/wishlist/events');
      es.onmessage = () => {
        setWishlistReconnecting(false);
        fetchTermsRef.current();
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

  const showToastMessage = (msg: string) => showToast(msg, 4000);

  const handleAddTerm = async (e: React.FormEvent) => {
    e.preventDefault();
    const term = newTerm.trim();
    if (!term) return;
    setAddError(null);
    try {
      const res = await fetch('/api/wishlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ term }),
      });
      if (!res.ok) {
        const t = await res.text();
        setAddError(t || 'Falha ao adicionar');
        return;
      }
      setNewTerm('');
      await fetchTerms();
      showToastMessage('Termo adicionado.');
    } catch (err) {
      setAddError(err instanceof Error ? err.message : 'Erro');
    }
  };

  const handleRemove = async (id: number) => {
    try {
      const res = await fetch(`/api/wishlist/${id}`, { method: 'DELETE' });
      if (!res.ok) return;
      await fetchTerms();
      showToastMessage('Termo removido.');
    } catch {
      // ignore
    }
  };

  const handleRun = async () => {
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
      const res = await fetch('/api/wishlist/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          term_ids: termIds.length ? termIds : undefined,
          lines: lines.length ? lines : undefined,
          content_type: contentType,
          start_now: true,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        showToastMessage(data.detail || res.statusText || 'Erro ao executar');
        return;
      }
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
  };

  return (
    <div className="atum-wishlist">
      <h1 className="atum-wishlist-title">Wishlist</h1>
      <p className="atum-wishlist-desc">
        Termos salvos e/ou lista colada (um por linha). Use Buscar e adicionar aos downloads para enfileirar o melhor resultado de cada um.
      </p>

      <section className="atum-wishlist-form" aria-labelledby="add-term-heading">
        <h2 id="add-term-heading" className="atum-wishlist-section-title">Adicionar termo</h2>
        <form onSubmit={handleAddTerm} className="atum-wishlist-add-form">
          <input
            type="text"
            value={newTerm}
            onChange={(e) => setNewTerm(e.target.value)}
            placeholder="Ex.: Artist - Album ou Nome do filme"
            className="atum-wishlist-input"
            aria-label="Novo termo"
          />
          <button type="submit" className="atum-btn atum-btn-primary">Adicionar</button>
        </form>
        {addError && <p className="atum-wishlist-error" role="alert">{addError}</p>}
      </section>

      <section className="atum-wishlist-terms" aria-labelledby="terms-heading">
        <h2 id="terms-heading" className="atum-wishlist-section-title">Termos salvos</h2>
        {wishlistReconnecting && <span className="atum-wishlist-reconnecting" aria-live="polite">Reconectando…</span>}
        {loading ? (
          <EmptyState title="Carregando…" description="Buscando termos salvos." />
        ) : terms.length === 0 ? (
          <EmptyState
            title="Nenhum termo salvo"
            description="Adicione um termo acima ou use o campo de lote abaixo para buscar e adicionar aos downloads."
          />
        ) : (
          <ul className="atum-wishlist-list">
            {terms.map((t) => (
              <li key={t.id} className="atum-wishlist-item">
                <span className="atum-wishlist-term-text">{t.term}</span>
                <button
                  type="button"
                  className="atum-btn atum-btn-small"
                  onClick={() => handleRemove(t.id)}
                  aria-label={`Remover ${t.term}`}
                >
                  Remover
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="atum-wishlist-batch" aria-labelledby="batch-heading">
        <h2 id="batch-heading" className="atum-wishlist-section-title">Colar lista (uma busca por linha)</h2>
        <textarea
          value={pastedLines}
          onChange={(e) => setPastedLines(e.target.value)}
          placeholder="Artist - Album"
          className="atum-wishlist-textarea"
          rows={6}
          aria-label="Linhas para busca em lote"
        />
      </section>

      <section className="atum-wishlist-run">
        <span className="atum-wishlist-label">Tipo de conteúdo:</span>
        <div className="atum-wishlist-pills" role="group" aria-label="Tipo de conteúdo">
          {(['music', 'movies', 'tv'] as const).map((t) => (
            <button
              key={t}
              type="button"
              className={`atum-wishlist-pill ${contentType === t ? 'atum-wishlist-pill--active' : ''}`}
              onClick={() => setContentType(t)}
              aria-pressed={contentType === t}
            >
              {t === 'music' ? 'Música' : t === 'movies' ? 'Filmes' : 'Séries'}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="atum-btn atum-btn-primary atum-wishlist-run-btn"
          onClick={handleRun}
          disabled={running}
        >
          {running ? 'Enviando…' : 'Buscar e adicionar aos downloads'}
        </button>
      </section>

    </div>
  );
}
