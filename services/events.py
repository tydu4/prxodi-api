from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from db import models
import schemas
from typing import Optional, List
from datetime import datetime

async def get_event_by_slug(session: AsyncSession, slug: str) -> Optional[models.Event]:
    stmt = (
        select(models.Event)
        .where(models.Event.slug == slug)
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
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def create_or_update_event(session: AsyncSession, event_data: schemas.EventCreate) -> models.Event:
    # 1. Handle Organizer
    organizer = None
    if event_data.organizer:
        stmt = select(models.Organizer).where(models.Organizer.name == event_data.organizer.name)
        res = await session.execute(stmt)
        organizer = res.scalar_one_or_none()
        if not organizer:
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

    # 3. Check for Existing Event
    existing_event = await get_event_by_slug(session, event_data.slug)

    if existing_event:
        # UPDATE
        existing_event.title = event_data.title
        existing_event.description = event_data.description
        existing_event.full_text = event_data.full_text
        if event_data.status: 
            existing_event.status = event_data.status
        existing_event.updated_at = datetime.now()
        existing_event.language = event_data.language
        existing_event.age_restriction = event_data.age_restriction
        
        if organizer: existing_event.organizer = organizer
        if venue: existing_event.default_venue = venue
        
        # Tags
        if event_data.tags is not None:
            existing_event.tags = [] # Clear and rebuild
            for t in event_data.tags:
                tag_obj = await _get_or_create_tag(session, t)
                existing_event.tags.append(tag_obj)

        # Occurrences
        if event_data.occurrences is not None:
            existing_event.occurrences = [] # Clear and rebuild
            for occ in event_data.occurrences:
                new_occ = models.EventOccurrence(
                    start_time=occ.start_time,
                    end_time=occ.end_time,
                    tz=occ.tz,
                    status=occ.status,
                    location_name=occ.location_name
                )
                  # TODO: If occurrence has venue override?
                existing_event.occurrences.append(new_occ)

        # Tickets
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

        # Images
        if event_data.images is not None:
            existing_event.images = []
            for img in event_data.images:
                new_img = models.EventImage(
                    url=img.url,
                    alt=img.alt,
                    sort_order=img.sort_order
                )
                existing_event.images.append(new_img)
        
        # Sources - append or replace? For sync, usually replace or ensuring consistency.
        # User didn't specify, but for full sync, replacing list is safest.
        if event_data.sources is not None:
             existing_event.sources = []
             for src in event_data.sources:
                 new_src = models.EventSource(
                     source_url=src.source_url,
                     source_name=src.source_name,
                     confidence=src.confidence,
                     fingerprint=src.fingerprint,
                     raw_payload=src.raw_payload
                 )
                 existing_event.sources.append(new_src)

        return existing_event

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
        # Occurrences
        if event_data.occurrences:
            for occ in event_data.occurrences:
                new_occ = models.EventOccurrence(
                    start_time=occ.start_time,
                    end_time=occ.end_time,
                    tz=occ.tz,
                    status=occ.status,
                    location_name=occ.location_name
                )
                new_event.occurrences.append(new_occ)
        
        # Tags
        if event_data.tags:
            for t in event_data.tags:
                 tag_obj = await _get_or_create_tag(session, t)
                 new_event.tags.append(tag_obj)

        # Tickets
        if event_data.tickets:
             for tkt in event_data.tickets:
                new_tkt = models.TicketType(
                    name=tkt.name,
                    price=tkt.price,
                    currency=tkt.currency,
                    capacity=tkt.capacity,
                    sold=tkt.sold
                )
                new_event.tickets.append(new_tkt)
        
        # Images
        if event_data.images:
            for img in event_data.images:
                new_img = models.EventImage(
                    url=img.url,
                    alt=img.alt,
                    sort_order=img.sort_order
                )
                new_event.images.append(new_img)

        # Sources
        if event_data.sources:
            for src in event_data.sources:
                 new_src = models.EventSource(
                     source_url=src.source_url,
                     source_name=src.source_name,
                     confidence=src.confidence,
                     fingerprint=src.fingerprint,
                     raw_payload=src.raw_payload
                 )
                 new_event.sources.append(new_src)

        return new_event

async def _get_or_create_tag(session: AsyncSession, tag_data: schemas.TagSchema):
    stmt = select(models.Tag).where(models.Tag.slug == tag_data.slug)
    res = await session.execute(stmt)
    tag_obj = res.scalar_one_or_none()
    if not tag_obj:
        tag_obj = models.Tag(name=tag_data.name, slug=tag_data.slug)
        session.add(tag_obj)
    return tag_obj

async def delete_event(session: AsyncSession, slug: str) -> bool:
    stmt = delete(models.Event).where(models.Event.slug == slug)
    result = await session.execute(stmt)
    return result.rowcount > 0
