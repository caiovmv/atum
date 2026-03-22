import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface Overview {
  mrr_brl: number;
  arr_brl: number;
  active_subscriptions: number;
  trialing_subscriptions: number;
  churn_last_30d: number;
  new_last_30d: number;
  month_revenue_brl: number;
}

interface Payment {
  id: string;
  amount_cents: number;
  currency: string;
  status: string;
  description: string;
  paid_at: string | null;
  owner_email: string;
}

const fmt = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const fmtDate = (d: string | null) => d ? new Date(d).toLocaleString("pt-BR") : "—";

export default function Financial() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);

  useEffect(() => {
    api.get<Overview>("/admin/financial/overview").then(setOverview).catch(() => {});
    api.get<{ items: Payment[] }>("/admin/financial/payments?per_page=30")
      .then((d) => setPayments(d.items))
      .catch(() => {});
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Financeiro</h1>
      </div>

      {overview && (
        <div className="stat-grid" style={{ marginBottom: "1.5rem" }}>
          <div className="stat-card">
            <div className="stat-label">MRR</div>
            <div className="stat-value">{fmt(overview.mrr_brl)}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">ARR</div>
            <div className="stat-value">{fmt(overview.arr_brl)}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Receita do mês</div>
            <div className="stat-value">{fmt(overview.month_revenue_brl)}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Churn (30d)</div>
            <div className="stat-value" style={{ color: "var(--danger)" }}>{overview.churn_last_30d}</div>
            <div className="stat-sub">{overview.new_last_30d} novos</div>
          </div>
        </div>
      )}

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>Usuário</th>
              <th>Valor</th>
              <th>Status</th>
              <th>Descrição</th>
              <th>Pago em</th>
            </tr>
          </thead>
          <tbody>
            {payments.map((p) => (
              <tr key={p.id}>
                <td>{p.owner_email}</td>
                <td>{fmt(p.amount_cents / 100)}</td>
                <td>
                  <span className={`badge ${p.status === "succeeded" ? "badge-active" : p.status === "failed" ? "badge-canceled" : ""}`}>
                    {p.status}
                  </span>
                </td>
                <td>{p.description || "—"}</td>
                <td>{fmtDate(p.paid_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
