import { useState, useEffect, useMemo } from 'react';
import { IoDownloadOutline } from 'react-icons/io5';
import { useParams, useSearchParams, useLocation, useNavigate, Link } from 'react-router-dom';
import { getLibraryItem, getLibraryItemFiles, type LibraryFile } from '../api/library';
import { useToast } from '../contexts/ToastContext';
import { useOfflineSave } from '../hooks/useOfflineSave';
import { hasFileSystemAccessSupport } from '../utils/fileSystemAccess';
import { SkeletonPlayer } from '../components/Skeleton';
import './Player.css';

interface RadioQueueItem {
  id: number;
  source?: string;
  file_index?: number;
  file_name?: string;
  item_name?: string;
  artist?: string;
  name?: string;
  content_type?: string;
}

export function Player() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [item, setItem] = useState<{ id: number; name?: string; content_type?: string; source?: string } | null>(null);
  const [files, setFiles] = useState<LibraryFile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fileIndexParam = searchParams.get('file');
  const source = searchParams.get('source');
  const radioState = location.state as { radioQueue?: RadioQueueItem[]; radioQueueIndex?: number } | null;
  const radioQueue = radioState?.radioQueue ?? null;
  const radioQueueIndex = Math.max(0, radioState?.radioQueueIndex ?? 0);
  const hasNext = radioQueue && radioQueueIndex + 1 < radioQueue.length;
  const nextItem = hasNext ? radioQueue[radioQueueIndex + 1] : null;
  const fileIndex = useMemo(() => {
    if (fileIndexParam == null || fileIndexParam === '') return 0;
    const n = parseInt(fileIndexParam, 10);
    return Number.isNaN(n) || n < 0 ? 0 : n;
  }, [fileIndexParam]);

  const isImport = source === 'import';

  useEffect(() => {
    if (!id) {
      setError('ID não informado.');
      setLoading(false);
      return;
    }
    const numId = parseInt(id, 10);
    if (Number.isNaN(numId)) {
      setError('ID inválido.');
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    const signal = controller.signal;
    setLoading(true);
    setError(null);
    Promise.all([
      getLibraryItem(numId, isImport, { signal }),
      getLibraryItemFiles(numId, isImport, { signal }),
    ])
      .then(([itemData, filesData]) => {
        setItem(itemData);
        setFiles(filesData.files);
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        const msg = err instanceof Error ? err.message : 'Erro';
        setError(msg.includes('404') ? 'Item não encontrado.' : msg);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [id, isImport]);

  const streamUrl = useMemo(() => {
    if (!item || files.length === 0) return '';
    const idx = fileIndex >= files.length ? 0 : fileIndex;
    return isImport
      ? `/api/library/imported/${item.id}/stream?file_index=${idx}`
      : `/api/library/${item.id}/stream?file_index=${idx}`;
  }, [item, files.length, fileIndex, isImport]);

  const isVideo = item?.content_type === 'movies' || item?.content_type === 'tv';
  const { showToast } = useToast();
  const { save, saving, progress } = useOfflineSave({
    itemId: item?.id ?? 0,
    isImport: item?.source === 'import',
    onSuccess: (saved) => showToast(`${saved} arquivo(s) salvo(s) na pasta escolhida.`, 4000),
    onError: (msg) => showToast(msg, 5000),
  });

  const goNextRadio = () => {
    if (!nextItem) return;
    const src = nextItem.source || 'download';
    const fileParam = nextItem.file_index != null ? `&file=${nextItem.file_index}` : '';
    navigate(`/play/${nextItem.id}?source=${encodeURIComponent(src)}${fileParam}`, {
      state: {
        radioQueue,
        radioQueueIndex: radioQueueIndex + 1,
      },
    });
  };

  const goToRadioTrack = (index: number) => {
    if (!radioQueue || index < 0 || index >= radioQueue.length) return;
    const t = radioQueue[index];
    const src = t.source || 'download';
    const fileParam = t.file_index != null ? `&file=${t.file_index}` : '';
    navigate(`/play/${t.id}?source=${encodeURIComponent(src)}${fileParam}`, {
      state: { radioQueue, radioQueueIndex: index },
    });
  };

  if (loading) {
    return (
      <div className="atum-player">
        <SkeletonPlayer />
      </div>
    );
  }

  if (error || !item) {
    return (
      <div className="atum-player">
        <Link to="/library" className="atum-player-back">← Voltar à Biblioteca</Link>
        <p className="atum-player-error">{error || 'Item não encontrado.'}</p>
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="atum-player">
        <Link to="/library" className="atum-player-back">← Voltar à Biblioteca</Link>
        <h1 className="atum-player-title">{item.name || 'Reproduzir'}</h1>
        <p className="atum-player-error">Nenhum arquivo de mídia encontrado neste download.</p>
      </div>
    );
  }

  const isRadio = radioQueue && radioQueue.length > 0;

  if (isRadio) {
    return (
      <div className="atum-player atum-player-radio-only">
        <div className="atum-player-radio-queue">
          <div className="atum-player-radio-queue-header">
            <span className="atum-player-radio-queue-title">Fila da rádio</span>
            {hasNext && (
              <button type="button" className="atum-player-next-btn" onClick={goNextRadio}>
                Próximo
              </button>
            )}
          </div>
          <div className="atum-player-radio-track-list-wrap">
            <table className="atum-player-radio-track-list" aria-label="Fila da rádio">
              <thead>
                <tr>
                  <th scope="col">#</th>
                  <th scope="col">Título</th>
                  <th scope="col">Álbum</th>
                </tr>
              </thead>
              <tbody>
                {radioQueue.map((t, i) => (
                  <tr
                    key={`${t.id}-${t.file_index ?? 0}-${i}`}
                    className={i === radioQueueIndex ? 'atum-player-radio-track-active' : ''}
                    role="button"
                    tabIndex={0}
                    onClick={() => goToRadioTrack(i)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goToRadioTrack(i); } }}
                  >
                    <td className="atum-player-radio-num">{i + 1}</td>
                    <td className="atum-player-radio-track-title">
                      {t.file_name || t.item_name || '—'}
                      {t.artist && <span className="atum-player-radio-track-artist">{t.artist}</span>}
                    </td>
                    <td className="atum-player-radio-track-album">{t.item_name || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="atum-player-media-wrap">
          {isVideo ? (
            <video key={streamUrl} controls autoPlay playsInline src={streamUrl}>
              Seu navegador não suporta vídeo.
            </video>
          ) : (
            <audio key={streamUrl} controls autoPlay src={streamUrl}>
              Seu navegador não suporta áudio.
            </audio>
          )}
        </div>
        {hasFileSystemAccessSupport() && (
          <div className="atum-player-actions">
            <button
              type="button"
              className="atum-btn atum-btn-ghost"
              onClick={() => save()}
              disabled={saving}
              aria-label="Salvar para offline"
            >
              <IoDownloadOutline size={18} aria-hidden />
              {saving && progress ? `Salvando ${progress.current}/${progress.total}…` : 'Salvar para offline'}
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="atum-player">
      <div className="atum-player-media-wrap">
        {isVideo ? (
          <video key={streamUrl} controls autoPlay playsInline src={streamUrl}>
            Seu navegador não suporta vídeo.
          </video>
        ) : (
          <audio key={streamUrl} controls autoPlay src={streamUrl}>
            Seu navegador não suporta áudio.
          </audio>
        )}
      </div>
      {hasFileSystemAccessSupport() && (
        <div className="atum-player-actions">
          <button
            type="button"
            className="atum-btn atum-btn-ghost"
            onClick={() => save()}
            disabled={saving}
            aria-label="Salvar para offline"
          >
            <IoDownloadOutline size={18} aria-hidden />
            {saving && progress ? `Salvando ${progress.current}/${progress.total}…` : 'Salvar para offline'}
          </button>
        </div>
      )}
    </div>
  );
}
