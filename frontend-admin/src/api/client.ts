/**
 * Cliente HTTP do backoffice.
 * Injeta Bearer token automaticamente a partir do localStorage.
 */

const API_BASE = "/api";
const TOKEN_KEY = "admin_access_token";
const REFRESH_KEY = "admin_refresh_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function _request<T>(
  method: string,
  path: string,
  body?: unknown,
  retry = true,
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && retry) {
    const refreshed = await _tryRefresh();
    if (refreshed) return _request(method, path, body, false);
    clearTokens();
    window.location.href = "/login";
    throw new Error("Sessão expirada");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

async function _tryRefresh(): Promise<boolean> {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

export const api = {
  get: <T>(path: string) => _request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => _request<T>("POST", path, body),
  patch: <T>(path: string, body?: unknown) => _request<T>("PATCH", path, body),
  delete: <T>(path: string) => _request<T>("DELETE", path),
};
