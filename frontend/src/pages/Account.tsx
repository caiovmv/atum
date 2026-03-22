import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { listDevices, revokeDevice, createFamilyInvite, type Device, type InviteCode } from "../api/auth";
import "./Account.css";

export default function Account() {
  const { user, accessToken, logout } = useAuth();
  const navigate = useNavigate();
  const [devices, setDevices] = useState<Device[]>([]);
  const [invite, setInvite] = useState<InviteCode | null>(null);
  const [inviteLoading, setInviteLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!accessToken) return;
    listDevices(accessToken)
      .then(setDevices)
      .catch(() => {});
  }, [accessToken]);

  async function handleRevokeDevice(deviceId: string) {
    if (!accessToken) return;
    try {
      await revokeDevice(accessToken, deviceId);
      setDevices((prev) => prev.filter((d) => d.id !== deviceId));
    } catch (err) {
      setError("Falha ao revogar dispositivo");
    }
  }

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  async function handleCreateInvite() {
    if (!accessToken) return;
    setInviteLoading(true);
    try {
      const inv = await createFamilyInvite(accessToken, 1, 7);
      setInvite(inv);
    } catch (err) {
      setError("Falha ao criar convite");
    } finally {
      setInviteLoading(false);
    }
  }

  if (!user) return null;

  const usagePercent = user.total_storage_gb > 0
    ? Math.min(100, (user.extra_storage_gb / user.total_storage_gb) * 100)
    : 0;

  return (
    <div className="account-page">
      <div className="account-header">
        <h1>Minha conta</h1>
        <button className="account-logout-btn" onClick={handleLogout}>
          Sair
        </button>
      </div>

      {error && <div className="account-error">{error}</div>}

      {/* Perfil */}
      <section className="account-section">
        <h2>Perfil</h2>
        <div className="account-profile">
          <div className="account-avatar">{user.display_name?.[0]?.toUpperCase() || "A"}</div>
          <div>
            <div className="account-name">{user.display_name || "—"}</div>
            <div className="account-email">{user.email}</div>
            <div className="account-role">
              <span className="badge">{user.role}</span>
              {user.backoffice_role && (
                <span className="badge badge-admin">{user.backoffice_role}</span>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Plano */}
      <section className="account-section">
        <h2>Plano</h2>
        <div className="account-plan">
          <div className="account-plan-name">{user.plan_name}</div>
          <div className="account-plan-features">
            <span className={`feature-badge ${user.hls_enabled ? "on" : "off"}`}>
              HLS {user.hls_enabled ? "✓" : "—"}
            </span>
            <span className={`feature-badge ${user.ai_enabled ? "on" : "off"}`}>
              AI {user.ai_enabled ? "✓" : "—"}
            </span>
            <span className={`feature-badge ${user.cold_tiering_enabled ? "on" : "off"}`}>
              Cloud Sync {user.cold_tiering_enabled ? "✓" : "—"}
            </span>
          </div>
          <div className="account-storage">
            <div className="account-storage-label">
              Storage: {user.base_storage_gb} GB base
              {user.extra_storage_gb > 0 && ` + ${user.extra_storage_gb} GB add-on`}
              {" "}= {user.total_storage_gb} GB total
            </div>
            <div className="account-storage-bar">
              <div className="account-storage-fill" style={{ width: `${usagePercent}%` }} />
            </div>
          </div>
          <div className="account-plan-actions">
            <button
              className="account-btn"
              onClick={() =>
                fetch("/api/webhooks/stripe/checkout/session", {
                  method: "POST",
                  headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${accessToken}`,
                  },
                  body: JSON.stringify({ plan_code: "premium" }),
                })
                  .then((r) => r.json())
                  .then((d) => d.url && window.open(d.url, "_blank"))
                  .catch(() => setError("Falha ao abrir checkout"))
              }
            >
              Gerenciar assinatura
            </button>
          </div>
        </div>
      </section>

      {/* Dispositivos */}
      <section className="account-section">
        <h2>Dispositivos</h2>
        <div className="account-devices">
          {devices.length === 0 && (
            <p className="account-empty">Nenhum dispositivo registrado</p>
          )}
          {devices.map((d) => (
            <div className="account-device" key={d.id}>
              <div className="account-device-info">
                <div className="account-device-name">{d.device_name}</div>
                <div className="account-device-meta">
                  Último acesso: {new Date(d.last_seen_at).toLocaleDateString("pt-BR")}
                  {d.ip_address && ` • ${d.ip_address}`}
                </div>
              </div>
              <button
                className="account-revoke-btn"
                onClick={() => handleRevokeDevice(d.id)}
              >
                Revogar
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Convites (owner only) */}
      {user.role === "owner" && (
        <section className="account-section">
          <h2>Convidar membro</h2>
          <p className="account-invite-hint">
            Compartilhe o link de convite para adicionar alguém à sua família.
          </p>
          {invite && (
            <div className="account-invite-code">
              <span>{`${window.location.origin}/register?invite=${invite.code}`}</span>
              <button
                onClick={() =>
                  navigator.clipboard.writeText(
                    `${window.location.origin}/register?invite=${invite.code}`,
                  )
                }
              >
                Copiar
              </button>
            </div>
          )}
          <button
            className="account-btn"
            onClick={handleCreateInvite}
            disabled={inviteLoading}
          >
            {inviteLoading ? "Gerando..." : "Gerar convite (7 dias)"}
          </button>
        </section>
      )}
    </div>
  );
}
