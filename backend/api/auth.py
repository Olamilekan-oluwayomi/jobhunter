"""Opaque, revocable cookie sessions. Passwords and session tokens are never stored raw."""

import hashlib
import hmac
import json
import secrets
import threading
import time
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.dependencies import get_db
from config import get_settings
from database.models import LoginSession, User
from utils.time import utcnow

router = APIRouter(prefix="/auth", tags=["accounts"])
COOKIE = "jobhunter_session"
SESSION_SECONDS = 7 * 24 * 3600
_attempts: dict[str, list[float]] = {}
_lock = threading.Lock()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=2**17, r=8, p=1, maxmem=256 * 1024 * 1024
    )
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        # Equal work for unknown accounts and valid accounts.
        encoded = "scrypt$" + "00" * 16 + "$" + "00" * 64
    try:
        algorithm, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=2**17, r=8, p=1, maxmem=256 * 1024 * 1024
        )
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def browser_write(request: Request):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    # A custom header requires a successful CORS preflight for cross-origin callers.
    if request.headers.get("x-requested-with") != "JobHunter":
        raise HTTPException(403, "Missing request protection header")
    origin = request.headers.get("origin")
    allowed = {*get_settings().effective_cors_origins, str(request.base_url).rstrip("/")}
    if origin and origin not in allowed:
        raise HTTPException(403, "Origin is not allowed")


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    browser_write(request)
    token = request.cookies.get(COOKIE, "")
    if not token or len(token) > 200:
        raise HTTPException(401, "Sign in to continue")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    user = db.scalar(
        select(User)
        .join(LoginSession, LoginSession.user_id == User.id)
        .where(
            LoginSession.token_hash == token_hash,
            LoginSession.expires_at > utcnow(),
            User.is_active.is_(True),
        )
    )
    if user is None:
        raise HTTPException(401, "Session expired. Sign in again")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Administrator access required")
    return user


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        if (
            value.count("@") != 1
            or "." not in value.split("@")[-1]
            or any(c.isspace() for c in value)
        ):
            raise ValueError("Enter a valid email address")
        return value


class Profile(BaseModel):
    name: str = Field("", max_length=100)
    role: str = Field("", max_length=100)
    location: str = Field("", max_length=100)
    level: str = Field("Not specified", max_length=50)
    skills: list[str] = Field(default_factory=list, max_length=50)
    remote: bool = True

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, values):
        values = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        if any(len(value) > 100 for value in values):
            raise ValueError("Skill names must be at most 100 characters")
        return values


def user_out(user):
    return {
        "id": user.id,
        "email": user.email,
        "is_admin": user.is_admin,
        "profile": Profile.model_validate(json.loads(user.profile or "{}")).model_dump(),
    }


def _session(db, user, response, request):
    # Rotate the current browser session and clear expired tokens.
    old = request.cookies.get(COOKIE)
    if old:
        db.execute(
            delete(LoginSession).where(
                LoginSession.token_hash == hashlib.sha256(old.encode()).hexdigest()
            )
        )
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= utcnow()))
    token = secrets.token_urlsafe(32)
    db.add(
        LoginSession(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            expires_at=utcnow() + timedelta(seconds=SESSION_SECONDS),
        )
    )
    db.commit()
    response.set_cookie(
        COOKIE,
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=get_settings().is_production,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return user_out(user)


def _throttle(request):
    now = time.monotonic()
    key = request.client.host if request.client else "unknown"
    with _lock:
        expired = [key for key, times in _attempts.items() if times[-1] < now - 300]
        for old in expired:
            del _attempts[old]
        times = [stamp for stamp in _attempts.get(key, []) if stamp > now - 300]
        if len(times) >= 10 or (key not in _attempts and len(_attempts) >= 10000):
            raise HTTPException(429, "Too many sign-in attempts. Try again in five minutes")
        _attempts[key] = [*times, now]


@router.post("/register", status_code=201, dependencies=[Depends(browser_write)])
def register(
    payload: Credentials, request: Request, response: Response, db: Session = Depends(get_db)
):
    _throttle(request)
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This email cannot be registered") from None
    return _session(db, user, response, request)


@router.post("/login", dependencies=[Depends(browser_write)])
def login(
    payload: Credentials, request: Request, response: Response, db: Session = Depends(get_db)
):
    _throttle(request)
    user = db.scalar(select(User).where(User.email == payload.email))
    valid = verify_password(payload.password, user.password_hash if user else None)
    if not user or not valid or not user.is_active:
        raise HTTPException(401, "Email or password is incorrect")
    return _session(db, user, response, request)


@router.get("/me")
def me(response: Response, user: User = Depends(current_user)):
    response.headers["Cache-Control"] = "no-store"
    return user_out(user)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256(request.cookies[COOKIE].encode()).hexdigest()
    db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash))
    db.commit()
    response.delete_cookie(COOKIE, path="/")


@router.put("/profile")
def update_profile(
    payload: Profile, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    db.execute(
        update(User)
        .where(User.id == user.id)
        .values(profile=payload.model_dump_json(), profile_version=User.profile_version + 1)
    )
    db.commit()
    db.refresh(user)
    return user_out(user)
