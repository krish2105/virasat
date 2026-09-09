"""Self-hosted auth: argon2 password hashes, signed JWT in an httpOnly cookie, roles."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from virasat.db.models import Officer, Role
from virasat.db.session import SessionLocal
from virasat.settings import settings

COOKIE = "virasat_session"
TTL = timedelta(hours=12)
_hasher = PasswordHasher()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def issue_session(response: Response, officer: Officer) -> None:
    token = jwt.encode(
        {"sub": str(officer.id), "role": officer.role.value, "exp": datetime.now(UTC) + TTL},
        settings.jwt_secret,
        algorithm="HS256",
    )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=int(TTL.total_seconds()),
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE)


def current_officer(
    db: Session = Depends(get_db), virasat_session: str | None = Cookie(default=None)
) -> Officer:
    if not virasat_session:
        raise HTTPException(401, "not signed in")
    try:
        claims = jwt.decode(virasat_session, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "session invalid or expired") from exc
    officer = db.get(Officer, uuid.UUID(claims["sub"]))
    if officer is None:
        raise HTTPException(401, "unknown officer")
    return officer


def require_role(*roles: Role):  # type: ignore[no-untyped-def]
    def check(officer: Officer = Depends(current_officer)) -> Officer:
        if officer.role not in roles:
            raise HTTPException(403, f"requires role {[r.value for r in roles]}")
        return officer

    return check
