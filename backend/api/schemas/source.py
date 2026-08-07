from pydantic import BaseModel


class SourceOut(BaseModel):
    id: int
    name: str
    url: str | None = None
    job_count: int = 0

    model_config = {"from_attributes": True}
