from pydantic import BaseModel, Field
from datetime import datetime


class ResumeUploadResponse(BaseModel):
    id: int = Field(
        ...,
        description="Database identifier of the uploaded resume record.",
        examples=[101],
    )
    file_name: str = Field(
        ...,
        description="Original PDF filename provided during upload.",
        examples=["Jane_Doe_Resume.pdf"],
    )
    status: str = Field(
        ...,
        description="Upload operation state returned by the API.",
        examples=["uploaded"],
    )

    class Config:
        from_attributes = True

class ResumeResponse(BaseModel):
    id: int = Field(
        ...,
        description="Resume primary key used in follow-up parse and retrieval operations.",
        examples=[101],
    )
    file_name: str = Field(
        ...,
        description="Stored filename for the uploaded resume document.",
        examples=["Jane_Doe_Resume.pdf"],
    )
    structured_data: dict | None = Field(
        default=None,
        description="Normalized resume content produced by parsing (contact info, skills, education, and work history).",
        examples=[{"name": "Jane Doe", "email": "jane@example.com", "skills": ["Python", "SQL"]}],
    )
    portal_ready: bool = Field(
        ...,
        description="True when required ATS/autofill fields are present after validation.",
        examples=[True],
    )
    parse_method: str | None = Field(
        default=None,
        description="Parser mode used most recently for this resume. Supported values: 'cloud', 'local', or 'rules'.",
        examples=["local"],
    )
    has_pdf: bool = Field(
        default=False,
        description="Indicates whether original binary PDF content is still available for download/preview.",
        examples=[True],
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp when the resume was first stored.",
        examples=["2026-03-31T14:22:33.123456Z"],
    )
    updated_at: datetime = Field(
        ...,
        description="UTC timestamp of the latest mutation (parse, validation, or metadata update).",
        examples=["2026-03-31T14:25:19.987654Z"],
    )

    class Config:
        from_attributes = True

class ResumeListItem(BaseModel):
    id: int = Field(
        ...,
        description="Resume identifier.",
        examples=[101],
    )
    file_name: str = Field(
        ...,
        description="Uploaded filename shown in list views.",
        examples=["Jane_Doe_Resume.pdf"],
    )
    portal_ready: bool = Field(
        ...,
        description="Quick indicator of whether this resume meets required portal fields.",
        examples=[False],
    )
    parse_method: str | None = Field(
        default=None,
        description="Most recent parse engine used for this resume.",
        examples=["cloud"],
    )
    has_pdf: bool = Field(
        default=False,
        description="Whether PDF binary content can be streamed via the PDF endpoint.",
        examples=[True],
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp when the resume was uploaded.",
        examples=["2026-03-31T14:22:33.123456Z"],
    )

    class Config:
        from_attributes = True

class PortalCheckResponse(BaseModel):
    portal_ready: bool = Field(
        ...,
        description="True when all mandatory application portal fields are currently present.",
        examples=[False],
    )
    missing_fields: list[str] = Field(
        ...,
        description="Names of fields still missing from structured resume data.",
        examples=[["phone", "work_auth", "employment_history"]],
    )
    total_required: int = Field(
        ...,
        description="Total number of required fields used by the readiness validator.",
        examples=[15],
    )
    filled_count: int = Field(
        ...,
        description="Count of required fields currently populated.",
        examples=[12],
    )

class ParseRequest(BaseModel):
    method: str = Field(
        default="local",
        description="Parsing strategy. Supported values: 'cloud' (ZAI), 'local' (Ollama), or 'rules' (deterministic parser).",
        examples=["local"],
    )


class ParseJobResponse(BaseModel):
    id: int = Field(
        ...,
        description="Parse job identifier used for polling and cancellation endpoints.",
        examples=[988],
    )
    resume_id: int = Field(
        ...,
        description="Resume identifier associated with this parse job.",
        examples=[101],
    )
    method: str = Field(
        ...,
        description="Parsing engine selected when the job was queued: cloud, local, or rules.",
        examples=["cloud"],
    )
    status: str = Field(
        ...,
        description="Current lifecycle state: queued, parsing, validating, success, failed, or cancelled.",
        examples=["parsing"],
    )
    progress_stage: str | None = Field(
        default=None,
        description="Human-readable progress text for UI status indicators.",
        examples=["AI parsing..."],
    )
    error_code: str | None = Field(
        default=None,
        description="Machine-readable failure code when status is failed.",
        examples=["OCR_TIMEOUT"],
    )
    error_message: str | None = Field(
        default=None,
        description="Human-readable explanation for a failed parse job.",
        examples=["Resume OCR request timed out. Please retry in a moment."],
    )
    result_summary: dict | None = Field(
        default=None,
        description="Compact outcome metrics when parsing succeeds (portal readiness, missing counts, extracted sections).",
        examples=[{"portal_ready": True, "skills_count": 14, "missing_count": 0}],
    )
    queue_snapshot: dict | None = Field(
        default=None,
        description="Optional queue status snapshot included when polling with include_queue=true.",
        examples=[{"current_user": {"active_jobs": 1, "active_job_position": 2}, "queue_depth_total": 4}],
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp when the parse job was created.",
        examples=["2026-03-31T14:30:00.000000Z"],
    )
    updated_at: datetime = Field(
        ...,
        description="UTC timestamp for the most recent parse job state transition.",
        examples=["2026-03-31T14:30:04.580000Z"],
    )

    class Config:
        from_attributes = True


class ParseJobStartResponse(BaseModel):
    job_id: int = Field(
        ...,
        description="Identifier of the newly queued parse job.",
        examples=[988],
    )
    status: str = Field(
        ...,
        description="Initial parse job state, typically 'queued'.",
        examples=["queued"],
    )
