# API Event Batch Creation Ref

**Endpoint:** `POST /events/batch`
**Headers:** `Content-Type: application/json`

The endpoint accepts a JSON **List** of event objects.

```json
[
  {
    "title": "String (Required)",
    "slug": "String (Unique, Required)",
    "description": "String (Optional)",
    "full_text": "String (Optional)",
    "language": "ru",
    "age_restriction": 0,
    "status": "scheduled", // draft, scheduled, cancelled, postponed, done

    // Nested Objects (will be created/found by name)
    "organizer": {
      "name": "String",
      "rating": 0.0,
      "social_links": { "vk": "..." } // Optional dict
    },

    "default_venue": {
      "name": "String",
      "address": "String",
      "city": "String",
      "lat": 0.0,
      "lon": 0.0
    },

    // Arrays
    "tags": [
      { "name": "Rock", "slug": "rock" }
    ],

    "occurrences": [
      {
        "start_time": "2026-05-20T19:00:00", // ISO 8601
        "end_time": "2026-05-20T22:00:00",
        "tz": "Europe/Moscow",
        "status": "scheduled",
        "location_name": "Main Hall" // Optional override
      }
    ],

    "tickets": [
      {
        "name": "VIP",
        "price": 5000,
        "currency": "RUB",
        "capacity": 100,
        "sold": 0
      }
    ],

    "images": [
      {
        "url": "https://example.com/img.jpg",
        "alt": "Concert photo",
        "sort_order": 0
      }
    ],

    "sources": [
      {
        "source_url": "https://source.com/event/123",
        "source_name": "kudago",
        "confidence": 1.0,
        "fingerprint": "unique_hash",
        "raw_payload": {} 
      }
    ]
  }
]
```

### Notes
- **Update Logic**: If an event with the same `slug` exists, it updates fields and **replaces** nested lists (tags, occurrences, tickets, etc.).
- **Deduplication**: Organizers and Venues are matched by name/city and reused if found.
