import type { PortalRole } from "./user";

export interface LoginPayload {
  username: string;
  password: string;
}

export interface AuthUser {
  id: string;
  name: string;
  username: string;
  role: PortalRole;
  token: string;
}
