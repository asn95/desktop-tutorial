export type UserRole = "admin" | "manager" | "officer";

export interface UserBase {
  name: string;
  telegram_id?: string;
  phone?: string;
  role: UserRole;
}

export interface User extends UserBase {
  id: string;
  created_at: string;
  active: boolean;
}

/** Peran yang bisa masuk portal web. Petugas hanya lewat Mini App Telegram. */
export type PortalRole = "admin" | "manager";

/** Beranda tiap peran — dipakai redirect setelah login dan untuk rute yang tidak cocok. */
export const HOME_PATH: Record<PortalRole, string> = {
  admin: "/users",
  manager: "/dashboard",
};
