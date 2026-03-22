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
  by_plan: { code: string; name: string; count: number }[];
}

export default function Dashboard() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Overview>("/admin/financial/overview")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  const fmt = (v: number) =>
    v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
      </div>

      {error && <div style={{ color: "var(--danger)", marginBottom: "1rem" }}>{error}</div>}

      {data && (
        <>
          <div className="stat-grid">
            <div className="stat-card">
              <div className="stat-label">MRR</div>
              <div className="stat-value">{fmt(data.mrr_brl)}</div>
              <div className="stat-sub">Receita Recorrente Mensal</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">ARR</div>
              <div className="stat-value">{fmt(data.arr_brl)}</div>
              <div className="stat-sub">Receita Recorrente Anual</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Assinantes Ativos</div>
              <div className="stat-value">{data.active_subscriptions}</div>
              <div className="stat-sub">+{data.trialing_subscriptions} em trial</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Receita do Mês</div>
              <div className="stat-value">{fmt(data.month_revenue_brl)}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Churn (30d)</div>
              <div className="stat-value" style={{ color: "var(--danger)" }}>
                {data.churn_last_30d}
              </div>
              <div className="stat-sub">{data.new_last_30d} novos no período</div>
            </div>
          </div>

          <div className="card">
            <h2 style={{ fontSize: "0.8rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-secondary)", marginBottom: "1rem" }}>
              Assinantes por plano
            </h2>
            <table>
              <thead>
                <tr>
                  <th>Plano</th>
                  <th>Código</th>
                  <th style={{ textAlign: "right" }}>Assinantes</th>
                </tr>
              </thead>
              <tbody>
                {data.by_plan.map((p) => (
                  <tr key={p.code}>
                    <td>{p.name}</td>
                    <td><code>{p.code}</code></td>
                    <td style={{ textAlign: "right", fontWeight: 600 }}>{p.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
