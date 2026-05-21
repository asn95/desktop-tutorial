export interface LoginPayload {
  username: string;
  password: string;
}

export interface AuthUser {
  id: string;
  name: string;
  username: string;
  role: "manager";
  token: string;
}
