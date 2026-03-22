import React from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { clearTokens } from "../api/client";
import "./AdminLayout.css";

const NAV = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/users", label: "Usuários" },
  { to: "/plans", label: "Planos" },
  { to: "/subscriptions", label: "Assinaturas" },
  { to: "/financial", label: "Financeiro" },
  { to: "/invites", label: "Convites" },
  { to: "/promo-codes", label: "Promo Codes" },
  { to: "/storage", label: "Storage" },
  { to: "/settings", label: "Configurações" },
];

export default function AdminLayout() {
  const navigate = useNavigate();

  function handleLogout() {
    clearTokens();
    navigate("/login");
  }

  return (
    <div className="admin-layout">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <span className="admin-brand-text">ATUM</span>
          <span className="admin-brand-sub">Backoffice</span>
        </div>
        <nav className="admin-nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `admin-nav-item${isActive ? " active" : ""}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="admin-sidebar-footer">
          <button className="btn" onClick={handleLogout}>Sair</button>
        </div>
      </aside>
      <main className="admin-content">
        <Outlet />
      </main>
    </div>
  );
}
