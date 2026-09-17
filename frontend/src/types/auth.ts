export type UserRole =
  | "admin"
  | "ciso"
  | "risk_analyst"
  | "compliance_officer"
  | "executive";

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  organization_id: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Administrator",
  ciso: "CISO",
  risk_analyst: "Risk Analyst",
  compliance_officer: "Compliance Officer",
  executive: "Executive",
};
