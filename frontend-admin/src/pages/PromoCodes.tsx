import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface PromoCode {
  id: string;
  code: string;
  description: string | null;
  discount_percent: number | null;
  discount_cents: number | null;
  max_uses: number | null;
  uses_count: number;
  valid_until: string | null;
}

export default function PromoCodes() {
  const [items, setItems] = useState<PromoCode[]>([]);

  useEffect(() => {
    api.get<PromoCode[]>("/admin/promo-codes").then(setItems).catch(() => {});
  }, []);

  async function deleteCode(id: string) {
    await api.delete(`/admin/promo-codes/${id}`);
    setItems((prev) => prev.filter((c) => c.id !== id));
  }

  const fmtDiscount = (c: PromoCode) =>
    c.discount_percent ? `${c.discount_percent}%` : `R$ ${((c.discount_cents || 0) / 100).toFixed(2)}`;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Promo Codes</h1>
      </div>
      <div className="card" style={{ padding: 0 }}>
        {items.length === 0 ? (
          <div className="empty-state">Nenhum código promocional</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Código</th>
                <th>Desconto</th>
                <th>Descrição</th>
                <th>Usos</th>
                <th>Válido até</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id}>
                  <td><code>{c.code}</code></td>
                  <td>{fmtDiscount(c)}</td>
                  <td>{c.description || "—"}</td>
                  <td>{c.uses_count}{c.max_uses ? `/${c.max_uses}` : ""}</td>
                  <td>{c.valid_until ? new Date(c.valid_until).toLocaleDateString("pt-BR") : "—"}</td>
                  <td>
                    <button className="btn btn-danger" onClick={() => deleteCode(c.id)}>
                      Remover
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
