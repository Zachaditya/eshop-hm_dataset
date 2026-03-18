from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.db.models import Event
from app.core.auth_utils import get_optional_user, SESSION_COOKIE

router = APIRouter()

VALID_TYPES = {"view", "add_to_cart", "purchase", "remove"}


class EventIn(BaseModel):
    type: str  # view|add_to_cart|purchase|remove
    productId: str
    ts: datetime | None = None


@router.post("/events")
def create_event(evt: EventIn, req: Request, db: Session = Depends(get_db)):
    event_type = evt.type
    if event_type not in VALID_TYPES:
        event_type = "view"  # safe default for unknown types

    user = get_optional_user(req, db)
    user_id = user.id if user else ""
    session_id = req.cookies.get(SESSION_COOKIE, "")

    record = Event(
        user_id=user_id,
        session_id=session_id,
        product_id=evt.productId,
        event_type=event_type,
        ts=evt.ts or datetime.utcnow(),
    )
    db.add(record)
    db.commit()

    return {"received": True}
