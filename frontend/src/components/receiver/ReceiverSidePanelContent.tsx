import type React from 'react';
import { IoChatbubbleEllipses, IoDownloadOutline, IoHeart, IoHeartOutline, IoList } from 'react-icons/io5';
import { CoverImage } from '../CoverImage';
import { useToast } from '../../contexts/ToastContext';
import { useOfflineSave } from '../../hooks/useOfflineSave';
import { hasFileSystemAccessSupport } from '../../utils/fileSystemAccess';
import { formatFileSize } from '../../utils/format';
import type { LibraryFile } from '../../api/library';

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

export interface ReceiverSidePanelContentProps {
  item: { id: number; name?: string; content_type?: string; source?: string };
  files: LibraryFile[];
  isImport: boolean;
  isRadio: boolean;
  radioQueue: RadioQueueItem[] | null;
  activeRadioQueueIndex: number;
  safeFileIndex: number;
  currentFile: LibraryFile | { name: string; size: number; index: number };
  qualityMeta: { codec?: string; bitrate?: string | number } | null;
  trackFavorited: boolean;
  onToggleFav: () => void;
  rpPlaylistOpen: boolean;
  setRpPlaylistOpen: React.Dispatch<React.SetStateAction<boolean>>;
  rpPlaylists: { id: number; name: string }[];
  rpPlaylistRef: React.RefObject<HTMLDivElement | null>;
  onAddToPlaylist: (playlistId: number) => void;
  savingQueue: boolean;
  onSaveQueueAsPlaylist: () => void;
  goToQueueTrack: (index: number) => void;
  goToFileTrack: (index: number) => void;
  aiInsight: string | null;
  aiLoading: boolean;
  onFetchAiInsight: () => void;
}

