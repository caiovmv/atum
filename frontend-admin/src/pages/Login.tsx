import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { setTokens } from "../api/client";
import "./Login.css";

export default function AdminLogin() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, device_name: "Backoffice" }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Erro" }));
        throw new Error(err.detail || "Falha no login");
      }
      const data = await res.json();
      // Verifica se tem acesso ao backoffice
      const meRes = await fetch("/api/auth/me", {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });
      const me = await meRes.json();
      if (!me.backoffice_role) {
        throw new Error("Sem acesso ao backoffice. Solicite permissões ao administrador.");
      }
      setTokens(data.access_token, data.refresh_token);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro no login");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <span>ATUM</span>
          <span className="login-brand-sub">Backoffice</span>
        </div>
        {error && <div className="login-error">{error}</div>}
        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label>E-mail</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="admin@loombeat.com"
            />
          </div>
          <div className="login-field">
            <label>Senha</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
            />
          </div>
          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%", marginTop: "0.5rem" }}>
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
