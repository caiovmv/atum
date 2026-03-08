import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../../contexts/ToastContext';
import { formatFileSize } from '../../utils/format';

interface TorrentFile {
  index: number;
  path: string;
  size: number;
}

interface SearchResult {
  title: string;
  magnet: string | null;
  torrent_url?: string | null;
  indexer: string;
  torrent_id: string;
}

interface SearchAddModalProps {
  result: SearchResult;
  contentType: 'music' | 'movies' | 'tv';
  onClose: () => void;
}

export function SearchAddModal({ result, contentType, onClose }: SearchAddModalProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<{ name: string; files: TorrentFile[] } | null>(null);
  const [included, setIncluded] = useState<Set<number>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const { showToast } = useToast();
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  function fetchMetadata() {
    setLoading(true);
    setError(null);
    setData(null);

    fetch('/api/torrent/metadata', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ magnet: result.magnet ?? null, torrent_url: result.torrent_url ?? null }),
    })
      .then(async (res) => {
        const json = await res.json().catch(() => null);
        if (!mountedRef.current) return;
        if (!res.ok) {
          const errMsg = typeof json?.detail === 'string'
            ? json.detail
            : (json?.detail ? JSON.stringify(json.detail) : res.statusText || 'Erro ao obter arquivos');
          setError(errMsg);
          return;
        }
        const files = (json?.files ?? []) as TorrentFile[];
        setData(json ? { name: json.name ?? result.title, files } : null);
        setIncluded(new Set(files.map((f) => f.index)));
      })
      .catch((err) => {
        if (mountedRef.current) setError(err instanceof Error ? err.message : 'Erro de rede');
      })
      .finally(() => {
        if (mountedRef.current) setLoading(false);
      });
  }

  useEffect(() => {
    fetchMetadata();
  }, [result]);

  function toggleFile(index: number) {
    setIncluded((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  function setIncludeAll(include: boolean) {
    if (!data) return;
    setIncluded(include ? new Set(data.files.map((f) => f.index)) : new Set());
  }

  async function handleConfirm() {
    const link = result.magnet || result.torrent_url;
    if (!link || !data || submitting) return;
    setSubmitting(true);
    const excluded_file_indices = data.files.map((f) => f.index).filter((i) => !included.has(i));
    try {
      const res = await fetch('/api/downloads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          magnet: link,
          name: result.title,
          content_type: contentType,
          start_now: true,
          excluded_file_indices,
          torrent_files: data.files,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      onClose();
      showToast('Download adicionado à fila.', 4000);
      navigate('/downloads');
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Erro ao adicionar', 4000);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="search-files-modal-backdrop" onClick={onClose} aria-hidden>
      <div className="search-add-modal search-files-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-labelledby="add-modal-title" aria-modal="true">
        <div className="search-files-modal-header">
          <h2 id="add-modal-title">Adicionar à fila</h2>
          <button type="button" className="search-files-modal-close" onClick={onClose} aria-label="Fechar">×</button>
        </div>
        <div className="search-files-modal-body">
          {loading && <p className="search-files-modal-loading">Obtendo lista de arquivos…</p>}
          {error && (
            <div className="search-files-modal-error-wrap" role="alert">
              <p className="search-files-modal-error">{error}</p>
              <button type="button" className="primary add-btn" onClick={fetchMetadata}>Tentar novamente</button>
            </div>
          )}
          {!loading && !error && data && (
            <>
              <p className="search-files-modal-name">{data.name || result.title}</p>
              <div className="search-add-modal-actions-row">
                <button type="button" className="secondary add-btn" onClick={() => setIncludeAll(true)}>Selecionar todos</button>
                <button type="button" className="secondary add-btn" onClick={() => setIncludeAll(false)}>Desmarcar todos</button>
              </div>
              <ul className="search-files-list">
                {data.files.map((f) => (
                  <li key={f.index} className="search-files-item search-add-file-item">
                    <label className="search-add-file-label">
                      <input
                        type="checkbox"
                        checked={included.has(f.index)}
                        onChange={() => toggleFile(f.index)}
                        aria-label={`Incluir ${f.path}`}
                      />
                      <span className="search-files-path">{f.path}</span>
                      <span className="search-files-size">{formatFileSize(f.size)}</span>
                    </label>
                  </li>
                ))}
              </ul>
              <div className="search-add-modal-footer">
                <button type="button" className="secondary add-btn" onClick={onClose}>Cancelar</button>
                <button type="button" className="primary add-btn" disabled={submitting} onClick={handleConfirm}>
                  {submitting ? '…' : 'Adicionar à fila'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
