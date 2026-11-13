import { Metrics, Model, ModelType, PredictResult } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

/** Turns FastAPI error payloads (string or validation array) into a readable message. */
function messageFrom(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d: { loc?: string[]; msg?: string }) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg}`).join("; ");
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError("Cannot reach the API. Is the backend running?", 0);
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(messageFrom(body, `Request failed (${res.status})`), res.status);
  return body as T;
}

export const api = {
  listModels: () => request<Model[]>("/models"),
  listMetrics: () => request<Metrics[]>("/metrics"),
  registerModel: (m: { name: string; version: string; model_type: ModelType; description?: string }) =>
    request<Model>("/models", { method: "POST", body: JSON.stringify(m) }),
  predict: (id: string, features: Record<string, number | string | boolean>) =>
    request<PredictResult>(`/models/${id}/predict`, { method: "POST", body: JSON.stringify({ features }) }),
};
