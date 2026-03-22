import type React from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  role: "owner" | "member";
  backoffice_role: string | null;
  plan_code: string;
  plan_name: string;
  hls_enabled: boolean;
  ai_enabled: boolean;
  cold_tiering_enabled: boolean;
  total_storage_gb: number;
  base_storage_gb: number;
  extra_storage_gb: number;
}

interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

interface AuthContextValue {
  user: AuthUser | null;
  accessToken: string | null;
  isLoading: boolean;
  login: (email: string, password: string, deviceName?: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<string | null>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const REFRESH_TOKEN_KEY = "atum_refresh_token";
const REFRESH_BEFORE_EXP_MS = 60_000; // renovar 1 minuto antes de expirar

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearAuth = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }
  }, []);

  const scheduleRefresh = useCallback(
    (expiresInSec: number, refreshToken: string) => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
      const delay = Math.max(0, expiresInSec * 1000 - REFRESH_BEFORE_EXP_MS);
      refreshTimerRef.current = setTimeout(async () => {
        try {
          await performRefresh(refreshToken);
        } catch {
          clearAuth();
        }
      }, delay);
    },
    [clearAuth],
  );

  const fetchMe = useCallback(async (token: string): Promise<AuthUser> => {
    const res = await fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error("Falha ao buscar perfil");
    return res.json();
  }, []);

  const performRefresh = useCallback(
    async (storedRefresh: string): Promise<string | null> => {
      const res = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: storedRefresh }),
      });
      if (!res.ok) {
        clearAuth();
        return null;
      }
      const tokens: AuthTokens = await res.json();
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
      setAccessToken(tokens.access_token);
      const me = await fetchMe(tokens.access_token);
      setUser(me);
      scheduleRefresh(tokens.expires_in, tokens.refresh_token);
      return tokens.access_token;
    },
    [clearAuth, fetchMe, scheduleRefresh],
  );

  // Inicialização: tenta renovar token salvo
  useEffect(() => {
    const stored = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!stored) {
      setIsLoading(false);
      return;
    }
    performRefresh(stored).finally(() => setIsLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const login = useCallback(
    async (email: string, password: string, deviceName = "Web Browser") => {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, device_name: deviceName }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Erro desconhecido" }));
        throw new Error(err.detail || "Falha no login");
      }
      const tokens: AuthTokens = await res.json();
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
      setAccessToken(tokens.access_token);
      const me = await fetchMe(tokens.access_token);
      setUser(me);
      scheduleRefresh(tokens.expires_in, tokens.refresh_token);
    },
    [fetchMe, scheduleRefresh],
  );

  const logout = useCallback(async () => {
    const stored = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (stored && accessToken) {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ refresh_token: stored }),
      }).catch(() => {});
    }
    clearAuth();
  }, [accessToken, clearAuth]);

  const refresh = useCallback(async () => {
    const stored = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!stored) return null;
    return performRefresh(stored);
  }, [performRefresh]);

  return (
    <AuthContext.Provider
      value={{
        user,
        accessToken,
        isLoading,
        login,
        logout,
        refresh,
        isAuthenticated: !!user && !!accessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de <AuthProvider>");
  return ctx;
}
