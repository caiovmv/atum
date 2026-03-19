import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDebouncedValue } from './useDebouncedValue';
import { useInfiniteRender } from './useInfiniteRender';
import { useToast } from '../contexts/ToastContext';
import { getLibrary, getLibraryFacets, getLibraryFolders, refreshCover, updateImportedItem, evictCache } from '../api/library';
import { evictCoverCache } from './useApiCache';
import { reorganizeLibrary } from '../api/settings';
import type { LibraryItem, Facets } from '../types/library';
import type { LibraryFolder } from '../api/library';

export type ContentTypeTab = 'music' | 'concerts' | 'movies' | 'tv';
export type ViewBy = 'folders' | 'artist' | 'album' | 'genre' | 'music';
export type ViewMode = 'grid' | 'list';

export interface EditForm {
  name: string;
  year: string;
  artist: string;
  album: string;
  genre: string;
  tagsStr: string;
}

export function useLibrary() {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [contentType, setContentType] = useState<ContentTypeTab>('music');
  const [viewBy, setViewBy] = useState<ViewBy>('artist');
  const [selectedFacet, setSelectedFacet] = useState<string>('');
  const [selectedFolder, setSelectedFolder] = useState<string>('');
  const [folders, setFolders] = useState<LibraryFolder[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    try {
      const s = localStorage.getItem('library-view-mode');
      return (s === 'list' || s === 'grid') ? s : 'grid';
    } catch {
      return 'grid';
    }
  });
  const [detailItem, setDetailItem] = useState<LibraryItem | null>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedMoods, setSelectedMoods] = useState<string[]>([]);
  const [selectedSubGenres, setSelectedSubGenres] = useState<string[]>([]);
  const [selectedDescriptors, setSelectedDescriptors] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search, 350);
  const [facets, setFacets] = useState<Facets>({
    artists: [],
    albums: [],
    genres: [],
    tags: [],
    moods: [],
    sub_genres: [],
    descriptors: [],
  });
  const [editingItem, setEditingItem] = useState<LibraryItem | null>(null);
  const [editForm, setEditForm] = useState<EditForm>({
    name: '',
    year: '',
    artist: '',
    album: '',
    genre: '',
    tagsStr: '',
  });
  const [savingEdit, setSavingEdit] = useState(false);
  const [coverRefreshItem, setCoverRefreshItem] = useState<LibraryItem | null>(null);
  const [coverQuery, setCoverQuery] = useState('');
  const [coverRefreshing, setCoverRefreshing] = useState(false);
  const [coverRefreshResult, setCoverRefreshResult] = useState<{ ok: boolean; message?: string } | null>(null);
  const [rescanning, setRescanning] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [libraryReconnecting, setLibraryReconnecting] = useState(false);
  const [aiModeOpen, setAiModeOpen] = useState(false);
  const [aiFilteredIndices, setAiFilteredIndices] = useState<number[] | null>(null);
  const [aiExplanation, setAiExplanation] = useState<string>('');

  const { showToast } = useToast();
  const navigate = useNavigate();

  const fetchFacets = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const data = await getLibraryFacets(contentType, { signal });
        if (signal?.aborted) return;
        setFacets({
          artists: data.artists || [],
          albums: data.albums || [],
          genres: data.genres || [],
          tags: data.tags || [],
          moods: data.moods || [],
          sub_genres: data.sub_genres || [],
          descriptors: data.descriptors || [],
        });
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setFacets({
          artists: [],
          albums: [],
          genres: [],
          tags: [],
          moods: [],
          sub_genres: [],
          descriptors: [],
        });
      }
    },
    [contentType]
  );

  const fetchFolders = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const list = await getLibraryFolders(contentType, { signal });
        if (signal?.aborted) return;
        setFolders(list);
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setFolders([]);
      }
    },
    [contentType]
  );

  const fetchLibrary = useCallback(
    async (silent = false, signal?: AbortSignal) => {
      if (!silent) {
        setLoading(true);
        setFetchError(null);
      }
      try {
        const params: Parameters<typeof getLibrary>[0] = {
          content_type: contentType,
          ...(viewBy === 'artist' && selectedFacet && { artist: selectedFacet }),
          ...(viewBy === 'album' && selectedFacet && { album: selectedFacet }),
          ...(viewBy === 'genre' && selectedFacet && { genre: selectedFacet }),
          ...(viewBy === 'folders' && selectedFolder && { folder_path: selectedFolder }),
          ...(selectedTags.length > 0 && { tag: selectedTags }),
          ...(selectedMoods.length === 1 && { mood: selectedMoods[0] }),
          ...(selectedSubGenres.length === 1 && { sub_genre: selectedSubGenres[0] }),
          ...(selectedDescriptors.length === 1 && { descriptor: selectedDescriptors[0] }),
          ...(debouncedSearch.trim() && { q: debouncedSearch.trim() }),
        };
        const list = await getLibrary(params, { staleMs: silent ? 5_000 : 30_000, signal });
        if (signal?.aborted) return;
        const filtered = list.filter((x) => (x.content_type || 'music') === contentType);
        setItems(filtered);
        setFetchError(null);
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        if (!silent) {
          setItems([]);
          setFetchError(err instanceof Error ? err.message : 'Não foi possível carregar a biblioteca.');
        }
      } finally {
        if (!signal?.aborted && !silent) setLoading(false);
      }
    },
    [
      contentType,
      viewBy,
      selectedFacet,
      selectedFolder,
      selectedTags,
      selectedMoods,
      selectedSubGenres,
      selectedDescriptors,
      debouncedSearch,
    ]
  );

  useEffect(() => {
    const controller = new AbortController();
    fetchFacets(controller.signal);
    return () => controller.abort();
  }, [fetchFacets]);

  useEffect(() => {
    if (viewBy !== 'folders') return;
    const controller = new AbortController();
    fetchFolders(controller.signal);
    return () => controller.abort();
  }, [viewBy, fetchFolders]);

  useEffect(() => {
    const controller = new AbortController();
    fetchLibrary(false, controller.signal);
    return () => controller.abort();
  }, [fetchLibrary]);

  const librarySseRef = useRef<EventSource | null>(null);
  const libraryReconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fetchLibraryRef = useRef(fetchLibrary);
  fetchLibraryRef.current = fetchLibrary;
  const fetchFacetsRef = useRef(fetchFacets);
  fetchFacetsRef.current = fetchFacets;

  useEffect(() => {
    let disposed = false;
    const open = () => {
      if (disposed || librarySseRef.current) return;
      const es = new EventSource('/api/library/events');
      es.onmessage = (e) => {
        setLibraryReconnecting(false);
        evictCache('/api/library');
        fetchLibraryRef.current(true);
        try {
          const payload = JSON.parse(e.data);
          if (payload.facets_dirty) {
            evictCache('/api/library/facets');
            fetchFacetsRef.current();
          }
          if (payload.covers_dirty) {
            evictCache('/api/cover');
            evictCoverCache(payload.covers_dirty);
          }
        } catch {
          /* ignore parse errors */
        }
      };
      es.onerror = () => {
        setLibraryReconnecting(true);
        es.close();
        librarySseRef.current = null;
        if (!disposed) {
          libraryReconnectRef.current = setTimeout(() => {
            libraryReconnectRef.current = null;
            if (document.visibilityState === 'visible') open();
          }, 5000);
        }
      };
      librarySseRef.current = es;
    };
    const close = () => {
      if (librarySseRef.current) {
        librarySseRef.current.close();
        librarySseRef.current = null;
      }
      if (libraryReconnectRef.current) {
        clearTimeout(libraryReconnectRef.current);
        libraryReconnectRef.current = null;
      }
    };
    const onVisibility = () => {
      if (document.visibilityState === 'visible') open();
      else close();
    };
    if (document.visibilityState === 'visible') open();
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      disposed = true;
      document.removeEventListener('visibilitychange', onVisibility);
      close();
    };
  }, []);

  const ctLabel = (ct: string) =>
    ct === 'movies' ? 'Filme' : ct === 'tv' ? 'Série' : ct === 'concerts' ? 'Concerto' : 'Música';

  const facetList =
    viewBy === 'artist'
      ? facets.artists
      : viewBy === 'album'
        ? facets.albums
        : viewBy === 'genre'
          ? facets.genres
          : [];

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]));
  };
  const toggleMood = (mood: string) => {
    setSelectedMoods((prev) => (prev.includes(mood) ? prev.filter((m) => m !== mood) : [...prev, mood]));
  };
  const toggleSubGenre = (sg: string) => {
    setSelectedSubGenres((prev) => (prev.includes(sg) ? prev.filter((s) => s !== sg) : [...prev, sg]));
  };
  const toggleDescriptor = (desc: string) => {
    setSelectedDescriptors((prev) =>
      prev.includes(desc) ? prev.filter((d) => d !== desc) : [...prev, desc]
    );
  };

  const openEdit = (item: LibraryItem) => {
    setEditingItem(item);
    setEditForm({
      name: item.name || '',
      year: item.year != null ? String(item.year) : '',
      artist: item.artist || '',
      album: item.album || '',
      genre: item.genre || '',
      tagsStr: (item.tags || []).join(', '),
    });
  };

  const closeEdit = () => {
    setEditingItem(null);
    setSavingEdit(false);
  };

  const openCoverRefresh = (item: LibraryItem) => {
    setCoverRefreshItem(item);
    setCoverQuery(item.name || '');
    setCoverRefreshResult(null);
  };

  const closeCoverRefresh = () => {
    setCoverRefreshItem(null);
    setCoverRefreshing(false);
    setCoverRefreshResult(null);
  };

  const doCoverRefresh = async () => {
    if (!coverRefreshItem) return;
    setCoverRefreshing(true);
    setCoverRefreshResult(null);
    try {
      const isImport = coverRefreshItem.source === 'import';
      const result = await refreshCover(coverRefreshItem.id, isImport, coverQuery || undefined);
      setCoverRefreshResult(result);
      if (result.ok) {
        fetchLibrary(true);
      }
    } catch {
      setCoverRefreshResult({ ok: false, message: 'Erro de rede.' });
    } finally {
      setCoverRefreshing(false);
    }
  };

  const saveEdit = async () => {
    if (!editingItem || editingItem.source !== 'import') return;
    setSavingEdit(true);
    try {
      const tags = editForm.tagsStr
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      const updated = await updateImportedItem(editingItem.id, {
        name: editForm.name || undefined,
        year: editForm.year ? parseInt(editForm.year, 10) : undefined,
        artist: editForm.artist || undefined,
        album: editForm.album || undefined,
        genre: editForm.genre || undefined,
        tags,
      });
      setItems((prev) =>
        prev.map((it) =>
          it.id === editingItem.id && it.source === 'import' ? { ...it, ...updated } : it
        )
      );
      closeEdit();
      fetchFacets();
    } catch {
      setSavingEdit(false);
    }
  };

  const doRescan = async () => {
    setRescanning(true);
    try {
      const data = await reorganizeLibrary(false);
      const parts = [`${data.processed} processados`];
      if (data.cleaned) parts.push(`${data.cleaned} limpos`);
      if (data.skipped) parts.push(`${data.skipped} pulados`);
      if (data.errors) parts.push(`${data.errors} erros`);
      showToast(`Rescan concluído: ${parts.join(', ')}`, 6000);
      fetchLibrary(true);
      fetchFacets();
    } catch {
      showToast('Erro de rede ao executar rescan.', 4000);
    } finally {
      setRescanning(false);
    }
  };

  const effectiveItems =
    aiFilteredIndices && aiFilteredIndices.length > 0
      ? items.filter((_, i) => aiFilteredIndices.includes(i))
      : items;
  const { visible: visibleItems, hasMore, sentinelRef } = useInfiniteRender(effectiveItems, 30);

  const handleAiResults = useCallback((ids: number[], explanation: string) => {
    setAiFilteredIndices(ids.length > 0 ? ids : null);
    setAiExplanation(explanation);
  }, []);

  const clearAiFilter = useCallback(() => {
    setAiFilteredIndices(null);
    setAiExplanation('');
  }, []);

  const aiFilteredItems =
    aiFilteredIndices && aiFilteredIndices.length > 0
      ? items.filter((_, i) => aiFilteredIndices.includes(i))
      : [];

  const playAiQueue = useCallback(() => {
    if (aiFilteredItems.length === 0) return;
    const musicItems = aiFilteredItems.filter((it) =>
      ['music', 'concerts'].includes((it.content_type || 'music').toLowerCase())
    );
    if (musicItems.length === 0) return;
    const queue = musicItems.map((it) => ({
      id: it.id,
      source: (it.source || 'import') as 'download' | 'import',
      file_index: 0,
      item_name: it.name,
      artist: it.artist,
      content_type: it.content_type,
    }));
    const first = queue[0];
    const src = first.source || 'import';
    navigate(`/play-receiver/${first.id}?source=${src}`, {
      state: { radioQueue: queue, radioQueueIndex: 0 },
    });
  }, [aiFilteredItems, navigate]);

  const persistViewMode = useCallback((mode: ViewMode) => {
    setViewMode(mode);
    try {
      localStorage.setItem('library-view-mode', mode);
    } catch {
      /* ignore */
    }
  }, []);

  return {
    // state
    contentType,
    setContentType,
    viewBy,
    setViewBy,
    viewMode,
    setViewMode: persistViewMode,
    detailItem,
    setDetailItem,
    selectedFacet,
    setSelectedFacet,
    selectedFolder,
    setSelectedFolder,
    folders,
    search,
    setSearch,
    facets,
    facetList,
    selectedTags,
    selectedMoods,
    selectedSubGenres,
    selectedDescriptors,
    loading,
    fetchError,
    items,
    visibleItems,
    hasMore,
    sentinelRef,
    libraryReconnecting,
    // edit modal
    editingItem,
    editForm,
    setEditForm,
    savingEdit,
    openEdit,
    closeEdit,
    saveEdit,
    // cover refresh modal
    coverRefreshItem,
    coverQuery,
    setCoverQuery,
    coverRefreshResult,
    coverRefreshing,
    openCoverRefresh,
    closeCoverRefresh,
    doCoverRefresh,
    // actions
    toggleTag,
    toggleMood,
    toggleSubGenre,
    toggleDescriptor,
    doRescan,
    rescanning,
    fetchLibrary,
    ctLabel,
    aiModeOpen,
    setAiModeOpen,
    aiFilteredIndices,
    aiExplanation,
    handleAiResults,
    clearAiFilter,
    aiFilteredItems,
    playAiQueue,
  };
}
