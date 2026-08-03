import { apiClient } from "../lib/apiClient";
import { mockDashboardSnapshot } from "../data/mockDashboard";
import type { DashboardSnapshot, PeriodsResponse } from "../types/dashboard";

const USE_MOCK = (import.meta.env.VITE_USE_MOCK ?? "false") === "true";

export async function getPeriods(): Promise<PeriodsResponse> {
  const response = await apiClient.get<PeriodsResponse>("/targets/periods");
  return {
    periods: Array.isArray(response.data?.periods) ? response.data.periods : [],
    active: response.data?.active ?? null,
  };
}

export async function getDashboardSnapshot(period?: string | null, limit?: number): Promise<DashboardSnapshot> {
  if (!USE_MOCK) {
    try {
      const params = new URLSearchParams();
      if (period && period !== "all") params.set("period", period);
      if (limit) params.set("limit", String(limit));
      const query = params.toString() ? `?${params}` : "";
      const response = await apiClient.get<DashboardSnapshot>(`/dashboard/${query}`);
      const data = response.data;
      return {
        stats: data?.stats ?? { totalTargets: 0, completed: 0, inProgress: 0, pending: 0 },
        targets: Array.isArray(data?.targets) ? data.targets : [],
      };
    } catch (error) {
      console.error("Failed to fetch dashboard snapshot:", error);
      // Fallback to mock in case of error during development if needed, 
      // or just rethrow. Here we rethrow to let the UI handle it.
      throw error;
    }
  }

  return new Promise((resolve) => {
    setTimeout(() => resolve(mockDashboardSnapshot), 250);
  });
}
