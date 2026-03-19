import { useState, useEffect, useRef, useCallback, memo, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useFocusTrap } from '../hooks/useFocusTrap';
import {
  IoSearch, IoHomeOutline, IoDownloadOutline, IoLibraryOutline,
  IoRadioOutline, IoHeartOutline, IoReaderOutline, IoSettingsOutline,
  IoMusicalNotesOutline, IoFilmOutline, IoTvOutline, IoReturnDownBack,
} from 'react-icons/io5';
import { Input } from './Input';
import './CommandPalette.css';

interface PaletteAction {
  id: string;
  label: string;
  section: string;
  icon: React.ComponentType<{ size?: number }>;
  action: () => void;
  keywords?: string;
}

export const CommandPalette = memo(function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIdx, setActiveIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const paletteRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useFocusTrap(paletteRef, open);

  const close = useCallback(() => {
    setOpen(false);
    setQuery('');
    setActiveIdx(0);
  }, []);

  const go = useCallback((path: string) => {
    close();
    navigate(path);
  }, [close, navigate]);

  const actions: PaletteAction[] = useMemo(() => [
    { id: 'nav-home', label: 'Início', section: 'Navegar', icon: IoHomeOutline, action: () => go('/'), keywords: 'home inicio' },
    { id: 'nav-search', label: 'Busca', section: 'Navegar', icon: IoSearch, action: () => go('/search'), keywords: 'search procurar' },
    { id: 'nav-library', label: 'Biblioteca', section: 'Navegar', icon: IoLibraryOutline, action: () => go('/library'), keywords: 'library acervo' },
    { id: 'nav-downloads', label: 'Downloads', section: 'Navegar', icon: IoDownloadOutline, action: () => go('/downloads'), keywords: 'baixar' },
    { id: 'nav-wishlist', label: 'Wishlist', section: 'Navegar', icon: IoHeartOutline, action: () => go('/wishlist'), keywords: 'desejos favoritos' },
    { id: 'nav-feeds', label: 'Feeds', section: 'Navegar', icon: IoReaderOutline, action: () => go('/feeds'), keywords: 'rss' },
    { id: 'nav-radio', label: 'Rádio', section: 'Navegar', icon: IoRadioOutline, action: () => go('/radio'), keywords: 'estação' },
    { id: 'nav-settings', label: 'Configurações', section: 'Navegar', icon: IoSettingsOutline, action: () => go('/settings'), keywords: 'preferencias opcoes' },
    { id: 'search-music', label: 'Buscar Música', section: 'Buscar', icon: IoMusicalNotesOutline, action: () => { close(); navigate('/search?type=music'); }, keywords: 'album artista' },
    { id: 'search-movies', label: 'Buscar Filmes', section: 'Buscar', icon: IoFilmOutline, action: () => { close(); navigate('/search?type=movies'); }, keywords: 'filme movie' },
    { id: 'search-tv', label: 'Buscar Séries', section: 'Buscar', icon: IoTvOutline, action: () => { close(); navigate('/search?type=tv'); }, keywords: 'serie show' },
  ], [go, close, navigate]);

  const filtered = useMemo(() => {
    if (!query.trim()) return actions;
    const q = query.toLowerCase();
    return actions.filter(a =>
      a.label.toLowerCase().includes(q) ||
      a.section.toLowerCase().includes(q) ||
      (a.keywords && a.keywords.includes(q))
    );
  }, [query, actions]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setOpen(o => !o);
      }
      if (e.key === 'Escape' && open) {
        e.preventDefault();
        close();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, close]);

  useEffect(() => {
    if (open) {
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  useEffect(() => { setActiveIdx(0); }, [query]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIdx(i => (i + 1) % filtered.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIdx(i => (i - 1 + filtered.length) % filtered.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const item = filtered[activeIdx];
      if (item) item.action();
    }
  }, [filtered, activeIdx]);

  useEffect(() => {
    const el = listRef.current?.children[activeIdx] as HTMLElement | undefined;
    el?.scrollIntoView({ block: 'nearest' });
  }, [activeIdx]);

  const goToSearch = useCallback(() => {
    if (query.trim()) {
      close();
      navigate(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  }, [query, close, navigate]);

  if (!open) return null;

  let lastSection = '';

  return (
    <div className="cmd-palette-overlay" onClick={close} role="presentation">
      <div ref={paletteRef} className="cmd-palette" onClick={e => e.stopPropagation()} role="dialog" aria-modal="true" aria-label="Paleta de comandos">
        <div className="cmd-palette-input-wrap">
          <IoSearch className="cmd-palette-input-icon" aria-hidden />
          <Input
            ref={inputRef}
            type="text"
            variant="ghost"
            className="cmd-palette-input"
            placeholder="Buscar ações, páginas…"
            value={query}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
            onKeyDown={(e) => handleKeyDown(e)}
            aria-label="Buscar no Command Palette"
            autoComplete="off"
            spellCheck={false}
          />
          <kbd className="cmd-palette-kbd">ESC</kbd>
        </div>

        <div className="cmd-palette-list" ref={listRef} role="listbox">
          {query.trim() && (
            <button
              type="button"
              className={`cmd-palette-item cmd-palette-item--search${activeIdx === -1 ? ' active' : ''}`}
              onClick={goToSearch}
            >
              <IoSearch size={16} />
              <span>Buscar "{query}" nos indexadores</span>
              <IoReturnDownBack size={14} className="cmd-palette-item-hint" />
            </button>
          )}
          {filtered.map((item, idx) => {
            const showSection = item.section !== lastSection;
            lastSection = item.section;
            const Icon = item.icon;
            return (
              <div key={item.id}>
                {showSection && (
                  <div className="cmd-palette-section">{item.section}</div>
                )}
                <button
                  type="button"
                  className={`cmd-palette-item${idx === activeIdx ? ' active' : ''}`}
                  onClick={item.action}
                  onMouseEnter={() => setActiveIdx(idx)}
                  role="option"
                  aria-selected={idx === activeIdx}
                >
                  <Icon size={16} />
                  <span>{item.label}</span>
                </button>
              </div>
            );
          })}
          {filtered.length === 0 && !query.trim() && (
            <p className="cmd-palette-empty">Nenhuma ação encontrada.</p>
          )}
        </div>

        <div className="cmd-palette-footer">
          <span><kbd>↑↓</kbd> navegar</span>
          <span><kbd>↵</kbd> selecionar</span>
          <span><kbd>esc</kbd> fechar</span>
        </div>
      </div>
    </div>
  );
});
