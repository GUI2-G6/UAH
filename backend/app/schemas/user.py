from pydantic import BaseModel, Field, AliasChoices


class UserRegister(BaseModel):
    email: str
    username: str
    password: str
    first_name: str | None = None
    last_name: str | None = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str | None
    first_name: str | None
    last_name: str | None
    avatar_url: str | None
    email_verified: bool = False
    is_active: bool

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ChangeEmailRequest(BaseModel):
    new_email: str
    password: str

class ChangeUsernameRequest(BaseModel):
    new_username: str
    password: str

class ChangeNameRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None

class VerifyEmailRequest(BaseModel):
    token: str

class MessageResponse(BaseModel):
    message: str

class SaveJobRequest(BaseModel):
    user_id: int = Field(validation_alias=AliasChoices("user_id", "userId"))
    job_id: int = Field(validation_alias=AliasChoices("job_id", "jobId"))
    name: str
    company: str
    url: str = Field(validation_alias=AliasChoices("url", "job_url", "jobUrl"))
