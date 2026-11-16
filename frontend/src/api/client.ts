import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export const api = axios.create({ baseURL: API_BASE_URL });

export function getAccessToken() {
  return localStorage.getItem("access_token");
}

export function getRefreshToken() {
  return localStorage.getItem("refresh_token");
}

export function setTokens(access: string, refresh?: string) {
  localStorage.setItem("access_token", access);
  if (refresh) localStorage.setItem("refresh_token", refresh);
}

export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  try {
    const response = await axios.post(`${API_BASE_URL}/auth/refresh/`, { refresh });
    const access = response.data.access as string;
    setTokens(access);
    return access;
  } catch {
    clearTokens();
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      refreshing = refreshing || refreshAccessToken();
      const newAccess = await refreshing;
      refreshing = null;
      if (newAccess) {
        original.headers.Authorization = `Bearer ${newAccess}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  }
);
