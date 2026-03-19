import { memo, useCallback } from 'react';
import { useNowPlaying } from '../contexts/NowPlayingContext';
import { useMediaSession } from '../hooks/useMediaSession';
import { useNowPlayingBar } from '../hooks/useNowPlayingBar';
import { CoverImage } from './CoverImage';
import { MiniVU } from './MiniVU';
import { NowPlayingBarControls } from './NowPlayingBarControls';
import './NowPlayingBar.css';

type ContentType = 'music' | 'movies' | 'tv';

function formatTime(s: number): string {
  if (!s || !Number.isFinite(s)) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, '0')}`;
}

export const NowPlayingBar = memo(function NowPlayingBar() {
  const { track, currentTime, duration, engine, receiverActive } = useNowPlaying();
  const npb = useNowPlayingBar();

  useMediaSession({
    title: track?.title || '',
    artist: track?.artist,
    album: track?.album,
    coverUrl: track ? (track.source === 'import' ? `/api/cover/file/import/${track.id}` : `/api/cover/file/${track.id}`) : undefined,
    isPlaying: npb.isPlaying && !receiverActive,
    currentTime,
    duration,
    onPlay: npb.resume,
    onPause: npb.pause,
  });

  const handlePlayPause = useCallback(() => {
    if (npb.isPlaying) npb.pause();
    else npb.resume();
  }, [npb.isPlaying, npb.pause, npb.resume]);

  if (!npb.track || npb.isOnReceiver) return null;

  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className="now-playing-bar" role="region" aria-label="Player">
      <div className="now-playing-bar-progress" aria-hidden>
        <div className="now-playing-bar-progress-fill" style={{ width: `${progressPercent}%` }} />
      </div>

      <div className="now-playing-bar-inner">
        <button
          type="button"
          className="now-playing-bar-track"
          onClick={npb.openReceiver}
          aria-label={`Abrir receiver: ${npb.track.title}`}
        >
          <div className="now-playing-bar-cover">
            <CoverImage
              contentType={(npb.track.contentType === 'movies' || npb.track.contentType === 'tv' ? npb.track.contentType : 'music') as ContentType}
              title={npb.track.title}
              size="thumb"
              downloadId={npb.track.source === 'import' ? undefined : npb.track.id}
              importId={npb.track.source === 'import' ? npb.track.id : undefined}
            />
          </div>
          <div className="now-playing-bar-info">
            <span className="now-playing-bar-title">{npb.track.title}</span>
            {npb.track.artist && <span className="now-playing-bar-artist">{npb.track.artist}</span>}
          </div>
        </button>

        <MiniVU engine={engine} isPlaying={npb.isPlaying} />

        <div className="now-playing-bar-time">
          <span>{formatTime(currentTime)}</span>
          {duration > 0 && <span className="now-playing-bar-time-sep">/</span>}
          {duration > 0 && <span>{formatTime(duration)}</span>}
        </div>

        <NowPlayingBarControls
          trackFavorited={!!npb.trackFavorited}
          onToggleFavorite={npb.handleToggleFavorite}
          addToPlaylistOpen={npb.addToPlaylistOpen}
          setAddToPlaylistOpen={npb.setAddToPlaylistOpen}
          playlists={npb.playlists}
          onAddToPlaylist={npb.handleAddToPlaylist}
          isRadio={npb.isRadio}
          onSaveQueue={npb.handleSaveQueue}
          hasQueue={npb.hasQueue}
          shuffled={npb.shuffled}
          onToggleShuffle={npb.toggleShuffle}
          hasPrev={npb.hasPrev}
          onPrev={npb.goPrev}
          isPlaying={npb.isPlaying}
          onPlayPause={handlePlayPause}
          hasNext={npb.hasNext}
          onNext={npb.goNext}
          volume={npb.volume}
          onVolumeChange={npb.setVolume}
          volumeOpen={npb.volumeOpen}
          setVolumeOpen={npb.setVolumeOpen}
          onOpenReceiver={npb.openReceiver}
          onStop={npb.stop}
        />
      </div>
    </div>
  );
});
