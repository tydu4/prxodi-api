from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from sqlalchemy.dialects.postgresql import insert
from typing import List

from database import get_async_session
import schemas
from db import models
# Import logic helpers if needed, but we'll keep it simple for now

router = APIRouter(prefix="/events", tags=["events"])

@router.get("/", response_model=List[schemas.EventResponse])
async def get_events(
    skip: int = 0, 
    limit: int = 100, 
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get list of events with pagination.
    """
    # Eager load relationships for the schema
    # Note: In real production code, use specialized queries to avoid N+1
    # For now, sqlalchemy's async loader is powerful enough for small batches
    stmt = (
        select(models.Event)
        .order_by(models.Event.id.desc())
        .offset(skip)
        .limit(limit)
        .execution_options(populate_existing=True)
    )
    result = await session.execute(stmt)
    # Important: .unique() is needed when joining/loading collections
    events = result.scalars().unique().all()
    return events

@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def batch_upsert_events(
    events: List[schemas.EventCreate],
    session: AsyncSession = Depends(get_async_session)
):
    """
    Batch upsert events.
    Logic:
    1. Check if event exists by slug.
    2. If exists -> Update.
    3. If new -> Insert.
    4. Handle nested relationships (Tags, Organizer, Venue, Occurrences, etc.)
       This is complex in SQL. For simplicity/MVP, we might use a loop or smarter ORM logic.
    """
    count_created = 0
    count_updated = 0
    
    for event_data in events:
        # 1. Handle Organizer
        organizer = None
        if event_data.organizer:
            # Find or Create Organizer
            stmt = select(models.Organizer).where(models.Organizer.name == event_data.organizer.name)
            res = await session.execute(stmt)
            organizer = res.scalar_one_or_none()
            if not organizer:
                organizer = models.Organizer(**event_data.organizer.model_dump())
                session.add(organizer)
                await session.flush() # get ID

        # 2. Handle Venue
        venue = None
        if event_data.default_venue:
            stmt = select(models.Venue).where(models.Venue.name == event_data.default_venue.name, models.Venue.city == event_data.default_venue.city)
            res = await session.execute(stmt)
            venue = res.scalar_one_or_none()
            if not venue:
                venue = models.Venue(**event_data.default_venue.model_dump())
                session.add(venue)
                await session.flush()

        # 3. Find Event by Slug
        stmt = select(models.Event).where(models.Event.slug == event_data.slug)
        res = await session.execute(stmt)
        existing_event = res.scalar_one_or_none()

        if existing_event:
            # UPDATE
            # Simplified: just update basic fields. 
            # Ideally verify if fields changed.
            existing_event.title = event_data.title
            existing_event.description = event_data.description
            existing_event.full_text = event_data.full_text
            existing_event.status = event_data.status
            existing_event.updated_at = datetime.now()
            
            # Update FKs
            if organizer: existing_event.organizer = organizer
            if venue: existing_event.default_venue = venue
            
            # Handle Tags (Clear and Re-add or Merge? Let's Merge)
            # Handle Occurrences (Delete old and add new? Or smart merge? Let's Delete Old for sync simplicity)
            # For MVP: We assume the 'parser' is the source of truth.
            # If we wipe Occurrences, we lose IDs. 
            # Let's keep it simple: If 'tickets' or 'occurrences' provided, replace them.
            
            # Clear old nested
            # Note: Cascade delete might handle this if we delete the event, but we are updating.
            # Manually clearing for accurate sync is safer for now.
            if event_data.occurrences:
                # remove old occurrences? 
                # Be careful not to delete past events if the parser only sends future ones.
                # Logic: The parser sends the "Current" view of the event.
                pass 

            count_updated += 1
        else:
            # INSERT
            new_event = models.Event(
                title=event_data.title,
                slug=event_data.slug,
                description=event_data.description,
                full_text=event_data.full_text,
                language=event_data.language,
                age_restriction=event_data.age_restriction,
                status=event_data.status,
                organizer=organizer,
                default_venue=venue
            )
            session.add(new_event)
            await session.flush() # Get ID for nested
            
            # Tags
            if event_data.tags:
                for t in event_data.tags:
                    # Find or convert tag
                    tag_stmt = select(models.Tag).where(models.Tag.slug == t.slug)
                    tag_res = await session.execute(tag_stmt)
                    tag_obj = tag_res.scalar_one_or_none()
                    if not tag_obj:
                        tag_obj = models.Tag(name=t.name, slug=t.slug)
                        session.add(tag_obj)
                    new_event.tags.append(tag_obj)

            # Occurrences
            for occ in event_data.occurrences:
                new_occ = models.EventOccurrence(
                    event_id=new_event.id,
                    start_time=occ.start_time,
                    end_time=occ.end_time,
                    tz=occ.tz,
                    status=occ.status,
                    location_name=occ.location_name
                )
                session.add(new_occ)

            # Sources
            for src in event_data.sources:
                new_src = models.EventSource(
                    event_id=new_event.id,
                    source_url=src.source_url,
                    source_name=src.source_name,
                    confidence=src.confidence,
                    fingerprint=src.fingerprint,
                    raw_payload=src.raw_payload
                )
                session.add(new_src)

            # Images
            for img in event_data.images:
                new_img = models.EventImage(
                    event_id=new_event.id,
                    url=img.url,
                    alt=img.alt,
                    sort_order=img.sort_order
                )
                session.add(new_img)
            
            # Tickets
            for tkt in event_data.tickets:
                new_tkt = models.TicketType(
                    event_id=new_event.id,
                    name=tkt.name,
                    price=tkt.price,
                    currency=tkt.currency,
                    capacity=tkt.capacity,
                    sold=tkt.sold
                )
                session.add(new_tkt)

            count_created += 1

    await session.commit()
    return {"created": count_created, "updated": count_updated}

@router.delete("/cleanup", status_code=204)
async def cleanup_database(session: AsyncSession = Depends(get_async_session)):
    """
    DEBUG ONLY: Clear all events (cascade delete).
    """
    # Delete all events. Cascade will kill occurrences, sources, images, tickets.
    # We keep Venues, Organizers, Tags as they might be shared/master data.
    stmt = delete(models.Event)
    await session.execute(stmt)
    await session.commit()
    return None
