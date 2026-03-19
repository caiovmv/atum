import { useState, useEffect, useMemo, useCallback, useRef, type TouchEvent as ReactTouchEvent } from 'react';
import { useParams, useSearchParams, useLocation, useNavigate } from 'react-router-dom';
import { inferQualityMeta } from '../audio/analysis';
import type { AudioEngine } from '../audio/audioEngine';
import { useNowPlaying } from '../contexts/NowPlayingContext';
import { useFavorites } from '../contexts/FavoritesContext';
import { useToast } from '../contexts/ToastContext';
import { getLibraryItem, getLibraryItemFiles, type LibraryFile } from '../api/library';
import { getPlaylists, addTrackToPlaylist, addFromQueue } from '../api/playlists';
import { chat } from '../api/chat';
import type { SmartQueueResult } from '../components/receiver/ReceiverAI';

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

export function useReceiverPlayer() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const nowPlaying = useNowPlaying();
  const { isFavorited, toggleFavorite } = useFavorites();
  const { showToast } = useToast();

  const [item, setItem] = useState<{ id: number; name?: string; content_type?: string; source?: string } | null>(null);
  const [files, setFiles] = useState<LibraryFile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sideOpen, setSideOpen] = useState(false);
  const [aiInsight, setAiInsight] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [rpPlaylistOpen, setRpPlaylistOpen] = useState(false);
  const [rpPlaylists, setRpPlaylists] = useState<{ id: number; name: string }[]>([]);
  const [savingQueue, setSavingQueue] = useState(false);
  const [receiverEngine, setReceiverEngine] = useState<AudioEngine | null>(null);
  const [showVisualizer, setShowVisualizer] = useState(false);

  const fileIndexParam = searchParams.get('file');
  const source = searchParams.get('source');
  const radioState = location.state as { radioQueue?: RadioQueueItem[]; radioQueueIndex?: number } | null;
  const radioQueue = radioState?.radioQueue ?? null;
  const initialRadioQueueIndex = Math.max(0, radioState?.radioQueueIndex ?? 0);
  const isImport = source === 'import';
  const initializedRef = useRef(false);
  const aiRequestedFor = useRef<string>('');
  const rpPlaylistRef = useRef<HTMLDivElement>(null);
  const sheetDragRef = useRef<{ startY: number; current: number } | null>(null);
  const sheetRef = useRef<HTMLElement>(null);

  const fileIndex = useMemo(() => {
    if (fileIndexParam == null || fileIndexParam === '') return 0;
    const n = parseInt(fileIndexParam, 10);
    return Number.isNaN(n) || n < 0 ? 0 : n;
  }, [fileIndexParam]);

  const ctxTrack = nowPlaying.track;
  const activeFileIndex = ctxTrack?.fileIndex ?? fileIndex;
  const activeRadioQueueIndex = ctxTrack?.radioQueueIndex ?? initialRadioQueueIndex;
  const safeFileIndex = activeFileIndex >= files.length ? 0 : activeFileIndex;

  const streamUrl = useMemo(() => {
    if (ctxTrack?.streamUrl) return ctxTrack.streamUrl;
    if (!item || files.length === 0) return '';
    return isImport
      ? `/api/library/imported/${item.id}/stream?file_index=${safeFileIndex}`
      : `/api/library/${item.id}/stream?file_index=${safeFileIndex}`;
  }, [ctxTrack?.streamUrl, item, files.length, safeFileIndex, isImport]);

  const isVideo = item?.content_type === 'movies' || item?.content_type === 'tv';
  const isRadio = radioQueue && radioQueue.length > 0;
  const hasNext = isRadio
    ? activeRadioQueueIndex + 1 < radioQueue!.length
    : safeFileIndex < files.length - 1;
  const hasPrev = isRadio ? activeRadioQueueIndex > 0 : safeFileIndex > 0;

  const currentFile = useMemo(() => {
    if (isRadio && ctxTrack && ctxTrack.id !== item?.id) {
      return { name: ctxTrack.title, size: 0, index: ctxTrack.fileIndex ?? 0 } as LibraryFile;
    }
    return files[safeFileIndex];
  }, [isRadio, ctxTrack, item?.id, files, safeFileIndex]);

  const title = useMemo(() => {
    if (isRadio) {
      const qItem = radioQueue![activeRadioQueueIndex];
      const name = ctxTrack?.title || currentFile?.name || qItem?.file_name || qItem?.item_name || item?.name || '—';
      const artist = ctxTrack?.artist || qItem?.artist;
      return artist ? `${name} · ${artist}` : name;
    }
    return currentFile?.name || item?.name || '—';
  }, [isRadio, radioQueue, activeRadioQueueIndex, ctxTrack, currentFile, item]);

  const qualityMeta = useMemo(
    () => inferQualityMeta(item?.content_type ?? null, currentFile?.name ?? ''),
    [item?.content_type, currentFile?.name]
  );

  const currentSource = useMemo(() => {
    const ctxSrc = nowPlaying.track?.source;
    if (ctxSrc) return ctxSrc;
    return isImport ? 'import' : 'download';
  }, [nowPlaying.track?.source, isImport]);

  const currentItemId = nowPlaying.track?.id ?? (item?.id ?? 0);
  const currentFileIdx = nowPlaying.track?.fileIndex ?? safeFileIndex;
  const trackFavorited = isFavorited(currentSource, currentItemId, currentFileIdx);

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
    const signal = controller.signal;
    if (!initializedRef.current) setLoading(true);
    setError(null);
    Promise.all([
      getLibraryItem(numId, isImport, { signal }),
      getLibraryItemFiles(numId, isImport, { signal }),
    ])
      .then(([itemData, filesData]) => {
        setItem(itemData);
        setFiles(filesData.files);
        initializedRef.current = true;
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        const msg = err instanceof Error ? err.message : 'Erro';
        setError(msg.includes('404') ? 'Item não encontrado.' : msg);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [id, isImport]);

  useEffect(() => {
    nowPlaying.setReceiverActive(true);
    return () => nowPlaying.setReceiverActive(false);
  }, [nowPlaying]);

  useEffect(() => {
    if (!item || !files.length) return;
    const fileStreamUrl = isImport
      ? `/api/library/imported/${item.id}/stream?file_index=${safeFileIndex}`
      : `/api/library/${item.id}/stream?file_index=${safeFileIndex}`;
    nowPlaying.play({
      id: item.id,
      title: currentFile?.name || item.name || '—',
      artist: isRadio && radioQueue?.[activeRadioQueueIndex]?.artist ? radioQueue[activeRadioQueueIndex].artist : undefined,
      album: item.name,
      coverUrl: isImport ? `/api/cover/file/import/${item.id}` : `/api/cover/file/${item.id}`,
      streamUrl: fileStreamUrl,
      source: isImport ? 'import' : 'download',
      contentType: item.content_type ?? 'music',
      fileIndex: safeFileIndex,
      fileCount: files.length,
      fileNames: files.map((f) => f.name),
      radioQueue: radioQueue ?? undefined,
      radioQueueIndex: activeRadioQueueIndex,
    });
  }, [item?.id, files.length, safeFileIndex, isImport, isRadio, radioQueue, activeRadioQueueIndex, currentFile, item, nowPlaying]);

  useEffect(() => {
    if (!rpPlaylistOpen) return;
    getPlaylists()
      .then((data) => setRpPlaylists(data.filter((p) => !p.system_kind).map((p) => ({ id: p.id, name: p.name }))))
      .catch((e) => {
        if (import.meta.env.DEV) console.warn('[ReceiverPlayer] getPlaylists failed', e);
        setRpPlaylists([]);
      });
    const handleClick = (e: MouseEvent) => {
      if (rpPlaylistRef.current && !rpPlaylistRef.current.contains(e.target as Node)) setRpPlaylistOpen(false);
    };
    document.addEventListener('pointerdown', handleClick);
    return () => document.removeEventListener('pointerdown', handleClick);
  }, [rpPlaylistOpen]);

  const goBack = useCallback(() => {
    if (window.history.length > 1) navigate(-1);
    else navigate('/library');
  }, [navigate]);

  const handleSheetTouchStart = useCallback((e: ReactTouchEvent) => {
    sheetDragRef.current = { startY: e.touches[0].clientY, current: 0 };
  }, []);

  const handleSheetTouchMove = useCallback((e: ReactTouchEvent) => {
    if (!sheetDragRef.current) return;
    const dy = Math.max(0, e.touches[0].clientY - sheetDragRef.current.startY);
    sheetDragRef.current.current = dy;
    if (sheetRef.current) {
      sheetRef.current.style.transform = `translateY(${dy}px)`;
      sheetRef.current.style.transition = 'none';
    }
  }, []);

  const handleSheetTouchEnd = useCallback(() => {
    if (!sheetDragRef.current || !sheetRef.current) return;
    sheetRef.current.style.transition = '';
    if (sheetDragRef.current.current > 120) {
      setSideOpen(false);
      try {
        navigator.vibrate?.(8);
      } catch {
        /* no vibration */
      }
    }
    sheetRef.current.style.transform = '';
    sheetDragRef.current = null;
  }, []);

  const fetchAiInsight = useCallback(() => {
    const trackKey = `${item?.id}-${safeFileIndex}`;
    if (aiLoading || aiRequestedFor.current === trackKey) return;
    aiRequestedFor.current = trackKey;
    setAiLoading(true);
    setAiInsight(null);

    const trackName = currentFile?.name || item?.name || '';
    const artistName = isRadio && radioQueue?.[activeRadioQueueIndex]?.artist ? radioQueue[activeRadioQueueIndex].artist : undefined;

    chat({
      messages: [
        {
          role: 'user',
          content: `Dê informações breves e interessantes sobre a faixa "${trackName}"${artistName ? ` do artista ${artistName}` : ''}. Inclua: gênero, curiosidades, sugestão de configuração de EQ (bass/mid/treble). Responda em 3-4 linhas.`,
        },
      ],
      context: {
        track: trackName,
        artist: artistName,
        album: item?.name,
        codec: qualityMeta?.codec,
        bitrate: qualityMeta?.bitrate != null ? `${qualityMeta.bitrate} kbps` : undefined,
      },
    })
      .then((data) => setAiInsight(data.content))
      .catch(() => setAiInsight(null))
      .finally(() => setAiLoading(false));
  }, [item, safeFileIndex, currentFile, radioQueue, activeRadioQueueIndex, qualityMeta, aiLoading]);

  const handleToggleFav = useCallback(() => {
    const fname = currentFile?.name || item?.name || '';
    toggleFavorite(currentSource, currentItemId, currentFileIdx, fname);
  }, [currentSource, currentItemId, currentFileIdx, currentFile, item, toggleFavorite]);

  const handleAddToPlaylist = useCallback(
    async (playlistId: number) => {
      try {
        await addTrackToPlaylist(playlistId, [
          {
            source: currentSource,
            item_id: currentItemId,
            file_index: currentFileIdx,
            file_name: currentFile?.name,
          },
        ]);
      } catch (e) {
        if (import.meta.env.DEV) console.warn('[ReceiverPlayer] addTrackToPlaylist failed', e);
        showToast('Erro ao adicionar à playlist');
      }
      setRpPlaylistOpen(false);
    },
    [currentSource, currentItemId, currentFileIdx, currentFile, showToast]
  );

  const handleSmartQueue = useCallback(
    (result: SmartQueueResult) => {
      if (result.ids.length === 0) return;
      const queue: RadioQueueItem[] = result.ids.map((qid) => ({
        id: qid,
        source: 'download',
      }));
      const first = queue[0];
      navigate(`/play-receiver/${first.id}?source=download`, {
        state: { radioQueue: queue, radioQueueIndex: 0 },
      });
    },
    [navigate]
  );

  const handleEngineReady = useCallback(
    (eng: AudioEngine | null) => {
      setReceiverEngine(eng);
      nowPlaying.setPlaybackEngine(eng);
    },
    [nowPlaying]
  );

  const handleSaveQueueAsPlaylist = useCallback(async () => {
    if (!radioQueue || radioQueue.length === 0) return;
    const name = window.prompt('Nome da playlist:');
    if (!name?.trim()) return;
    setSavingQueue(true);
    try {
      const tracks = radioQueue.map((t) => ({
        id: t.id,
        source: t.source || 'download',
        file_index: t.file_index ?? 0,
        file_name: t.file_name || t.item_name || t.name,
      }));
      await addFromQueue(name.trim(), tracks);
      showToast(`Playlist "${name.trim()}" salva`);
    } catch {
      showToast('Erro ao salvar playlist');
    } finally {
      setSavingQueue(false);
    }
  }, [radioQueue, showToast]);

  const goToQueueTrack = useCallback(
    (index: number) => {
      if (!radioQueue || index < 0 || index >= radioQueue.length) return;
      const target = radioQueue[index];
      const src = (target.source || 'download') as 'download' | 'import';
      nowPlaying.play({
        ...(nowPlaying.track ?? ({} as never)),
        id: target.id,
        title: target.file_name || target.item_name || target.name || '—',
        artist: target.artist,
        streamUrl:
          src === 'import'
            ? `/api/library/imported/${target.id}/stream?file_index=${target.file_index ?? 0}`
            : `/api/library/${target.id}/stream?file_index=${target.file_index ?? 0}`,
        source: src === 'import' ? 'import' : 'download',
        contentType: target.content_type || item?.content_type || 'music',
        fileIndex: target.file_index ?? 0,
        radioQueue,
        radioQueueIndex: index,
      });
    },
    [radioQueue, item, nowPlaying]
  );

  const goToFileTrack = useCallback(
    (idx: number) => {
      if (idx < 0 || idx >= files.length || !item) return;
      const fileStreamUrl = isImport
        ? `/api/library/imported/${item.id}/stream?file_index=${idx}`
        : `/api/library/${item.id}/stream?file_index=${idx}`;
      nowPlaying.play({
        ...(nowPlaying.track ?? ({} as never)),
        id: item.id,
        title: files[idx]?.name || item.name || '—',
        streamUrl: fileStreamUrl,
        source: isImport ? 'import' : 'download',
        contentType: item.content_type ?? 'music',
        fileIndex: idx,
        fileCount: files.length,
        fileNames: files.map((f) => f.name),
      });
    },
    [files, item, isImport, nowPlaying]
  );

  return {
    loading,
    error,
    item,
    files,
    streamUrl,
    title,
    isVideo,
    isRadio,
    isImport,
    radioQueue,
    activeRadioQueueIndex,
    safeFileIndex,
    currentFile,
    qualityMeta,
    hasNext,
    hasPrev,
    ctxTrack,
    trackFavorited,
    sideOpen,
    setSideOpen,
    aiInsight,
    aiLoading,
    rpPlaylistOpen,
    setRpPlaylistOpen,
    rpPlaylists,
    rpPlaylistRef,
    savingQueue,
    receiverEngine,
    showVisualizer,
    setShowVisualizer,
    sheetRef,
    goBack,
    handleToggleFav,
    handleAddToPlaylist,
    handleSmartQueue,
    handleEngineReady,
    handleSaveQueueAsPlaylist,
    fetchAiInsight,
    goToQueueTrack,
    goToFileTrack,
    handleSheetTouchStart,
    handleSheetTouchMove,
    handleSheetTouchEnd,
    navigate,
  };
}
