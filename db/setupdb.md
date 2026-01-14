pip install -r requirements.txt
docker compose up -d

настройка миграций:
alembic init alembic

Зайди в созданный файл alembic/env.py, найди там строку target_metadata = None и замени её на:

# В начале файла добавь импорт твоих моделей
import sys
import os
sys.path.append(os.getcwd()) # Чтобы питон видел папку db
from db.models import Base

# ... ниже в файле найди и замени:
target_metadata = Base.metadata

Зайди в файл alembic.ini (в корне), найди строку sqlalchemy.url и замени на (подставь свои данные из .env, но тут нужно строкой):

sqlalchemy.url = postgresql://postgres:supersecretpassword@localhost:5432/events_aggregator

3. Применение изменений (Это ты будешь делать всегда при изменениях)
Создать файл миграции (Слепок того, что у тебя в models.py):
alembic revision --autogenerate -m "Initial migration"

Если выпадет ошибка про вектор, открой созданный файл в папке alembic/versions/...py и добавь в функцию upgrade() первой строчкой op.execute("CREATE EXTENSION IF NOT EXISTS vector").

Применить миграцию (Накатить на базу):
alembic upgrade head

Да, именно так.

    Docker — это виртуальный контейнер (как маленькая виртуальная машина), где будет жить база.

    docker-compose.yml — это инструкция для Докера: «Скачай Постгрес, настрой пароль, создай том для данных и запусти».

    Твой код (Python) будет стучаться в этот контейнер через порт 5432, как будто база стоит у тебя на компе.

Чтобы ты мог в будущем легко менять поля (добавить колонку, удалить таблицу), нам нужна система миграций. Стандартом в Python является Alembic. Я включил его в архитектуру.

Ниже — готовое решение. Просто создай файлы по этой структуре.
Структура твоего проекта

Создай папку проекта (например, event_aggregator), а внутри вот такую структуру:
Plaintext

event_aggregator/
├── docker-compose.yml       # Инструкция для запуска БД
├── .env                     # Пароли и настройки (чтобы не хранить в коде)
├── requirements.txt         # Список библиотек
├── main.py                  # Твой скрипт запуска (для теста)
└── db/                      # Тот самый модуль базы данных
    ├── __init__.py
    ├── config.py            # Чтение настроек из .env
    ├── database.py          # Подключение и сессии
    └── models.py            # Описание таблиц (Events, Venues...)

Шаг 1. Файлы настройки и окружения

1. docker-compose.yml (в корне проекта) Мы берем образ pgvector/pgvector, чтобы сразу работали нейронные векторы.
YAML

version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg16  # Postgres 16 + Vector support
    container_name: events_db_container
    restart: always
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    ports:
      - "${DB_PORT}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:

2. .env (в корне проекта) Создай этот файл и впиши настройки.
Ini, TOML

DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=supersecretpassword
DB_NAME=events_aggregator

3. requirements.txt (в корне проекта)
Plaintext

sqlalchemy==2.0.25
psycopg2-binary==2.9.9
pgvector==0.2.4
alembic==1.13.1
python-dotenv==1.0.0

Шаг 2. Модуль db (Код на Python)

Создай папку db и положи туда 4 файла.

1. db/config.py Загружает настройки, чтобы не хардкодить пароли.
Python

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "events_db")

    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()

2. db/database.py Отвечает за подключение.
Python

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

# Создаем движок
engine = create_engine(settings.DATABASE_URL, echo=False)

# Фабрика сессий (через нее мы будем делать запросы)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
class Base(DeclarativeBase):
    pass

# Вспомогательная функция для получения сессии (удобно использовать в контекстных менеджерах)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

3. db/models.py Здесь вся структура данных. Я добавил метод __repr__ для красивого вывода в консоль.
Python

from typing import List, Optional
from datetime import datetime
from sqlalchemy import String, ForeignKey, Text, DateTime, Float, Integer, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from .database import Base

# --- Организатор ---
class Organizer(Base):
    __tablename__ = "organizers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    social_links: Mapped[dict] = mapped_column(JSONB, nullable=True) # JSON для ссылок

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

    events: Mapped[List["Event"]] = relationship(back_populates="venue")

# --- Теги ---
class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True)

# --- Связь Many-to-Many ---
class EventTag(Base):
    __tablename__ = "event_tags"
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)

# --- ГЛАВНАЯ СУЩНОСТЬ: Event ---
class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    
    description: Mapped[str] = mapped_column(Text, nullable=True)
    full_text: Mapped[str] = mapped_column(Text, nullable=True) # Для полного контента
    
    # Логистика
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Деньги
    price_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")

    # Ссылки
    source_url: Mapped[str] = mapped_column(String, nullable=True) # Откуда спарсили
    image_url: Mapped[str] = mapped_column(String, nullable=True)

    # Внешние ключи
    organizer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizers.id"))
    venue_id: Mapped[Optional[int]] = mapped_column(ForeignKey("venues.id"))

    # Связи
    organizer: Mapped["Organizer"] = relationship(back_populates="events")
    venue: Mapped["Venue"] = relationship(back_populates="events")
    tags: Mapped[List["Tag"]] = relationship(secondary="event_tags")

    # === AI / ML ===
    # Вектор описания (384 - стандарт для модели 'all-MiniLM-L6-v2', популярной и быстрой)
    embedding = mapped_column(Vector(384), nullable=True) 

    def __repr__(self):
        return f"<Event {self.title} ({self.start_time})>"

4. db/__init__.py Чтобы ты мог писать from db import Event, get_db.
Python

from .database import get_db, engine, Base, SessionLocal
from .models import Event, Organizer, Venue, Tag

Инструкция: Как запустить и как менять поля (Самое важное!)
1. Первый запуск

Открой терминал в папке проекта.

    Установи библиотеки:
    Bash

pip install -r requirements.txt

Запусти базу (Докер):
Bash

    docker compose up -d

    (Подожди секунд 10, пока база прогрузится)

2. Настройка миграций (Делается один раз)

Чтобы база знала, как создавать таблицы, и чтобы ты мог потом их менять без боли.

В терминале (в корне проекта):

    Инициализируй Alembic:
    Bash

alembic init alembic

Зайди в созданный файл alembic/env.py, найди там строку target_metadata = None и замени её на:
Python

# В начале файла добавь импорт твоих моделей
import sys
import os
sys.path.append(os.getcwd()) # Чтобы питон видел папку db
from db.models import Base

# ... ниже в файле найди и замени:
target_metadata = Base.metadata

Зайди в файл alembic.ini (в корне), найди строку sqlalchemy.url и замени на (подставь свои данные из .env, но тут нужно строкой):
Ini, TOML

    sqlalchemy.url = postgresql://postgres:supersecretpassword@localhost:5432/events_aggregator

3. Применение изменений (Это ты будешь делать всегда при изменениях)

Сейчас у нас пустая база. Давай создадим таблицы.

    Создать файл миграции (Слепок того, что у тебя в models.py):
    Bash

alembic revision --autogenerate -m "Initial migration"

Если выпадет ошибка про вектор, открой созданный файл в папке alembic/versions/...py и добавь в функцию upgrade() первой строчкой op.execute("CREATE EXTENSION IF NOT EXISTS vector").

Применить миграцию (Накатить на базу):
Bash

    alembic upgrade head

Всё! Таблицы созданы.
Как менять поля в будущем?

Допустим, ты захотел добавить поле age_limit в Event:

    Идешь в db/models.py, добавляешь строчку age_limit: Mapped[int] = ...

    В терминале: alembic revision --autogenerate -m "added age limit"

    В терминале: alembic upgrade head База обновится, данные не пропадут.