from app.db.database import SessionLocal
from app.db.models.ticket import Ticket


def _normalize_phone(phone_number: str) -> str:
    if not phone_number:
        return None

    cleaned = "+".join([p for p in phone_number.strip().replace(" ", "").split("+") if p])
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned

    return cleaned


def generate_ticket_number():
    db = SessionLocal()

    try:
        last_ticket = (
            db.query(Ticket)
            .order_by(Ticket.id.desc())
            .first()
        )

        if not last_ticket or not last_ticket.ticket_number:
            return "TKT-1001"

        try:
            last_num = int(last_ticket.ticket_number.split("-")[1])
        except (IndexError, ValueError):
            last_num = last_ticket.id + 1000

        return f"TKT-{last_num + 1}"
    finally:
        db.close()


def create_ticket(
    customer_phone: str,
    problem: str,
    driver_phone: str = None,
    customer_id: int = None,
    driver_id: int = None,
    status: str = "OPEN"
):
    normalized_customer_phone = _normalize_phone(customer_phone)
    normalized_driver_phone = _normalize_phone(driver_phone) if driver_phone else None

    ticket_number = generate_ticket_number()
    db = SessionLocal()

    try:
        ticket = Ticket(
            ticket_number=ticket_number,
            customer_phone=normalized_customer_phone,
            driver_phone=normalized_driver_phone,
            customer_id=customer_id,
            driver_id=driver_id,
            problem=problem,
            status=status
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket
    finally:
        db.close()


def get_ticket(ticket_number: str):
    db = SessionLocal()

    try:
        return (
            db.query(Ticket)
            .filter(Ticket.ticket_number == ticket_number)
            .first()
        )
    finally:
        db.close()


def list_tickets():
    db = SessionLocal()

    try:
        return db.query(Ticket).order_by(Ticket.created_at.desc()).all()
    finally:
        db.close()
