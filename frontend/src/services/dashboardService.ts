import { apiClient } from "../lib/apiClient";
import { mockDashboardSnapshot } from "../data/mockDashboard";
import type { DashboardSnapshot } from "../types/dashboard";

const USE_MOCK = (import.meta.env.VITE_USE_MOCK ?? "true") === "true";

export async function getDashboardSnapshot(): Promise<DashboardSnapshot> {
  if (!USE_MOCK) {
    try {
      const response = await apiClient.get<DashboardSnapshot>("/dashboard");
      return response.data;
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
