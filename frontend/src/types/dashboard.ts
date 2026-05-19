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
