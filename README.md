# AutoRia Scraper

A containerized asynchronous web scraper for collecting car listing details from [auto.ria.com](https://auto.ria.com) using **Playwright**, **aiohttp**, and **PostgreSQL**. Designed to run periodically via **cron**.

---

## 📁 Project Structure

```
autoria-scraper/
├── app/
│   ├── __init__.py
│   ├── main.py              # Main entry point to launch the scraper
│   ├── db.py                # Async database logic (check/insert)
│   ├── utils.py             # HTML helpers (e.g., extract secure hash)
│   └── settings.py          # Config constants (BASE_URL, DB URL, etc.)
├── db_init/
│   └── init.sql             # SQL script to initialize 'cars' table
├── dumps/                   # Directory where database dumps are stored
├── .env.template            # Template environment config
├── Dockerfile               # Docker build for Playwright + app
├── docker-compose.yml       # Multi-container orchestration
├── crontab                  # Daily & test (every minute) schedules           
└── README.md                # You're reading this file
```

---

## ⚙️ Requirements

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- `.env` file with correct configuration (see below)

---

## 🧪 Environment Variables

Duplicate `.env.template` into `.env` and fill in your own config if needed:

```env
POSTGRES_USER=auto_ria_user
POSTGRES_PASSWORD=auto_ria_password
POSTGRES_DB=auto_ria_db
DATABASE_URL=postgresql://auto_ria_user:auto_ria_password@db:5432/auto_ria_db
```

---

## 🚀 Setup & Run

### 1. Build & Start Containers

```bash
docker-compose up --build -d
```

This will:

- Launch PostgreSQL database
- Initialize schema from `init.sql`
- Start cron which executes scraper until container is stopped

---

## 🕒 Scheduling via Cron

Two presets:

- `* * * * *` – every minute (for testing)
- `0 0 * * *` – every day at midnight

Modify `crontab` as needed and ensure the container runs with cron enabled (or use host cron to invoke it).

---

## 🧼 Database Dump

After every successful scraping run, a dump is created under `/dumps/` folder inside container (mounted to host). Dumps are in SQL format:

```
dumps/dump_YYYY-MM-DD_HH-MM-SS.sql
```

---

## 🧩 Features

- ✅ Asynchronous scraping with `aiohttp` + `playwright`
- ✅ Phone number resolution via API
- ✅ Graceful handling of deleted listings
- ✅ Deduplication (skip already parsed cars)
- ✅ PostgreSQL auto-init with schema
- ✅ Dumps of DB contents
- ✅ Easy to run with Docker & Docker Compose

---

## 🧱 Table Schema

```sql
CREATE TABLE IF NOT EXISTS cars (
    id SERIAL PRIMARY KEY,
    url VARCHAR(255) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    price_usd INTEGER NOT NULL,
    odometer INTEGER NOT NULL,
    username VARCHAR(255) NOT NULL,
    phone_number BIGINT NOT NULL,
    image_url VARCHAR(255) NOT NULL,
    images_count INTEGER NOT NULL,
    car_number VARCHAR(255) NOT NULL,
    car_vin VARCHAR(255) NOT NULL,
    datetime_found TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
```

---

## 🔍 Notes

- The scraper uses `Playwright` to simulate clicks on “Show phone” and extract data from scripts.
- Rate limits are respected via randomized `sleep()` and retry logic.
- You must use the correct version of `pg_dump` matching PostgreSQL server. Optionally add `postgres-client` to the scraper Dockerfile.

---

## 🔧 Ways to Improve

- **Implement batching (DB & requests):**  
  Insert data in batches instead of per-record, and send multiple requests in parallel for higher throughput and lower DB overhead.
- **Retry with exponential backoff:**  
  Use smarter retry logic for requests and API calls, especially on rate-limits or temporary failures.
- **Async connection pool:**  
  Consider using a connection pool for aiohttp to further improve efficiency.
- **Proxy and user-agent rotation:**  
  Reduce risk of blocking or bans by rotating proxies and user-agents for each session/request.

---

## 📜 License

MIT – do whatever you want, but don't DDoS auto.ria 🙂
