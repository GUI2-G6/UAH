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
    review_status: str | None = Field(
        default=None,
        description="Review state for parsed resume data before it is merged into an applicant profile.",
        examples=["pending"],
    )
    has_review_draft: bool = Field(
        default=False,
        description="True when this resume has a persisted review draft that can be resumed later.",
        examples=[True],
    )
    review_updated_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the persisted review draft was last updated.",
        examples=["2026-04-14T14:25:19.987654Z"],
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
    review_status: str | None = Field(
        default=None,
        description="Review state for the resume's persisted parse draft.",
        examples=["pending"],
    )
    has_review_draft: bool = Field(
        default=False,
        description="Whether a persisted review draft is available for resume-review resumption.",
        examples=[True],
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
    started_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when worker execution started for this job.",
        examples=["2026-03-31T14:30:02.100000Z"],
    )
    completed_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when this job reached a terminal state.",
        examples=["2026-03-31T14:30:09.300000Z"],
    )
    elapsed_seconds: int | None = Field(
        default=None,
        description="Elapsed time in seconds from enqueue/start to current or terminal state.",
        examples=[7],
    )
    attempt: int | None = Field(
        default=None,
        description="Current retry attempt number tracked by the queue worker.",
        examples=[0],
    )
    queue_position: int | None = Field(
        default=None,
        description="Position of the current user's active job in the focused method queue.",
        examples=[2],
    )
    queue_total: int | None = Field(
        default=None,
        description="Total active jobs in the focused method queue.",
        examples=[6],
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


class ResumeReviewDraftUpdate(BaseModel):
    review_draft: dict = Field(
        ...,
        description="Edited review draft based on parsed structured resume data.",
        examples=[{"personal_info": {"first_name": "Jane"}}],
    )


class ResumeReviewDraftResponse(BaseModel):
    resume_id: int = Field(..., description="Resume identifier whose review draft is being inspected.", examples=[101])
    file_name: str = Field(..., description="Stored resume filename.", examples=["Jane_Doe_Resume.pdf"])
    parse_method: str | None = Field(default=None, description="Parser method used to produce the draft.", examples=["local"])
    review_status: str | None = Field(default=None, description="Current review lifecycle state for this draft.", examples=["pending"])
    review_updated_at: datetime | None = Field(default=None, description="UTC timestamp of the latest persisted review draft update.", examples=["2026-04-14T14:25:19.987654Z"])
    review_draft: dict = Field(..., description="Editable structured review draft returned to the frontend.", examples=[{"personal_info": {"first_name": "Jane"}}])


class ResumeReviewConflictRequest(BaseModel):
    profile_id: int = Field(..., description="Applicant profile identifier selected for merge preview.", examples=[15])
    reviewed_data: dict | None = Field(default=None, description="Optional reviewed draft override from the UI before merge preview.", examples=[{"personal_info": {"first_name": "Jane"}}])


class ResumeReviewConflictResponse(BaseModel):
    profile_id: int = Field(..., description="Applicant profile identifier used for conflict evaluation.", examples=[15])
    conflict_count: int = Field(..., description="Number of conflicting non-empty values between the selected profile and reviewed draft.", examples=[4])
    conflicts: list[dict] = Field(default_factory=list, description="Conflict items keyed by canonical path for frontend review resolution.")


class ResumeReviewApplyRequest(BaseModel):
    mode: str = Field(..., description="Apply mode: 'existing' to merge into a profile or 'new' to create one.", examples=["existing"])
    reviewed_data: dict = Field(..., description="Final reviewed structured data to commit into the applicant profile system.", examples=[{"personal_info": {"first_name": "Jane"}}])
    profile_id: int | None = Field(default=None, description="Existing applicant profile identifier when mode='existing'.", examples=[15])
    profile_name: str | None = Field(default=None, description="Name for the new applicant profile when mode='new'.", examples=["Spring 2026 Profile"])
    conflict_resolutions: dict | None = Field(default=None, description="Per-path resolution map. Use 'incoming' to override an existing profile value.", examples=[{"personal_info.email": "incoming"}])


class ResumeReviewApplyResponse(BaseModel):
    resume_id: int = Field(..., description="Resume identifier whose review draft was applied.", examples=[101])
    profile_id: int = Field(..., description="Applicant profile identifier that received the reviewed data.", examples=[15])
    review_status: str = Field(..., description="Review status after apply completes.", examples=["applied"])
    conflict_count: int = Field(..., description="Total number of conflicts that were evaluated during merge.", examples=[4])
    profile: dict = Field(..., description="Updated applicant profile payload after the review draft was applied.")
