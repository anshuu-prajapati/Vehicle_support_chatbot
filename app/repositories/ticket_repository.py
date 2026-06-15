import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.models.ticket import Ticket

logger = logging.getLogger("app.ticket_repository")


class TicketRepository:
    """Repository for ticket data access operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, ticket_id: int) -> Optional[Ticket]:
        """Get ticket by ID"""
        return self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    def get_by_ticket_number(self, ticket_number: str) -> Optional[Ticket]:
        """Get ticket by ticket number"""
        return self.db.query(Ticket).filter(Ticket.ticket_number == ticket_number).first()
    
    def get_by_vehicle_number(self, vehicle_number: str) -> List[Ticket]:
        """Get all tickets for a vehicle"""
        return self.db.query(Ticket).filter(Ticket.vehicle_number == vehicle_number).all()
    
    def list_open(self, skip: int = 0, limit: int = 100) -> List[Ticket]:
        """List all open tickets"""
        return (
            self.db.query(Ticket)
            .filter(Ticket.status == "OPEN")
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def list_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Ticket]:
        """List tickets by status"""
        return (
            self.db.query(Ticket)
            .filter(Ticket.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def list_by_issue_type(self, issue_type: str, skip: int = 0, limit: int = 100) -> List[Ticket]:
        """List tickets by issue type"""
        return (
            self.db.query(Ticket)
            .filter(Ticket.issue_type == issue_type)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def list_assigned_to_engineer(self, engineer_id: int, skip: int = 0, limit: int = 100) -> List[Ticket]:
        """List tickets assigned to a specific engineer"""
        return (
            self.db.query(Ticket)
            .filter(Ticket.assigned_engineer_id == engineer_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create(self, **kwargs) -> Ticket:
        """Create a new ticket"""
        ticket = Ticket(**kwargs)
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        logger.info(f"Created ticket: {ticket.ticket_number}", extra={"ticket_id": ticket.id})
        return ticket
    
    def update(self, ticket: Ticket, **kwargs) -> Ticket:
        """Update ticket fields"""
        for key, value in kwargs.items():
            if hasattr(ticket, key) and value is not None:
                setattr(ticket, key, value)
        self.db.commit()
        self.db.refresh(ticket)
        logger.info(f"Updated ticket: {ticket.ticket_number}", extra={"ticket_id": ticket.id, "fields": list(kwargs.keys())})
        return ticket
    
    def delete(self, ticket: Ticket) -> bool:
        """Delete a ticket (soft delete by setting status to DELETED)"""
        ticket.status = "DELETED"
        self.db.commit()
        logger.info(f"Deleted ticket: {ticket.ticket_number}", extra={"ticket_id": ticket.id})
        return True
