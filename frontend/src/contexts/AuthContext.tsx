import { createContext, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { loginManager } from "../services/authService";
import type { AuthUser, LoginPayload } from "../types/auth";

const IDLE_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  logout: () => void;
}

const STORAGE_KEY = "c3mr:web-admin:auth-user";

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readStoredUser(): AuthUser | null {
  try {
    const serialized = localStorage.getItem(STORAGE_KEY);
    if (!serialized) return null;
    const user = JSON.parse(serialized) as AuthUser;
    // Check if JWT token is expired
    if (user?.token) {
      const payload = JSON.parse(atob(user.token.split(".")[1]));
      if (payload.exp && payload.exp * 1000 < Date.now()) {
        localStorage.removeItem(STORAGE_KEY);
        return null;
      }
    }
    return user;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser());
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
    // Jangan tinggalkan riwayat chat Asisten AI di perangkat setelah logout.
    localStorage.removeItem("c3mr:assistant-chat");
  }, []);

  const resetIdleTimer = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(logout, IDLE_TIMEOUT_MS);
  }, [logout]);

  // Set up idle listeners when authenticated
  useEffect(() => {
    if (!user) return;

    const events = ["mousedown", "keydown", "touchstart", "scroll"];
    const handler = () => resetIdleTimer();

    resetIdleTimer(); // start timer on mount
    events.forEach(e => window.addEventListener(e, handler, { passive: true }));

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      events.forEach(e => window.removeEventListener(e, handler));
    };
  }, [user, resetIdleTimer]);

  const login = async (payload: LoginPayload) => {
    const authenticatedUser = await loginManager(payload);
    setUser(authenticatedUser);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(authenticatedUser));
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      login,
      logout,
    }),
    [user, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
