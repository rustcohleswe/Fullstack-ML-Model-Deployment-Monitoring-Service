"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import ModelCard from "@/components/ModelCard";
import RegisterModelForm from "@/components/RegisterModelForm";
import { api } from "@/lib/api";
import { Metrics, Model } from "@/lib/types";

const POLL_MS = 3000;

export default function Dashboard() {
  const [models, setModels] = useState<Model[]>([]);
  const [metrics, setMetrics] = useState<Record<string, Metrics>>({});
  const [nameFilter, setNameFilter] = useState("");
  const [versionFilter, setVersionFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [m, stats] = await Promise.all([api.listModels(), api.listMetrics()]);
      setModels(m);
      setMetrics(Object.fromEntries(stats.map((s) => [s.model_id, s])));
      setUpdatedAt(new Date());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  // Real-time-ish: poll the API every few seconds.
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, POLL_MS);
    return () => clearInterval(t);
  }, [refresh]);

  const filtered = useMemo(() => {
    const n = nameFilter.trim().toLowerCase();
    const v = versionFilter.trim().toLowerCase();
    return models.filter((m) => m.name.toLowerCase().includes(n) && m.version.toLowerCase().includes(v));
  }, [models, nameFilter, versionFilter]);

  return (
    <main>
      <header>
        <h1>ML Model Monitor</h1>
        <span className="muted">
          {updatedAt ? `Live · updated ${updatedAt.toLocaleTimeString()} (every ${POLL_MS / 1000}s)` : "Connecting…"}
        </span>
      </header>

      <div className="toolbar">
        <input placeholder="Filter by name" value={nameFilter} onChange={(e) => setNameFilter(e.target.value)} aria-label="Filter by name" />
        <input placeholder="Filter by version" value={versionFilter} onChange={(e) => setVersionFilter(e.target.value)} aria-label="Filter by version" />
        <span className="muted" style={{ alignSelf: "center" }}>{filtered.length} of {models.length} models</span>
      </div>

      {error && <div className="error" role="alert">{error}</div>}

      <RegisterModelForm onRegistered={refresh} />

      <h2>Models</h2>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : filtered.length === 0 ? (
        <p className="muted">{models.length === 0 ? "No models registered yet." : "No models match the filters."}</p>
      ) : (
        <div className="grid">
          {filtered.map((m) => (
            <ModelCard key={m.id} model={m} metrics={metrics[m.id]} onPredicted={refresh} />
          ))}
        </div>
      )}
    </main>
  );
}
