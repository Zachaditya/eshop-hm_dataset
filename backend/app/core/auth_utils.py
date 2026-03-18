"""Shared auth utilities used by auth.py, cart.py, and orders.py."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models import User, UserSession

SESSION_COOKIE = "sid"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_optional_user(
    req: Request,
    db: Session,
    *,
    delete_expired: bool = False,
) -> User | None:
    """
    Returns the authenticated User for the current request, or None.

    If delete_expired=True, expired sessions are removed from the DB
    (used in auth routes where we want to clean up on access).
    """
    raw = req.cookies.get(SESSION_COOKIE)
    if not raw:
        return None

    th = token_hash(raw)
    sess = db.query(UserSession).filter(UserSession.token_hash == th).first()
    if not sess:
        return None

    now = datetime.now(timezone.utc)
    exp = sess.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)

    if exp < now:
        if delete_expired:
            db.delete(sess)
            db.commit()
        return None

    return db.query(User).filter(User.id == sess.user_id).first()
