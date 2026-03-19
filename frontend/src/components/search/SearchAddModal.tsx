import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../../contexts/ToastContext';
import { BottomSheet } from '../BottomSheet';
import { formatFileSize } from '../../utils/format';
import { getTorrentMetadata, type TorrentFile } from '../../api/torrent';
import { createDownload } from '../../api/downloads';

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

  const fetchMetadata = useCallback(() => {
    setLoading(true);
    setError(null);
    setData(null);

    getTorrentMetadata({ magnet: result.magnet, torrent_url: result.torrent_url })
      .then((meta) => {
        if (!mountedRef.current) return;
        setData({ name: meta.name ?? result.title, files: meta.files });
        setIncluded(new Set(meta.files.map((f) => f.index)));
      })
      .catch((err) => {
        if (mountedRef.current) {
          const msg = err instanceof Error ? err.message : 'Erro de rede';
          setError(typeof msg === 'string' ? msg : 'Erro ao obter arquivos');
        }
      })
      .finally(() => {
        if (mountedRef.current) setLoading(false);
      });
  }, [result]);

  useEffect(() => {
    fetchMetadata();
  }, [fetchMetadata]);

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
    if ((!result.magnet && !result.torrent_url) || !data || submitting) return;
    setSubmitting(true);
    const excluded_file_indices = data.files.map((f) => f.index).filter((i) => !included.has(i));
    try {
      await createDownload({
        magnet: result.magnet || null,
        torrent_url: result.torrent_url || null,
        name: result.title,
        content_type: contentType,
        start_now: true,
        excluded_file_indices,
        torrent_files: data.files,
      });
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
    <BottomSheet open title="Adicionar à fila" onClose={onClose} showCloseButton>
      <>
        {loading && <p className="search-files-modal-loading">Obtendo lista de arquivos…</p>}
        {error && (
          <div className="search-files-modal-error-wrap" role="alert">
            <p className="search-files-modal-error">{error}</p>
            <button type="button" className="atum-btn atum-btn-primary" onClick={fetchMetadata}>Tentar novamente</button>
          </div>
        )}
        {!loading && !error && data && (
          <>
            <p className="search-files-modal-name">{data.name || result.title}</p>
            <div className="search-add-modal-actions-row">
              <button type="button" className="atum-btn" onClick={() => setIncludeAll(true)}>Selecionar todos</button>
              <button type="button" className="atum-btn" onClick={() => setIncludeAll(false)}>Desmarcar todos</button>
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
              <button type="button" className="atum-btn" onClick={onClose}>Cancelar</button>
              <button type="button" className="atum-btn atum-btn-primary" disabled={submitting} onClick={handleConfirm}>
                {submitting ? '…' : 'Adicionar à fila'}
              </button>
            </div>
          </>
        )}
      </>
    </BottomSheet>
  );
}
