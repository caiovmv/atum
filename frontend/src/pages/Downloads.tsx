import { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useDownloadsEvents } from '../contexts/DownloadsEventsContext';
import { useToast } from '../contexts/ToastContext';
import { CoverImage } from '../components/CoverImage';
import { EmptyState } from '../components/EmptyState';
import './Downloads.css';

const STATUS_LABELS: Record<string, string> = {
  queued: 'Enfileirado',
  downloading: 'Baixando',
  paused: 'Pausado',
  completed: 'Concluído',
  failed: 'Falhou',
};

function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

type ContentType = 'music' | 'movies' | 'tv';

interface DownloadRow {
  id: number;
  status: string;
  name?: string;
  save_path?: string;
  content_type?: string;
  progress?: number;
  num_seeds?: number;
  num_peers?: number;
  /** Leechers (num_peers - num_seeds); preenchido pela API quando disponível */
  num_leechers?: number | null;
  total_bytes?: number;
  downloaded_bytes?: number;
  download_speed_bps?: number;
  eta_seconds?: number;
}

export function Downloads() {
  const { downloads: contextDownloads, lastUpdated: contextLastUpdated, refetch: contextRefetch, reconnecting } = useDownloadsEvents();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const { showToast } = useToast();
  const [removeModalId, setRemoveModalId] = useState<number | null>(null);
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
  const lastUpdated = contextLastUpdated;

  const fetchDownloads = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = statusFilter ? `/api/downloads?status=${encodeURIComponent(statusFilter)}` : '/api/downloads';
      const res = await fetch(url);
      if (!res.ok) {
        if (res.status === 503) throw new Error('Runner não configurado. Inicie: dl-torrent runner');
        throw new Error(await res.text());
      }
      contextRefetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, contextRefetch]);

  useEffect(() => {
    fetchDownloads();
  }, [fetchDownloads]);

  const showToastMessage = (msg: string) => showToast(msg, 4000);

  async function start(id: number) {
    try {
      const res = await fetch(`/api/downloads/${id}/start`, { method: 'POST' });
      if (res.ok) fetchDownloads();
      else showToastMessage('Falha ao iniciar. Tente novamente.');
    } catch {
      showToastMessage('Erro de rede ao iniciar.');
    }
  }

  async function stop(id: number) {
    try {
      const res = await fetch(`/api/downloads/${id}/stop`, { method: 'POST' });
      if (res.ok) fetchDownloads();
      else showToastMessage('Falha ao parar. Tente novamente.');
    } catch {
      showToastMessage('Erro de rede ao parar.');
    }
  }

  async function remove(id: number) {
    setRemoveModalId(null);
    try {
      const res = await fetch(`/api/downloads/${id}`, { method: 'DELETE' });
      if (res.ok) fetchDownloads();
      else showToastMessage('Falha ao remover. Tente novamente.');
    } catch {
      showToastMessage('Erro de rede ao remover.');
    }
  }

  function formatBytes(n: number | undefined): string {
    if (n == null || n === 0) return '—';
    const u = ['B', 'KB', 'MB', 'GB', 'TB'];
    let i = 0;
    while (n >= 1024 && i < u.length - 1) {
      n /= 1024;
      i++;
    }
    return `${n.toFixed(1)} ${u[i]}`;
  }

  function formatSpeed(bps: number | undefined): string {
    if (bps == null || bps <= 0) return '—';
    return `${formatBytes(bps)}/s`;
  }

  function formatEta(seconds: number | undefined): string {
    if (seconds == null || seconds < 0) return '—';
    const s = Number(seconds);
    if (s < 60) return `${s.toFixed(0)} s`;
    if (s < 3600) return `${(s / 60).toFixed(1)} min`;
    if (s < 86400) return `${(s / 3600).toFixed(1)} h`;
    return `${(s / 86400).toFixed(1)} d`;
  }

  function progressPercent(r: DownloadRow): string {
    const p = r.progress;
    if (p == null) return '—';
    const pct = p <= 1 ? p * 100 : Math.min(100, p);
    return `${Math.min(100, pct).toFixed(1)}%`;
  }

  const lastUpdatedStr = lastUpdated ? `Atualizado há ${Math.round((Date.now() - lastUpdated.getTime()) / 1000)} s` : '';

  return (
    <div className="atum-page downloads-page">
      <h1 className="atum-page-title">Downloads</h1>
      {removeModalId != null && (
        <div className="downloads-modal-overlay" role="dialog" aria-modal="true" aria-labelledby="remove-modal-title">
          <div className="downloads-modal">
            <h2 id="remove-modal-title">Remover download</h2>
            <p>Remover este download da lista?</p>
            <div className="downloads-modal-actions">
              <button type="button" className="primary" onClick={() => remove(removeModalId)}>Remover</button>
              <button type="button" onClick={() => setRemoveModalId(null)}>Cancelar</button>
            </div>
          </div>
        </div>
      )}
      <div className="downloads-toolbar">
        <div className="downloads-pills" role="group" aria-label="Filtrar por status">
          {(['', 'queued', 'downloading', 'paused', 'completed', 'failed'] as const).map((status) => (
            <button
              key={status || 'all'}
              type="button"
              className={`downloads-pill ${statusFilter === status ? 'downloads-pill--active' : ''}`}
              onClick={() => setStatusFilter(status)}
              aria-pressed={statusFilter === status}
            >
              {status ? statusLabel(status) : 'Todos'}
              {status && (
                <span className="downloads-pill-count">{statusCounts[status]}</span>
              )}
            </button>
          ))}
        </div>
        <button type="button" onClick={() => fetchDownloads()} disabled={loading} aria-busy={loading}>Atualizar</button>
        {lastUpdatedStr && <span className="downloads-last-updated" aria-live="polite">{lastUpdatedStr}</span>}
        {reconnecting && <span className="downloads-reconnecting" aria-live="polite">Reconectando…</span>}
      </div>
      {error && <p className="downloads-error" role="alert">{error}</p>}
      {loading && rows.length === 0 ? (
        <EmptyState title="Carregando…" description="Buscando downloads." />
      ) : rows.length === 0 ? (
        <EmptyState
          title="Nenhum download na fila"
          description="Busque torrents e adicione à fila para começar."
          action={<Link to="/search">Ir à busca</Link>}
        />
      ) : (
        <>
          <div className="downloads-table-wrap">
            <table className="downloads-table" aria-describedby="downloads-table-caption">
              <caption id="downloads-table-caption" className="visually-hidden">Lista de downloads com capa, nome, status, progresso e ações</caption>
              <thead>
                <tr>
                  <th scope="col" className="cover-th">Capa</th>
                  <th scope="col">ID</th>
                  <th scope="col">Nome</th>
                  <th scope="col">Status</th>
                  <th scope="col">Progresso</th>
                  <th scope="col">Se/Le</th>
                  <th scope="col">Total</th>
                  <th scope="col">Baixado</th>
                  <th scope="col">Velocidade</th>
                  <th scope="col">ETA</th>
                  <th scope="col">Ações</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td className="cover-cell">
                      <CoverImage
                        contentType={(r.content_type === 'movies' || r.content_type === 'tv' ? r.content_type : 'music') as ContentType}
                        title={r.name || ''}
                        size="thumb"
                        downloadId={r.id}
                      />
                    </td>
                    <td>{r.id}</td>
                    <td className="name-cell">{r.name || '—'}</td>
                    <td><span className={`status status-${r.status}`}>{statusLabel(r.status)}</span></td>
                    <td>
                      <span className="progress-text">{progressPercent(r)}</span>
                      {r.status === 'downloading' && r.progress != null && (
                        <div className="progress-bar-wrap" role="progressbar" aria-valuenow={r.progress <= 1 ? r.progress * 100 : r.progress} aria-valuemin={0} aria-valuemax={100} aria-label="Progresso">
                          <div className="progress-bar" style={{ width: `${Math.min(100, r.progress <= 1 ? r.progress * 100 : r.progress)}%` }} />
                        </div>
                      )}
                    </td>
                    <td>{r.num_seeds ?? '—'} / {r.num_leechers != null ? r.num_leechers : (r.num_peers ?? '—')}</td>
                    <td>{formatBytes(r.total_bytes)}</td>
                    <td>{formatBytes(r.downloaded_bytes)}</td>
                    <td>{formatSpeed(r.download_speed_bps)}</td>
                    <td>{r.status === 'completed' ? '—' : formatEta(r.eta_seconds)}</td>
                    <td>
                      {r.status === 'queued' || r.status === 'paused' ? (
                        <button type="button" className="primary" onClick={() => start(r.id)}>Iniciar</button>
                      ) : r.status === 'downloading' ? (
                        <button type="button" onClick={() => stop(r.id)}>Parar</button>
                      ) : null}
                      {' '}
                      <button type="button" onClick={() => setRemoveModalId(r.id)}>Remover</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="downloads-cards" aria-label="Lista de downloads em cards">
            {rows.map((r) => (
              <div key={r.id} className="download-card">
                <div className="download-card-cover">
                  <CoverImage
                    contentType={(r.content_type === 'movies' || r.content_type === 'tv' ? r.content_type : 'music') as ContentType}
                    title={r.name || ''}
                    size="card"
                    downloadId={r.id}
                  />
                </div>
                <div className="download-card-body">
                  <div className="download-card-name">{r.name || '—'}</div>
                  <span className={`status status-${r.status}`}>{statusLabel(r.status)}</span>
                  <div className="download-card-meta">
                    {progressPercent(r)} · {r.num_seeds ?? '—'}/{r.num_leechers != null ? r.num_leechers : (r.num_peers ?? '—')} · {formatBytes(r.total_bytes)}
                  </div>
                  {r.status === 'downloading' && r.progress != null && (
                    <div className="progress-bar-wrap" role="progressbar" aria-valuenow={r.progress <= 1 ? r.progress * 100 : r.progress} aria-valuemin={0} aria-valuemax={100}>
                      <div className="progress-bar" style={{ width: `${Math.min(100, r.progress <= 1 ? r.progress * 100 : r.progress)}%` }} />
                    </div>
                  )}
                  <div className="download-card-actions">
                    {r.status === 'queued' || r.status === 'paused' ? (
                      <button type="button" className="primary" onClick={() => start(r.id)}>Iniciar</button>
                    ) : r.status === 'downloading' ? (
                      <button type="button" onClick={() => stop(r.id)}>Parar</button>
                    ) : null}
                    <button type="button" onClick={() => setRemoveModalId(r.id)}>Remover</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
