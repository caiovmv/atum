import { useState, useEffect } from 'react';
import { BottomSheet } from '../BottomSheet';
import { formatFileSize } from '../../utils/format';
import { getTorrentMetadata } from '../../api/torrent';

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
  const [data, setData] = useState<{ name: string; files: Array<{ index: number; path: string; size: number }> } | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);

    getTorrentMetadata({ magnet: result.magnet, torrent_url: result.torrent_url })
      .then((meta) => {
        if (cancelled) return;
        setData({ name: meta.name ?? result.title, files: meta.files });
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
    <BottomSheet open title="Arquivos do torrent" onClose={onClose} showCloseButton>
      <>
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
                className="atum-btn atum-btn-primary"
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
      </>
    </BottomSheet>
  );
}
