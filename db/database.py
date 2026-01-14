from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings
import logging

logger = logging.getLogger(__name__)

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

def init_db():
    """
    Инициализация базы данных:
    1. Создание расширения vector (если нет)
    2. Создание всех таблиц (если нет)
    """
    logger.info("Initializing database...")
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            logger.info("Extension pgvector ensured.")
            
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables checked/created.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise e