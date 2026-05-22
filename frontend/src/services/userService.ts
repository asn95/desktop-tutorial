import { apiClient } from "../lib/apiClient";
import type { User, UserBase } from "../types/user";

export async function getUsers(): Promise<User[]> {
  const response = await apiClient.get<User[]>("/users/");
  return Array.isArray(response.data) ? response.data : [];
}

export async function createUser(payload: UserBase): Promise<User> {
  const response = await apiClient.post<User>("/users/", payload);
  return response.data;
}

export async function updateUser(userId: string, payload: { name?: string; telegram_id?: string }): Promise<User> {
  const response = await apiClient.patch<User>(`/users/${userId}`, payload);
  return response.data;
}

export async function deleteUser(userId: string): Promise<void> {
  await apiClient.delete(`/users/${userId}`);
}
