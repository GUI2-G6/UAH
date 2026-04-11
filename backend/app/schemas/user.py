from pydantic import BaseModel, Field, AliasChoices, field_validator
from app.core.validation import require_valid_email


class UserRegister(BaseModel):
    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Unique login email used for authentication, password recovery, and account notifications.",
        examples=["jane.doe@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Account password in plain text at request time; it is hashed before persistence.",
        examples=["MySecurePass!123"],
    )
    first_name: str | None = Field(
        default=None,
        max_length=100,
        description="Optional given name shown in profile displays and generated messages.",
        examples=["Jane"],
    )
    last_name: str | None = Field(
        default=None,
        max_length=100,
        description="Optional family name shown in profile displays and generated messages.",
        examples=["Doe"],
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return require_valid_email(value)

class UserLogin(BaseModel):
    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        validation_alias=AliasChoices("email", "username"),
        description="Existing account email for credential-based login. Legacy `username` payload key is accepted temporarily for compatibility.",
        examples=["jane.doe@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Account password for the specified email account.",
        examples=["MySecurePass!123"],
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return require_valid_email(value)

class UserResponse(BaseModel):
    id: int = Field(
        ...,
        description="Database identifier of the authenticated user.",
        examples=[42],
    )
    email: str = Field(
        ...,
        description="Primary account email address.",
        examples=["jane.doe@example.com"],
    )
    username: str | None = Field(
        default=None,
        description="Compatibility field mirrored to the account email while username sunset is in progress.",
        examples=["jane.doe@example.com"],
    )
    first_name: str | None = Field(
        default=None,
        description="Optional first name currently saved on the profile.",
        examples=["Jane"],
    )
    last_name: str | None = Field(
        default=None,
        description="Optional last name currently saved on the profile.",
        examples=["Doe"],
    )
    avatar_url: str | None = Field(
        default=None,
        description="Optional URL to an avatar image (commonly sourced from OAuth providers).",
        examples=["https://lh3.googleusercontent.com/a-/example"],
    )
    email_verified: bool = Field(
        default=False,
        description="True when the account owner has successfully completed email verification.",
        examples=[True],
    )
    is_admin: bool = Field(
        default=False,
        description="True when the account can access admin-only backend operations.",
        examples=[False],
    )
    is_developer: bool = Field(
        default=False,
        description="True when the account can access developer-only frontend tools.",
        examples=[False],
    )
    is_active: bool = Field(
        ...,
        description="False means the account cannot authenticate until re-enabled.",
        examples=[True],
    )

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str = Field(
        ...,
        description="Signed JWT access token supplied in Authorization headers as 'Bearer <token>'.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example.signature"],
    )
    token_type: str = Field(
        default="bearer",
        description="OAuth token type. Always 'bearer' for this API.",
        examples=["bearer"],
    )
    user: UserResponse = Field(
        ...,
        description="Snapshot of the authenticated user's profile immediately after login or registration.",
    )

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Current account password for re-authentication before change.",
        examples=["OldSecurePass!123"],
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Replacement password that will be hashed and stored after validation.",
        examples=["NewSecurePass!123"],
    )

class ResetPasswordRequest(BaseModel):
    token: str = Field(
        ...,
        description="Password reset token issued by the forgot-password flow.",
        examples=["eyJhbGciOiJIUzI1NiJ9.password-reset.token"],
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password to set once the reset token is validated.",
        examples=["BrandNewPass!456"],
    )

class ForgotPasswordRequest(BaseModel):
    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Email address associated with the account requesting password reset.",
        examples=["jane.doe@example.com"],
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return require_valid_email(value)

class ChangeEmailRequest(BaseModel):
    new_email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="New email to attach to the authenticated account. Must be unique.",
        examples=["jane.new@example.com"],
    )

    @field_validator("new_email")
    @classmethod
    def validate_new_email(cls, value: str) -> str:
        return require_valid_email(value, field_name="new_email")

class ChangeUsernameRequest(BaseModel):
    new_username: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Deprecated request shape retained for compatibility while username sunset is in progress.",
        examples=["jane_doe_2"],
    )

class ChangeNameRequest(BaseModel):
    first_name: str | None = Field(
        default=None,
        max_length=100,
        description="New optional first name; blank strings are normalized to null.",
        examples=["Jane"],
    )
    last_name: str | None = Field(
        default=None,
        max_length=100,
        description="New optional last name; blank strings are normalized to null.",
        examples=["Doe"],
    )

class VerifyEmailRequest(BaseModel):
    token: str = Field(
        ...,
        description="Email verification token generated by the send-verification endpoint.",
        examples=["eyJhbGciOiJIUzI1NiJ9.email-verify.token"],
    )

class MessageResponse(BaseModel):
    message: str = Field(
        ...,
        description="Human-readable operation result intended for UI toast/alert display.",
        examples=["Password has been reset successfully"],
    )

class SaveJobRequest(BaseModel):
    user_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("user_id", "userId"),
        description="Deprecated — ignored, user is derived from JWT token.",
        examples=[42],
    )
    job_id: int = Field(
        validation_alias=AliasChoices("job_id", "jobId"),
        description="External or provider job identifier used to deduplicate saved jobs.",
        examples=[7619281],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Job title shown in the saved jobs list.",
        examples=["Software Engineer II"],
    )
    company: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Employer or organization name.",
        examples=["Acme Technologies"],
    )
    url: str = Field(
        validation_alias=AliasChoices("url", "job_url", "jobUrl"),
        description="Canonical URL of the job posting landing page.",
        examples=["https://www.themuse.com/jobs/acme/software-engineer-ii"],
    )
