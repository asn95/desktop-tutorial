export type UserRole = "manager" | "officer";

export interface UserBase {
  name: string;
  telegram_id?: string;
  role: UserRole;
}

export interface User extends UserBase {
  id: string;
  created_at: string;
}
