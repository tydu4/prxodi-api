# 🚀 Deployment Instructions

## 1. Initial Setup (First Run)

Run this one-liner on your VPS to set up Docker and start the project:

```bash
```bash
git clone https://github.com/tydu4/prxodi-api.git && \
cd prxodi-api && \
echo -e "DB_USER=postgres\nDB_PASSWORD=change_me_please\nDB_NAME=events_db" > .env && \
bash setup_server.sh && \
chmod +x init_ssl.sh && ./init_ssl.sh
```
```

---

## 2. 🔄 Update Code

To pull the latest changes and restart (the "1-click" update):

```bash
git pull && docker compose up -d --build
```

---

## 3. 💥 Troubleshooting / Clean

If you need to view logs:
```bash
docker compose logs -f
```

If you need to completely restart (wipe data and start fresh):
```bash
docker compose down -v
docker compose up -d --build
```
