from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class EventIn(BaseModel):
    type: str  # view|add_to_cart|purchase|remove
    productId: str
    ts: datetime | None = None

@router.post("/events")
def create_event(evt: EventIn):
    return {"received": True, **evt.model_dump()}
