import { QueryClient } from "@tanstack/react-query";

export const API_BASE = "/backend-api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 1,
    },
  },
});

export async function apiFetch<T>(
  path: string,
  options?: RequestInit & { token?: string }
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (options?.token) {
    headers["Authorization"] = `Bearer ${options.token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { ...headers, ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `API error: ${res.status}`);
  }
  return res.json();
}
