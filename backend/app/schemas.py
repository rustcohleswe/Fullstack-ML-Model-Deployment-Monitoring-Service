"""API request/response schemas (validation lives here)."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelType(str, Enum):
    classification = "classification"
    regression = "regression"
    clustering = "clustering"
    nlp = "nlp"
    other = "other"


class ModelCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=50)
    model_type: ModelType
    description: Optional[str] = Field(default=None, max_length=500)

    @field_validator("name", "version")
    @classmethod
    def strip_and_require(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class ModelOut(BaseModel):
    id: UUID
    name: str
    version: str
    model_type: ModelType
    description: Optional[str] = None
    created_at: datetime


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    features: Dict[str, Union[int, float, str, bool]] = Field(min_length=1, max_length=100)


class PredictResponse(BaseModel):
    prediction_id: UUID
    model_id: UUID
    prediction: Union[str, float]
    confidence: float
    latency_ms: float
    created_at: datetime


class PredictionLogOut(BaseModel):
    id: UUID
    model_id: UUID
    request: Dict[str, Any]
    response: Dict[str, Any]
    latency_ms: float
    confidence: Optional[float] = None
    created_at: datetime


class MetricsOut(BaseModel):
    model_id: UUID
    request_count: int = 0
    avg_latency_ms: float = 0.0
    avg_confidence: float = 0.0  # simple proxy for drift: a falling trend is a warning sign
    last_request_at: Optional[datetime] = None
