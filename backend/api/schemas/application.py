from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from api.schemas.job import JobOut

ApplicationStatus = Literal["applied", "interview", "offer", "rejected"]


class ApplicationOut(BaseModel):
    id: int
    job_id: int
    status: ApplicationStatus
    applied_at: datetime
    notes: str | None = None
    job: JobOut | None = None

    model_config = {"from_attributes": True}


class ApplicationCreate(BaseModel):
    job_id: int = Field(..., gt=0)
    status: ApplicationStatus = "applied"
    notes: str | None = Field(None, max_length=2000)


class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ApplicationStatus | None = None
    notes: str | None = Field(None, max_length=2000)
