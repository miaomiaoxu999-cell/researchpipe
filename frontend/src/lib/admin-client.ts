/**
 * Admin API client — adds X-Admin-Key from localStorage.
 * Used by /admin/* pages.
 */

const BASE = process.env.NEXT_PUBLIC_RP_BACKEND_URL || "http://localhost:3725";
const KEY_STORAGE = "rp-admin-key";

export function getAdminKey(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(KEY_STORAGE);
}

export function setAdminKey(key: string) {
  localStorage.setItem(KEY_STORAGE, key);
}

export function clearAdminKey() {
  localStorage.removeItem(KEY_STORAGE);
}

export async function adminFetch<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const key = getAdminKey();
  if (!key) throw new Error("not_authenticated");
  const resp = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "X-Admin-Key": key,
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
  });
  if (resp.status === 401) {
    clearAdminKey();
    throw new Error("invalid_key");
  }
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`http_${resp.status}: ${text.slice(0, 200)}`);
  }
  return resp.json() as Promise<T>;
}
