import { useState, useCallback, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useNowPlaying, type RadioQueueItem } from '../contexts/NowPlayingContext';
import { useFavorites } from '../contexts/FavoritesContext';
import { useToast } from '../contexts/ToastContext';
import { getPlaylists, addTrackToPlaylist, addFromQueue } from '../api/playlists';

export function useNowPlayingBar() {
  const {
    track,
    isPlaying,
    pause,
    resume,
    stop,
    goNext,
    goPrev,
    shuffled,
    toggleShuffle,
    volume,
    setVolume,
  } = useNowPlaying();
  const { isFavorited, toggleFavorite } = useFavorites();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const [addToPlaylistOpen, setAddToPlaylistOpen] = useState(false);
  const [playlists, setPlaylists] = useState<{ id: number; name: string; system_kind?: string }[]>([]);
  const [volumeOpen, setVolumeOpen] = useState(false);

  const isOnReceiver = location.pathname.startsWith('/play-receiver');

  const radioQueue = track?.radioQueue ?? null;
  const radioQueueIndex = track?.radioQueueIndex ?? 0;
  const fileIndex = track?.fileIndex ?? 0;
  const fileCount = track?.fileCount ?? 1;
  const isRadio = radioQueue != null && radioQueue.length > 0;
  const isAlbum = !isRadio && fileCount > 1;
  const hasQueue = isRadio || isAlbum;

  const hasNext = shuffled
    ? hasQueue
    : isRadio
      ? radioQueueIndex + 1 < radioQueue!.length
      : isAlbum
        ? fileIndex + 1 < fileCount
        : false;
  const hasPrev = shuffled
    ? hasQueue
    : isRadio
      ? radioQueueIndex > 0
      : isAlbum
        ? fileIndex > 0
        : false;

  const openReceiver = useCallback(() => {
    if (!track) return;
    const sourceParam = track.source === 'import' ? '?source=import' : '';
    const fileParam = track.fileIndex != null ? `${sourceParam ? '&' : '?'}file=${track.fileIndex}` : '';
    navigate(`/play-receiver/${track.id}${sourceParam}${fileParam}`, {
      state: track.radioQueue
        ? { radioQueue: track.radioQueue, radioQueueIndex: track.radioQueueIndex ?? 0 }
        : undefined,
    });
  }, [track, navigate]);

  useEffect(() => {
    if (!addToPlaylistOpen) return;
    getPlaylists()
      .then((data) => setPlaylists(data.filter((p) => !p.system_kind)))
      .catch((err) => {
        if (import.meta.env.DEV) console.warn('[NowPlayingBar] playlists fetch failed', err);
      });
  }, [addToPlaylistOpen]);

  const handleToggleFavorite = useCallback(() => {
    if (!track) return;
    toggleFavorite(track.source, track.id, track.fileIndex ?? 0, track.title);
  }, [track, toggleFavorite]);

  const handleAddToPlaylist = useCallback(
    async (playlistId: number) => {
      if (!track) return;
      try {
        await addTrackToPlaylist(playlistId, [
          {
            source: track.source,
            item_id: track.id,
            file_index: track.fileIndex ?? 0,
            file_name: track.title,
          },
        ]);
      } catch {
        if (import.meta.env.DEV) console.warn('[NowPlayingBar] addTrackToPlaylist failed');
      }
      setAddToPlaylistOpen(false);
    },
    [track]
  );

  const handleSaveQueue = useCallback(async () => {
    if (!radioQueue || radioQueue.length === 0) return;
    const name = window.prompt('Nome da playlist:');
    if (!name?.trim()) return;
    try {
      const tracks = radioQueue.map((t: RadioQueueItem) => ({
        id: t.id,
        source: t.source || 'download',
        file_index: t.file_index ?? 0,
        file_name: t.file_name || t.item_name || t.name,
      }));
      await addFromQueue(name.trim(), tracks);
      showToast(`Playlist "${name.trim()}" salva`);
    } catch {
      showToast('Erro ao salvar playlist');
    }
  }, [radioQueue, showToast]);

  const trackFavorited = track ? isFavorited(track.source, track.id, track.fileIndex ?? 0) : false;

  return {
    track,
    isPlaying,
    pause,
    resume,
    stop,
    goNext,
    goPrev,
    shuffled,
    toggleShuffle,
    volume,
    setVolume,
    hasNext,
    hasPrev,
    isRadio,
    hasQueue,
    isOnReceiver,
    addToPlaylistOpen,
    setAddToPlaylistOpen,
    playlists,
    volumeOpen,
    setVolumeOpen,
    openReceiver,
    handleToggleFavorite,
    handleAddToPlaylist,
    handleSaveQueue,
    trackFavorited,
  };
}
