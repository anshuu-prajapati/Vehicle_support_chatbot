from pydantic import BaseModel
from typing import Optional


class TicketCreate(BaseModel):
    customer_phone: str
    problem: str
    driver_phone: Optional[str] = None
    customer_id: Optional[int] = None
    driver_id: Optional[int] = None


class TicketOut(BaseModel):
    ticket_number: str
    customer_phone: str
    driver_phone: Optional[str] = None
    problem: str
    status: str

    class Config:
        orm_mode = True
