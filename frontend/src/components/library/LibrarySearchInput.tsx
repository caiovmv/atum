import { useState, useEffect, useRef, useCallback } from 'react';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { getLibraryAutocomplete } from '../../api/library';
import type { AutocompleteSuggestion } from '../../api/library';
import './LibrarySearchInput.css';

const SUGGESTION_TYPE_LABELS: Record<string, string> = {
  artist: 'Artista',
  album: 'Álbum',
  title: 'Título',
  genre: 'Gênero',
};

interface LibrarySearchInputProps {
  value: string;
  onChange: (v: string) => void;
  contentType: string;
  placeholder?: string;
  'aria-label'?: string;
}

export function LibrarySearchInput({
  value,
  onChange,
  contentType,
  placeholder = 'Buscar na biblioteca (título, artista, mood, gênero…)',
  'aria-label': ariaLabel = 'Buscar na biblioteca',
}: LibrarySearchInputProps) {
  const [suggestions, setSuggestions] = useState<AutocompleteSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const debouncedValue = useDebouncedValue(value, 300);

  useFocusTrap(containerRef, open && suggestions.length > 0);

  useEffect(() => {
    if (!debouncedValue.trim()) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    const ctrl = new AbortController();
    getLibraryAutocomplete(debouncedValue, contentType, { limit: 10, signal: ctrl.signal })
      .then((list) => {
        setSuggestions(list);
        setOpen(list.length > 0);
        setActiveIdx(0);
      })
      .catch(() => {
        setSuggestions([]);
        setOpen(false);
      });
    return () => ctrl.abort();
  }, [debouncedValue, contentType]);

  const handleSelect = useCallback(
    (s: AutocompleteSuggestion) => {
      onChange(s.value);
      setOpen(false);
      setSuggestions([]);
      inputRef.current?.blur();
    },
    [onChange]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!open || suggestions.length === 0) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIdx((i) => (i + 1) % suggestions.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIdx((i) => (i - 1 + suggestions.length) % suggestions.length);
      } else if (e.key === 'Enter') {
        const s = suggestions[activeIdx];
        if (s) {
          e.preventDefault();
          handleSelect(s);
        }
      } else if (e.key === 'Escape') {
        setOpen(false);
      }
    },
    [open, suggestions, activeIdx, handleSelect]
  );

  useEffect(() => {
    const el = containerRef.current?.querySelector(`[data-index="${activeIdx}"]`) as HTMLElement | undefined;
    el?.scrollIntoView({ block: 'nearest' });
  }, [activeIdx]);

  const handleBlur = useCallback(() => {
    setTimeout(() => setOpen(false), 150);
  }, []);

  return (
    <div ref={containerRef} className="atum-library-search-wrap">
      <input
        ref={inputRef}
        type="text"
        className="atum-library-search-input"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => value.trim() && suggestions.length > 0 && setOpen(true)}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        aria-label={ariaLabel}
        aria-autocomplete="list"
        aria-expanded={open && suggestions.length > 0}
        aria-controls="atum-library-search-list"
        aria-activedescendant={open ? `suggestion-${activeIdx}` : undefined}
        autoComplete="off"
        spellCheck={false}
      />
      {open && suggestions.length > 0 && (
        <ul
          id="atum-library-search-list"
          className="atum-library-search-list"
          role="listbox"
        >
          {suggestions.map((s, idx) => (
            <li key={`${s.type}-${s.value}-${idx}`}>
              <button
                type="button"
                className={`atum-library-search-suggestion ${idx === activeIdx ? 'active' : ''}`}
                data-index={idx}
                id={`suggestion-${idx}`}
                role="option"
                aria-selected={idx === activeIdx}
                onClick={() => handleSelect(s)}
                onMouseEnter={() => setActiveIdx(idx)}
              >
                <span className="atum-library-search-suggestion-type">
                  {SUGGESTION_TYPE_LABELS[s.type] ?? s.type}
                </span>
                <span className="atum-library-search-suggestion-value">{s.value}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
