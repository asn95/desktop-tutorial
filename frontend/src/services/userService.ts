import { apiClient } from "../lib/apiClient";
import type { User, UserBase } from "../types/user";

export async function getUsers(): Promise<User[]> {
  const response = await apiClient.get<User[]>("/users");
  return response.data;
}

export async function createUser(payload: UserBase): Promise<User> {
  const response = await apiClient.post<User>("/users", payload);
  return response.data;
}

export async function deleteUser(userId: string): Promise<void> {
  await apiClient.delete(`/users/${userId}`);
}
