# Authentication Router for HireLoop

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.apps.api.app.db.session import get_db
from hireloop.apps.api.app.models.models import User
from hireloop.apps.api.app.services.auth import hash_password, verify_password, create_access_token

router = APIRouter()

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "candidate"  # candidate, recruiter

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user in PostgreSQL and return access token."""
    # Check if email is already taken
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )

    # Validate role
    if req.role not in {"candidate", "recruiter", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be candidate, recruiter, or admin"
        )

    hashed = hash_password(req.password)
    user = User(
        email=req.email,
        password_hash=hashed,
        role=req.role
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": user.email, "role": user.role})
    return TokenResponse(access_token=token)

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate credentials against PostgreSQL and return access token."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalars().first()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user.email, "role": user.role})
    return TokenResponse(access_token=token)
