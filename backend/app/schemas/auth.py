from pydantic import BaseModel, EmailStr

from app.schemas.user import UserRead


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    """
    Self-registration is intentionally restricted: the first Phase-1 demo
    ships with a seeded admin account. This endpoint lets that admin (or
    another ADMIN-role user) create additional users for the org.
    """
    email: EmailStr
    full_name: str | None = None
    password: str
    role: str
