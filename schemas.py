from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from enum import Enum

# Enums
class EventStatus(str, Enum):
    draft = "draft"
    scheduled = "scheduled"
    cancelled = "cancelled"
    postponed = "postponed"
    done = "done"

# Nested Models
class OrganizerSchema(BaseModel):
    name: str
    rating: float = 0.0
    social_links: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class VenueSchema(BaseModel):
    name: str
    address: str
    city: str
    lat: Optional[float] = None
    lon: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class TagSchema(BaseModel):
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)

class TicketTypeSchema(BaseModel):
    name: str
    price: int
    currency: str = "RUB"
    capacity: Optional[int] = None
    sold: int = 0

    model_config = ConfigDict(from_attributes=True)

class EventOccurrenceSchema(BaseModel):
    start_time: datetime
    end_time: Optional[datetime] = None
    tz: str = 'Europe/Moscow'
    status: str = 'scheduled'
    location_name: Optional[str] = None
    
    # Optional override venue
    venue: Optional[VenueSchema] = None

    model_config = ConfigDict(from_attributes=True)

class EventImageSchema(BaseModel):
    url: str
    alt: Optional[str] = None
    sort_order: int = 0

    model_config = ConfigDict(from_attributes=True)

class EventSourceSchema(BaseModel):
    source_url: str
    source_name: str
    confidence: float = 1.0
    fingerprint: str
    raw_payload: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

# Main Event Schemas

class EventBase(BaseModel):
    title: str
    slug: str
    description: Optional[str] = None
    full_text: Optional[str] = None
    language: str = "ru"
    age_restriction: int = 0
    status: EventStatus = EventStatus.draft

class EventCreate(EventBase):
    """Schema for creating/upserting an event."""
    # Nested data for creation
    organizer: Optional[OrganizerSchema] = None
    default_venue: Optional[VenueSchema] = None
    tags: List[TagSchema] = []
    
    occurrences: List[EventOccurrenceSchema] = []
    tickets: List[TicketTypeSchema] = []
    images: List[EventImageSchema] = []
    sources: List[EventSourceSchema] = []

    model_config = ConfigDict(from_attributes=True)

class EventResponse(EventBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    organizer: Optional[OrganizerSchema] = None
    default_venue: Optional[VenueSchema] = None
    tags: List[TagSchema] = []
    
    occurrences: List[EventOccurrenceSchema] = []
    tickets: List[TicketTypeSchema] = []
    images: List[EventImageSchema] = []
    
    model_config = ConfigDict(from_attributes=True)
