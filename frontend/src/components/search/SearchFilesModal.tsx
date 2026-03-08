import { useState, useEffect } from 'react';
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

interface SearchFilesModalProps {
  result: SearchResult;
  onClose: () => void;
  onAddToQueue: () => void;
}

export function SearchFilesModal({ result, onClose, onAddToQueue }: SearchFilesModalProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<{ name: string; files: TorrentFile[] } | null>(null);

  useEffect(() => {
    let cancelled = false;
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
        if (cancelled) return;
        if (!res.ok) {
          setError(json?.detail || res.statusText || 'Erro ao obter arquivos');
          return;
        }
        setData(json || null);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Erro de rede');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [result]);

  return (
    <div className="search-files-modal-backdrop" onClick={onClose} aria-hidden>
      <div className="search-files-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-labelledby="files-modal-title" aria-modal="true">
        <div className="search-files-modal-header">
          <h2 id="files-modal-title">Arquivos do torrent</h2>
          <button type="button" className="search-files-modal-close" onClick={onClose} aria-label="Fechar">×</button>
        </div>
        <div className="search-files-modal-body">
          {loading && <p className="search-files-modal-loading">Obtendo lista de arquivos…</p>}
          {error && <p className="search-files-modal-error" role="alert">{error}</p>}
          {!loading && !error && data && (
            <>
              <p className="search-files-modal-name">{data.name || result.title}</p>
              <ul className="search-files-list">
                {(data.files ?? []).map((f) => (
                  <li key={f.index} className="search-files-item">
                    <span className="search-files-path">{f.path}</span>
                    <span className="search-files-size">{formatFileSize(f.size)}</span>
                  </li>
                ))}
              </ul>
              <div className="search-files-modal-footer">
                <button
                  type="button"
                  className="primary add-btn"
                  onClick={() => {
                    onClose();
                    onAddToQueue();
                  }}
                  aria-label={`Adicionar ${result.title} à fila`}
                >
                  Adicionar à fila
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
