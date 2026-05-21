import axios from "axios";

const STORAGE_KEY = "c3mr:web-admin:auth-user";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
  timeout: 10_000,
});

// Ensure trailing slashes on API paths (FastAPI routes require them)
apiClient.interceptors.request.use((config) => {
  if (config.url) {
    const [path, query] = config.url.split("?", 2);
    if (path && !path.endsWith("/")) {
      config.url = path + "/" + (query ? "?" + query : "");
    }
  }
  return config;
});

// Attach JWT token to every request
apiClient.interceptors.request.use((config) => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const user = JSON.parse(stored);
      if (user?.token) {
        config.headers.Authorization = `Bearer ${user.token}`;
      }
    }
  } catch {
    // ignore parse errors
  }
  return config;
});

// Auto-logout on 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(STORAGE_KEY);
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
