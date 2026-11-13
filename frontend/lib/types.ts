export type ModelType = "classification" | "regression" | "clustering" | "nlp" | "other";

export interface Model {
  id: string;
  name: string;
  version: string;
  model_type: ModelType;
  description: string | null;
  created_at: string;
}

export interface Metrics {
  model_id: string;
  request_count: number;
  avg_latency_ms: number;
  avg_confidence: number;
  last_request_at: string | null;
}

export interface PredictResult {
  prediction_id: string;
  prediction: string | number;
  confidence: number;
  latency_ms: number;
}

export const MODEL_TYPES: ModelType[] = ["classification", "regression", "clustering", "nlp", "other"];
