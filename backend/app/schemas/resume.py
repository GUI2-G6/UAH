from pydantic import BaseModel
from datetime import datetime


class ResumeUploadResponse(BaseModel):
    id: int
    file_name: str
    status: str

    class Config:
        from_attributes = True

class ResumeResponse(BaseModel):
    id: int
    file_name: str
    structured_data: dict | None
    portal_ready: bool
    parse_method: str | None
    has_pdf: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ResumeListItem(BaseModel):
    id: int
    file_name: str
    portal_ready: bool
    parse_method: str | None
    has_pdf: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class PortalCheckResponse(BaseModel):
    portal_ready: bool
    missing_fields: list[str]
    total_required: int
    filled_count: int

class ParseRequest(BaseModel):
    method: str = "llm"


class ParseJobResponse(BaseModel):
    id: int
    resume_id: int
    method: str
    status: str
    progress_stage: str | None
    error_code: str | None
    error_message: str | None
    result_summary: dict | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ParseJobStartResponse(BaseModel):
    job_id: int
    status: str
