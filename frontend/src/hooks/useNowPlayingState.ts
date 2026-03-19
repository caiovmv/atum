import { useState, useRef, useCallback, useEffect } from 'react';
import { createAudioEngine, type AudioEngine } from '../audio/audioEngine';
import { loadDspState, saveDspState, applyDspToEngine } from '../audio/dspPersist';
import { incrementPlayCount } from '../api/playlists';
import type { NowPlayingTrack } from '../contexts/NowPlayingContext';

function buildStreamUrl(itemId: number, fileIndex: number, source: string): string {
  return source === 'import'
    ? `/api/library/imported/${itemId}/stream?file_index=${fileIndex}`
    : `/api/library/${itemId}/stream?file_index=${fileIndex}`;
}

function reportPlayCount(source: string, itemId: number, fileIndex: number): void {
  incrementPlayCount({ source, item_id: itemId, file_index: fileIndex }).catch((e) => {
    if (import.meta.env.DEV) console.warn('[NowPlayingContext] incrementPlayCount failed', e);
  });
}

function pickRandom(length: number, exclude: number): number {
  if (length <= 1) return 0;
  let idx: number;
  do {
    idx = Math.floor(Math.random() * length);
  } while (idx === exclude && length > 1);
  return idx;
}

export function useNowPlayingState(audioRef: React.RefObject<HTMLAudioElement | null>) {
  const [track, setTrack] = useState<NowPlayingTrack | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [receiverActive, setReceiverActive] = useState(false);
  const [volume, setVolumeState] = useState(() => loadDspState().volume ?? 50);
  const [engine, setEngine] = useState<AudioEngine | null>(null);
  const [shuffled, setShuffled] = useState(false);

  const receiverActiveRef = useRef(false);
  const trackRef = useRef<NowPlayingTrack | null>(null);
  const currentTimeRef = useRef(0);
  const isPlayingRef = useRef(false);
  const shuffledRef = useRef(false);
  const engineRef = useRef<AudioEngine | null>(null);

  useEffect(() => {
    trackRef.current = track;
  }, [track]);
  useEffect(() => {
    engineRef.current = engine;
  }, [engine]);
  useEffect(() => {
    currentTimeRef.current = currentTime;
  }, [currentTime]);
  useEffect(() => {
    isPlayingRef.current = isPlaying;
  }, [isPlaying]);

  const ensureEngine = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return null;
    const eng = createAudioEngine(audio);
    eng.ctx.resume().catch(() => {});
    engineRef.current = eng;
    setEngine(eng);
    return eng;
  }, [audioRef]);

  const play = useCallback(
    (newTrack: NowPlayingTrack) => {
      setTrack(newTrack);
      trackRef.current = newTrack;
      setCurrentTime(0);
      setDuration(0);
      setIsPlaying(true);

      if (!receiverActiveRef.current) {
        const audio = audioRef.current;
        if (audio) {
          audio.src = newTrack.streamUrl;
          const eng = ensureEngine();
          if (eng) applyDspToEngine(eng, loadDspState());
          audio.play().catch(() => {});
        }
      }
    },
    [ensureEngine, audioRef]
  );

  const pause = useCallback(() => {
    setIsPlaying(false);
    if (!receiverActiveRef.current) {
      audioRef.current?.pause();
    }
  }, [audioRef]);

  const resume = useCallback(() => {
    setIsPlaying(true);
    if (!receiverActiveRef.current) {
      const audio = audioRef.current;
      if (audio) {
        const eng = (audio as unknown as Record<string, unknown>)['__receiverEngine'] as AudioEngine | undefined;
        if (eng?.ctx.state === 'suspended') eng.ctx.resume().catch(() => {});
        audio.play().catch(() => {});
      }
    }
  }, [audioRef]);

  const stop = useCallback(() => {
    setTrack(null);
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.src = '';
    }
  }, [audioRef]);

  const seekTo = useCallback(
    (time: number) => {
      setCurrentTime(time);
      if (!receiverActiveRef.current) {
        const audio = audioRef.current;
        if (audio) audio.currentTime = time;
      }
    },
    [audioRef]
  );

  const updateTime = useCallback((time: number) => {
    setCurrentTime(time);
    currentTimeRef.current = time;
  }, []);

  const updateDuration = useCallback((dur: number) => {
    setDuration(dur);
  }, []);

  const updatePlaying = useCallback((playing: boolean) => {
    setIsPlaying(playing);
    isPlayingRef.current = playing;
  }, []);

  const setPlaybackEngine = useCallback((eng: AudioEngine | null) => {
    engineRef.current = eng;
    setEngine(eng);
  }, []);

  const setVolume = useCallback(
    (vol: number) => {
      setVolumeState(vol);
      const audio = audioRef.current;
      if (audio && !receiverActiveRef.current) {
        const eng = engineRef.current ?? ensureEngine();
        if (eng) {
          const dsp = loadDspState();
          dsp.volume = vol;
          applyDspToEngine(eng, dsp);
        }
      }
      saveDspState({ volume: vol });
    },
    [ensureEngine, audioRef]
  );

  const goNext = useCallback(() => {
    const t = trackRef.current;
    if (!t) return;

    const queue = t.radioQueue;
    const qIdx = t.radioQueueIndex ?? 0;
    const fIdx = t.fileIndex ?? 0;
    const fCount = t.fileCount ?? 1;
    const isRadio = queue && queue.length > 0;
    const isAlbum = !isRadio && fCount > 1;

    if (isRadio) {
      const nextIdx = shuffledRef.current ? pickRandom(queue.length, qIdx) : qIdx + 1;
      if (nextIdx >= queue.length) return;
      const next = queue[nextIdx];
      const src = (next.source || 'download') as 'download' | 'import';
      play({
        ...t,
        id: next.id,
        title: next.file_name || next.item_name || next.name || '—',
        artist: next.artist,
        streamUrl: buildStreamUrl(next.id, next.file_index ?? 0, src),
        source: src === 'import' ? 'import' : 'download',
        contentType: next.content_type || t.contentType,
        fileIndex: next.file_index ?? 0,
        radioQueueIndex: nextIdx,
      });
    } else if (isAlbum) {
      const nextFile = shuffledRef.current ? pickRandom(fCount, fIdx) : fIdx + 1;
      if (nextFile >= fCount) return;
      const names = t.fileNames;
      play({
        ...t,
        title: names?.[nextFile] || t.album || '—',
        streamUrl: buildStreamUrl(t.id, nextFile, t.source),
        fileIndex: nextFile,
      });
    }
  }, [play]);

  const goPrev = useCallback(() => {
    const t = trackRef.current;
    if (!t) return;

    const queue = t.radioQueue;
    const qIdx = t.radioQueueIndex ?? 0;
    const fIdx = t.fileIndex ?? 0;
    const fCount = t.fileCount ?? 1;
    const isRadio = queue && queue.length > 0;
    const isAlbum = !isRadio && fCount > 1;

    if (isRadio) {
      const prevIdx = shuffledRef.current ? pickRandom(queue.length, qIdx) : qIdx - 1;
      if (prevIdx < 0) return;
      const prev = queue[prevIdx];
      const src = (prev.source || 'download') as 'download' | 'import';
      play({
        ...t,
        id: prev.id,
        title: prev.file_name || prev.item_name || prev.name || '—',
        artist: prev.artist,
        streamUrl: buildStreamUrl(prev.id, prev.file_index ?? 0, src),
        source: src === 'import' ? 'import' : 'download',
        contentType: prev.content_type || t.contentType,
        fileIndex: prev.file_index ?? 0,
        radioQueueIndex: prevIdx,
      });
    } else if (isAlbum) {
      const prevFile = shuffledRef.current ? pickRandom(fCount, fIdx) : fIdx - 1;
      if (prevFile < 0) return;
      const names = t.fileNames;
      play({
        ...t,
        title: names?.[prevFile] || t.album || '—',
        streamUrl: buildStreamUrl(t.id, prevFile, t.source),
        fileIndex: prevFile,
      });
    }
  }, [play]);

  const toggleShuffle = useCallback(() => {
    setShuffled((prev) => {
      shuffledRef.current = !prev;
      return !prev;
    });
  }, []);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || receiverActive) return;

    const onTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      currentTimeRef.current = audio.currentTime;
    };
    const onDurationChange = () => setDuration(audio.duration || 0);
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const onEnded = () => {
      setIsPlaying(false);
      const t = trackRef.current;
      if (!t) return;
      reportPlayCount(t.source, t.id, t.fileIndex ?? 0);
      const queue = t.radioQueue;
      const qIdx = t.radioQueueIndex ?? 0;
      const fIdx = t.fileIndex ?? 0;
      const fCount = t.fileCount ?? 1;
      const canAdvance =
        (queue && qIdx + 1 < queue.length) || (!queue && fCount > 1 && fIdx + 1 < fCount);
      if (canAdvance) {
        setTimeout(() => goNext(), 0);
      }
    };

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('durationchange', onDurationChange);
    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);
    audio.addEventListener('ended', onEnded);

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('durationchange', onDurationChange);
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('pause', onPause);
      audio.removeEventListener('ended', onEnded);
    };
  }, [receiverActive, goNext, audioRef]);

  const setReceiverActiveStable = useCallback((active: boolean) => {
    const wasActive = receiverActiveRef.current;
    receiverActiveRef.current = active;
    setReceiverActive(active);

    if (active && !wasActive) {
      engineRef.current = null;
      setEngine(null);
    } else if (!active && wasActive) {
      const t = trackRef.current;
      const audio = audioRef.current;
      if (audio && t) {
        if (!audio.crossOrigin) audio.crossOrigin = 'anonymous';

        const eng = createAudioEngine(audio);
        engineRef.current = eng;
        setEngine(eng);
        eng.ctx.resume().catch(() => {});

        const dsp = loadDspState();
        applyDspToEngine(eng, dsp);
        setVolumeState(dsp.volume ?? 50);
      }
    }
  }, [audioRef]);

  return {
    track,
    isPlaying,
    currentTime,
    duration,
    receiverActive,
    volume,
    engine,
    shuffled,
    play,
    pause,
    resume,
    stop,
    seekTo,
    updateTime,
    updateDuration,
    updatePlaying,
    setVolume,
    goNext,
    goPrev,
    toggleShuffle,
    setReceiverActive: setReceiverActiveStable,
    setPlaybackEngine,
  };
}
