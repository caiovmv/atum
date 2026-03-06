import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../contexts/ToastContext';
import { EmptyState } from '../components/EmptyState';
import './Feeds.css';

type ContentType = 'music' | 'movies' | 'tv';

interface Feed {
  id: number;
  url: string;
  title?: string;
  content_type: string;
  created_at?: string;
}

interface PendingItem {
  id: number;
  feed_id: number;
  entry_id: string;
  title: string;
  link: string | null;
  quality_label: string;
  created_at?: string;
  content_type?: string;
}

export function Feeds() {
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [pending, setPending] = useState<PendingItem[]>([]);
  const [newUrl, setNewUrl] = useState('');
  const [contentType, setContentType] = useState<ContentType>('music');
  const [loading, setLoading] = useState(true);
  const [pendingLoading, setPendingLoading] = useState(true);
  const [polling, setPolling] = useState(false);
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const { showToast } = useToast();
  const [selectedPending, setSelectedPending] = useState<Set<number>>(new Set());
  const [organize, setOrganize] = useState(false);
  const [addToDownloadsRunning, setAddToDownloadsRunning] = useState(false);
  const navigate = useNavigate();

  const fetchFeeds = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/feeds');
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setFeeds(Array.isArray(data) ? data : []);
    } catch {
      setFeeds([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchPending = useCallback(async () => {
    setPendingLoading(true);
    try {
      const res = await fetch('/api/feeds/pending');
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setPending(Array.isArray(data) ? data : []);
      setSelectedPending(new Set());
    } catch {
      setPending([]);
    } finally {
      setPendingLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFeeds();
  }, [fetchFeeds]);

  useEffect(() => {
    fetchPending();
  }, [fetchPending]);

  const feedsSseRef = useRef<EventSource | null>(null);
  const [feedsReconnecting, setFeedsReconnecting] = useState(false);
  useEffect(() => {
    const open = () => {
      if (feedsSseRef.current) return;
      const es = new EventSource('/api/feeds/events');
      es.onmessage = () => {
        setFeedsReconnecting(false);
        fetchPending();
      };
      es.onerror = () => {
        setFeedsReconnecting(true);
        es.close();
      };
      feedsSseRef.current = es;
    };
    const close = () => {
      if (feedsSseRef.current) {
        feedsSseRef.current.close();
        feedsSseRef.current = null;
      }
    };
    const onVisibility = () => {
      if (document.visibilityState === 'visible') open();
      else close();
    };
    if (document.visibilityState === 'visible') open();
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      close();
    };
  }, [fetchPending]);

  const showToastMessage = (msg: string) => showToast(msg, 4000);

  const handleAddFeed = async (e: React.FormEvent) => {
    e.preventDefault();
    const url = newUrl.trim();
    if (!url) return;
    setAddError(null);
    setAdding(true);
    try {
      const res = await fetch('/api/feeds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, content_type: contentType }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setAddError(data.detail || res.statusText || 'Falha ao adicionar');
        return;
      }
      setNewUrl('');
      await fetchFeeds();
      showToastMessage('Feed adicionado.');
    } catch (err) {
      setAddError(err instanceof Error ? err.message : 'Erro');
    } finally {
      setAdding(false);
    }
  };

  const handleRemoveFeed = async (id: number) => {
    try {
      const res = await fetch(`/api/feeds/${id}`, { method: 'DELETE' });
      if (!res.ok) return;
      await fetchFeeds();
      await fetchPending();
      showToastMessage('Feed removido.');
    } catch {
      // ignore
    }
  };

  const handlePoll = async () => {
    setPolling(true);
    try {
      const res = await fetch('/api/feeds/poll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        showToastMessage(data.detail || res.statusText || 'Erro ao verificar');
        return;
      }
      const saved = data.saved ?? 0;
      if (saved > 0) {
        showToastMessage(`${saved} novo(s) item(ns) em pendentes.`);
        await fetchPending();
      } else if ((data.errors || []).length > 0) {
        showToastMessage(data.errors[0] || 'Nenhuma novidade.');
      } else {
        showToastMessage('Nenhuma novidade.');
      }
    } catch (err) {
      showToastMessage(err instanceof Error ? err.message : 'Erro de rede');
    } finally {
      setPolling(false);
    }
  };

  const togglePending = (id: number) => {
    setSelectedPending((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAllPending = () => {
    if (selectedPending.size === pending.length) {
      setSelectedPending(new Set());
    } else {
      setSelectedPending(new Set(pending.map((p) => p.id)));
    }
  };

  const handleAddToDownloads = async () => {
    const ids = Array.from(selectedPending);
    if (ids.length === 0) {
      showToastMessage('Selecione pelo menos um item.');
      return;
    }
    setAddToDownloadsRunning(true);
    try {
      const res = await fetch('/api/feeds/pending/add-to-downloads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pending_ids: ids, organize }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        showToastMessage(data.detail || res.statusText || 'Erro');
        return;
      }
      const ok = data.ok ?? 0;
      const fail = data.fail ?? 0;
      if (ok > 0) {
        showToastMessage(`${ok} item(ns) adicionado(s) aos downloads.`);
        await fetchPending();
        navigate('/downloads');
      }
      if (fail > 0) showToastMessage((ok > 0 ? ' ' : '') + `${fail} falha(s).`);
    } catch (err) {
      showToastMessage(err instanceof Error ? err.message : 'Erro de rede');
    } finally {
      setAddToDownloadsRunning(false);
    }
  };

  return (
    <div className="atum-feeds">
      <h1 className="atum-feeds-title">Feeds</h1>
      <p className="atum-feeds-desc">
        Inscreva feeds RSS (música, filmes, séries). Verifique para ver novidades e adicione aos pendentes; depois escolha o que baixar.
      </p>

      <section className="atum-feeds-form" aria-labelledby="add-feed-heading">
        <h2 id="add-feed-heading" className="atum-feeds-section-title">Adicionar feed</h2>
        <form onSubmit={handleAddFeed} className="atum-feeds-add-form">
          <input
            type="url"
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            placeholder="https://…"
            className="atum-feeds-input"
            aria-label="URL do feed RSS"
          />
          <div className="atum-feeds-pills" role="group" aria-label="Tipo de conteúdo">
            {(['music', 'movies', 'tv'] as const).map((t) => (
              <button
                key={t}
                type="button"
                className={`atum-feeds-pill ${contentType === t ? 'atum-feeds-pill--active' : ''}`}
                onClick={() => setContentType(t)}
                aria-pressed={contentType === t}
              >
                {t === 'music' ? 'Música' : t === 'movies' ? 'Filmes' : 'Séries'}
              </button>
            ))}
          </div>
          <button type="submit" className="atum-btn atum-btn-primary" disabled={adding}>
            {adding ? 'Adicionando…' : 'Adicionar'}
          </button>
        </form>
        {addError && <p className="atum-feeds-error" role="alert">{addError}</p>}
      </section>

      <section className="atum-feeds-list-section" aria-labelledby="feeds-list-heading">
        <h2 id="feeds-list-heading" className="atum-feeds-section-title">Feeds inscritos</h2>
        {loading ? (
          <EmptyState title="Carregando…" description="Buscando feeds." />
        ) : feeds.length === 0 ? (
          <EmptyState
            title="Nenhum feed"
            description="Adicione uma URL de feed RSS acima para receber novidades."
          />
        ) : (
          <ul className="atum-feeds-ul">
            {feeds.map((f) => (
              <li key={f.id} className="atum-feeds-item">
                <div className="atum-feeds-item-info">
                  <span className="atum-feeds-item-url">{f.url}</span>
                  {f.title && <span> — {f.title}</span>}
                  <span className="atum-feeds-item-badge">{(f.content_type || 'music')}</span>
                </div>
                <button
                  type="button"
                  className="atum-btn atum-btn-small"
                  onClick={() => handleRemoveFeed(f.id)}
                  aria-label={`Remover feed ${f.url}`}
                >
                  Remover
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="atum-feeds-actions">
        <button
          type="button"
          className="atum-btn atum-btn-primary"
          onClick={handlePoll}
          disabled={polling || feeds.length === 0}
        >
          {polling ? 'Verificando…' : 'Verificar feeds agora'}
        </button>
      </section>

      <section className="atum-feeds-pending-section" aria-labelledby="pending-heading">
        <h2 id="pending-heading" className="atum-feeds-section-title">Itens pendentes</h2>
        {feedsReconnecting && <span className="atum-feeds-reconnecting" aria-live="polite">Reconectando…</span>}
        {pendingLoading ? (
          <EmptyState title="Carregando…" description="Buscando itens pendentes." />
        ) : pending.length === 0 ? (
          <EmptyState
            title="Nenhum item pendente"
            description="Use &quot;Verificar feeds agora&quot; para buscar novidades."
          />
        ) : (
          <>
            <div style={{ marginBottom: '0.5rem' }}>
              <label>
                <input
                  type="checkbox"
                  checked={selectedPending.size === pending.length && pending.length > 0}
                  onChange={selectAllPending}
                />
                {' '}Selecionar todos
              </label>
              <label style={{ marginLeft: '1rem' }}>
                <input
                  type="checkbox"
                  checked={organize}
                  onChange={(e) => setOrganize(e.target.checked)}
                />
                {' '}Organizar em subpastas
              </label>
            </div>
            <ul className="atum-feeds-ul">
              {pending.map((p) => (
                <li key={p.id} className="atum-feeds-pending-item">
                  <input
                    type="checkbox"
                    checked={selectedPending.has(p.id)}
                    onChange={() => togglePending(p.id)}
                    aria-label={`Selecionar ${p.title}`}
                  />
                  <div className="atum-feeds-pending-label">
                    <span>{p.title || '(sem título)'}</span>
                    <span className="atum-feeds-pending-quality"> [{p.quality_label || '?'}]</span>
                  </div>
                </li>
              ))}
            </ul>
            <button
              type="button"
              className="atum-btn atum-btn-primary"
              onClick={handleAddToDownloads}
              disabled={addToDownloadsRunning || selectedPending.size === 0}
              style={{ marginTop: '0.75rem' }}
            >
              {addToDownloadsRunning ? 'Enviando…' : 'Adicionar selecionados aos downloads'}
            </button>
          </>
        )}
      </section>

    </div>
  );
}
