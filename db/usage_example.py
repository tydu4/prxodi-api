from datetime import datetime
from db import get_db, Event, Organizer, Venue

# Получаем сессию
db = next(get_db())

# 1. Создаем организатора
org = Organizer(name="Яндекс", rating=5.0)
db.add(org)
db.commit() # Сохраняем, чтобы получить ID

# 2. Создаем ивент
new_event = Event(
    title="Python Meetup",
    start_time=datetime.now(),
    description="Обсуждаем нейронки",
    organizer_id=org.id,
    # embedding=[0.1, 0.2, ... ] # Сюда потом засунешь вектор
)

db.add(new_event)
db.commit()
db.refresh(new_event)

print(f"Создан ивент: {new_event.title}, ID: {new_event.id}")

# 3. Читаем из базы
events = db.query(Event).all()
print("Все ивенты в базе:", events)