export function ReceiverSidePanelContent({
  item,
  files,
  isImport,
  isRadio,
  radioQueue,
  activeRadioQueueIndex,
  safeFileIndex,
  currentFile,
  qualityMeta,
  trackFavorited,
  onToggleFav,
  rpPlaylistOpen,
  setRpPlaylistOpen,
  rpPlaylists,
  rpPlaylistRef,
  onAddToPlaylist,
  savingQueue,
  onSaveQueueAsPlaylist,
  goToQueueTrack,
  goToFileTrack,
  aiInsight,
  aiLoading,
  onFetchAiInsight,
}: ReceiverSidePanelContentProps) {
  const { showToast } = useToast();
  const { save, saving, progress } = useOfflineSave({
    itemId: item.id,
    isImport,
    onSuccess: (saved) => showToast(`${saved} arquivo(s) salvo(s) na pasta escolhida.`, 4000),
    onError: (msg) => showToast(msg, 5000),
  });

  return (
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

      <div className="receiver-side-actions">
        <button
          type="button"
          className={`receiver-side-action-btn${trackFavorited ? ' receiver-side-action-btn--fav-active' : ''}`}
          onClick={onToggleFav}
          aria-label={trackFavorited ? 'Remover dos favoritos' : 'Favoritar'}
        >
          {trackFavorited ? <IoHeart size={18} /> : <IoHeartOutline size={18} />}
          <span>{trackFavorited ? 'Favoritado' : 'Favoritar'}</span>
        </button>
        <div className="receiver-side-playlist-wrap" ref={rpPlaylistRef}>
          <button
            type="button"
            className="receiver-side-action-btn"
            onClick={() => setRpPlaylistOpen((p) => !p)}
            aria-label="Adicionar a playlist"
          >
            <IoList size={18} />
            <span>Playlist</span>
          </button>
          {rpPlaylistOpen && (
            <div className="receiver-side-playlist-popup">
              {rpPlaylists.length === 0 ? (
                <span className="receiver-side-playlist-empty">Nenhuma playlist</span>
              ) : (
                rpPlaylists.map((p) => (
                  <button key={p.id} type="button" className="receiver-side-playlist-item" onClick={() => onAddToPlaylist(p.id)}>
                    {p.name}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {hasFileSystemAccessSupport() && (
        <button
          type="button"
          className="receiver-side-action-btn"
          onClick={() => save()}
          disabled={saving}
          aria-label="Salvar para offline"
        >
          <IoDownloadOutline size={18} />
          <span>{saving && progress ? `Salvando ${progress.current}/${progress.total}…` : 'Salvar para offline'}</span>
        </button>
      )}

      {radioQueue && radioQueue.length > 0 && (
        <button
          type="button"
          className="receiver-side-action-btn"
          onClick={onSaveQueueAsPlaylist}
          disabled={savingQueue}
          aria-label="Salvar fila como playlist"
        >
          <IoList size={18} />
          <span>{savingQueue ? 'Salvando…' : 'Salvar fila'}</span>
        </button>
      )}

      <div className="receiver-side-section">
        <span className="receiver-side-section-title">{isRadio ? 'FILA DA RÁDIO' : 'FAIXAS'}</span>
        <div className="receiver-side-tracks">
          {isRadio && radioQueue
            ? radioQueue.map((t, i) => (
                <div
                  key={`${t.id}-${t.file_index ?? 0}-${i}`}
                  className={`receiver-side-track${i === activeRadioQueueIndex ? ' receiver-side-track--active' : ''}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => goToQueueTrack(i)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      goToQueueTrack(i);
                    }
                  }}
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
                  onClick={() => goToFileTrack(i)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      goToFileTrack(i);
                    }
                  }}
                >
                  <span className="receiver-side-track-num">{i + 1}</span>
                  <span className="receiver-side-track-name">{f.name}</span>
                  <span className="receiver-side-track-size">{formatFileSize(f.size)}</span>
                </div>
              ))}
        </div>
      </div>

      <div className="receiver-side-section">
        <span className="receiver-side-section-title">METADADOS</span>
        <div className="receiver-side-meta">
          <div className="receiver-side-meta-row">
            <span className="receiver-side-meta-label">Codec</span>
            <span className="receiver-side-meta-value">{qualityMeta?.codec || '—'}</span>
          </div>
          {qualityMeta?.bitrate != null && (
            <div className="receiver-side-meta-row">
              <span className="receiver-side-meta-label">Bitrate</span>
              <span className="receiver-side-meta-value">{qualityMeta.bitrate}</span>
            </div>
          )}
          <div className="receiver-side-meta-row">
            <span className="receiver-side-meta-label">Arquivo</span>
            <span className="receiver-side-meta-value">{currentFile?.name || '—'}</span>
          </div>
          {currentFile?.size != null && currentFile.size > 0 && (
            <div className="receiver-side-meta-row">
              <span className="receiver-side-meta-label">Tamanho</span>
              <span className="receiver-side-meta-value">{formatFileSize(currentFile.size)}</span>
            </div>
          )}
          <div className="receiver-side-meta-row">
            <span className="receiver-side-meta-label">Faixa</span>
            <span className="receiver-side-meta-value">
              {(isRadio ? activeRadioQueueIndex : safeFileIndex) + 1} / {isRadio ? radioQueue!.length : files.length}
            </span>
          </div>
        </div>
      </div>

      <div className="receiver-side-section">
        <div className="receiver-side-section-header">
          <span className="receiver-side-section-title">
            <IoChatbubbleEllipses size={12} className="receiver-side-icon" />
            AI INSIGHT
          </span>
          {!aiInsight && !aiLoading && (
            <button type="button" className="receiver-side-ai-btn" onClick={onFetchAiInsight}>
              Analisar
            </button>
          )}
        </div>
        {aiLoading && <p className="receiver-side-ai-text receiver-side-ai-text--loading">Analisando faixa…</p>}
        {aiInsight && <p className="receiver-side-ai-text">{aiInsight}</p>}
      </div>
    </div>
  );
}
