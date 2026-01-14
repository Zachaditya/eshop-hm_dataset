# app/auth.py
from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session as DbSession
from datetime import datetime, timedelta, timezone
import secrets, hashlib

from app.core.db import get_db
from app.db.models import User, UserSession

from app.services.cart_service import attach_guest_cart_to_user 

CART_COOKIE = "cart_id" 

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE = "sid"
SESSION_TTL_DAYS = 30

def _new_token() -> str:
    return secrets.token_urlsafe(32)

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def _expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)

def _set_session_cookie(resp: Response, token: str):
    resp.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # set True in prod (https)
        max_age=SESSION_TTL_DAYS * 24 * 60 * 60,
        path="/",
    )

def _clear_session_cookie(resp: Response):
    resp.delete_cookie(key=SESSION_COOKIE, path="/")

def _placeholder_password_hash() -> str:
    # satisfies NOT NULL constraint; not used for auth in this MVP
    return secrets.token_hex(32)

def _get_user_from_request(req: Request, db: DbSession) -> User | None:
    token = req.cookies.get(SESSION_COOKIE)
    if not token:
        return None

    th = _token_hash(token)
    sess = db.query(UserSession).filter(UserSession.token_hash == th).first()
    if not sess:
        return None

    now = datetime.now(timezone.utc)
    exp = sess.expires_at
    # SQLite may return naive datetimes; treat as UTC
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)

    if exp < now:
        db.delete(sess)
        db.commit()
        return None

    return db.query(User).filter(User.id == sess.user_id).first()

# ----- Schemas (passwordless) -----
class RegisterIn(BaseModel):
    email: EmailStr
    name: str | None = None

class LoginIn(BaseModel):
    email: EmailStr

class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str | None = None

@router.post("/register", response_model=UserOut)
def register(payload: RegisterIn, req: Request, resp: Response, db: DbSession = Depends(get_db)):
    email = payload.email.lower().strip()

    exists = db.query(User).filter(User.email == email).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=email,
        name=(payload.name.strip() if payload.name else None),
        password_hash=_placeholder_password_hash(),
    )
    db.add(user)
    db.flush()  # user.id available


    guest_cart_id = req.cookies.get(CART_COOKIE)
    if guest_cart_id:
        attach_guest_cart_to_user(db, guest_cart_id, user.id)

    token = _new_token()
    sess = UserSession(user_id=user.id, token_hash=_token_hash(token), expires_at=_expires_at())
    db.add(sess)
    db.commit()

    _set_session_cookie(resp, token)
    return {"id": user.id, "email": user.email, "name": user.name}


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, req: Request, resp: Response, db: DbSession = Depends(get_db)):
    email = payload.email.lower().strip()

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="No account for this email")


    guest_cart_id = req.cookies.get(CART_COOKIE)
    if guest_cart_id:
        attach_guest_cart_to_user(db, guest_cart_id, user.id)

    token = _new_token()
    sess = UserSession(user_id=user.id, token_hash=_token_hash(token), expires_at=_expires_at())
    db.add(sess)
    db.commit()

    _set_session_cookie(resp, token)
    return {"id": user.id, "email": user.email, "name": user.name}


@router.post("/logout")
def logout(req: Request, resp: Response, db: DbSession = Depends(get_db)):
    token = req.cookies.get(SESSION_COOKIE)
    if token:
        th = _token_hash(token)
        sess = db.query(UserSession).filter(UserSession.token_hash == th).first()
        if sess:
            db.delete(sess)
            db.commit()

    _clear_session_cookie(resp)
    return {"ok": True}

@router.get("/me", response_model=UserOut)
def me(req: Request, db: DbSession = Depends(get_db)):
    user = _get_user_from_request(req, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"id": user.id, "email": user.email, "name": user.name}
