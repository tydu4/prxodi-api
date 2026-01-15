# API Documentation

The API uses FastAPI and provides an interactive Swagger UI documentation at `/docs` (e.g., `http://localhost:8000/docs`).

Below is a summary of the available endpoints for the **Events** resource.

## Events Endpoints

| Method | Path | Summary | Description |
| :--- | :--- | :--- | :--- |
| **GET** | `/events/` | List Events | Get a list of events. Supports pagination (`skip`, `limit`) and filtering by `status`, `tag_slug`, `start_date`, `end_date`. |
| **POST** | `/events/` | Create/Upsert Event | Create a new event. If the `slug` already exists, it updates the existing event (Upsert). |
| **GET** | `/events/{slug}` | Get Event | Retrieve full details of a single event by its unique `slug`. |
| **PUT** | `/events/{slug}` | Update Event | Update an existing event. The `slug` in the path must match the body. |
| **DELETE** | `/events/{slug}` | Delete Event | Permanently remove an event and its related data (occurrences, tickets, images, etc.). |
| **POST** | `/events/batch` | Batch Upsert | Accept a list of events to create or update in bulk. Useful for synchronization. |
| **DELETE** | `/events/cleanup` | Delete All | **Debug/Dev only.** Clears the entire events table. |

## Helper Endpoints

| Method | Path | Summary |
| :--- | :--- | :--- |
| **GET** | `/events/tags` | List all available tags. |
| **GET** | `/events/organizers` | List all organizers. |
| **GET** | `/events/venues` | List all venues. |

## Data Schemas

The API uses standard JSON schemas. See `/docs` for detailed field models (e.g. `EventCreate`, `EventResponse`).

### Example: Create Event Payload

```json
{
  "title": "My Concert",
  "slug": "my-concert-2025",
  "description": "Live in Moscow",
  "status": "scheduled",
  "organizer": { "name": "Best Org" },
  "default_venue": { "name": "Big Hall", "city": "Moscow", "address": "Lenina 1" },
  "occurrences": [
    { "start_time": "2025-10-01T19:00:00" }
  ],
  "tickets": [
    { "name": "VIP", "price": 5000 }
  ]
}
```
