from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from database import get_async_session
import schemas
from db import models
from services import events as event_service

router = APIRouter(prefix="/events", tags=["events"])

@router.post("/", response_model=schemas.EventResponse, status_code=status.HTTP_201_CREATED, 
             summary="Create or Upsert an Event", 
             description="Create a new event or update if it exists (by slug).")
async def create_event(
    event: schemas.EventCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Create a new event. If an event with the same slug exists, it will be updated (upsert behavior).
    """
    try:
        db_event = await event_service.create_or_update_event(session, event)
        await session.commit()
        # Refresh to load relationships for response
        return await event_service.get_event_by_slug(session, db_event.slug)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create event: {str(e)}")

@router.put("/{slug}", response_model=schemas.EventResponse, summary="Update an Event")
async def update_event(
    slug: str,
    event: schemas.EventCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Update an existing event by slug.
    """
    if event.slug != slug:
        raise HTTPException(status_code=400, detail="Slug in body must match path")
    
    existing = await event_service.get_event_by_slug(session, slug)
    if not existing:
        raise HTTPException(status_code=404, detail="Event not found")

    try:
        db_event = await event_service.create_or_update_event(session, event)
        await session.commit()
        return await event_service.get_event_by_slug(session, db_event.slug)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update event: {str(e)}")

@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an Event")
async def delete_event(
    slug: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Delete an event by slug.
    """
    deleted = await event_service.delete_event(session, slug)
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")
    await session.commit()
    return None

@router.get("/", response_model=List[schemas.EventResponse], summary="List Events")
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
        .options(
             selectinload(models.Event.organizer),
             selectinload(models.Event.default_venue),
             selectinload(models.Event.tags),
             selectinload(models.Event.occurrences).selectinload(models.EventOccurrence.venue),
             selectinload(models.Event.tickets),
             selectinload(models.Event.images),
             selectinload(models.Event.sources)
        )
    )
    
    # Apply filters
    if status:
        stmt = stmt.where(models.Event.status == status)
    
    if tag_slug:
        stmt = stmt.join(models.Event.tags).where(models.Tag.slug == tag_slug)

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


@router.get("/tags", response_model=List[schemas.TagSchema], summary="List Tags")
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


@router.get("/organizers", response_model=List[schemas.OrganizerSchema], summary="List Organizers")
async def get_organizers(
    limit: int = 100, 
    session: AsyncSession = Depends(get_async_session)
):
    stmt = select(models.Organizer).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/venues", response_model=List[schemas.VenueSchema], summary="List Venues")
async def get_venues(
    limit: int = 100, 
    session: AsyncSession = Depends(get_async_session)
):
    stmt = select(models.Venue).limit(limit)
    res = await session.execute(stmt)
    return res.scalars().all()


@router.get("/{slug}", response_model=schemas.EventResponse, summary="Get Event by Slug")
async def get_event_by_slug(
    slug: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get a single event by its slug with all details.
    """
    event = await event_service.get_event_by_slug(session, slug)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.post("/batch", status_code=status.HTTP_201_CREATED, summary="Batch Upsert Events")
async def batch_upsert_events(
    events: List[schemas.EventCreate],
    session: AsyncSession = Depends(get_async_session)
):
    """
    Batch upsert events. Uses the same logic as single create/update.
    """
    processed_slugs = []
    
    for event_data in events:
        try:
            await event_service.create_or_update_event(session, event_data)
            processed_slugs.append(event_data.slug)
        except Exception as e:
            print(f"Error processing event {event_data.slug}: {e}")
            raise e 

    await session.commit()
    
    return {"status": "success", "processed": len(processed_slugs), "slugs": processed_slugs}

@router.delete("/cleanup", status_code=204, summary="Delete ALL Events")
async def cleanup_database(session: AsyncSession = Depends(get_async_session)):
    """
    DEBUG ONLY: Clear all events (cascade delete).
    """
    stmt = delete(models.Event)
    await session.execute(stmt)
    await session.commit()
    return None
