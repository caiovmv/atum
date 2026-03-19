import { useState, useMemo, useCallback } from 'react';
import { useDownloadsEvents } from '../contexts/DownloadsEventsContext';
import { useToast } from '../contexts/ToastContext';
import { useSearch } from '../hooks/useSearch';
import { resolveMagnet } from '../api/search';
import { SearchFilesModal } from '../components/search/SearchFilesModal';
import { SearchAddModal } from '../components/search/SearchAddModal';
import { SearchFilters } from '../components/search/SearchFilters';
import { SearchResultsGrid } from '../components/search/SearchResultsGrid';
import { SearchHero } from '../components/search/SearchHero';
import { SearchProgressSection } from '../components/search/SearchProgressSection';
import type { SearchResult } from '../types/search';
import './Search.css';

export function Search() {
  const search = useSearch();
  const {
    query,
    setQuery,
    contentType,
    setContentType,
    sortBy,
    setSortBy,
    results,
    setPage,
    loading,
    error,
    indexerStatus,
    sourceFilter,
    indexerProgress,
    indexerCounts,
    indexersReconnecting,
    allIndexersForFilter,
    filteredResults,
    pageResults,
    page,
    totalPages,
    start,
    toggleSource,
    handleSearch,
    clearFilters,
    newSearch,
    yearFilter,
    setYearFilter,
    genreFilter,
    setGenreFilter,
    qualityFilter,
    setQualityFilter,
    audioFilter,
    setAudioFilter,
    nameFilter,
    setNameFilter,
    onlyRelevant,
    setOnlyRelevant,
    clientSort,
    setClientSort,
    filterSuggestions,
  } = search;

  const { showToast } = useToast();
  const [filesModalResult, setFilesModalResult] = useState<SearchResult | null>(null);
  const [addModalResult, setAddModalResult] = useState<SearchResult | null>(null);
  const { downloads: contextDownloads } = useDownloadsEvents();
  const downloads = useMemo(
    () =>
      contextDownloads.map((d) => ({
        id: d.id,
        magnet: d.magnet,
        status: (d.status ?? 'queued') as string,
        progress: d.progress,
      })),
    [contextDownloads]
  );

  const ensureMagnetOrTorrentUrl = useCallback(async (r: SearchResult): Promise<SearchResult | null> => {
    if (r.magnet || r.torrent_url) return r;
    if (!r.indexer || !r.torrent_id) return null;
    const data = await resolveMagnet(r.indexer, r.torrent_id);
    if (data?.magnet) return { ...r, magnet: data.magnet };
    return null;
  }, []);

  const openModal = useCallback(async (r: SearchResult, setter: (v: SearchResult | null) => void) => {
    const resolved = await ensureMagnetOrTorrentUrl(r);
    if (!resolved || (!resolved.magnet && !resolved.torrent_url)) {
      showToast('Este resultado não possui magnet nem link do .torrent.', 4000);
      return;
    }
    setter(resolved);
  }, [ensureMagnetOrTorrentUrl, showToast]);

  return (
    <div className="atum-page search-page">
      <h1 className="atum-page-title">Busca</h1>
      {indexersReconnecting && <span className="search-reconnecting" aria-live="polite">Reconectando indexadores…</span>}
      <SearchHero
        query={query}
        setQuery={setQuery}
        contentType={contentType}
        setContentType={setContentType}
        sortBy={sortBy}
        setSortBy={setSortBy}
        loading={loading}
        error={error}
        onSubmit={handleSearch}
      />
      {error && <p id="search-error" className="search-error" role="alert">{error}</p>}
      <SearchProgressSection indexerProgress={indexerProgress} indexerCounts={indexerCounts} />
      <section className="results-section" aria-live="polite" aria-busy={loading}>
        {results.length > 0 && (
          <>
            <SearchFilters
              allIndexersForFilter={allIndexersForFilter}
              indexerStatus={indexerStatus}
              sourceFilter={sourceFilter}
              toggleSource={toggleSource}
              yearFilter={yearFilter}
              setYearFilter={setYearFilter}
              genreFilter={genreFilter}
              setGenreFilter={setGenreFilter}
              qualityFilter={qualityFilter}
              setQualityFilter={setQualityFilter}
              audioFilter={audioFilter}
              setAudioFilter={setAudioFilter}
              nameFilter={nameFilter}
              setNameFilter={setNameFilter}
              onlyRelevant={onlyRelevant}
              setOnlyRelevant={setOnlyRelevant}
              clientSort={clientSort}
              setClientSort={setClientSort}
              filterSuggestions={filterSuggestions}
              results={results}
              setPage={setPage}
              onClearFilters={clearFilters}
              onNewSearch={newSearch}
              filteredResultsLength={filteredResults.length}
              resultsLength={results.length}
            />
          </>
        )}
        {results.length > 0 && filteredResults.length === 0 && (
          <p className="search-empty" role="status">Nenhum resultado para &quot;{query.trim()}&quot; com os filtros atuais. Tente limpar filtros ou alterar a busca.</p>
        )}
        <SearchResultsGrid
          loading={loading}
          resultsLength={results.length}
          pageResults={pageResults}
          filteredResultsLength={filteredResults.length}
          page={page}
          totalPages={totalPages}
          setPage={setPage}
          contentType={contentType}
          sortBy={sortBy}
          query={query}
          start={start}
          downloads={downloads}
          onOpenFilesModal={(r) => openModal(r, setFilesModalResult)}
          onOpenAddModal={(r) => openModal(r, setAddModalResult)}
        />
      </section>

      {filesModalResult && (
        <SearchFilesModal
          result={filesModalResult}
          onClose={() => setFilesModalResult(null)}
          onAddToQueue={() => setAddModalResult(filesModalResult)}
        />
      )}

      {addModalResult && (
        <SearchAddModal
          result={addModalResult}
          contentType={contentType}
          onClose={() => setAddModalResult(null)}
        />
      )}
    </div>
  );
}
