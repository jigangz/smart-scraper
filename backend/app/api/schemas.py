from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict


class JobCreate(BaseModel):
    name: str
    url: str
    selectors: dict
    pagination_config: Optional[dict] = None
    schedule: Optional[str] = None
    anti_detection: bool = True
    mode: Literal["fast", "dynamic", "stealth"] = "fast"
    webhook_url: Optional[str] = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    selectors: dict
    pagination_config: Optional[dict] = None
    schedule: Optional[str] = None
    anti_detection: bool
    mode: str = "fast"
    status: str
    created_at: datetime
    updated_at: datetime
    last_run: Optional[datetime] = None
    results_count: int
    webhook_url: Optional[str] = None


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


class ResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    data: dict
    scraped_at: datetime


class StatsResponse(BaseModel):
    total_jobs: int
    active_jobs: int
    total_results: int
    success_rate: float
    recent_activity: list[dict]


class LogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    level: str
    message: str
    timestamp: datetime


class ExportRequest(BaseModel):
    format: str  # "csv" or "json"
