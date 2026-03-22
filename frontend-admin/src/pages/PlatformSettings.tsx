import React, { useEffect, useState } from "react";
import { api } from "../api/client";

type SettingsMap = Record<string, string>;

export default function PlatformSettings() {
  const [settings, setSettings] = useState<SettingsMap>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.get<SettingsMap>("/admin/platform-settings").then(setSettings).catch(() => {});
  }, []);

  function set(key: string, value: string) {
    setSettings((prev) => ({ ...prev, [key]: value }));
  }

  async function save() {
    setSaving(true);
    setSaved(false);
    try {
      await api.patch("/admin/platform-settings", {
        registration_open: settings["registration_open"] === "true",
        cold_tier_days: settings["cold_tier_days"] ? Number(settings["cold_tier_days"]) : undefined,
        storage_pressure_pct: settings["storage_pressure_pct"] ? Number(settings["storage_pressure_pct"]) : undefined,
        cloud_sync_hours: settings["cloud_sync_hours"] || undefined,
        hls_strategy: settings["hls_strategy"] || undefined,
        hls_lru_max_gb: settings["hls_lru_max_gb"] ? Number(settings["hls_lru_max_gb"]) : undefined,
        prefetch_count: settings["prefetch_count"] ? Number(settings["prefetch_count"]) : undefined,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  }

  const field = (key: string, label: string, type: "text" | "number" | "select" = "text", options?: string[]) => (
    <div style={{ marginBottom: "1rem" }}>
      <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)", marginBottom: "0.35rem" }}>
        {label}
      </label>
      {type === "select" && options ? (
        <select value={settings[key] || ""} onChange={(e) => set(key, e.target.value)}>
          {options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <input
          type={type}
          value={settings[key] || ""}
          onChange={(e) => set(key, e.target.value)}
        />
      )}
    </div>
  );

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Configurações da Plataforma</h1>
        <button className="btn btn-primary" onClick={save} disabled={saving}>
          {saving ? "Salvando..." : saved ? "Salvo ✓" : "Salvar"}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div className="card">
          <h2 style={{ fontSize: "0.8rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-secondary)", marginBottom: "1rem" }}>
            Acesso
          </h2>
          {field("registration_open", "Registro aberto", "select", ["false", "true"])}
        </div>

        <div className="card">
          <h2 style={{ fontSize: "0.8rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-secondary)", marginBottom: "1rem" }}>
            HLS Streaming
          </h2>
          {field("hls_strategy", "Estratégia", "select", ["on_demand", "automatic", "lru"])}
          {field("hls_lru_max_gb", "Tamanho máximo LRU (GB)", "number")}
        </div>

        <div className="card">
          <h2 style={{ fontSize: "0.8rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-secondary)", marginBottom: "1rem" }}>
            Cloud Sync
          </h2>
          {field("cold_tier_days", "Cold tier após N dias", "number")}
          {field("storage_pressure_pct", "Pressão de disco (%)", "number")}
          {field("cloud_sync_hours", "Janela de sync (HH:MM-HH:MM)")}
          {field("prefetch_count", "Prefetch count", "number")}
        </div>
      </div>
    </div>
  );
}
