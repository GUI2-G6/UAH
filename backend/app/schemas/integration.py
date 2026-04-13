from pydantic import BaseModel, Field


class ServiceAction(BaseModel):
    key: str = Field(..., examples=["connect"])
    label: str = Field(..., examples=["Connect"])
    enabled: bool = Field(default=True, examples=[True])
    style: str = Field(default="primary", examples=["primary"])
    method: str | None = Field(default=None, examples=["POST"])
    href: str | None = Field(default=None, examples=["/api/integrations/gmail/connect/start"])


class ServiceReadiness(BaseModel):
    title: str = Field(..., examples=["Ready for mailbox-powered updates"])
    description: str = Field(..., examples=["UAH can use this connection for future job-update signals."])
    tone: str = Field(default="neutral", examples=["positive"])


class ServiceSummary(BaseModel):
    key: str = Field(..., examples=["gmail"])
    label: str = Field(..., examples=["Gmail Updates"])
    category: str = Field(..., examples=["communication"])
    status: str = Field(..., examples=["connected"])
    connected: bool = Field(..., examples=[True])
    availability: str = Field(..., examples=["available"])
    summary: str = Field(..., examples=["Mailbox ready for future job-update scanning and timeline enrichment."])
    account_label: str | None = Field(default=None, examples=["jane.doe@example.com"])
    primary_action: ServiceAction
    can_view_details: bool = Field(default=True, examples=[True])


class ServiceDetail(BaseModel):
    key: str = Field(..., examples=["gmail"])
    label: str = Field(..., examples=["Gmail Updates"])
    status: str = Field(..., examples=["connected"])
    connected: bool = Field(..., examples=[True])
    account_label: str | None = Field(default=None, examples=["jane.doe@example.com"])
    availability: str = Field(..., examples=["available"])
    description: str = Field(..., examples=["Connect Gmail so UAH can prepare for inbox-driven job update workflows."])
    capabilities: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    readiness: ServiceReadiness
    planned_features: list[str] = Field(default_factory=list)
    actions: list[ServiceAction] = Field(default_factory=list)
