from fastapi import APIRouter

from app.db.database import SessionLocal
from app.db.models.ticket import Ticket
from app.schemas.ticket_schema import TicketCreate
from app.services.ticket_service import create_ticket, list_tickets

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get("/")
def get_tickets():
    db = SessionLocal()

    try:
        return list_tickets()
    finally:
        db.close()


@router.post("/")
def post_ticket(ticket: TicketCreate):
    return create_ticket(
        customer_phone=ticket.customer_phone,
        problem=ticket.problem,
        driver_phone=ticket.driver_phone,
        customer_id=ticket.customer_id,
        driver_id=ticket.driver_id
    )


@router.get("/{ticket_number}")
def get_ticket(ticket_number: str):
    db = SessionLocal()

    try:
        ticket = (
            db.query(Ticket)
            .filter(Ticket.ticket_number == ticket_number)
            .first()
        )
        return ticket
    finally:
        db.close()
