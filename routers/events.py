from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from sqlalchemy.dialects.postgresql import insert
from typing import List
from datetime import datetime

from database import get_async_session
import schemas
from db import models
# Import logic helpers if needed, but we'll keep it simple for now

router = APIRouter(prefix="/events", tags=["events"])

@router.get("/", response_model=List[schemas.EventResponse])
async def get_events(
    skip: int = 0, 
    limit: int = 100, 
    start_date: datetime = None,
    end_date: datetime = None,
    status: schemas.EventStatus = None,
    tag_slug: str = None,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get list of events with pagination and filters.
    """
    stmt = (
        select(models.Event)
        .order_by(models.Event.start_time.asc() if hasattr(models.Event, 'start_time') else models.Event.id.desc())
        # .order_by(models.Event.id.desc()) # Fallback
        .options(
             # Optimize loading
             # joinedload(models.Event.organizer),
             # joinedload(models.Event.default_venue),
             # selectinload(models.Event.tags)
        )
    )
    
    # Apply filters
    if status:
        stmt = stmt.where(models.Event.status == status)
    
    if tag_slug:
        stmt = stmt.join(models.Event.tags).where(models.Tag.slug == tag_slug)

    # Date filtering (complex because of occurrences)
    # For MVP, we might filter by 'updated_at' or if we had a denormalized 'next_occurrence'
    # Here we can filter by checking if ANY occurrence falls in range.
    if start_date or end_date:
        stmt = stmt.join(models.Event.occurrences)
        if start_date:
            stmt = stmt.where(models.EventOccurrence.start_time >= start_date)
        if end_date:
            stmt = stmt.where(models.EventOccurrence.start_time <= end_date)
        
    stmt = stmt.offset(skip).limit(limit).execution_options(populate_existing=True)

    result = await session.execute(stmt)
    events = result.scalars().unique().all()
    return events


@router.get("/tags", response_model=List[schemas.TagSchema])
async def get_tags(
    search: str = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session)
):
    stmt = select(models.Tag).limit(limit)
    if search:
        stmt = stmt.where(models.Tag.name.ilike(f"%{search}%"))
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/organizers", response_model=List[schemas.OrganizerSchema])
async def get_organizers(
    limit: int = 100, 
    session: AsyncSession = Depends(get_async_session)
):
    stmt = select(models.Organizer).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/venues", response_model=List[schemas.VenueSchema])
async def get_venues(
    limit: int = 100, 
    session: AsyncSession = Depends(get_async_session)
):
    stmt = select(models.Venue).limit(limit)
    res = await session.execute(stmt)
    return res.scalars().all()


@router.get("/{slug}", response_model=schemas.EventResponse)
async def get_event_by_slug(
    slug: str,
    session: AsyncSession = Depends(get_async_session)
):
    stmt = select(models.Event).where(models.Event.slug == slug)
    result = await session.execute(stmt)
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

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
    
    # Batch Upsert Logic Improved
    for event_data in events:
        try:
            # 1. Handle Organizer
            organizer = None
            if event_data.organizer:
                stmt = select(models.Organizer).where(models.Organizer.name == event_data.organizer.name)
                res = await session.execute(stmt)
                organizer = res.scalar_one_or_none()
                if not organizer:
                    # Fix: Handle empty social_links gracefully if needed
                    organizer = models.Organizer(
                        name=event_data.organizer.name,
                        rating=event_data.organizer.rating or 0.0,
                        social_links=event_data.organizer.social_links
                    )
                    session.add(organizer)
                    await session.flush()

            # 2. Handle Venue
            venue = None
            if event_data.default_venue:
                stmt = select(models.Venue).where(
                    models.Venue.name == event_data.default_venue.name, 
                    models.Venue.city == event_data.default_venue.city
                )
                res = await session.execute(stmt)
                venue = res.scalar_one_or_none()
                if not venue:
                    venue = models.Venue(
                        name=event_data.default_venue.name,
                        address=event_data.default_venue.address,
                        city=event_data.default_venue.city,
                        lat=event_data.default_venue.lat,
                        lon=event_data.default_venue.lon
                    )
                    session.add(venue)
                    await session.flush()

            # 3. Find Event by Slug
            stmt = select(models.Event).where(models.Event.slug == event_data.slug)
            res = await session.execute(stmt)
            existing_event = res.scalar_one_or_none()

            if existing_event:
                # UPDATE
                existing_event.title = event_data.title
                existing_event.description = event_data.description
                existing_event.full_text = event_data.full_text
                # Existing event might not have these updated correctly if logic was skipped
                if event_data.status: existing_event.status = event_data.status
                existing_event.updated_at = datetime.now()
                
                if organizer: existing_event.organizer = organizer
                if venue: existing_event.default_venue = venue
                
                # Update Tags
                if event_data.tags is not None:
                    # Clear existing? Or merge. 
                    # Simpler to clear and re-add for sync consistency
                    existing_event.tags = []
                    for t in event_data.tags:
                        tag_stmt = select(models.Tag).where(models.Tag.slug == t.slug)
                        tag_res = await session.execute(tag_stmt)
                        tag_obj = tag_res.scalar_one_or_none()
                        if not tag_obj:
                            tag_obj = models.Tag(name=t.name, slug=t.slug)
                            session.add(tag_obj)
                        existing_event.tags.append(tag_obj)

                # Update Occurrences (Replace)
                if event_data.occurrences is not None:
                    # To replace, we can clear the list. SQLAlchemy cascade should handle delete.
                    existing_event.occurrences = []
                    for occ in event_data.occurrences:
                        new_occ = models.EventOccurrence(
                            start_time=occ.start_time,
                            end_time=occ.end_time,
                            tz=occ.tz,
                            status=occ.status,
                            location_name=occ.location_name
                        )
                        existing_event.occurrences.append(new_occ)

                # Update Tickets
                if event_data.tickets is not None:
                    existing_event.tickets = []
                    for tkt in event_data.tickets:
                        new_tkt = models.TicketType(
                            name=tkt.name,
                            price=tkt.price,
                            currency=tkt.currency,
                            capacity=tkt.capacity,
                            sold=tkt.sold
                        )
                        existing_event.tickets.append(new_tkt)

                # Update Sources (Merge or Append? - usually append if different)
                # For sync, maybe just ensure current source is there?
                # Simplification: Append new ones from this batch
                for src in event_data.sources:
                     # Check duplicates?
                     # Ideally check fingerprint
                     pass 
                     # For now, just add new sources logic if needed, 
                     # but be careful of duplicates.

                # Image updates... similar logic.

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
                await session.flush() 
                
                # Tags
                if event_data.tags:
                    for t in event_data.tags:
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
        except Exception as e:
            # Log error but continue? or Fail batch?
            # 500 error usually means one failed.
            # Best to log specific event failure and re-raise or skip.
            print(f"Error processing event {event_data.slug}: {e}")
            raise e # Re-raise to see traceback in global handler

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
