from pydantic import BaseModel, EmailStr


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
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    picture_url: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
