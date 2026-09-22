from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SaleItemRead(BaseModel):
    """
    Schema for reading sales data within the Plan Engine.
    Optimized for the properties the Algorithm actually needs.
    """
    id: str  # Firestore Document ID
    name: str
    price: float
    unit: str
    price_per_unit: Optional[float] = None
    category: str
    valid_to: datetime

    class Config:
        from_attributes = True