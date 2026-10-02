from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hmac

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type
from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.saas import CompanyMember, SaaSUser

# New passwords use Argon2id. Parameters intentionally follow the argon2-cffi
# interactive-login defaults and can be increased later without invalidating
# existing hashes; check_needs_rehash() handles transparent upgrades.
_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

# Used when an e-mail does not exist so login still performs a password hash
# verification and does not expose an obvious user-enumeration timing shortcut.
_DUMMY_ARGON2_HASH = _password_hasher.hash("AIAffiliateIntelligence-dummy-password")
ALGO = "HS256"


def hash_password(value: str) -> str:
    """Hash a new password with Argon2id.

    Passwords are never silently truncated. The API schema currently caps them
    at 128 Unicode characters, so bcrypt's historical 72-byte limit is no
    longer relevant for newly-created accounts.
    """
    if not isinstance(value, str) or not value:
        raise ValueError("Senha inválida")
    return _password_hasher.hash(value)


def _is_argon2_hash(hashed: str) -> bool:
    return isinstance(hashed, str) and hashed.startswith("$argon2")


def _is_bcrypt_hash(hashed: str) -> bool:
    return isinstance(hashed, str) and hashed.startswith(("$2a$", "$2b$", "$2y$"))


def verify_password(value: str, hashed: str) -> bool:
    """Verify Argon2id and legacy bcrypt hashes without passlib.

    Direct bcrypt verification is kept only for accounts created by older
    releases. New hashes are always Argon2id.
    """
    if not isinstance(value, str) or not isinstance(hashed, str):
        return False
    try:
        if _is_argon2_hash(hashed):
            return _password_hasher.verify(hashed, value)
        if _is_bcrypt_hash(hashed):
            return bcrypt.checkpw(value.encode("utf-8"), hashed.encode("utf-8"))
    except (VerifyMismatchError, VerificationError, InvalidHashError, ValueError, TypeError):
        return False
    return False


def password_needs_rehash(hashed: str) -> bool:
    """Legacy bcrypt hashes and outdated Argon2 parameters are upgraded at login."""
    if _is_bcrypt_hash(hashed):
        return True
    if _is_argon2_hash(hashed):
        try:
            return _password_hasher.check_needs_rehash(hashed)
        except (InvalidHashError, ValueError, TypeError):
            return True
    return True


def verify_dummy_password(value: str) -> None:
    """Consume comparable work for login attempts against unknown e-mails."""
    try:
        _password_hasher.verify(_DUMMY_ARGON2_HASH, value or "")
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        pass


def create_token(user_id: int, company_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "company_id": company_id,
            "role": role,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=12)).timestamp()),
        },
        settings.jwt_secret,
        algorithm=ALGO,
    )


@dataclass
class Principal:
    user_id: int
    company_id: int
    role: str
    is_super_admin: bool = False


ROLE_LEVEL = {"VIEWER": 10, "EDITOR": 20, "ADMIN": 30, "OWNER": 40}


def current_principal(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Autenticação necessária")
    try:
        payload = jwt.decode(
            authorization.split(" ", 1)[1], settings.jwt_secret, algorithms=[ALGO]
        )
    except JWTError:
        raise HTTPException(401, "Sessão inválida ou expirada")

    uid = int(payload.get("sub") or 0)
    cid = int(payload.get("company_id") or 0)
    user = db.get(SaaSUser, uid)
    member = db.scalar(
        select(CompanyMember).where(
            CompanyMember.user_id == uid,
            CompanyMember.company_id == cid,
            CompanyMember.status == "active",
        )
    )
    if not user or not user.is_active or not member:
        raise HTTPException(401, "Acesso não autorizado")
    return Principal(uid, cid, member.role, user.is_super_admin)


def require_role(minimum: str):
    def dep(p: Principal = Depends(current_principal)):
        if not p.is_super_admin and ROLE_LEVEL.get(p.role, 0) < ROLE_LEVEL[minimum]:
            raise HTTPException(403, "Permissão insuficiente")
        return p

    return dep
