import {
  IoPlay,
  IoPause,
  IoPlaySkipBack,
  IoPlaySkipForward,
  IoChevronUp,
  IoPower,
  IoShuffle,
  IoHeart,
  IoHeartOutline,
  IoAdd,
} from 'react-icons/io5';
import { NowPlayingBarVolume } from './NowPlayingBarVolume';
import { NowPlayingBarPlaylistPopup } from './NowPlayingBarPlaylistPopup';

interface NowPlayingBarControlsProps {
  trackFavorited: boolean;
  onToggleFavorite: () => void;
  addToPlaylistOpen: boolean;
  setAddToPlaylistOpen: (v: boolean | ((p: boolean) => boolean)) => void;
  playlists: { id: number; name: string }[];
  onAddToPlaylist: (id: number) => void;
  isRadio: boolean;
  onSaveQueue: () => void;
  hasQueue: boolean;
  shuffled: boolean;
  onToggleShuffle: () => void;
  hasPrev: boolean;
  onPrev: () => void;
  isPlaying: boolean;
  onPlayPause: () => void;
  hasNext: boolean;
  onNext: () => void;
  volume: number;
  onVolumeChange: (v: number) => void;
  volumeOpen: boolean;
  setVolumeOpen: (v: boolean | ((p: boolean) => boolean)) => void;
  onOpenReceiver: () => void;
  onStop: () => void;
}

export function NowPlayingBarControls({
  trackFavorited,
  onToggleFavorite,
  addToPlaylistOpen,
  setAddToPlaylistOpen,
  playlists,
  onAddToPlaylist,
  isRadio,
  onSaveQueue,
  hasQueue,
  shuffled,
  onToggleShuffle,
  hasPrev,
  onPrev,
  isPlaying,
  onPlayPause,
  hasNext,
  onNext,
  volume,
  onVolumeChange,
  volumeOpen,
  setVolumeOpen,
  onOpenReceiver,
  onStop,
}: NowPlayingBarControlsProps) {
  return (
    <div className="now-playing-bar-controls">
      <button
        type="button"
        className={`now-playing-bar-btn now-playing-bar-btn--fav${trackFavorited ? ' now-playing-bar-btn--fav-active' : ''}`}
        onClick={onToggleFavorite}
        aria-label={trackFavorited ? 'Remover dos favoritos' : 'Adicionar aos favoritos'}
      >
        {trackFavorited ? <IoHeart size={16} /> : <IoHeartOutline size={16} />}
      </button>

      <NowPlayingBarPlaylistPopup
        open={addToPlaylistOpen}
        onClose={() => setAddToPlaylistOpen(false)}
        playlists={playlists}
        onAddToPlaylist={onAddToPlaylist}
        onToggle={() => setAddToPlaylistOpen((p) => !p)}
      />

      {isRadio && (
        <button
          type="button"
          className="now-playing-bar-btn"
          onClick={onSaveQueue}
          aria-label="Salvar fila como playlist"
          title="Salvar fila"
        >
          <IoAdd size={16} />
        </button>
      )}

      {hasQueue && (
        <button
          type="button"
          className={`now-playing-bar-btn now-playing-bar-btn--shuffle${shuffled ? ' now-playing-bar-btn--active' : ''}`}
          onClick={onToggleShuffle}
          aria-label={shuffled ? 'Desativar aleatório' : 'Ativar aleatório'}
        >
          <IoShuffle size={15} />
        </button>
      )}

      <button type="button" className="now-playing-bar-btn" onClick={onPrev} disabled={!hasPrev} aria-label="Faixa anterior">
        <IoPlaySkipBack size={16} />
      </button>

      <button
        type="button"
        className="now-playing-bar-btn now-playing-bar-btn--play"
        onClick={onPlayPause}
        aria-label={isPlaying ? 'Pausar' : 'Reproduzir'}
      >
        {isPlaying ? <IoPause size={20} /> : <IoPlay size={20} />}
      </button>

      <button type="button" className="now-playing-bar-btn" onClick={onNext} disabled={!hasNext} aria-label="Próxima faixa">
        <IoPlaySkipForward size={16} />
      </button>

      <NowPlayingBarVolume
        volume={volume}
        onVolumeChange={onVolumeChange}
        open={volumeOpen}
        onToggle={() => setVolumeOpen((p) => !p)}
        onClose={() => setVolumeOpen(false)}
      />

      <button type="button" className="now-playing-bar-btn now-playing-bar-btn--expand" onClick={onOpenReceiver} aria-label="Abrir receiver">
        <IoChevronUp size={18} />
      </button>

      <button type="button" className="now-playing-bar-btn now-playing-bar-btn--power" onClick={onStop} aria-label="Desligar player">
        <IoPower size={16} />
      </button>
    </div>
  );
}
