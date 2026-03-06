import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { IoSearch, IoLibraryOutline, IoDownloadOutline, IoHeartOutline, IoReaderOutline, IoPlay } from 'react-icons/io5';
import { CoverImage } from '../components/CoverImage';
import './Home.css';

function getGreeting(): string {
  const h = new Date().getHours();
  if (h >= 5 && h < 12) return 'Bom dia';
  if (h >= 12 && h < 18) return 'Boa tarde';
  return 'Boa noite';
}

const SHORTCUTS = [
  { to: '/search', icon: IoSearch, label: 'Buscar', desc: 'Música, filmes e séries' },
  { to: '/library', icon: IoLibraryOutline, label: 'Biblioteca', desc: 'Seus downloads e importados' },
  { to: '/downloads', icon: IoDownloadOutline, label: 'Downloads', desc: 'Fila e progresso' },
  { to: '/wishlist', icon: IoHeartOutline, label: 'Wishlist', desc: 'Termos e busca automática' },
  { to: '/feeds', icon: IoReaderOutline, label: 'Feeds', desc: 'RSS e itens pendentes' },
] as const;

const LIBRARY_HOME_LIMIT = 15;
type ContentType = 'music' | 'movies' | 'tv';

interface LibraryItem {
  id: number;
  name?: string;
  content_type?: string;
  source?: 'download' | 'import';
  content_path?: string;
}

export function Home() {
  const greeting = getGreeting();
  const navigate = useNavigate();
  const [libraryItems, setLibraryItems] = useState<LibraryItem[]>([]);
  const [libraryLoading, setLibraryLoading] = useState(true);

  useEffect(() => {
    setLibraryLoading(true);
    fetch('/api/library')
      .then((r) => (r.ok ? r.json() : []))
      .then((list: LibraryItem[]) => {
        const playable = (list || []).filter((x) => x.content_path);
        setLibraryItems(playable.slice(0, LIBRARY_HOME_LIMIT));
      })
      .catch(() => setLibraryItems([]))
      .finally(() => setLibraryLoading(false));
  }, []);

  const playUrl = (item: LibraryItem) => {
    if (!item.content_path) return;
    const q = item.source === 'import' ? '?source=import' : '';
    const playBase = (item.content_type === 'movies' || item.content_type === 'tv') ? '/play' : '/play-receiver';
    navigate(`${playBase}/${item.id}${q}`);
  };

  return (
    <div className="atum-page home-page">
      <h1 className="home-greeting">{greeting}</h1>

      {libraryItems.length > 0 && (
        <section className="home-library-section" aria-label="Sua biblioteca">
          <div className="home-section-header">
            <h2 className="home-section-title">Sua biblioteca</h2>
            <Link to="/library" className="home-section-link">Ver tudo</Link>
          </div>
          <div className="home-library-row">
            {libraryItems.map((item) => (
              <button
                key={`${item.source ?? 'download'}-${item.id}`}
                type="button"
                className="home-library-card"
                onClick={() => playUrl(item)}
                aria-label={`Reproduzir ${item.name || 'item'}`}
              >
                <div className="home-library-card-cover">
                  <CoverImage
                    contentType={(item.content_type === 'movies' || item.content_type === 'tv' ? item.content_type : 'music') as ContentType}
                    title={item.name || ''}
                    size="card"
                    downloadId={item.source === 'import' ? undefined : item.id}
                    importId={item.source === 'import' ? item.id : undefined}
                  />
                  <span className="home-library-card-play" aria-hidden>
                    <IoPlay size={28} />
                  </span>
                </div>
                <span className="home-library-card-title">{item.name || '—'}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {(libraryLoading || libraryItems.length === 0) && (
        <section className="home-library-section" aria-label="Sua biblioteca">
          <h2 className="home-section-title">Sua biblioteca</h2>
          {libraryLoading ? (
            <p className="home-library-empty" aria-busy="true">Carregando…</p>
          ) : (
            <p className="home-library-empty">Nenhum item para reproduzir. Adicione downloads ou importe pastas na <Link to="/library">Biblioteca</Link>.</p>
          )}
        </section>
      )}

      <section className="home-shortcuts" aria-label="Atalhos">
        <div className="home-shortcuts-grid">
          {SHORTCUTS.map(({ to, icon: Icon, label, desc }) => (
            <Link
              key={to}
              to={to}
              className="home-shortcut-card"
              aria-label={`Ir para ${label}`}
            >
              <span className="home-shortcut-icon" aria-hidden>
                <Icon size={28} />
              </span>
              <span className="home-shortcut-label">{label}</span>
              {desc && <span className="home-shortcut-desc">{desc}</span>}
            </Link>
          ))}
        </div>
      </section>

      <section className="home-search-cta">
        <p className="home-search-cta-text">Encontre artistas, álbums, filmes e séries.</p>
        <Link to="/search" className="home-search-cta-btn primary">
          Abrir Busca
        </Link>
      </section>
    </div>
  );
}
