import { createContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { loginManager } from "../services/authService";
import type { AuthUser, LoginPayload } from "../types/auth";

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

  const login = async (payload: LoginPayload) => {
    const authenticatedUser = await loginManager(payload);
    setUser(authenticatedUser);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(authenticatedUser));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      login,
      logout,
    }),
    [user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
