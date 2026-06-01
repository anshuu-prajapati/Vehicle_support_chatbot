from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.state_schema import StateResponse
from app.services.state_manager import StateManager

router = APIRouter(prefix="/conversation-state", tags=["Conversation State"])


@router.get("/{phone}", response_model=StateResponse)
def read_conversation_state(phone: str, db: Session = Depends(get_db)):
    state = StateManager(db).get_state(phone)
    if not state:
        raise HTTPException(status_code=404, detail="Conversation state not found")
    return state


@router.delete("/{phone}")
def delete_conversation_state(phone: str, db: Session = Depends(get_db)):
    deleted = StateManager(db).delete_state(phone)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation state not found")
    return {"status": "deleted", "phone_number": phone}


@router.post("/reset/{phone}", response_model=StateResponse)
def reset_conversation_state(phone: str, db: Session = Depends(get_db)):
    state = StateManager(db).clear_state(phone)
    return state
