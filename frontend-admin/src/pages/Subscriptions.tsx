import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface Subscription {
  id: string;
  family_id: string;
  status: string;
  billing_period: string;
  current_period_start: string;
  current_period_end: string;
  plan_code: string;
  plan_name: string;
  family_name: string;
}

const fmtDate = (d: string) => new Date(d).toLocaleDateString("pt-BR");

export default function Subscriptions() {
  const [items, setItems] = useState<Subscription[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);

  useEffect(() => {
    api.get<{ items: Subscription[]; total: number }>(`/admin/subscriptions?page=${page}&per_page=50`)
      .then((d) => { setItems(d.items); setTotal(d.total); })
      .catch(() => {});
  }, [page]);

  const statusClass: Record<string, string> = {
    active: "badge-active", canceled: "badge-canceled",
    trialing: "badge-trialing", past_due: "badge-past-due", paused: "badge-paused",
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Assinaturas ({total})</h1>
      </div>
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>Família</th>
              <th>Plano</th>
              <th>Status</th>
              <th>Cobrança</th>
              <th>Período início</th>
              <th>Período fim</th>
            </tr>
          </thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.id}>
                <td>{s.family_name}</td>
                <td><span className="badge">{s.plan_code}</span></td>
                <td>
                  <span className={`badge ${statusClass[s.status] || ""}`}>{s.status}</span>
                </td>
                <td>{s.billing_period}</td>
                <td>{fmtDate(s.current_period_start)}</td>
                <td>{fmtDate(s.current_period_end)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
        <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>← Anterior</button>
        <button className="btn" onClick={() => setPage((p) => p + 1)}>Próxima →</button>
      </div>
    </div>
  );
}
