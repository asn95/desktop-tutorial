import type { Target } from "./target";

export interface DashboardStats {
  totalTargets: number;
  completed: number;
  inProgress: number;
  pending: number;
}

export interface DashboardSnapshot {
  stats: DashboardStats;
  targets: Target[];
}

export interface PeriodInfo {
  period: string;
  total: number;
}

export interface PeriodsResponse {
  periods: PeriodInfo[];
  active: string | null;
}
