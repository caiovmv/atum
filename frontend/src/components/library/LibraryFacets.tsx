import { IoGridOutline, IoListOutline, IoSparklesOutline } from 'react-icons/io5';
import { LibrarySearchInput } from './LibrarySearchInput';
import type { Facets } from '../../types/library';
import type { ContentTypeTab, ViewBy, ViewMode } from '../../hooks/useLibrary';

interface LibraryFolder {
  path: string;
  name: string;
  count: number;
}

interface LibraryFacetsProps {
  contentType: ContentTypeTab;
  setContentType: (c: ContentTypeTab) => void;
  onAiModeClick?: () => void;
  setSelectedFacet: (v: string) => void;
  viewBy: ViewBy;
  setViewBy: (v: ViewBy) => void;
  viewMode: ViewMode;
  setViewMode: (v: ViewMode) => void;
  selectedFacet: string;
  selectedFolder: string;
  setSelectedFolder: (v: string) => void;
  folders: LibraryFolder[];
  facets: Facets;
  facetList: string[];
  selectedTags: string[];
  selectedMoods: string[];
  selectedSubGenres: string[];
  selectedDescriptors: string[];
  toggleTag: (t: string) => void;
  toggleMood: (m: string) => void;
  toggleSubGenre: (sg: string) => void;
  toggleDescriptor: (d: string) => void;
  search: string;
  setSearch: (v: string) => void;
}

export function LibraryFacets({
  contentType,
  setContentType,
  setSelectedFacet,
  viewBy,
  setViewBy,
  viewMode,
  setViewMode,
  selectedFacet,
  onAiModeClick,
  selectedFolder,
  setSelectedFolder,
  folders,
  facets,
  facetList,
  selectedTags,
  selectedMoods,
  selectedSubGenres,
  selectedDescriptors,
  toggleTag,
  toggleMood,
  toggleSubGenre,
  toggleDescriptor,
  search,
  setSearch,
}: LibraryFacetsProps) {
  const viewByOptions: { value: ViewBy; label: string }[] =
    contentType === 'movies' || contentType === 'tv'
      ? [
          { value: 'folders', label: 'Pastas' },
          { value: 'genre', label: 'Gênero' },
          { value: 'music', label: 'Lista' },
        ]
      : [
          { value: 'folders', label: 'Pastas' },
          { value: 'artist', label: 'Artista' },
          { value: 'album', label: 'Álbum' },
          { value: 'genre', label: 'Gênero' },
          { value: 'music', label: 'Música' },
        ];

  return (
    <>
      <div className="atum-library-tabs">
        {(['music', 'concerts', 'movies', 'tv'] as const).map((ct) => (
          <button
            key={ct}
            type="button"
            className={`atum-library-tab ${contentType === ct ? 'atum-library-tab--active' : ''}`}
            onClick={() => {
              setContentType(ct);
              setSelectedFacet('');
              setSelectedFolder('');
              setViewBy(ct === 'movies' || ct === 'tv' ? 'genre' : 'artist');
            }}
          >
            {ct === 'music' ? 'Música' : ct === 'concerts' ? 'Concertos' : ct === 'movies' ? 'Filmes' : 'TV'}
          </button>
        ))}
      </div>

      <div className="atum-library-view-by">
        <span className="atum-library-view-by-label">Ver por:</span>
        {viewByOptions.map((opt) => (
          <button
            key={opt.value}
            type="button"
            className={`atum-btn ${viewBy === opt.value ? 'atum-btn-primary' : ''}`}
            onClick={() => { setViewBy(opt.value); setSelectedFacet(''); setSelectedFolder(''); }}
          >
            {opt.label}
          </button>
        ))}
        {onAiModeClick && (
          <button
            type="button"
            className="atum-btn atum-btn-ghost"
            onClick={onAiModeClick}
            title="Modo AI - buscar por mood/estilo"
            aria-label="Modo AI"
          >
            <IoSparklesOutline size={18} />
            <span className="atum-library-ai-btn-label">Modo AI</span>
          </button>
        )}
        <span className="atum-library-view-by-label atum-library-view-mode-label">Exibir:</span>
        <button
          type="button"
          className={`atum-btn atum-btn-icon ${viewMode === 'grid' ? 'atum-btn-primary' : ''}`}
          onClick={() => setViewMode('grid')}
          aria-label="Visualização em grade"
          title="Grade"
        >
          <IoGridOutline size={18} />
        </button>
        <button
          type="button"
          className={`atum-btn atum-btn-icon ${viewMode === 'list' ? 'atum-btn-primary' : ''}`}
          onClick={() => setViewMode('list')}
          aria-label="Visualização em lista"
          title="Lista"
        >
          <IoListOutline size={18} />
        </button>
      </div>

      {viewBy === 'folders' && folders.length > 0 && (
        <div className="atum-library-facets">
          <button
            type="button"
            className={`atum-library-facet-chip ${!selectedFolder ? 'atum-library-facet-chip--active' : ''}`}
            onClick={() => setSelectedFolder('')}
          >
            Todas
          </button>
          {folders.map((f) => (
            <button
              key={f.path}
              type="button"
              className={`atum-library-facet-chip ${selectedFolder === f.path ? 'atum-library-facet-chip--active' : ''}`}
              onClick={() => setSelectedFolder(selectedFolder === f.path ? '' : f.path)}
            >
              {f.name} ({f.count})
            </button>
          ))}
        </div>
      )}

      {facetList.length > 0 && viewBy !== 'music' && viewBy !== 'folders' && (
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

      {facets.moods.length > 0 && (
        <div className="atum-library-tags">
          <span className="atum-library-tags-label">Moods:</span>
          {facets.moods.map((m) => (
            <button
              key={m}
              type="button"
              className={`atum-library-facet-chip ${selectedMoods.includes(m) ? 'atum-library-facet-chip--active' : ''}`}
              onClick={() => toggleMood(m)}
            >
              {m}
            </button>
          ))}
        </div>
      )}

      {facets.sub_genres.length > 0 && (
        <div className="atum-library-tags">
          <span className="atum-library-tags-label">Sub-gêneros:</span>
          {facets.sub_genres.map((sg) => (
            <button
              key={sg}
              type="button"
              className={`atum-library-facet-chip ${selectedSubGenres.includes(sg) ? 'atum-library-facet-chip--active' : ''}`}
              onClick={() => toggleSubGenre(sg)}
            >
              {sg}
            </button>
          ))}
        </div>
      )}

      {facets.descriptors.length > 0 && (
        <div className="atum-library-tags">
          <span className="atum-library-tags-label">Contexto:</span>
          {facets.descriptors.map((d) => (
            <button
              key={d}
              type="button"
              className={`atum-library-facet-chip ${selectedDescriptors.includes(d) ? 'atum-library-facet-chip--active' : ''}`}
              onClick={() => toggleDescriptor(d)}
            >
              {d}
            </button>
          ))}
        </div>
      )}

      <div className="atum-library-filters">
        <LibrarySearchInput
          value={search}
          onChange={setSearch}
          contentType={contentType}
          placeholder="Buscar na biblioteca (título, artista, mood, gênero…)"
          aria-label="Buscar na biblioteca"
        />
      </div>
    </>
  );
}
