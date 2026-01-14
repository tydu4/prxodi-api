import enum
from typing import List, Optional
from datetime import datetime

from sqlalchemy import (
    String, ForeignKey, Text, DateTime, Float, Integer, 
    Boolean, Enum as PgEnum, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from pgvector.sqlalchemy import Vector
from .database import Base

# --- ENUMS (Перечисления) ---
class EventStatus(str, enum.Enum):
    draft = "draft"          # Черновик/на модерации
    scheduled = "scheduled"  # Актуально
    cancelled = "cancelled"  # Отменено
    postponed = "postponed"  # Перенесено
    done = "done"            # Прошло

# --- Организатор ---
class Organizer(Base):
    __tablename__ = "organizers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    social_links: Mapped[dict] = mapped_column(JSONB, nullable=True)

    events: Mapped[List["Event"]] = relationship(back_populates="organizer")

    def __repr__(self):
        return f"<Organizer {self.name}>"

# --- Место проведения ---
class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100), index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=True)
    lon: Mapped[float] = mapped_column(Float, nullable=True)

    # Связи
    events: Mapped[List["Event"]] = relationship(back_populates="default_venue")
    occurrences: Mapped[List["EventOccurrence"]] = relationship(back_populates="venue")

# --- Теги ---
class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True)

# --- Связь Event <-> Tag ---
class EventTag(Base):
    __tablename__ = "event_tags"
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

# --- ГЛАВНАЯ СУЩНОСТЬ: Event ---
class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    
    # Контент
    description: Mapped[str] = mapped_column(Text, nullable=True) # Короткое
    full_text: Mapped[str] = mapped_column(Text, nullable=True)   # Полное
    language: Mapped[str] = mapped_column(String(5), default="ru")
    age_restriction: Mapped[int] = mapped_column(Integer, default=0) # 0, 6, 12, 16, 18
    
    # Статус
    status: Mapped[EventStatus] = mapped_column(PgEnum(EventStatus), default=EventStatus.draft)
    
    # Метаданные создания
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Внешние ключи (Основной организатор и Дефолтная площадка)
    organizer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizers.id"))
    venue_id: Mapped[Optional[int]] = mapped_column(ForeignKey("venues.id"))

    # === RELATIONSHIPS (СВЯЗИ) ===
    # cascade="all, delete-orphan" означает: если удалить ивент, удалятся все его билеты, картинки и расписание
    organizer: Mapped["Organizer"] = relationship(back_populates="events")
    default_venue: Mapped["Venue"] = relationship(back_populates="events")
    tags: Mapped[List["Tag"]] = relationship(secondary="event_tags")
    
    # Новые таблицы
    occurrences: Mapped[List["EventOccurrence"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    tickets: Mapped[List["TicketType"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    images: Mapped[List["EventImage"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    sources: Mapped[List["EventSource"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    embeddings: Mapped[List["EventEmbedding"]] = relationship(back_populates="event", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Event {self.title} (ID: {self.id})>"

# --- Расписание (Occurrences) ---
# Для повторяющихся событий или точного времени проведения
class EventOccurrence(Base):
    __tablename__ = "event_occurrences"
    __table_args__ = (Index('idx_event_time', "event_id", "start_time", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    tz: Mapped[str] = mapped_column(String(50), default='Europe/Moscow') # Таймзона
    status: Mapped[str] = mapped_column(String(20), default='scheduled')
    
    # Возможность переопределить площадку для конкретной даты (например, тур группы)
    venue_id: Mapped[Optional[int]] = mapped_column(ForeignKey("venues.id"))

    location_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, comment="Уточнение места: Большой зал, Аудитория 401 и т.п.")
    event: Mapped["Event"] = relationship(back_populates="occurrences")
    venue: Mapped["Venue"] = relationship(back_populates="occurrences")

# --- Билеты (Tickets) ---
class TicketType(Base):
    __tablename__ = "ticket_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    
    name: Mapped[str] = mapped_column(String(100)) # "VIP", "Танцпол"
    price: Mapped[int] = mapped_column(Integer, default=0) # В копейках или целых единицах
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # Всего мест
    sold: Mapped[int] = mapped_column(Integer, default=0) # Продано

    event: Mapped["Event"] = relationship(back_populates="tickets")

# --- Изображения (Images) ---
class EventImage(Base):
    __tablename__ = "event_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    
    url: Mapped[str] = mapped_column(String, nullable=False)
    alt: Mapped[str] = mapped_column(String, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0) # Для сортировки галереи

    event: Mapped["Event"] = relationship(back_populates="images")

# --- Источники данных (Sources) ---
# Чтобы знать, откуда пришел ивент и не дублировать
class EventSource(Base):
    __tablename__ = "event_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    
    source_url: Mapped[str] = mapped_column(String, index=True)
    source_name: Mapped[str] = mapped_column(String(50)) # 'vk', 'kudago'
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    confidence: Mapped[float] = mapped_column(Float, default=1.0) # Оценка качества парсинга
    fingerprint: Mapped[str] = mapped_column(String, index=True) # Хеш для дедупликации
    
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=True) # Сырой ответ источника

    event: Mapped["Event"] = relationship(back_populates="sources")

# --- Векторные эмбеддинги (Embeddings) ---
# Вынесены отдельно, чтобы поддерживать разные модели (OpenAI, BERT, RuBERT)
class EventEmbedding(Base):
    __tablename__ = "event_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    
    model_name: Mapped[str] = mapped_column(String(50)) # e.g. "text-embedding-3-small"
    dim: Mapped[int] = mapped_column(Integer) # 1536, 384...
    
    # Вектор. Важно: для индексации в Postgres лучше знать размерность заранее.
    # Но если моделей много, можно оставить просто Vector(None) или задать максимум.
    # Здесь используем 384 как дефолт для open-source моделей.
    embedding = mapped_column(Vector(384))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    event: Mapped["Event"] = relationship(back_populates="embeddings")