import { useState, useEffect } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import {
  IoHomeOutline, IoSearch, IoDownloadOutline,
  IoHeartOutline, IoReaderOutline, IoLibraryOutline, IoRadioOutline,
  IoSettingsOutline, IoEllipsisHorizontal, IoListOutline,
  IoChevronBack,
} from 'react-icons/io5';
import { useToast } from '../contexts/ToastContext';
import { useNowPlaying } from '../contexts/NowPlayingContext';
import { useLayoutNotifications } from '../hooks/useLayoutNotifications';
import { NowPlayingBar } from './NowPlayingBar';
import { CommandPalette } from './CommandPalette';
import { LayoutNotifications } from './layout/LayoutNotifications';
import { PWAInstallBanner } from './PWAInstallBanner';
import './Layout.css';

const MORE_ROUTES = [
  { to: '/wishlist', icon: IoHeartOutline, label: 'Wishlist' },
  { to: '/feeds', icon: IoReaderOutline, label: 'Feeds' },
  { to: '/radio', icon: IoRadioOutline, label: 'Rádio' },
  { to: '/settings', icon: IoSettingsOutline, label: 'Configurações' },
] as const;

export function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const { showToast } = useToast();
  const { track: nowPlayingTrack } = useNowPlaying();
  const location = useLocation();

  const notif = useLayoutNotifications(showToast, notifOpen);
  const isMoreActive = MORE_ROUTES.some(r => location.pathname.startsWith(r.to));

  useEffect(() => { setMoreOpen(false); }, [location.pathname]);

  return (
    <div className={`atum-layout${nowPlayingTrack ? ' atum-layout--has-player' : ''}`}>
      <a href="#main-content" className="atum-skip-link">Pular para conteúdo principal</a>
      <CommandPalette />
      <PWAInstallBanner />
      <NowPlayingBar />
      <button
        type="button"
        className="atum-menu-toggle"
        onClick={() => setMenuOpen((o) => !o)}
        aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'}
        aria-expanded={menuOpen}
      >
        <span className="atum-menu-toggle-bar" />
        <span className="atum-menu-toggle-bar" />
        <span className="atum-menu-toggle-bar" />
      </button>
      <div
        className="atum-sidebar-backdrop"
        aria-hidden
        data-open={menuOpen}
        onClick={() => setMenuOpen(false)}
      />
      <aside className={`atum-sidebar${sidebarCollapsed ? ' atum-sidebar--collapsed' : ''}`} data-open={menuOpen}>
        <div className="atum-sidebar-top">
          {sidebarCollapsed ? (
            <button
              type="button"
              className="atum-sidebar-brand atum-sidebar-brand--btn"
              onClick={() => setSidebarCollapsed(false)}
              aria-label="Expandir menu"
            >
              A
            </button>
          ) : (
            <>
              <div className="atum-sidebar-brand">Atum</div>
              <button
                type="button"
                className="atum-sidebar-collapse-btn"
                onClick={() => setSidebarCollapsed(true)}
                aria-label="Recolher menu"
              >
                <IoChevronBack size={16} />
              </button>
            </>
          )}
        </div>
        <nav className="atum-nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoHomeOutline className="atum-nav-icon" aria-hidden />
            <span>Início</span>
          </NavLink>
          <NavLink to="/search" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoSearch className="atum-nav-icon" aria-hidden />
            <span>Busca</span>
          </NavLink>
          <NavLink to="/downloads" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoDownloadOutline className="atum-nav-icon" aria-hidden />
            <span>Downloads</span>
          </NavLink>
          <NavLink to="/wishlist" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoHeartOutline className="atum-nav-icon" aria-hidden />
            <span>Wishlist</span>
          </NavLink>
          <NavLink to="/feeds" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoReaderOutline className="atum-nav-icon" aria-hidden />
            <span>Feeds</span>
          </NavLink>
          <NavLink to="/library" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoLibraryOutline className="atum-nav-icon" aria-hidden />
            <span>Biblioteca</span>
          </NavLink>
          <NavLink to="/playlists" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoListOutline className="atum-nav-icon" aria-hidden />
            <span>Playlists</span>
          </NavLink>
          <NavLink to="/radio" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoRadioOutline className="atum-nav-icon" aria-hidden />
            <span>Rádio</span>
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            <IoSettingsOutline className="atum-nav-icon" aria-hidden />
            <span>Configurações</span>
          </NavLink>
        </nav>
      </aside>
      <main className="atum-main">
        <div className="atum-main-header">
          <span />
          <LayoutNotifications
            open={notifOpen}
            onClose={() => setNotifOpen(false)}
            onOpenChange={setNotifOpen}
            unreadCount={notif.unreadCount}
            notifications={notif.notifications}
            loading={notif.notifLoading}
            reconnecting={notif.notifReconnecting}
            onMarkRead={notif.markRead}
            onMarkAllRead={notif.markAllRead}
            onClearAll={notif.clearAll}
          />
        </div>
        <div id="main-content" className="atum-main-content">
          <Outlet />
        </div>
      </main>

      <nav className="atum-tab-bar" aria-label="Navegação principal">
        <NavLink to="/" end className={({ isActive }) => `atum-tab-item${isActive ? ' active' : ''}`}>
          <IoHomeOutline className="atum-tab-icon" aria-hidden />
          <span className="atum-tab-label">Início</span>
        </NavLink>
        <NavLink to="/search" className={({ isActive }) => `atum-tab-item${isActive ? ' active' : ''}`}>
          <IoSearch className="atum-tab-icon" aria-hidden />
          <span className="atum-tab-label">Busca</span>
        </NavLink>
        <NavLink to="/library" className={({ isActive }) => `atum-tab-item${isActive ? ' active' : ''}`}>
          <IoLibraryOutline className="atum-tab-icon" aria-hidden />
          <span className="atum-tab-label">Biblioteca</span>
        </NavLink>
        <NavLink to="/downloads" className={({ isActive }) => `atum-tab-item${isActive ? ' active' : ''}`}>
          <IoDownloadOutline className="atum-tab-icon" aria-hidden />
          <span className="atum-tab-label">Downloads</span>
        </NavLink>
        <div className="atum-tab-more-wrap">
          <button
            type="button"
            className={`atum-tab-item${isMoreActive ? ' active' : ''}`}
            onClick={() => setMoreOpen(o => !o)}
            aria-label="Mais opções"
            aria-expanded={moreOpen}
          >
            <IoEllipsisHorizontal className="atum-tab-icon" aria-hidden />
            <span className="atum-tab-label">Mais</span>
          </button>
          {moreOpen && (
            <>
              <div className="atum-tab-more-backdrop" onClick={() => setMoreOpen(false)} />
              <div className="atum-tab-more-menu" role="menu">
                {MORE_ROUTES.map(({ to, icon: Icon, label }) => (
                  <NavLink
                    key={to}
                    to={to}
                    className={({ isActive }) => `atum-tab-more-item${isActive ? ' active' : ''}`}
                    role="menuitem"
                    onClick={() => setMoreOpen(false)}
                  >
                    <Icon className="atum-tab-more-icon" aria-hidden />
                    <span>{label}</span>
                  </NavLink>
                ))}
              </div>
            </>
          )}
        </div>
      </nav>
    </div>
  );
}
