import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { IoPlay, IoRefresh } from 'react-icons/io5';
import { MediaCard } from '../components/MediaCard';
import { EmptyState } from '../components/EmptyState';
import { useToast } from '../contexts/ToastContext';
import { statusLabel } from '../utils/format';
import './Library.css';

type ContentType = 'music' | 'movies' | 'tv';

interface LibraryItem {
  id: number;
  name?: string;
  content_type?: string;
  year?: number;
  content_path?: string;
  cover_path_small?: string;
  cover_path_large?: string;
  status?: string;
  progress?: number;
  source?: 'download' | 'import';
  artist?: string;
  album?: string;
  genre?: string;
  tags?: string[];
}

interface Facets {
  artists: string[];
  albums: string[];
  genres: string[];
  tags: string[];
}


type SectionTab = 'music' | 'videos';
type ViewBy = 'artist' | 'album' | 'genre';

export function Library() {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [section, setSection] = useState<SectionTab>('music');
  const [viewBy, setViewBy] = useState<ViewBy>('artist');
  const [selectedFacet, setSelectedFacet] = useState<string>('');
  const [videoKind, setVideoKind] = useState<string>(''); // '' | movies | tv
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [facets, setFacets] = useState<Facets>({ artists: [], albums: [], genres: [], tags: [] });
  const [editingItem, setEditingItem] = useState<LibraryItem | null>(null);
  const [editForm, setEditForm] = useState({ name: '', year: '', artist: '', album: '', genre: '', tagsStr: '' });
  const [savingEdit, setSavingEdit] = useState(false);
  const [coverRefreshItem, setCoverRefreshItem] = useState<LibraryItem | null>(null);
  const [coverQuery, setCoverQuery] = useState('');
  const [coverRefreshing, setCoverRefreshing] = useState(false);
  const [coverRefreshResult, setCoverRefreshResult] = useState<{ ok: boolean; message?: string } | null>(null);
  const [rescanning, setRescanning] = useState(false);
  const navigate = useNavigate();
  const { showToast } = useToast();

  const contentTypeForFacets = section === 'music' ? 'music' : (videoKind || 'movies');

  const fetchFacets = useCallback(async () => {
    try {
      if (section === 'videos' && !videoKind) {
        const [r1, r2] = await Promise.all([
          fetch('/api/library/facets?content_type=movies'),
          fetch('/api/library/facets?content_type=tv'),
        ]);
        const d1 = r1.ok ? await r1.json() : {};
        const d2 = r2.ok ? await r2.json() : {};
        const merge = (a: string[], b: string[]) => [...new Set([...(a || []), ...(b || [])])].sort();
        setFacets({
          artists: [],
          albums: [],
          genres: merge(d1.genres || [], d2.genres || []),
          tags: merge(d1.tags || [], d2.tags || []),
        });
      } else {
        const ct = section === 'music' ? 'music' : contentTypeForFacets;
        const res = await fetch(`/api/library/facets?content_type=${ct}`);
        const data = await res.ok ? await res.json() : {};
        setFacets({
          artists: data.artists || [],
          albums: data.albums || [],
          genres: data.genres || [],
          tags: data.tags || [],
        });
      }
    } catch {
      setFacets({ artists: [], albums: [], genres: [], tags: [] });
    }
  }, [section, contentTypeForFacets, videoKind]);

  const fetchLibrary = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const params = new URLSearchParams();
      if (section === 'music') {
        params.set('content_type', 'music');
        if (viewBy === 'artist' && selectedFacet) params.set('artist', selectedFacet);
        if (viewBy === 'album' && selectedFacet) params.set('album', selectedFacet);
        if (viewBy === 'genre' && selectedFacet) params.set('genre', selectedFacet);
      } else {
        if (videoKind) params.set('content_type', videoKind);
        if (selectedFacet) params.set('genre', selectedFacet);
      }
      selectedTags.forEach((t) => params.append('tag', t));
      if (search.trim()) params.set('q', search.trim());
      const res = await fetch(`/api/library?${params}`);
      if (!res.ok) {
        if (res.status === 503) throw new Error('Runner não configurado.');
        throw new Error(await res.text());
      }
      const data = await res.json();
      let list = Array.isArray(data) ? data : [];
      if (section === 'videos' && !videoKind) {
        list = list.filter((x: LibraryItem) => x.content_type === 'movies' || x.content_type === 'tv');
      }
      setItems(list);
    } catch {
      if (!silent) setItems([]);
    } finally {
      if (!silent) setLoading(false);
    }
  }, [section, viewBy, selectedFacet, videoKind, selectedTags, search]);

  useEffect(() => {
    fetchFacets();
  }, [fetchFacets]);

  useEffect(() => {
    fetchLibrary();
  }, [fetchLibrary]);

  const librarySseRef = useRef<EventSource | null>(null);
  const [libraryReconnecting, setLibraryReconnecting] = useState(false);
  const libraryReconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fetchLibraryRef = useRef(fetchLibrary);
  fetchLibraryRef.current = fetchLibrary;
  useEffect(() => {
    let disposed = false;
    const open = () => {
      if (disposed || librarySseRef.current) return;
      const es = new EventSource('/api/library/events');
      es.onmessage = () => {
        setLibraryReconnecting(false);
        fetchLibraryRef.current(true);
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

  const ctLabel = (ct: string) => (ct === 'movies' ? 'Filme' : ct === 'tv' ? 'Série' : 'Música');

  const facetList = section === 'music'
    ? (viewBy === 'artist' ? facets.artists : viewBy === 'album' ? facets.albums : facets.genres)
    : facets.genres;

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]));
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
      const url = isImport
        ? `/api/library/imported/${coverRefreshItem.id}/refresh-cover`
        : `/api/library/${coverRefreshItem.id}/refresh-cover`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: coverQuery || undefined }),
      });
      if (res.ok) {
        const data = await res.json();
        setCoverRefreshResult({
          ok: data.ok,
          message: data.ok ? 'Capa atualizada com sucesso!' : 'Nenhuma capa encontrada para esse termo.',
        });
        if (data.ok) {
          fetchLibrary(true);
        }
      } else {
        setCoverRefreshResult({ ok: false, message: 'Erro ao buscar capa.' });
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
      const tags = editForm.tagsStr.split(',').map((t) => t.trim()).filter(Boolean);
      const res = await fetch(`/api/library/imported/${editingItem.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editForm.name || undefined,
          year: editForm.year ? parseInt(editForm.year, 10) : undefined,
          artist: editForm.artist || undefined,
          album: editForm.album || undefined,
          genre: editForm.genre || undefined,
          tags,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const updated = await res.json();
      setItems((prev) => prev.map((it) => (it.id === editingItem.id && it.source === 'import' ? { ...it, ...updated } : it)));
      closeEdit();
      fetchFacets();
    } catch {
      setSavingEdit(false);
    }
  };

  const doRescan = async () => {
    setRescanning(true);
    try {
      const res = await fetch('/api/settings/reorganize-library', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        const parts = [`${data.processed} processados`];
        if (data.cleaned) parts.push(`${data.cleaned} limpos`);
        if (data.skipped) parts.push(`${data.skipped} pulados`);
        if (data.errors) parts.push(`${data.errors} erros`);
        showToast(`Rescan concluído: ${parts.join(', ')}`, 6000);
        fetchLibrary(true);
        fetchFacets();
      } else {
        showToast('Erro ao executar rescan.', 4000);
      }
    } catch {
      showToast('Erro de rede ao executar rescan.', 4000);
    } finally {
      setRescanning(false);
    }
  };

  return (
    <div className="atum-library">
      <div className="atum-library-header">
        <div>
          <h1 className="atum-library-title">Minha Biblioteca</h1>
          <p className="atum-library-desc">
            Downloads concluídos e pastas importadas disponíveis para reprodução.
          </p>
        </div>
        <button
          type="button"
          className="atum-btn atum-library-rescan-btn"
          onClick={doRescan}
          disabled={rescanning}
          title="Reorganizar itens existentes seguindo o padrão Plex"
        >
          <IoRefresh className={rescanning ? 'atum-spin' : ''} />
          {rescanning ? 'Processando…' : 'Rescan'}
        </button>
      </div>
      {libraryReconnecting && <span className="atum-library-reconnecting" aria-live="polite">Reconectando…</span>}

      <div className="atum-library-tabs">
        <button
          type="button"
          className={`atum-library-tab ${section === 'music' ? 'atum-library-tab--active' : ''}`}
          onClick={() => { setSection('music'); setSelectedFacet(''); setVideoKind(''); }}
        >
          Música
        </button>
        <button
          type="button"
          className={`atum-library-tab ${section === 'videos' ? 'atum-library-tab--active' : ''}`}
          onClick={() => { setSection('videos'); setSelectedFacet(''); setViewBy('genre'); }}
        >
          Vídeos
        </button>
      </div>

      {section === 'videos' && (
        <div className="atum-library-video-kind">
          <button
            type="button"
            className={`atum-btn ${!videoKind ? 'atum-btn-primary' : ''}`}
            onClick={() => setVideoKind('')}
          >
            Todos
          </button>
          <button
            type="button"
            className={`atum-btn ${videoKind === 'movies' ? 'atum-btn-primary' : ''}`}
            onClick={() => setVideoKind('movies')}
          >
            Filmes
          </button>
          <button
            type="button"
            className={`atum-btn ${videoKind === 'tv' ? 'atum-btn-primary' : ''}`}
            onClick={() => setVideoKind('tv')}
          >
            Séries
          </button>
        </div>
      )}

      {section === 'music' && (
        <div className="atum-library-view-by">
          <span className="atum-library-view-by-label">Ver por:</span>
          {(['artist', 'album', 'genre'] as const).map((v) => (
            <button
              key={v}
              type="button"
              className={`atum-btn ${viewBy === v ? 'atum-btn-primary' : ''}`}
              onClick={() => { setViewBy(v); setSelectedFacet(''); }}
            >
              {v === 'artist' ? 'Artista' : v === 'album' ? 'Álbum' : 'Gênero'}
            </button>
          ))}
        </div>
      )}

      {section === 'videos' && (
        <div className="atum-library-view-by">
          <span className="atum-library-view-by-label">Gênero:</span>
          <button
            type="button"
            className={`atum-btn ${!selectedFacet ? 'atum-btn-primary' : ''}`}
            onClick={() => setSelectedFacet('')}
          >
            Todos
          </button>
          {facets.genres.map((g) => (
            <button
              key={g}
              type="button"
              className={`atum-btn ${selectedFacet === g ? 'atum-btn-primary' : ''}`}
              onClick={() => setSelectedFacet(selectedFacet === g ? '' : g)}
            >
              {g}
            </button>
          ))}
        </div>
      )}

      {section === 'music' && facetList.length > 0 && (
        <div className="atum-library-facets">
          <button
            type="button"
            className={`atum-library-facet-chip ${!selectedFacet ? 'atum-library-facet-chip--active' : ''}`}
            onClick={() => setSelectedFacet('')}
          >
            Todos
          </button>
          {facetList.map((v) => (
            <button
              key={v}
              type="button"
              className={`atum-library-facet-chip ${selectedFacet === v ? 'atum-library-facet-chip--active' : ''}`}
              onClick={() => setSelectedFacet(selectedFacet === v ? '' : v)}
            >
              {v}
            </button>
          ))}
        </div>
      )}

      {facets.tags.length > 0 && (
        <div className="atum-library-tags">
          <span className="atum-library-tags-label">Tags:</span>
          {facets.tags.map((t) => (
            <button
              key={t}
              type="button"
              className={`atum-library-facet-chip ${selectedTags.includes(t) ? 'atum-library-facet-chip--active' : ''}`}
              onClick={() => toggleTag(t)}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      <div className="atum-library-filters">
        <input
          type="text"
          placeholder="Buscar por título..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Buscar na biblioteca"
        />
      </div>

      {loading ? (
        <EmptyState title="Carregando…" description="Buscando itens da biblioteca." />
      ) : items.length === 0 ? (
        <EmptyState
          title="Nenhum item na biblioteca"
          description="Conclua downloads ou importe pastas para ver aqui."
        />
      ) : (
        <div className="atum-library-grid">
          {items.map((item) => (
            <MediaCard
              key={`${item.source || 'download'}-${item.id}`}
              cover={{
                contentType: (item.content_type === 'movies' || item.content_type === 'tv' ? item.content_type : 'music') as ContentType,
                title: item.name || '',
                downloadId: item.source === 'import' ? undefined : item.id,
                importId: item.source === 'import' ? item.id : undefined,
              }}
              coverShape={section === 'music' ? 'square' : 'poster'}
              title={item.name || '—'}
              meta={[
                item.year ? String(item.year) : '',
                item.artist && section === 'music' ? item.artist : '',
                item.album && section === 'music' ? item.album : '',
                ctLabel(item.content_type || 'music'),
              ].filter(Boolean)}
              showSeLe={false}
              overlay={
                item.source !== 'import' && item.status && item.status !== 'completed'
                  ? {
                      type: item.progress != null ? 'progress' : 'status',
                      label: statusLabel(item.status),
                      percent: item.progress,
                    }
                  : undefined
              }
              primaryAction={
                item.content_path ? (
                  <button
                    type="button"
                    className="media-card-play-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      const playBase = (item.content_type === 'movies' || item.content_type === 'tv') ? '/play' : '/play-receiver';
                      navigate(`${playBase}/${item.id}${item.source === 'import' ? '?source=import' : ''}`);
                    }}
                    aria-label={`Reproduzir ${item.name || 'item'}`}
                  >
                    <IoPlay size={24} />
                  </button>
                ) : undefined
              }
              actions={
                <div className="atum-library-card-actions-inner">
                  {item.content_path && (
                    <button
                      type="button"
                      className="atum-btn atum-btn-primary"
                      style={{ flex: 1 }}
                      onClick={() => {
                        const playBase = (item.content_type === 'movies' || item.content_type === 'tv') ? '/play' : '/play-receiver';
                        navigate(`${playBase}/${item.id}${item.source === 'import' ? '?source=import' : ''}`);
                      }}
                    >
                      Reproduzir
                    </button>
                  )}
                  <button
                    type="button"
                    className="atum-btn"
                    onClick={() => openCoverRefresh(item)}
                    title="Buscar capa"
                    aria-label={`Buscar capa de ${item.name || 'item'}`}
                  >
                    Capa
                  </button>
                  {item.source === 'import' && (
                    <button
                      type="button"
                      className="atum-btn"
                      onClick={() => openEdit(item)}
                      title="Editar metadados"
                      aria-label={`Editar metadados de ${item.name || 'item'}`}
                    >
                      Editar
                    </button>
                  )}
                </div>
              }
            />
          ))}
        </div>
      )}

      {coverRefreshItem && (
        <div className="atum-library-modal-backdrop" onClick={closeCoverRefresh} role="presentation">
          <div className="atum-library-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Buscar capa">
            <h2 className="atum-library-modal-title">Buscar Capa</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--atum-muted)', marginBottom: '0.75rem' }}>
              Busca nos serviços de enriquecimento (TMDB, iTunes). Altere o termo se a capa automática estiver errada.
            </p>
            <div className="atum-library-modal-form">
              <label>
                Termo de busca
                <input
                  type="text"
                  value={coverQuery}
                  onChange={(e) => setCoverQuery(e.target.value)}
                  placeholder="Nome do filme, série ou álbum"
                />
              </label>
            </div>
            {coverRefreshResult && (
              <p style={{
                fontSize: '0.85rem',
                marginBottom: '0.75rem',
                color: coverRefreshResult.ok ? '#4caf50' : '#f44336',
              }}>
                {coverRefreshResult.message}
              </p>
            )}
            <div className="atum-library-modal-actions">
              <button type="button" className="atum-btn" onClick={closeCoverRefresh}>
                Fechar
              </button>
              <button
                type="button"
                className="atum-btn atum-btn-primary"
                onClick={doCoverRefresh}
                disabled={coverRefreshing}
              >
                {coverRefreshing ? 'Buscando…' : 'Buscar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {editingItem && (
        <div className="atum-library-modal-backdrop" onClick={closeEdit} role="presentation">
          <div className="atum-library-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Editar metadados">
            <h2 className="atum-library-modal-title">Editar metadados</h2>
            <div className="atum-library-modal-form">
              <label>
                Nome
                <input
                  type="text"
                  value={editForm.name}
                  onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                />
              </label>
              <label>
                Ano
                <input
                  type="text"
                  inputMode="numeric"
                  value={editForm.year}
                  onChange={(e) => setEditForm((f) => ({ ...f, year: e.target.value }))}
                />
              </label>
              {(editingItem.content_type === 'music' || section === 'music') && (
                <>
                  <label>
                    Artista
                    <input
                      type="text"
                      value={editForm.artist}
                      onChange={(e) => setEditForm((f) => ({ ...f, artist: e.target.value }))}
                    />
                  </label>
                  <label>
                    Álbum
                    <input
                      type="text"
                      value={editForm.album}
                      onChange={(e) => setEditForm((f) => ({ ...f, album: e.target.value }))}
                    />
                  </label>
                </>
              )}
              <label>
                Gênero
                <input
                  type="text"
                  value={editForm.genre}
                  onChange={(e) => setEditForm((f) => ({ ...f, genre: e.target.value }))}
                />
              </label>
              <label>
                Tags (separadas por vírgula)
                <input
                  type="text"
                  value={editForm.tagsStr}
                  onChange={(e) => setEditForm((f) => ({ ...f, tagsStr: e.target.value }))}
                  placeholder="ex: rock, ao-vivo"
                />
              </label>
            </div>
            <div className="atum-library-modal-actions">
              <button type="button" className="atum-btn" onClick={closeEdit}>
                Cancelar
              </button>
              <button type="button" className="atum-btn atum-btn-primary" onClick={saveEdit} disabled={savingEdit}>
                {savingEdit ? 'Salvando…' : 'Salvar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
