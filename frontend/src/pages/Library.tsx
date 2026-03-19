import { useNavigate } from 'react-router-dom';
import { IoRefresh } from 'react-icons/io5';
import { evictCoverCache } from '../hooks/useApiCache';
import { CoverRefreshBottomSheet } from '../components/library/CoverRefreshBottomSheet';
import { LibraryEditBottomSheet } from '../components/library/LibraryEditBottomSheet';
import { LibraryItemDetailBottomSheet } from '../components/library/LibraryItemDetailBottomSheet';
import { LibraryAIMode } from '../components/library/LibraryAIMode';
import { LibraryFacets } from '../components/library/LibraryFacets';
import { LibraryGrid } from '../components/library/LibraryGrid';
import { useLibrary } from '../hooks/useLibrary';
import type { ContentType } from '../types/library';
import './Library.css';

function toContentType(ct: string | undefined): ContentType {
  if (ct === 'movies' || ct === 'tv') return ct;
  return 'music'; // music, concerts -> music for play
}

export function Library() {
  const navigate = useNavigate();
  const lib = useLibrary();

  const handlePlay = (item: { id: number; content_type?: string; source?: string }) => {
    const playBase = toContentType(item.content_type) !== 'music' ? '/play' : '/play-receiver';
    navigate(`${playBase}/${item.id}${item.source === 'import' ? '?source=import' : ''}`);
  };

  return (
    <div className="atum-page library-page atum-library">
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
          onClick={lib.doRescan}
          disabled={lib.rescanning}
          title="Reorganizar itens existentes seguindo o padrão Plex"
        >
          <IoRefresh className={lib.rescanning ? 'atum-spin' : ''} />
          {lib.rescanning ? 'Processando…' : 'Rescan'}
        </button>
      </div>
      {lib.libraryReconnecting && (
        <span className="atum-library-reconnecting" aria-live="polite">
          Reconectando…
        </span>
      )}

      <LibraryFacets
        contentType={lib.contentType}
        setContentType={lib.setContentType}
        setSelectedFacet={lib.setSelectedFacet}
        onAiModeClick={() => lib.setAiModeOpen(true)}
        viewBy={lib.viewBy}
        setViewBy={lib.setViewBy}
        viewMode={lib.viewMode}
        setViewMode={lib.setViewMode}
        selectedFacet={lib.selectedFacet}
        selectedFolder={lib.selectedFolder}
        setSelectedFolder={lib.setSelectedFolder}
        folders={lib.folders}
        facets={lib.facets}
        facetList={lib.facetList}
        selectedTags={lib.selectedTags}
        selectedMoods={lib.selectedMoods}
        selectedSubGenres={lib.selectedSubGenres}
        selectedDescriptors={lib.selectedDescriptors}
        toggleTag={lib.toggleTag}
        toggleMood={lib.toggleMood}
        toggleSubGenre={lib.toggleSubGenre}
        toggleDescriptor={lib.toggleDescriptor}
        search={lib.search}
        setSearch={lib.setSearch}
      />

      <LibraryGrid
        contentType={lib.contentType}
        viewMode={lib.viewMode}
        loading={lib.loading}
        fetchError={lib.fetchError}
        visibleItems={lib.visibleItems}
        hasMore={lib.hasMore}
        sentinelRef={lib.sentinelRef}
        onRetry={() => lib.fetchLibrary()}
        onPlay={handlePlay}
        onCoverRefresh={lib.openCoverRefresh}
        onEdit={lib.openEdit}
        onInfoClick={lib.setDetailItem}
      />

      <CoverRefreshBottomSheet
        open={!!lib.coverRefreshItem}
        onClose={lib.closeCoverRefresh}
        coverQuery={lib.coverQuery}
        setCoverQuery={lib.setCoverQuery}
        coverRefreshResult={lib.coverRefreshResult}
        coverRefreshing={lib.coverRefreshing}
        onRefresh={lib.doCoverRefresh}
      />

      <LibraryEditBottomSheet
        open={!!lib.editingItem}
        onClose={lib.closeEdit}
        editingItem={lib.editingItem}
        editForm={lib.editForm}
        setEditForm={lib.setEditForm}
        onSave={lib.saveEdit}
        saving={lib.savingEdit}
        contentType={lib.contentType}
      />
      <LibraryItemDetailBottomSheet
        open={!!lib.detailItem}
        onClose={() => lib.setDetailItem(null)}
        item={lib.detailItem}
        onEdit={(item) => { lib.setDetailItem(null); lib.openEdit(item); }}
        onCoverUpdate={(id) => { evictCoverCache([id]); lib.fetchLibrary(true); }}
      />
      <LibraryAIMode
        open={lib.aiModeOpen}
        onClose={() => lib.setAiModeOpen(false)}
        items={lib.items}
        onAiResults={lib.handleAiResults}
      />
      {lib.aiFilteredIndices && lib.aiFilteredIndices.length > 0 && (
        <div className="atum-library-ai-badge">
          <span>Modo AI: {lib.aiFilteredIndices.length} itens</span>
          {lib.aiExplanation && (
            <span className="atum-library-ai-badge-explanation" title={lib.aiExplanation}>
              {lib.aiExplanation.slice(0, 60)}{lib.aiExplanation.length > 60 ? '…' : ''}
            </span>
          )}
          <button
            type="button"
            className="atum-btn atum-btn-primary"
            onClick={lib.playAiQueue}
            disabled={lib.aiFilteredItems.length === 0}
          >
            Reproduzir
          </button>
          <button
            type="button"
            className="atum-btn atum-btn-ghost"
            onClick={lib.playAiQueue}
            disabled={lib.aiFilteredItems.length === 0}
          >
            Adicionar à fila
          </button>
          <button onClick={lib.clearAiFilter} className="atum-btn atum-btn-ghost atum-library-ai-clear">
            Mostrar todos
          </button>
        </div>
      )}
    </div>
  );
}
