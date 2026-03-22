import React, { useEffect, useState } from "react";
import { api } from "../api/client";

interface StorageOverview {
  minio: {
    total_gb: number;
    buckets: Record<string, { gb: number; bytes: number }>;
  };
  hls_jobs: Record<string, number>;
  cloud_sync_queue: Record<string, number>;
}

const fmtGB = (v: number) => `${v.toFixed(2)} GB`;

export default function Storage() {
  const [data, setData] = useState<StorageOverview | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<StorageOverview>("/admin/storage/overview")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Storage</h1>
      </div>

      {error && <div style={{ color: "var(--danger)", marginBottom: "1rem" }}>{error}</div>}

      {data && (
        <>
          <div className="stat-grid">
            <div className="stat-card">
              <div className="stat-label">MinIO Total</div>
              <div className="stat-value">{fmtGB(data.minio.total_gb)}</div>
            </div>
            {Object.entries(data.minio.buckets).map(([bucket, info]) => (
              <div className="stat-card" key={bucket}>
                <div className="stat-label">{bucket}</div>
                <div className="stat-value">{fmtGB(info.gb)}</div>
              </div>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div className="card">
              <h2 style={{ fontSize: "0.75rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-secondary)", marginBottom: "0.75rem" }}>
                HLS Jobs
              </h2>
              {Object.entries(data.hls_jobs).map(([status, count]) => (
                <div key={status} style={{ display: "flex", justifyContent: "space-between", padding: "0.35rem 0", borderBottom: "1px solid var(--border)" }}>
                  <span>{status}</span>
                  <strong>{count}</strong>
                </div>
              ))}
              {Object.keys(data.hls_jobs).length === 0 && <div className="empty-state">Nenhum job</div>}
            </div>

            <div className="card">
              <h2 style={{ fontSize: "0.75rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-secondary)", marginBottom: "0.75rem" }}>
                Fila de Cloud Sync
              </h2>
              {Object.entries(data.cloud_sync_queue).map(([status, count]) => (
                <div key={status} style={{ display: "flex", justifyContent: "space-between", padding: "0.35rem 0", borderBottom: "1px solid var(--border)" }}>
                  <span>{status}</span>
                  <strong>{count}</strong>
                </div>
              ))}
              {Object.keys(data.cloud_sync_queue).length === 0 && <div className="empty-state">Fila vazia</div>}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
