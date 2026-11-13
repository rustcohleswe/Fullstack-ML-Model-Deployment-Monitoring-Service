"use client";

import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { MODEL_TYPES, ModelType } from "@/lib/types";

export default function RegisterModelForm({ onRegistered }: { onRegistered: () => void }) {
  const [name, setName] = useState("");
  const [version, setVersion] = useState("");
  const [type, setType] = useState<ModelType>("classification");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.registerModel({ name, version, model_type: type, description: description || undefined });
      setName("");
      setVersion("");
      setDescription("");
      onRegistered();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to register model");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" aria-label="Register model">
      <h3>Register a model</h3>
      <form className="register" onSubmit={submit}>
        <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={100} />
        <input placeholder="Version (e.g. 1.0.0)" value={version} onChange={(e) => setVersion(e.target.value)} required maxLength={50} />
        <select value={type} onChange={(e) => setType(e.target.value as ModelType)}>
          {MODEL_TYPES.map((t) => <option key={t}>{t}</option>)}
        </select>
        <input placeholder="Description (optional)" value={description} onChange={(e) => setDescription(e.target.value)} maxLength={500} />
        <button type="submit" disabled={busy}>{busy ? "Registering…" : "Register"}</button>
      </form>
      {error && <div className="error" role="alert">{error}</div>}
    </section>
  );
}
