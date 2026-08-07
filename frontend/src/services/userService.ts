import { apiClient } from "../lib/apiClient";
import type { User, UserBase } from "../types/user";

export async function getUsers(): Promise<User[]> {
  const response = await apiClient.get<User[]>("/users/");
  return Array.isArray(response.data) ? response.data : [];
}

/** Peran portal (admin/manajer) wajib membawa email + password; backend menolak
 *  keduanya untuk petugas, yang aksesnya lewat Telegram. */
export type CreateUserPayload = UserBase & { email?: string; password?: string };

export async function createUser(payload: CreateUserPayload): Promise<User> {
  const response = await apiClient.post<User>("/users/", payload);
  return response.data;
}

export async function updateUser(userId: string, payload: { name?: string; telegram_id?: string; phone?: string; active?: boolean }): Promise<User> {
  const response = await apiClient.patch<User>(`/users/${userId}`, payload);
  return response.data;
}

export async function deleteUser(userId: string): Promise<void> {
  await apiClient.delete(`/users/${userId}`);
}
