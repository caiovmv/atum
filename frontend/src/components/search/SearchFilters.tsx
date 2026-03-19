import { indexerLabel } from '../../utils/searchStorage';
import type { FilterSuggestions, SearchResult } from '../../types/search';
import { Input, Select } from '../Input';

interface SearchFiltersProps {
  allIndexersForFilter: string[];
  indexerStatus: Record<string, boolean>;
  sourceFilter: Set<string>;
  toggleSource: (key: string) => void;
  yearFilter: number | '';
  setYearFilter: (v: number | '') => void;
  genreFilter: string;
  setGenreFilter: (v: string) => void;
  qualityFilter: string;
  setQualityFilter: (v: string) => void;
  audioFilter: string;
  setAudioFilter: (v: string) => void;
  nameFilter: string;
  setNameFilter: (v: string) => void;
  onlyRelevant: boolean;
  setOnlyRelevant: (v: boolean) => void;
  clientSort: 'seeders' | 'size' | 'quality';
  setClientSort: (v: 'seeders' | 'size' | 'quality') => void;
  filterSuggestions: FilterSuggestions;
  results: SearchResult[];
  setPage: (v: number | ((p: number) => number)) => void;
  onClearFilters: () => void;
  onNewSearch: () => void;
  filteredResultsLength: number;
  resultsLength: number;
}

export function SearchFilters({
  allIndexersForFilter,
  indexerStatus,
  sourceFilter,
  toggleSource,
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
  results,
  setPage,
  onClearFilters,
  onNewSearch,
  filteredResultsLength,
  resultsLength,
}: SearchFiltersProps) {
  const yearsFromResults = results
    .map((r) => r.parsed_year)
    .filter((y): y is number => typeof y === 'number')
    .filter((y, i, arr) => arr.indexOf(y) === i)
    .sort((a, b) => b - a);

  const audioCodecs = results
    .map((r) => r.parsed_audio_codec)
    .filter((a): a is string => typeof a === 'string' && a.length > 0)
    .filter((a, i, arr) => arr.indexOf(a) === i)
    .sort((a, b) => a.localeCompare(b));

  return (
    <>
      <div className="results-filters">
        {allIndexersForFilter.length > 0 && (
          <div className="filter-row filter-row--chips">
            <span className="filter-label">Fonte:</span>
            <div className="filter-chips">
              {allIndexersForFilter.map((key) => {
                const enabled = indexerStatus[key] !== false;
                const active = sourceFilter.has(key);
                return (
                  <button
                    key={key}
                    type="button"
                    className={`search-pill search-pill--chip ${active ? 'search-pill--active' : ''} ${!enabled ? 'search-pill--disabled' : ''}`}
                    onClick={() => enabled && toggleSource(key)}
                    disabled={!enabled}
                    title={!enabled ? 'Fonte desativada' : undefined}
                    aria-pressed={active}
                  >
                    {indexerLabel(key)}{!enabled ? ' (indisponível)' : ''}
                  </button>
                );
              })}
            </div>
          </div>
        )}
        <div className="filter-row">
          <span className="filter-label">Ano:</span>
          <Select
            size="small"
            className="atum-select--pill"
            value={yearFilter}
            onChange={(e) => { setYearFilter(e.target.value === '' ? '' : Number(e.target.value)); setPage(1); }}
          >
            <option value="">Todos</option>
            {filterSuggestions.years.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
            {filterSuggestions.years.length === 0 && yearsFromResults.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </Select>
          <span className="filter-label">Gênero:</span>
          <Select
            size="small"
            className="atum-select--pill"
            value={genreFilter}
            onChange={(e) => { setGenreFilter(e.target.value); setPage(1); }}
          >
            <option value="">Todos</option>
            {filterSuggestions.genres.map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </Select>
          <span className="filter-label">Qualidade:</span>
          <Select
            size="small"
            className="atum-select--pill"
            value={qualityFilter}
            onChange={(e) => { setQualityFilter(e.target.value); setPage(1); }}
          >
            <option value="">Todas</option>
            {filterSuggestions.qualities.map((q) => (
              <option key={q} value={q}>{q}</option>
            ))}
          </Select>
          <span className="filter-label">Áudio:</span>
          <Select
            size="small"
            className="atum-select--pill"
            value={audioFilter}
            onChange={(e) => { setAudioFilter(e.target.value); setPage(1); }}
          >
            <option value="">Todos</option>
            {audioCodecs.map((codec) => (
              <option key={codec} value={codec}>{codec}</option>
            ))}
          </Select>
        </div>
        <div className="filter-row">
          <span className="filter-label">Nome:</span>
          <Input
            type="text"
            size="small"
            placeholder="Filtrar pelo título…"
            value={nameFilter}
            onChange={(e) => { setNameFilter(e.target.value); setPage(1); }}
            className="filter-name-input"
          />
          <label className="filter-check">
            <input
              type="checkbox"
              checked={onlyRelevant}
              onChange={(e) => { setOnlyRelevant(e.target.checked); setPage(1); }}
            />
            Só títulos relacionados à busca
          </label>
        </div>
        <div className="filter-row filter-row--pills">
          <span className="filter-label">Ordenar:</span>
          <div className="filter-chips">
            <button type="button" className={`search-pill search-pill--chip ${clientSort === 'seeders' ? 'search-pill--active' : ''}`} onClick={() => { setClientSort('seeders'); setPage(1); }} aria-pressed={clientSort === 'seeders'}>Se/Le</button>
            <button type="button" className={`search-pill search-pill--chip ${clientSort === 'size' ? 'search-pill--active' : ''}`} onClick={() => { setClientSort('size'); setPage(1); }} aria-pressed={clientSort === 'size'}>Tamanho</button>
            <button type="button" className={`search-pill search-pill--chip ${clientSort === 'quality' ? 'search-pill--active' : ''}`} onClick={() => { setClientSort('quality'); setPage(1); }} aria-pressed={clientSort === 'quality'}>Qualidade</button>
          </div>
        </div>
      </div>
      <p className="results-meta">
        {filteredResultsLength} resultado(s){filteredResultsLength !== resultsLength && ` (de ${resultsLength})`}
        <button type="button" className="clear-search-btn" onClick={onClearFilters}>
          Limpar filtros
        </button>
        <button type="button" className="clear-search-btn" onClick={onNewSearch}>
          Nova busca
        </button>
      </p>
    </>
  );
}
