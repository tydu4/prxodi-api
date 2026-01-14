Вот актуальная документация базы данных (`DB_SCHEMA.md`).

Архитектура обновлена: теперь время, билеты, источники и векторы вынесены в отдельные таблицы для максимальной гибкости (One-to-Many).

---

# Структура базы данных (Event Aggregator)

## 1. Основные сущности

### Events (События) — `events`

*Мета-информация о событии (без привязки к конкретной дате).*

| Поле | Тип (SQL) | Описание |
| --- | --- | --- |
| `id` | Integer (PK) | Уникальный ID |
| `title` | String(255) | Название события |
| `slug` | String(255) | ЧПУ (URL), уникальный |
| `description` | Text | Краткий анонс / лид |
| `full_text` | Text | Полное описание (HTML/Markdown) |
| `language` | String(5) | Язык контента (ru, en) |
| `age_restriction` | Integer | Возрастной ценз (0, 12, 18) |
| `status` | Enum | `draft`, `scheduled`, `cancelled`, `postponed`, `done` |
| `created_at` | DateTime | Дата создания в базе |
| `updated_at` | DateTime | Дата последнего изменения |
| `organizer_id` | Integer (FK) | Организатор (Default) |
| `venue_id` | Integer (FK) | Площадка (Default) |

### Event Occurrences (Расписание) — `event_occurrences`

*Конкретные даты проведения. У одного Event может быть много Occurrences.*

| Поле | Тип (SQL) | Описание |
| --- | --- | --- |
| `id` | Integer (PK) | Уникальный ID слота |
| `event_id` | Integer (FK) | Ссылка на событие |
| `start_time` | DateTime | **Точное начало** (с таймзоной) |
| `end_time` | DateTime | Окончание (NULL если неизвестно) |
| `tz` | String(50) | Таймзона (напр. 'Europe/Moscow') |
| `status` | String(20) | Статус слота (напр. `scheduled`, `cancelled`) |
| `venue_id` | Integer (FK) | Площадка (если отличается от дефолтной) |

---

## 2. Данные и Метаданные

### Ticket Types (Билеты) — `ticket_types`

*Варианты билетов (VIP, Танцпол, Входной).*

| Поле | Тип (SQL) | Описание |
| --- | --- | --- |
| `id` | Integer (PK) | ID типа билета |
| `event_id` | Integer (FK) | Ссылка на событие |
| `name` | String(100) | Название категории (VIP, Early Bird) |
| `price` | Integer | Цена (в минимальных единицах/копейках) |
| `currency` | String(3) | Валюта (RUB, USD) |
| `capacity` | Integer | Общее кол-во мест (NULL если безлим) |
| `sold` | Integer | Сколько уже продано |

### Event Sources (Источники) — `event_sources`

*Откуда пришло событие (для контроля качества парсинга и дедупликации).*

| Поле | Тип (SQL) | Описание |
| --- | --- | --- |
| `id` | Integer (PK) | ID записи источника |
| `event_id` | Integer (FK) | Ссылка на событие |
| `source_name` | String(50) | Имя источника (vk, kassy, afisha) |
| `source_url` | String | Оригинальная ссылка |
| `scraped_at` | DateTime | Когда спарсили |
| `confidence` | Float | Уверенность в качестве данных (0.0 - 1.0) |
| `fingerprint` | String | Хеш контента (для проверки дублей) |
| `raw_payload` | JSONB | Сырой JSON ответа источника |

### Event Embeddings (AI Векторы) — `event_embeddings`

*Векторные представления для рекомендаций.*

| Поле | Тип (SQL) | Описание |
| --- | --- | --- |
| `id` | Integer (PK) | ID вектора |
| `event_id` | Integer (FK) | Ссылка на событие |
| `model_name` | String(50) | Название нейронки (напр. `text-embedding-3`) |
| `dim` | Integer | Размерность вектора (напр. 384) |
| `embedding` | Vector(384) | **Сам вектор (массив чисел)** |

---

## 3. Справочники и Медиа

### Venues (Площадки) — `venues`

| Поле | Тип (SQL) | Описание |
| --- | --- | --- |
| `id` | Integer (PK) | ID площадки |
| `name` | String(150) | Название (Клуб "Космос") |
| `address` | String(255) | Адрес |
| `city` | String(100) | Город |
| `lat` / `lon` | Float | Координаты |

### Organizers (Организаторы) — `organizers`

| Поле | Тип (SQL) | Описание |
| --- | --- | --- |
| `id` | Integer (PK) | ID организатора |
| `name` | String(150) | Название |
| `rating` | Float | Внутренний рейтинг |
| `social_links` | JSONB | Ссылки на соцсети |

### Event Images (Изображения) — `event_images`

| Поле | Тип (SQL) | Описание |
| --- | --- | --- |
| `id` | Integer (PK) | ID картинки |
| `event_id` | Integer (FK) | Ссылка на событие |
| `url` | String | Ссылка на файл |
| `sort_order` | Integer | Порядок отображения (0 = главная) |

### Tags (Теги) — `tags`

| Поле | Тип (SQL) | Описание |
| --- | --- | --- |
| `id` | Integer (PK) | ID тега |
| `name` | String(50) | Название (Rock, IT) |
| `slug` | String(50) | ЧПУ тега |

### Event Tags (Связь) — `event_tags`

| Поле | Тип (SQL) | Описание |
| --- | --- | --- |
| `event_id` | Integer (FK) | Ссылка на событие |
| `tag_id` | Integer (FK) | Ссылка на тег |