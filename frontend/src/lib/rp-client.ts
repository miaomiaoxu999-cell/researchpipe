"use client";

const BASE = process.env.NEXT_PUBLIC_RP_BACKEND_URL || "http://localhost:3725";
const KEY = process.env.NEXT_PUBLIC_RP_DEV_KEY || "rp-demo-public";

export async function rpFetch<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Authorization": `Bearer ${KEY}`,
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`);
  }
  return (await res.json()) as T;
}
