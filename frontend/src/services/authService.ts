import type { AuthUser, LoginPayload } from "../types/auth";
import { apiClient } from "../lib/apiClient";

/** Login admin tidak langsung mengembalikan token: server mengirim kode enam digit
 *  ke Telegram dan membalas {mfa_required}. Token baru terbit setelah kode ditukar. */
export type LoginResult =
  | { kind: "signed-in"; user: AuthUser }
  | { kind: "mfa"; username: string };

export async function loginManager(payload: LoginPayload): Promise<LoginResult> {
  if (!payload.username.trim() || !payload.password.trim()) {
    throw new Error("Username and password are required.");
  }
  if (payload.password.length < 6) {
    throw new Error("Password must contain at least 6 characters.");
  }

  const { data } = await apiClient.post<AuthUser & { mfa_required?: boolean }>("/auth/login", payload);
  if (data.mfa_required) return { kind: "mfa", username: data.username };
  return { kind: "signed-in", user: data as AuthUser };
}

export async function loginWith2fa(username: string, code: string): Promise<AuthUser> {
  const { data } = await apiClient.post<AuthUser>("/auth/login-2fa", { username, code });
  return data;
}
