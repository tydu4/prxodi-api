# 🚀 Deployment Instructions

## 1. Initial Setup (First Run)

Run this one-liner on your VPS to clone the repo, set up a basic environment, and start everything:

```bash
git clone https://github.com/tydu4/prxodi-api.git && \
cd prxodi-api && \
echo -e "DB_USER=postgres\nDB_PASSWORD=change_me_please\nDB_NAME=events_db" > .env && \
bash setup_server.sh && \
./deploy.sh
```

> **Note:** This creates a default `.env` file. You should edit it (`nano .env`) to set your real database password if needed.

---

## 2. 🔄 Update Code

To pull the latest changes from GitHub and restart the server automatically:

```bash
./deploy.sh
```

---

## 3. 💥 Clean Re-Install (Fix Problems)

If the database is corrupted or you want to wipe everything and start fresh (deletes all data!):

```bash
./deploy.sh --clean
```
