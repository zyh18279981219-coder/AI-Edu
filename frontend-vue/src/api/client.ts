import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/api",
  withCredentials: true,
});

const backendOrigin = (import.meta.env.VITE_BACKEND_ORIGIN as string | undefined)?.replace(/\/$/, "")
  ?? (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

export function buildBackendUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${backendOrigin}${normalizedPath}`;
}
