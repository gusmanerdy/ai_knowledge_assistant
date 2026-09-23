from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
import time
from typing import Literal

from dotenv import load_dotenv
from fastapi import HTTPException, Request, status

from backend.app.core.paths import PROJECT_ROOT


load_dotenv(PROJECT_ROOT / ".env")

Role = Literal["admin", "researcher", "viewer"]
SESSION_COOKIE = "aka_session"
SESSION_DURATION_SECONDS = 8 * 60 * 60


@dataclass(frozen=True)
class Account:
    username: str
    display_name: str
    role: Role
    password_digest: bytes


@dataclass(frozen=True)
class SessionUser:
    username: str
    display_name: str
    role: Role


def _password_digest(username: str, password: str) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        f"ai-knowledge-assistant:{username}".encode("utf-8"),
        210_000,
    )


def _account(username: str, display_name: str, role: Role, password: str) -> Account:
    return Account(
        username=username,
        display_name=display_name,
        role=role,
        password_digest=_password_digest(username, password),
    )


def _load_accounts() -> dict[str, Account]:
    definitions: list[tuple[str, str, Role, str]] = [
        (
            os.getenv("ADMIN_USERNAME", "admin"),
            os.getenv("ADMIN_DISPLAY_NAME", "Administrator"),
            "admin",
            os.getenv("ADMIN_PASSWORD", "admin123"),
        ),
        (
            os.getenv("RESEARCHER_USERNAME", "researcher"),
            os.getenv("RESEARCHER_DISPLAY_NAME", "Researcher"),
            "researcher",
            os.getenv("RESEARCHER_PASSWORD", "research123"),
        ),
        (
            os.getenv("VIEWER_USERNAME", "viewer"),
            os.getenv("VIEWER_DISPLAY_NAME", "Viewer"),
            "viewer",
            os.getenv("VIEWER_PASSWORD", "viewer123"),
        ),
    ]
    return {
        username: _account(username, display_name, role, password)
        for username, display_name, role, password in definitions
        if username and password
    }


ACCOUNTS = _load_accounts()


def authenticate(username: str, password: str) -> SessionUser | None:
    account = ACCOUNTS.get(username.strip())
    if account is None:
        return None
    candidate = _password_digest(account.username, password)
    if not hmac.compare_digest(account.password_digest, candidate):
        return None
    return SessionUser(account.username, account.display_name, account.role)


def _url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _session_secret() -> bytes:
    return os.getenv("AUTH_SECRET", "development-secret-change-me").encode("utf-8")


def create_session_token(user: SessionUser) -> str:
    payload = json.dumps(
        {
            "username": user.username,
            "role": user.role,
            "expires_at": int(time.time()) + SESSION_DURATION_SECONDS,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    encoded_payload = _url_encode(payload)
    signature = hmac.new(_session_secret(), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded_payload}.{_url_encode(signature)}"


def read_session_token(token: str | None) -> SessionUser | None:
    if not token:
        return None
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        expected = hmac.new(
            _session_secret(), encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected, _url_decode(encoded_signature)):
            return None
        payload = json.loads(_url_decode(encoded_payload))
        if int(payload["expires_at"]) <= int(time.time()):
            return None
        account = ACCOUNTS.get(payload["username"])
        if account is None or account.role != payload["role"]:
            return None
        return SessionUser(account.username, account.display_name, account.role)
    except (binascii.Error, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def current_user_or_none(request: Request) -> SessionUser | None:
    return read_session_token(request.cookies.get(SESSION_COOKIE))


def require_user(request: Request) -> SessionUser:
    user = current_user_or_none(request)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesi login diperlukan.")
    return user


def require_roles(*roles: Role):
    def dependency(request: Request) -> SessionUser:
        user = require_user(request)
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akun Anda tidak memiliki akses ke fitur ini.",
            )
        return user

    return dependency


def landing_path(role: Role) -> str:
    return {
        "admin": "/admin",
        "researcher": "/research",
        "viewer": "/viewer",
    }[role]
