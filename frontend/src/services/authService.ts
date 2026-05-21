import type { AuthUser, LoginPayload } from "../types/auth";
import { apiClient } from "../lib/apiClient";

export async function loginManager(payload: LoginPayload): Promise<AuthUser> {
  if (!payload.username.trim() || !payload.password.trim()) {
    throw new Error("Username and password are required.");
  }
  if (payload.password.length < 6) {
    throw new Error("Password must contain at least 6 characters.");
  }

  const response = await apiClient.post<AuthUser>("/auth/login", payload);
  return response.data;
}
