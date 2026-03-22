/**
 * API client para endpoints de autenticação.
 * Todas as funções que precisam de Bearer token recebem o token como parâmetro
 * ou são chamadas após o AuthContext já tê-lo injetado.
 */

const BASE = "/api/auth";

async function _post<T>(path: string, body: unknown, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Erro desconhecido" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function _get<T>(path: string, token: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Erro" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function _delete(path: string, token: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`HTTP ${res.status}`);
  }
}

// ─── tipos públicos ────────────────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Device {
  id: string;
  device_name: string;
  user_agent: string;
  ip_address: string;
  created_at: string;
  last_seen_at: string;
}

export interface InviteCode {
  id: string;
  code: string;
  family_id: string;
  max_uses: number;
  expires_at: string | null;
}

// ─── funções ──────────────────────────────────────────────────────────────────

export function register(
  email: string,
  password: string,
  displayName: string,
  inviteCode?: string,
): Promise<LoginResponse> {
  return _post("/register", {
    email,
    password,
    display_name: displayName,
    invite_code: inviteCode || "",
  });
}

export function login(
  email: string,
  password: string,
  deviceName = "Web Browser",
): Promise<LoginResponse> {
  return _post("/login", { email, password, device_name: deviceName });
}

export function refreshToken(refreshTokenValue: string): Promise<LoginResponse> {
  return _post("/refresh", { refresh_token: refreshTokenValue });
}

export function logout(token: string, refreshTokenValue: string): Promise<void> {
  return _post("/logout", { refresh_token: refreshTokenValue }, token);
}

export function getMe(token: string): Promise<Record<string, unknown>> {
  return _get("/me", token);
}

export function listDevices(token: string): Promise<Device[]> {
  return _get("/devices", token);
}

export function revokeDevice(token: string, deviceId: string): Promise<void> {
  return _delete(`/devices/${deviceId}`, token);
}

export function createFamilyInvite(
  token: string,
  maxUses = 1,
  expiresInDays?: number,
): Promise<InviteCode> {
  return _post(
    "/invite",
    { max_uses: maxUses, expires_in_days: expiresInDays },
    token,
  );
}
