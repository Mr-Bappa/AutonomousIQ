import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { apiRequest, setAuthToken } from "@/shared/api/client";

type TokenResponse = { access_token: string; token_type: string };
type AuthContextValue = {
  token: string | null;
  isAuthenticated: boolean;
  isPlatformAdmin: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
};
const STORAGE_KEY = "autonomousiq_access_token";
const AuthContext = createContext<AuthContextValue | null>(null);

function decodePayload(token: string | null): Record<string, unknown> {
  if (!token) return {};
  try {
    const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(part));
  } catch { return {}; }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    const saved = sessionStorage.getItem(STORAGE_KEY); setAuthToken(saved); return saved;
  });
  const isPlatformAdmin = useMemo(() => decodePayload(token).is_platform_admin === true, [token]);
  const login = useCallback(async (email: string, password: string) => {
    const result = await apiRequest<TokenResponse>("/v1/auth/login", { method: "POST", body: { email, password }, auth: false });
    sessionStorage.setItem(STORAGE_KEY, result.access_token); setAuthToken(result.access_token); setToken(result.access_token);
    return decodePayload(result.access_token).is_platform_admin === true;
  }, []);
  const logout = useCallback(() => { sessionStorage.removeItem(STORAGE_KEY); setAuthToken(null); setToken(null); }, []);
  return <AuthContext.Provider value={{ token, isAuthenticated: token !== null, isPlatformAdmin, login, logout }}>{children}</AuthContext.Provider>;
}
export function useAuth() { const ctx = useContext(AuthContext); if (!ctx) throw new Error("useAuth must be used within AuthProvider"); return ctx; }
