import { useState, useEffect, useMemo } from 'react';
import { useParams, useSearchParams, useLocation, useNavigate, Link } from 'react-router-dom';
import { ReceiverPanel } from '../components/receiver/ReceiverPanel';
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

interface MediaFile {
  index: number;
  name: string;
  size: number;
}

/**
 * Página do Player no estilo Vintage Receiver (VU meters, spectrum, etc.).
 * Usada para reprodução de áudio da biblioteca ou rádio (sintonia).
 * Vídeo redireciona para o Player clássico.
 */
export function ReceiverPlayer() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [item, setItem] = useState<{ id: number; name?: string; content_type?: string; source?: string } | null>(null);
  const [files, setFiles] = useState<MediaFile[]>([]);
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
    setLoading(true);
    setError(null);
    const itemUrl = isImport ? `/api/library/imported/${numId}` : `/api/library/${numId}`;
    const filesUrl = isImport ? `/api/library/imported/${numId}/files` : `/api/library/${numId}/files`;
    Promise.all([
      fetch(itemUrl).then((r) => {
        if (!r.ok) throw new Error(r.status === 404 ? 'Item não encontrado.' : r.statusText);
        return r.json();
      }),
      fetch(filesUrl).then((r) => {
        if (!r.ok) return { files: [] };
        return r.json();
      }),
    ])
      .then(([itemData, filesData]) => {
        setItem(itemData);
        setFiles(Array.isArray(filesData?.files) ? filesData.files : []);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Erro'))
      .finally(() => setLoading(false));
  }, [id, isImport]);

  const streamUrl = useMemo(() => {
    if (!item || files.length === 0) return '';
    const idx = fileIndex >= files.length ? 0 : fileIndex;
    return isImport
      ? `/api/library/imported/${item.id}/stream?file_index=${idx}`
      : `/api/library/${item.id}/stream?file_index=${idx}`;
  }, [item, files.length, fileIndex, isImport]);

  const isVideo = item?.content_type === 'movies' || item?.content_type === 'tv';

  const goNextRadio = () => {
    if (!nextItem) return;
    const src = nextItem.source || 'download';
    const fileParam = nextItem.file_index != null ? `&file=${nextItem.file_index}` : '';
    navigate(`/play-receiver/${nextItem.id}?source=${encodeURIComponent(src)}${fileParam}`, {
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
    navigate(`/play-receiver/${t.id}?source=${encodeURIComponent(src)}${fileParam}`, {
      state: { radioQueue, radioQueueIndex: index },
    });
  };

  const currentFile = files[fileIndex >= files.length ? 0 : fileIndex];
  const title = radioQueue
    ? `${currentFile?.name || item?.name || '—'}${radioQueue[radioQueueIndex]?.artist ? ` · ${radioQueue[radioQueueIndex].artist}` : ''}`
    : (currentFile?.name || item?.name || '—');

  if (loading) {
    return (
      <div className="atum-player">
        <p className="atum-player-loading">Carregando…</p>
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

  if (isVideo) {
    navigate(`/play/${id}?${searchParams.toString()}`, { replace: true, state: location.state });
    return (
      <div className="atum-player">
        <p className="atum-player-loading">Redirecionando para o player de vídeo…</p>
      </div>
    );
  }

  const isRadio = radioQueue && radioQueue.length > 0;

  return (
    <div className="atum-player">
      <Link to="/library" className="atum-player-back">← Voltar à Biblioteca</Link>
      {isRadio && (
        <div className="atum-player-radio-queue" style={{ marginBottom: '1rem' }}>
          <div className="atum-player-radio-queue-header">
            <span className="atum-player-radio-queue-title">Fila da rádio</span>
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
      )}
      <ReceiverPanel
        streamUrl={streamUrl}
        title={title}
        fileName={currentFile?.name}
        contentType={item?.content_type ?? null}
        onNext={hasNext ? goNextRadio : undefined}
        hasNext={hasNext ?? false}
      />
    </div>
  );
}
