import axios from "axios";

// In local dev this stays a relative path — vite.config.ts proxies /api to
// the local backend, so no env var is needed. In production (Netlify), the
// frontend and backend are on different hosts, so VITE_API_URL must be set
// at build time to the backend's actual URL (e.g. https://api.example.com).
const API_BASE = `${import.meta.env.VITE_API_URL ?? ""}/api/v1`;

export const api = axios.create({ baseURL: API_BASE });

const ACCESS_TOKEN_KEY = "dms_access_token";
const REFRESH_TOKEN_KEY = "dms_refresh_token";

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string) {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refreshToken });
          setTokens(data.access_token, data.refresh_token);
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api(originalRequest);
        } catch {
          clearTokens();
        }
      }
    }
    return Promise.reject(error);
  }
);

export interface CurrentUser {
  id: number;
  email: string;
  full_name: string;
  roles: string[];
  permissions: string[];
}
