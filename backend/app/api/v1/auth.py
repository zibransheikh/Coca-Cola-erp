from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
)
from app.db.session import get_db
from app.models import Permission, RefreshToken, Role, RolePermission, User, UserRole
from app.schemas.auth import RefreshRequest, TokenPair, UserOut
from app.services.audit import record_audit

router = APIRouter(prefix="/auth", tags=["auth"])


def _permission_codes_for_user(db: Session, user_id: int) -> list[str]:
    rows = db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .distinct()
    ).scalars()
    return list(rows)


def _role_names_for_user(db: Session, user_id: int) -> list[str]:
    rows = db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
    ).scalars()
    return list(rows)


@router.post("/login", response_model=TokenPair)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.execute(select(User).where(User.email == form_data.username)).scalar_one_or_none()
    if user is None or not verify_password(form_data.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    permissions = _permission_codes_for_user(db, user.id)
    access_token = create_access_token(subject=str(user.id), permissions=permissions)
    refresh_token, expires_at = create_refresh_token(subject=str(user.id))

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            issued_at=datetime.now(timezone.utc),
            expires_at=expires_at,
        )
    )
    record_audit(
        db,
        user_id=user.id,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    try:
        payload = decode_token(body.refresh_token)
    except ValueError:
        raise invalid
    if payload.get("type") != "refresh":
        raise invalid

    token_hash = hash_token(body.refresh_token)
    stored = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()
    if stored is None or stored.revoked_at is not None:
        raise invalid
    if stored.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise invalid

    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise invalid

    # Rotate: revoke the old refresh token, issue a new pair.
    stored.revoked_at = datetime.now(timezone.utc)
    permissions = _permission_codes_for_user(db, user.id)
    access_token = create_access_token(subject=str(user.id), permissions=permissions)
    new_refresh_token, expires_at = create_refresh_token(subject=str(user.id))
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_refresh_token),
            issued_at=datetime.now(timezone.utc),
            expires_at=expires_at,
        )
    )
    db.commit()

    return TokenPair(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserOut)
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        roles=_role_names_for_user(db, user.id),
        permissions=_permission_codes_for_user(db, user.id),
    )
