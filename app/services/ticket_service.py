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
    status: str = "OPEN",
    **kwargs  # Accept additional fields for service engineer assignment
):
    """
    Create a new ticket with optional service engineer assignment fields.
    
    Args:
        customer_phone: Customer phone number
        problem: Problem description
        driver_phone: Driver phone number (optional)
        customer_id: Customer user ID (optional)
        driver_id: Driver user ID (optional)
        status: Ticket status (default: OPEN)
        **kwargs: Additional fields (issue_type, vehicle_number, location, etc.)
    """
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
            status=status,
            **kwargs  # Pass through additional fields
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket
    finally:
        db.close()


def update_ticket(ticket_number: str, **kwargs):
    """
    Update ticket fields.
    
    Args:
        ticket_number: Ticket number to update
        **kwargs: Fields to update (status, location, visit_date, etc.)
    
    Returns:
        Updated ticket or None if not found
    """
    db = SessionLocal()
    try:
        from app.repositories.ticket_repository import TicketRepository
        repo = TicketRepository(db)
        ticket = repo.get_by_ticket_number(ticket_number)
        if not ticket:
            return None
        return repo.update(ticket, **kwargs)
    finally:
        db.close()


def close_ticket(ticket_number: str, closure_reason: str):
    """
    Close a ticket with a reason.
    
    Args:
        ticket_number: Ticket number to close
        closure_reason: Reason for closure
    
    Returns:
        Closed ticket or None if not found
    """
    return update_ticket(
        ticket_number,
        status="CLOSED",
        closure_reason=closure_reason
    )


def assign_engineer(ticket_number: str, engineer_id: int):
    """
    Assign an engineer to a ticket.
    
    Args:
        ticket_number: Ticket number to assign
        engineer_id: Engineer user ID
    
    Returns:
        Updated ticket or None if not found
    """
    return update_ticket(
        ticket_number,
        assigned_engineer_id=engineer_id,
        status="ASSIGNED"
    )


def create_service_request_ticket(
    vehicle_number: str,
    issue_type: str,
    customer_phone: str,
    **kwargs
):
    """
    Create a ticket specifically for service engineer assignment workflow.
    
    Args:
        vehicle_number: Vehicle registration number
        issue_type: Issue type classification (WORKSHOP, ACCIDENT, etc.)
        customer_phone: Customer phone number
        **kwargs: Additional service request fields
    
    Returns:
        Created ticket
    """
    return create_ticket(
        customer_phone=customer_phone,
        problem=f"{issue_type} - Service Request",
        status="OPEN",
        vehicle_number=vehicle_number,
        issue_type=issue_type,
        **kwargs
    )


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
