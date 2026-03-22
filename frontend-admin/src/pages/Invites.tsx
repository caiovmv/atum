import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface Invite {
  id: string;
  code: string;
  max_uses: number;
  uses_count: number;
  expires_at: string | null;
  created_at: string;
  created_by_email: string;
  family_name: string | null;
  plan_code: string | null;
}

export default function Invites() {
  const [invites, setInvites] = useState<Invite[]>([]);
  const [creating, setCreating] = useState(false);

  const load = () =>
    api.get<Invite[]>("/admin/invites").then(setInvites).catch(() => {});

  useEffect(() => { load(); }, []);

  async function createInvite() {
    setCreating(true);
    try {
      await api.post("/admin/invites", { max_uses: 1, expires_in_days: 7 });
      load();
    } finally {
      setCreating(false);
    }
  }

  async function deleteInvite(id: string) {
    await api.delete(`/admin/invites/${id}`);
    load();
  }

  const fmtDate = (d: string | null) =>
    d ? new Date(d).toLocaleDateString("pt-BR") : "—";

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Convites</h1>
        <button className="btn btn-primary" onClick={createInvite} disabled={creating}>
          {creating ? "Criando..." : "Novo convite"}
        </button>
      </div>
      <div className="card" style={{ padding: 0 }}>
        {invites.length === 0 ? (
          <div className="empty-state">Nenhum convite</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Código</th>
                <th>Criado por</th>
                <th>Família</th>
                <th>Plano</th>
                <th>Usos</th>
                <th>Expira</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {invites.map((inv) => (
                <tr key={inv.id}>
                  <td><code>{inv.code}</code></td>
                  <td>{inv.created_by_email}</td>
                  <td>{inv.family_name || "Nova família"}</td>
                  <td>{inv.plan_code || "—"}</td>
                  <td>{inv.uses_count}/{inv.max_uses}</td>
                  <td>{fmtDate(inv.expires_at)}</td>
                  <td>
                    <button className="btn btn-danger" onClick={() => deleteInvite(inv.id)}>
                      Revogar
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
