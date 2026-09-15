import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { apiRequest, setAuthToken } from "@/shared/api/client";

/**
 * Auth state lives here, not in Zustand or React Query -- it's neither
 * "server data that gets refetched" (React Query's job) nor generic
 * cross-feature UI state (Zustand's job per STANDARDS.md Section 2). A
 * JWT is session identity: it gates the whole app tree, so it gets its
 * own context provider wrapping the router.
 *
 * Storage choice: sessionStorage, not localStorage. Phase 0 auth is
 * stateless JWT (Baseline decision) -- there's no server-side session to
 * revoke, so persisting the token across a full browser restart (what
 * localStorage would do) has no corresponding "logout everywhere"
 * safety net yet. sessionStorage clears on tab close, which is the
 * safer default until that's built.
 */

interface TokenResponse {
  access_token: string;
  token_type: string;
}

interface AuthContextValue {
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEY = "autonomousiq_token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    if (stored) setAuthToken(stored);
    return stored;
  });

  const login = useCallback(async (email: string, password: string) => {
    // Hits POST /v1/auth/login (apps/api/auth.py) -- the "real DB round
    // trip" for the frontend, mirroring what workspaces.py was for the
    // backend Baseline slice.
    const result = await apiRequest<TokenResponse>("/v1/auth/login", {
      method: "POST",
      body: { email, password },
    });
    sessionStorage.setItem(STORAGE_KEY, result.access_token);
    setAuthToken(result.access_token);
    setToken(result.access_token);
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(STORAGE_KEY);
    setAuthToken(null);
    setToken(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, isAuthenticated: token !== null, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
