import { useEffect, useRef } from 'react';

interface MediaSessionOptions {
  title: string;
  artist?: string;
  album?: string;
  coverUrl?: string;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  onPlay?: () => void;
  onPause?: () => void;
  onSeekBackward?: () => void;
  onSeekForward?: () => void;
  onPreviousTrack?: () => void;
  onNextTrack?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
}

export function useMediaSession({
  title,
  artist,
  album,
  coverUrl,
  isPlaying,
  currentTime,
  duration,
  onPlay,
  onPause,
  onSeekBackward,
  onSeekForward,
  onPreviousTrack,
  onNextTrack,
  hasPrev,
  hasNext,
}: MediaSessionOptions): void {
  const handlersRef = useRef({ onPlay, onPause, onSeekBackward, onSeekForward, onPreviousTrack, onNextTrack });
  handlersRef.current = { onPlay, onPause, onSeekBackward, onSeekForward, onPreviousTrack, onNextTrack };

  useEffect(() => {
    if (!('mediaSession' in navigator)) return;

    const artwork: MediaImage[] = [];
    if (coverUrl) {
      const absUrl = coverUrl.startsWith('/')
        ? new URL(coverUrl, window.location.origin).href
        : coverUrl;
      artwork.push({ src: absUrl, sizes: '512x512', type: 'image/jpeg' });
    }

    navigator.mediaSession.metadata = new MediaMetadata({
      title: title || 'Atum',
      artist: artist || '',
      album: album || '',
      artwork,
    });
  }, [title, artist, album, coverUrl]);

  useEffect(() => {
    if (!('mediaSession' in navigator)) return;
    navigator.mediaSession.playbackState = isPlaying ? 'playing' : 'paused';
  }, [isPlaying]);

  useEffect(() => {
    if (!('mediaSession' in navigator) || !('setPositionState' in navigator.mediaSession)) return;
    if (duration <= 0) return;
    try {
      navigator.mediaSession.setPositionState({
        duration: Math.max(0, duration),
        playbackRate: 1,
        position: Math.max(0, Math.min(currentTime, duration)),
      });
    } catch {
      // position state may throw if values are invalid
    }
  }, [currentTime, duration]);

  useEffect(() => {
    if (!('mediaSession' in navigator)) return;

    const handlers: Array<[MediaSessionAction, MediaSessionActionHandler | null]> = [
      ['play', () => handlersRef.current.onPlay?.()],
      ['pause', () => handlersRef.current.onPause?.()],
      ['seekbackward', () => handlersRef.current.onSeekBackward?.()],
      ['seekforward', () => handlersRef.current.onSeekForward?.()],
      ['previoustrack', hasPrev ? (() => handlersRef.current.onPreviousTrack?.()) : null],
      ['nexttrack', hasNext ? (() => handlersRef.current.onNextTrack?.()) : null],
    ];

    for (const [action, handler] of handlers) {
      try {
        navigator.mediaSession.setActionHandler(action, handler);
      } catch {
        // some actions may not be supported
      }
    }

    return () => {
      for (const [action] of handlers) {
        try {
          navigator.mediaSession.setActionHandler(action, null);
        } catch {
          // ignore
        }
      }
    };
  }, [hasPrev, hasNext]);
}
