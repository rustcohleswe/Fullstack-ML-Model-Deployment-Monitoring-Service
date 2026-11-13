"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Metrics, Model } from "@/lib/types";

export default function ModelCard({ model, metrics, onPredicted }: { model: Model; metrics?: Metrics; onPredicted: () => void }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  /** Sends a sample request so the dashboard has live traffic to show. */
  async function sendTest() {
    setBusy(true);
    setError(null);
    try {
      const r = await api.predict(model.id, { value: Math.round(Math.random() * 100), source: "dashboard" });
      setResult(`${r.prediction} (confidence ${(r.confidence * 100).toFixed(1)}%, ${r.latency_ms} ms)`);
      onPredicted();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setBusy(false);
    }
  }

  const m = metrics;
  return (
    <article className="card">
      <h3>{model.name}</h3>
      <span className="badge">v{model.version}</span>
      <span className="badge">{model.model_type}</span>
      {model.description && <p className="muted">{model.description}</p>}
      <div className="stats">
        <div className="stat"><b>{m ? m.request_count : "–"}</b><span className="muted">requests</span></div>
        <div className="stat"><b>{m ? `${m.avg_latency_ms.toFixed(1)} ms` : "–"}</b><span className="muted">avg latency</span></div>
        <div className="stat"><b>{m ? `${(m.avg_confidence * 100).toFixed(1)}%` : "–"}</b><span className="muted">avg confidence</span></div>
      </div>
      <div className="muted">Last request: {m?.last_request_at ? new Date(m.last_request_at).toLocaleString() : "never"}</div>
      <p><button className="secondary" onClick={sendTest} disabled={busy}>{busy ? "Sending…" : "Send test prediction"}</button></p>
      {result && <div className="result">{result}</div>}
      {error && <div className="error" role="alert">{error}</div>}
    </article>
  );
}
