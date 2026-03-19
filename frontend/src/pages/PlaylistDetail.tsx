import { useParams } from 'react-router-dom';
import { IoPlay, IoTrash, IoArrowBack, IoDownload, IoDocument, IoClose, IoRefresh, IoCreate } from 'react-icons/io5';
import { Skeleton, SkeletonRow } from '../components/Skeleton';
import { PlaylistCover } from '../components/playlists/PlaylistCover';
import { PlaylistEditModal } from '../components/playlists/PlaylistEditModal';
import { PlaylistDownloadPanel } from '../components/playlists/PlaylistDownloadPanel';
import { getPlaylistIcon, getPlaylistKindLabel } from '../components/playlists/playlistUtils';
import { usePlaylistDetail } from '../hooks/usePlaylistDetail';
import './PlaylistDetail.css';

export function PlaylistDetail() {
  const { id } = useParams<{ id: string }>();
  const pd = usePlaylistDetail(id);
  const { playlist, loading, fetchError, navigate } = pd;

  if (loading) {
    return (
      <div className="atum-page pd-page" aria-busy="true">
        <div className="pd-skeleton-back">
          <Skeleton width="4rem" height="1.25rem" borderRadius="6px" />
        </div>
        <div className="pd-header">
          <div className="pd-header-visual">
            <Skeleton width="120px" height="120px" borderRadius="12px" />
          </div>
          <div className="pd-header-info">
            <Skeleton width="70%" height="1.3rem" borderRadius="4px" />
            <Skeleton width="40%" height="0.9rem" borderRadius="4px" className="pd-skeleton-meta" />
          </div>
        </div>
        <div className="pd-skeleton-tracks">
          {Array.from({ length: 6 }, (_, i) => (
            <SkeletonRow key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (!loading && (!playlist || fetchError)) {
    return (
      <div className="atum-page pd-page">
        <button type="button" className="pd-back" onClick={() => navigate('/playlists')}>
          <IoArrowBack size={16} /> Voltar
        </button>
        <p className="pd-error">{fetchError || 'Coleção não encontrada.'}</p>
      </div>
    );
  }

  if (!playlist) return null;

  const isDynamic = playlist.kind === 'dynamic_rules' || playlist.kind === 'dynamic_ai';

  return (
    <div className="atum-page pd-page">
      <button type="button" className="pd-back" onClick={() => navigate('/playlists')}>
        <IoArrowBack size={16} /> Coleções
      </button>

      <div className="pd-header">
        <div className="pd-header-visual">
          <PlaylistCover
            playlistId={playlist.id}
            fallbackIcon={getPlaylistIcon(playlist.kind, playlist.system_kind)}
            className="pd-cover"
          />
        </div>
        <div className="pd-header-info">
          <h1 className="pd-name">{playlist.name}</h1>
          <span className="pd-meta">
            {getPlaylistKindLabel(playlist.kind)} · {playlist.tracks.length} {playlist.tracks.length === 1 ? 'faixa' : 'faixas'}
          </span>
          {playlist.description && <p className="pd-description">{playlist.description}</p>}
          {playlist.kind === 'dynamic_ai' && playlist.ai_prompt && (
            <p className="pd-prompt">Prompt: &quot;{playlist.ai_prompt}&quot;</p>
          )}
          {playlist.ai_notes && (
            <div className="pd-notes">
              <h3 className="pd-notes-title">Notas da construção</h3>
              <p className="pd-notes-text">{playlist.ai_notes}</p>
            </div>
          )}
          {playlist.kind === 'dynamic_rules' && playlist.rules && playlist.rules.length > 0 && (
            <div className="pd-rules">
              {playlist.rules.map((r, i) => (
                <span key={i} className={`pd-rule-chip pd-rule-chip--${r.kind}`}>
                  {r.kind === 'include' ? '+' : '-'} {r.type}: {r.value}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="pd-actions">
        <button type="button" className="atum-btn atum-btn-primary" onClick={pd.playAll} disabled={playlist.tracks.length === 0}>
          <IoPlay size={16} /> Reproduzir
        </button>
        {isDynamic && (
          <button type="button" className="atum-btn" onClick={pd.handleRegenerate} disabled={pd.regenerating}>
            <IoRefresh size={16} /> {pd.regenerating ? 'Gerando…' : 'Regenerar'}
          </button>
        )}
        {!playlist.system_kind && (
          <button type="button" className="atum-btn" onClick={pd.openEdit}>
            <IoCreate size={16} /> Editar
          </button>
        )}
        <button type="button" className="atum-btn" onClick={() => pd.setDownloadOpen(!pd.downloadOpen)}>
          <IoDownload size={16} /> Download
        </button>
        <a href={`/api/playlists/${playlist.id}/download/m3u`} className="atum-btn" download>
          <IoDocument size={16} /> .m3u
        </a>
        {!playlist.system_kind && (
          <button type="button" className="atum-btn atum-btn--danger" onClick={pd.deletePlaylist}>
            <IoTrash size={16} /> Excluir
          </button>
        )}
      </div>

      <PlaylistEditModal
        open={pd.editing}
        onClose={() => pd.setEditing(false)}
        editName={pd.editName}
        setEditName={pd.setEditName}
        editDescription={pd.editDescription}
        setEditDescription={pd.setEditDescription}
        editPrompt={pd.editPrompt}
        setEditPrompt={pd.setEditPrompt}
        playlistId={playlist.id}
        hasCustomCover={!!playlist.cover_path}
        onCoverUpload={pd.handleCoverUpload}
        onSave={pd.handleSaveEdit}
        isDynamicAI={playlist.kind === 'dynamic_ai'}
      />

      <PlaylistDownloadPanel
        open={pd.downloadOpen}
        onClose={() => pd.setDownloadOpen(false)}
        selectedSize={pd.selectedSize}
        setSelectedSize={pd.setSelectedSize}
        playlistId={playlist.id}
      />

      {playlist.tracks.length === 0 ? (
        <div className="pd-empty">
          <p>
            {isDynamic
              ? 'Clique em "Regenerar" para gerar faixas com base nas regras/prompt.'
              : 'Nenhuma faixa nesta coleção.'}
          </p>
          {isDynamic && (
            <button type="button" className="atum-btn atum-btn-primary" onClick={pd.handleRegenerate} disabled={pd.regenerating}>
              <IoRefresh size={16} /> {pd.regenerating ? 'Gerando…' : 'Gerar faixas'}
            </button>
          )}
        </div>
      ) : (
        <div className="pd-tracks">
          {playlist.tracks.map((t, i) => (
            <div key={t.id ?? `${t.item_id}-${t.file_index}-${i}`} className="pd-track">
              <span className="pd-track-num">{i + 1}</span>
              <button type="button" className="pd-track-play" onClick={() => pd.playTrack(i)} aria-label="Reproduzir">
                <IoPlay size={14} />
              </button>
              <div className="pd-track-info">
                <span className="pd-track-name">{t.file_name || t.item_name || '—'}</span>
                {t.artist && <span className="pd-track-artist">{t.artist}</span>}
              </div>
              {t.play_count != null && t.play_count > 0 && (
                <span className="pd-track-plays">{t.play_count}x</span>
              )}
              {!playlist.system_kind && playlist.kind === 'static' && (
                <button type="button" className="pd-track-remove" onClick={() => pd.removeTrack(t.id)} aria-label="Remover">
                  <IoClose size={14} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
