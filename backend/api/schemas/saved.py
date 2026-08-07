from datetime import datetime

from pydantic import BaseModel, Field

from api.schemas.job import JobOut


class SavedJobOut(BaseModel):
    id: int
    job_id: int
    saved_at: datetime
    job: JobOut

    model_config = {"from_attributes": True}


class SaveJobIn(BaseModel):
    job_id: int = Field(..., gt=0)
