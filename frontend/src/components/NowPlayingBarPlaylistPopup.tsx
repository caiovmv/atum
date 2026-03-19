import { useEffect, useRef } from 'react';
import { IoList } from 'react-icons/io5';

interface PlaylistItem {
  id: number;
  name: string;
  system_kind?: string;
}

interface NowPlayingBarPlaylistPopupProps {
  open: boolean;
  onClose: () => void;
  playlists: PlaylistItem[];
  onAddToPlaylist: (playlistId: number) => void;
  onToggle: () => void;
}

export function NowPlayingBarPlaylistPopup({
  open,
  onClose,
  playlists,
  onAddToPlaylist,
  onToggle,
}: NowPlayingBarPlaylistPopupProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener('pointerdown', handleClick);
    return () => document.removeEventListener('pointerdown', handleClick);
  }, [open, onClose]);

  return (
    <div className="now-playing-bar-playlist-wrap" ref={ref}>
      <button
        type="button"
        className="now-playing-bar-btn"
        onClick={onToggle}
        aria-label="Adicionar a playlist"
      >
        <IoList size={16} />
      </button>
      {open && (
        <div className="now-playing-bar-playlist-popup">
          {playlists.length === 0 ? (
            <span className="now-playing-bar-playlist-empty">Nenhuma playlist</span>
          ) : (
            playlists.map((p) => (
              <button
                key={p.id}
                type="button"
                className="now-playing-bar-playlist-item"
                onClick={() => onAddToPlaylist(p.id)}
                aria-label={`Adicionar à playlist ${p.name}`}
              >
                {p.name}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
