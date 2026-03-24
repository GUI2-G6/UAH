from pydantic import BaseModel, EmailStr, Field, AliasChoices


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
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class SaveJobRequest(BaseModel):
    user_id: int = Field(validation_alias=AliasChoices("user_id", "userId"))
    job_id: int = Field(validation_alias=AliasChoices("job_id", "jobId"))
    name: str
    company: str
    url: str = Field(validation_alias=AliasChoices("url", "job_url", "jobUrl"))