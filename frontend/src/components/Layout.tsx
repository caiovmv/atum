import { useState } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import './Layout.css';

export function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="atum-layout">
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
      <aside className="atum-sidebar" data-open={menuOpen}>
        <div className="atum-sidebar-brand">Atum</div>
        <nav className="atum-nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            Busca
          </NavLink>
          <NavLink to="/downloads" className={({ isActive }) => (isActive ? 'atum-nav-item active' : 'atum-nav-item')} onClick={() => setMenuOpen(false)}>
            Downloads
          </NavLink>
        </nav>
      </aside>
      <main className="atum-main">
        <Outlet />
      </main>
    </div>
  );
}
