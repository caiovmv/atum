import { createContext, useContext, useRef, useMemo, type ReactNode } from 'react';
import { useNowPlayingState } from '../hooks/useNowPlayingState';

export interface NowPlayingTrack {
  id: number;
  title: string;
  artist?: string;
  album?: string;
  coverUrl?: string;
  streamUrl: string;
  source: 'download' | 'import';
  contentType: string;
  fileIndex?: number;
  fileCount?: number;
  fileNames?: string[];
  radioQueue?: RadioQueueItem[];
  radioQueueIndex?: number;
}

export interface RadioQueueItem {
  id: number;
  source?: string;
  file_index?: number;
  file_name?: string;
  item_name?: string;
  artist?: string;
  name?: string;
  content_type?: string;
}

interface NowPlayingState {
  track: NowPlayingTrack | null;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  receiverActive: boolean;
  volume: number;
  engine: import('../audio/audioEngine').AudioEngine | null;
  shuffled: boolean;
}

interface NowPlayingActions {
  play(track: NowPlayingTrack): void;
  pause(): void;
  resume(): void;
  stop(): void;
  seekTo(time: number): void;
  setReceiverActive(active: boolean): void;
  updateTime(time: number): void;
  updateDuration(dur: number): void;
  updatePlaying(playing: boolean): void;
  setVolume(vol: number): void;
  goNext(): void;
  goPrev(): void;
  toggleShuffle(): void;
  setPlaybackEngine(engine: import('../audio/audioEngine').AudioEngine | null): void;
  audioRef: React.RefObject<HTMLAudioElement | null>;
}

type NowPlayingContextType = NowPlayingState & NowPlayingActions;

const NowPlayingCtx = createContext<NowPlayingContextType | null>(null);

export function useNowPlaying(): NowPlayingContextType {
  const ctx = useContext(NowPlayingCtx);
  if (!ctx) throw new Error('useNowPlaying must be used within NowPlayingProvider');
  return ctx;
}

export function NowPlayingProvider({ children }: { children: ReactNode }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const state = useNowPlayingState(audioRef);

  const value = useMemo<NowPlayingContextType>(
    () => ({ ...state, audioRef }),
    [state, audioRef]
  );

  return (
    <NowPlayingCtx.Provider value={value}>
      <audio ref={audioRef} preload="auto" crossOrigin="anonymous" style={{ display: 'none' }} />
      {children}
    </NowPlayingCtx.Provider>
  );
}
