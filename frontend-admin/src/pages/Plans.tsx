import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface Plan {
  id: string;
  code: string;
  name: string;
  price_monthly_cents: number;
  price_yearly_cents: number;
  max_family_members: number;
  max_devices_per_member: number;
  base_storage_gb: number;
  hls_enabled: boolean;
  ai_enabled: boolean;
  cold_tiering_enabled: boolean;
  trial_days: number;
  is_active: boolean;
}

const fmtBRL = (cents: number) => (cents / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export default function Plans() {
  const [plans, setPlans] = useState<Plan[]>([]);

  useEffect(() => {
    api.get<Plan[]>("/admin/plans").then(setPlans).catch(() => {});
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Planos</h1>
      </div>
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>Nome</th>
              <th>Mensal</th>
              <th>Anual</th>
              <th>Membros</th>
              <th>Dispositivos</th>
              <th>Storage</th>
              <th>HLS</th>
              <th>IA</th>
              <th>Cloud</th>
              <th>Trial</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((p) => (
              <tr key={p.id}>
                <td><strong>{p.name}</strong> <code style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>{p.code}</code></td>
                <td>{fmtBRL(p.price_monthly_cents)}</td>
                <td>{fmtBRL(p.price_yearly_cents)}</td>
                <td>{p.max_family_members}</td>
                <td>{p.max_devices_per_member}</td>
                <td>{p.base_storage_gb} GB</td>
                <td>{p.hls_enabled ? "✓" : "—"}</td>
                <td>{p.ai_enabled ? "✓" : "—"}</td>
                <td>{p.cold_tiering_enabled ? "✓" : "—"}</td>
                <td>{p.trial_days > 0 ? `${p.trial_days}d` : "—"}</td>
                <td>
                  <span className={`badge ${p.is_active ? "badge-active" : "badge-canceled"}`}>
                    {p.is_active ? "Ativo" : "Inativo"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
