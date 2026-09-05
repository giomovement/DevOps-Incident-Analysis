import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Cookie, Depends, Header, HTTPException, Response, status

from .config import settings
from .database import db, utcnow

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
SESSION_DAYS = 7


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def issue_session(response: Response, user_id: str) -> str:
    session = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    now = datetime.now(UTC)
    with db() as conn:
        conn.execute(
            "INSERT INTO sessions(id_hash,user_id,csrf_hash,expires_at,created_at) VALUES(?,?,?,?,?)",
            (digest(session), user_id, digest(csrf), (now + timedelta(days=SESSION_DAYS)).isoformat(), now.isoformat()),
        )
    cookie = dict(secure=settings.session_cookie_secure, samesite="lax", path="/", max_age=SESSION_DAYS * 86400)
    response.set_cookie("dias_session", session, httponly=True, **cookie)
    response.set_cookie("dias_csrf", csrf, httponly=False, **cookie)
    return csrf


def authenticate(email: str, password: str):
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE lower(email)=lower(?)", (email,)).fetchone()
    if not user:
        return None
    try:
        password_hasher.verify(user["password_hash"], password)
    except VerifyMismatchError:
        return None
    return dict(user)


def current_user(dias_session: str | None = Cookie(default=None)):
    if not dias_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    with db() as conn:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.id_hash=? AND s.expires_at>?",
            (digest(dias_session), utcnow()),
        ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    return dict(row)


def require_mutation(
    user=Depends(current_user),
    dias_session: str | None = Cookie(default=None),
    dias_csrf: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None),
):
    if not dias_session or not dias_csrf or not x_csrf_token or not secrets.compare_digest(dias_csrf, x_csrf_token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF validation failed")
    with db() as conn:
        row = conn.execute("SELECT csrf_hash FROM sessions WHERE id_hash=?", (digest(dias_session),)).fetchone()
    if not row or not secrets.compare_digest(row["csrf_hash"], digest(x_csrf_token)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF validation failed")
    return user


def require_responder(user=Depends(require_mutation)):
    if user["role"] not in ("admin", "responder"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Responder role required")
    return user


def public_user(user: dict) -> dict:
    return {k: user[k] for k in ("id", "email", "display_name", "role", "workspace_id")}


def create_user(email: str, password: str, display_name: str):
    user_id = str(uuid4())
    with db() as conn:
        count = conn.execute("SELECT count(*) FROM users").fetchone()[0]
        role = "admin" if count == 0 else "responder"
        conn.execute(
            "INSERT INTO users(id,email,password_hash,display_name,role,workspace_id,created_at) VALUES(?,?,?,?,?,'default',?)",
            (user_id, email.lower(), password_hasher.hash(password), display_name, role, utcnow()),
        )
        return dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
