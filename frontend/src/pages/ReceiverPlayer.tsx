import { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams, useSearchParams, useLocation, useNavigate } from 'react-router-dom';
import { ReceiverPanel } from '../components/receiver/ReceiverPanel';
import { CoverImage } from '../components/CoverImage';
import { inferQualityMeta } from '../audio/analysis';
import { formatFileSize } from '../utils/format';
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

export function ReceiverPlayer() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [item, setItem] = useState<{ id: number; name?: string; content_type?: string; source?: string } | null>(null);
  const [files, setFiles] = useState<MediaFile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sideOpen, setSideOpen] = useState(true);

  const fileIndexParam = searchParams.get('file');
  const source = searchParams.get('source');
  const radioState = location.state as { radioQueue?: RadioQueueItem[]; radioQueueIndex?: number } | null;
  const radioQueue = radioState?.radioQueue ?? null;
  const radioQueueIndex = Math.max(0, radioState?.radioQueueIndex ?? 0);
  const hasNext = radioQueue ? radioQueueIndex + 1 < radioQueue.length : false;
  const hasPrev = radioQueue ? radioQueueIndex > 0 : false;
  const nextItem = hasNext ? radioQueue![radioQueueIndex + 1] : null;
  const prevItem = hasPrev ? radioQueue![radioQueueIndex - 1] : null;
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
    setLoading(true);
    setError(null);
    const itemUrl = isImport ? `/api/library/imported/${numId}` : `/api/library/${numId}`;
    const filesUrl = isImport ? `/api/library/imported/${numId}/files` : `/api/library/${numId}/files`;
    Promise.all([
      fetch(itemUrl, { signal: controller.signal }).then((r) => {
        if (!r.ok) throw new Error(r.status === 404 ? 'Item não encontrado.' : r.statusText);
        return r.json();
      }),
      fetch(filesUrl, { signal: controller.signal }).then((r) => {
        if (!r.ok) return { files: [] };
        return r.json();
      }),
    ])
      .then(([itemData, filesData]) => {
        setItem(itemData);
        setFiles(Array.isArray(filesData?.files) ? filesData.files : []);
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Erro');
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [id, isImport]);

  const safeFileIndex = fileIndex >= files.length ? 0 : fileIndex;

  const streamUrl = useMemo(() => {
    if (!item || files.length === 0) return '';
    return isImport
      ? `/api/library/imported/${item.id}/stream?file_index=${safeFileIndex}`
      : `/api/library/${item.id}/stream?file_index=${safeFileIndex}`;
  }, [item, files.length, safeFileIndex, isImport]);

  const isVideo = item?.content_type === 'movies' || item?.content_type === 'tv';

  const navigateToTrack = useCallback((target: RadioQueueItem | null, idx: number) => {
    if (!target || !radioQueue) return;
    const src = target.source || 'download';
    const fileParam = target.file_index != null ? `&file=${target.file_index}` : '';
    navigate(`/play-receiver/${target.id}?source=${encodeURIComponent(src)}${fileParam}`, {
      state: { radioQueue, radioQueueIndex: idx },
    });
  }, [radioQueue, navigate]);

  const goNextRadio = useCallback(() => {
    navigateToTrack(nextItem, radioQueueIndex + 1);
  }, [nextItem, radioQueueIndex, navigateToTrack]);

  const goPrevRadio = useCallback(() => {
    navigateToTrack(prevItem, radioQueueIndex - 1);
  }, [prevItem, radioQueueIndex, navigateToTrack]);

  const goToRadioTrack = useCallback((index: number) => {
    if (!radioQueue || index < 0 || index >= radioQueue.length) return;
    navigateToTrack(radioQueue[index], index);
  }, [radioQueue, navigateToTrack]);

  const goToFileIndex = useCallback((idx: number) => {
    if (idx < 0 || idx >= files.length || !item) return;
    const base = isImport ? 'import' : source || 'download';
    navigate(`/play-receiver/${item.id}?source=${encodeURIComponent(base)}&file=${idx}`, {
      state: location.state,
      replace: true,
    });
  }, [files.length, item, isImport, source, navigate, location.state]);

  const hasPrevFile = !radioQueue && safeFileIndex > 0;
  const hasNextFile = !radioQueue && safeFileIndex < files.length - 1;

  const goPrevFile = useCallback(() => {
    goToFileIndex(safeFileIndex - 1);
  }, [safeFileIndex, goToFileIndex]);

  const goNextFile = useCallback(() => {
    goToFileIndex(safeFileIndex + 1);
  }, [safeFileIndex, goToFileIndex]);

  const currentFile = files[safeFileIndex];
  const title = radioQueue
    ? `${currentFile?.name || item?.name || '—'}${radioQueue[radioQueueIndex]?.artist ? ` · ${radioQueue[radioQueueIndex].artist}` : ''}`
    : (currentFile?.name || item?.name || '—');

  const qualityMeta = useMemo(
    () => inferQualityMeta(item?.content_type ?? null, currentFile?.name ?? ''),
    [item?.content_type, currentFile?.name],
  );

  const goBack = useCallback(() => {
    if (window.history.length > 1) navigate(-1);
    else navigate('/library');
  }, [navigate]);

  if (loading) {
    return (
      <div className="atum-player atum-player--fullscreen">
        <p className="atum-player-loading">Carregando…</p>
      </div>
    );
  }

  if (error || !item) {
    return (
      <div className="atum-player atum-player--fullscreen">
        <button type="button" className="atum-receiver-back" onClick={goBack}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
          Voltar
        </button>
        <p className="atum-player-error">{error || 'Item não encontrado.'}</p>
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="atum-player atum-player--fullscreen">
        <button type="button" className="atum-receiver-back" onClick={goBack}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
          Voltar
        </button>
        <h1 className="atum-player-title">{item.name || 'Reproduzir'}</h1>
        <p className="atum-player-error">Nenhum arquivo de mídia encontrado neste download.</p>
      </div>
    );
  }

  if (isVideo) {
    navigate(`/play/${id}?${searchParams.toString()}`, { replace: true, state: location.state });
    return (
      <div className="atum-player atum-player--fullscreen">
        <p className="atum-player-loading">Redirecionando para o player de vídeo…</p>
      </div>
    );
  }

  const isRadio = radioQueue && radioQueue.length > 0;
  const effectiveHasNext = isRadio ? hasNext : hasNextFile;
  const effectiveHasPrev = isRadio ? hasPrev : hasPrevFile;
  const effectiveOnNext = isRadio ? goNextRadio : hasNextFile ? goNextFile : undefined;
  const effectiveOnPrev = isRadio ? goPrevRadio : hasPrevFile ? goPrevFile : undefined;

  return (
    <div className="atum-player atum-player--fullscreen">
      <button type="button" className="atum-receiver-back" onClick={goBack}>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
        Voltar
      </button>

      <div className="receiver-layout">
        <ReceiverPanel
          streamUrl={streamUrl}
          title={title}
          fileName={currentFile?.name}
          contentType={item?.content_type ?? null}
          onNext={effectiveOnNext}
          onPrev={effectiveOnPrev}
          hasNext={effectiveHasNext}
          hasPrev={effectiveHasPrev}
          className="receiver-layout-main"
        />

        <button
          type="button"
          className={`receiver-side-toggle${sideOpen ? ' receiver-side-toggle--open' : ''}`}
          onClick={() => setSideOpen((p) => !p)}
          aria-label={sideOpen ? 'Fechar painel' : 'Abrir painel'}
        >
          {sideOpen ? '›' : '‹'}
        </button>

        {/* Bottom sheet overlay (mobile only via CSS) */}
        <div
          className={`receiver-bottom-overlay${sideOpen ? ' receiver-bottom-overlay--visible' : ''}`}
          onClick={() => setSideOpen(false)}
        />

        {/* FAB to open bottom sheet (mobile only via CSS) */}
        <button
          type="button"
          className="receiver-bottom-sheet-fab"
          onClick={() => setSideOpen((p) => !p)}
          aria-label="Abrir detalhes"
        >
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path d="M3 4h14v2H3zM3 9h14v2H3zM3 14h10v2H3z" />
          </svg>
        </button>

        <aside className={`receiver-side-panel${sideOpen ? '' : ' receiver-side-panel--collapsed'}`}>
          <div className="receiver-side-frame">
          <div className="receiver-side-glass">
          <div className="receiver-side-inner">
            <div className="receiver-side-cover">
              <CoverImage
                contentType={(item.content_type as 'music' | 'movies' | 'tv') || 'music'}
                title={item.name || ''}
                downloadId={isImport ? undefined : item.id}
                importId={isImport ? item.id : undefined}
                size="card"
              />
            </div>

            <div className="receiver-side-section">
              <span className="receiver-side-section-title">
                {isRadio ? 'FILA DA RÁDIO' : 'FAIXAS'}
              </span>
              <div className="receiver-side-tracks">
                {isRadio
                  ? radioQueue!.map((t, i) => (
                      <div
                        key={`${t.id}-${t.file_index ?? 0}-${i}`}
                        className={`receiver-side-track${i === radioQueueIndex ? ' receiver-side-track--active' : ''}`}
                        role="button"
                        tabIndex={0}
                        onClick={() => goToRadioTrack(i)}
                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goToRadioTrack(i); } }}
                      >
                        <span className="receiver-side-track-num">{i + 1}</span>
                        <span className="receiver-side-track-name">
                          {t.file_name || t.item_name || '—'}
                          {t.artist && <span className="receiver-side-track-artist"> · {t.artist}</span>}
                        </span>
                      </div>
                    ))
                  : files.map((f, i) => (
                      <div
                        key={f.index}
                        className={`receiver-side-track${i === safeFileIndex ? ' receiver-side-track--active' : ''}`}
                        role="button"
                        tabIndex={0}
                        onClick={() => goToFileIndex(i)}
                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goToFileIndex(i); } }}
                      >
                        <span className="receiver-side-track-num">{i + 1}</span>
                        <span className="receiver-side-track-name">{f.name}</span>
                        <span className="receiver-side-track-size">{formatFileSize(f.size)}</span>
                      </div>
                    ))
                }
              </div>
            </div>

            <div className="receiver-side-section">
              <span className="receiver-side-section-title">METADADOS</span>
              <div className="receiver-side-meta">
                <div className="receiver-side-meta-row">
                  <span className="receiver-side-meta-label">Codec</span>
                  <span className="receiver-side-meta-value">{qualityMeta?.codec || '—'}</span>
                </div>
                {qualityMeta?.bitrate && (
                  <div className="receiver-side-meta-row">
                    <span className="receiver-side-meta-label">Bitrate</span>
                    <span className="receiver-side-meta-value">{qualityMeta.bitrate}</span>
                  </div>
                )}
                <div className="receiver-side-meta-row">
                  <span className="receiver-side-meta-label">Arquivo</span>
                  <span className="receiver-side-meta-value">{currentFile?.name || '—'}</span>
                </div>
                {currentFile?.size != null && (
                  <div className="receiver-side-meta-row">
                    <span className="receiver-side-meta-label">Tamanho</span>
                    <span className="receiver-side-meta-value">{formatFileSize(currentFile.size)}</span>
                  </div>
                )}
                <div className="receiver-side-meta-row">
                  <span className="receiver-side-meta-label">Faixa</span>
                  <span className="receiver-side-meta-value">
                    {safeFileIndex + 1} / {isRadio ? radioQueue!.length : files.length}
                  </span>
                </div>
              </div>
            </div>
          </div>
          </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
