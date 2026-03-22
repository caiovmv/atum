import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
  backoffice_role: string | null;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
  plan_code: string;
  plan_name: string;
}

export default function Users() {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const params = new URLSearchParams({ page: String(page), per_page: "50", search });
    api.get<{ items: User[]; total: number }>(`/admin/users?${params}`)
      .then((d) => { setUsers(d.items); setTotal(d.total); })
      .catch((e) => setError(e.message));
  }

  useEffect(() => { load(); }, [page, search]); // eslint-disable-line react-hooks/exhaustive-deps

  async function toggleActive(u: User) {
    await api.patch(`/admin/users/${u.id}`, { is_active: !u.is_active });
    load();
  }

  const fmtDate = (d: string | null) =>
    d ? new Date(d).toLocaleDateString("pt-BR") : "—";

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Usuários ({total})</h1>
      </div>

      {error && <div style={{ color: "var(--danger)", marginBottom: "1rem" }}>{error}</div>}

      <div style={{ marginBottom: "1rem" }}>
        <input
          placeholder="Buscar por email ou nome..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          style={{ maxWidth: 360 }}
        />
      </div>

      <div className="card" style={{ padding: 0 }}>
        {users.length === 0 ? (
          <div className="empty-state">Nenhum usuário encontrado</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>E-mail</th>
                <th>Nome</th>
                <th>Plano</th>
                <th>Role</th>
                <th>Backoffice</th>
                <th>Ativo</th>
                <th>Criado</th>
                <th>Último login</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.email}</td>
                  <td>{u.display_name || "—"}</td>
                  <td><span className="badge">{u.plan_code}</span></td>
                  <td>{u.role}</td>
                  <td>{u.backoffice_role || "—"}</td>
                  <td>
                    <span className={`badge ${u.is_active ? "badge-active" : "badge-canceled"}`}>
                      {u.is_active ? "Ativo" : "Suspenso"}
                    </span>
                  </td>
                  <td>{fmtDate(u.created_at)}</td>
                  <td>{fmtDate(u.last_login_at)}</td>
                  <td>
                    <button className="btn btn-danger" onClick={() => toggleActive(u)}>
                      {u.is_active ? "Suspender" : "Reativar"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
