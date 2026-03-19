# File Converter

A self-hosted web application for converting documents, presentations, spreadsheets, and images between common formats. All processing happens server-side — files never leave your infrastructure.

## Features

- **12 conversion types**: PDF, DOCX, PPTX, XLSX, HTML, JPG, PNG, and PDF/A
- **Multi-engine**: LibreOffice, Ghostscript, Poppler, and Pillow handle different conversions
- **Async task queue**: Per-engine concurrency limits prevent resource contention
- **Containerized**: Runs entirely in Docker — no host dependencies

## Supported Conversions

| From | To |
|------|----|
| DOCX, PPTX, XLSX, HTML | PDF |
| JPG, PNG | PDF |
| PDF | DOCX, PPTX, XLSX |
| PDF | JPG |
| PDF | PDF/A |

## Architecture

```
Browser
   │
   ▼
 nginx
   ├─ Serves Astro static frontend
   └─ Proxies /api/* to backend
         │
         ▼
   FastAPI backend
   ├─ Converters
   ├─ Task queue
   ├─ LibreOffice
   ├─ Ghostscript
   ├─ Poppler
   └─ Pillow
```

## Project Structure

```
.
├── backend/                  # Python / FastAPI
│   ├── app/
│   │   ├── main.py           # App init, middleware, lifespan
│   │   ├── config.py         # Pydantic settings (FC_ prefix)
│   │   ├── models.py         # TaskInfo, TaskResponse, TaskStatus
│   │   ├── queue.py          # Async task queue with per-engine semaphores
│   │   ├── registry.py       # Auto-discovers BaseConverter subclasses
│   │   ├── routes/           # /convert and /tasks endpoints
│   │   └── converters/       # One file per conversion type
│   ├── tests/                # Pytest unit, integration, and manual .http tests
│   ├── Dockerfile.dev
│   └── Dockerfile.prod
│
├── frontend/                 # Astro / Tailwind CSS
│   ├── src/
│   │   ├── pages/index.astro # Main UI — upload, poll, download
│   │   └── layouts/
│   ├── Dockerfile.dev
│   └── Dockerfile.prod
│
├── nginx/
│   ├── nginx.conf            # Reverse proxy config
│   └── Dockerfile.prod       # Multi-stage: builds Astro → copies into nginx
│
├── docker-compose.dev.yml    # backend + frontend (Astro dev server)
├── docker-compose.prod.yml   # backend + nginx
│
├── .env.config.dev           # Dev config (safe to commit)
├── .env.config.prod          # Prod config (safe to commit)
└── .env.credentials.example  # Secrets template (copy to .env.credentials)
```

## Running Locally (Development)

```bash
docker compose -f docker-compose.dev.yml up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:4321
- API docs: http://localhost:8000/docs

No authentication in dev — both services are directly accessible.

## Deploying to Production

**1. Set up secrets**

```bash
cp .env.credentials.example .env.credentials
# Fill in any required secrets
```

**2. Start**

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

Nginx serves the built Astro frontend and proxies `/api/*` to the backend.

## Environment Variables

### Backend (`FC_` prefix)

| Variable | Default | Description |
|----------|---------|-------------|
| `FC_WORK_DIR` | `/tmp/conversions` | Where task files are stored |
| `FC_TASK_TTL_SECONDS` | `1800` | Auto-delete completed tasks after this many seconds |
| `FC_MAX_UPLOAD_BYTES` | `52428800` | Max upload size (50 MB) |
| `FC_LIBREOFFICE_TIMEOUT` | `120` | LibreOffice subprocess timeout (seconds) |
| `FC_GHOSTSCRIPT_TIMEOUT` | `120` | Ghostscript subprocess timeout (seconds) |
| `FC_ENGINE_CONCURRENCY` | `{"libreoffice":1,"pillow":4,"poppler":4,"ghostscript":2}` | Per-engine parallel job limits |
| `FC_ROOT_PATH` | `""` | Set to `/api` in prod for correct OpenAPI paths |

### Frontend

| Variable | Description |
|----------|-------------|
| `PUBLIC_API_BASE` | API base URL. `http://localhost:8000` in dev, `/api` in prod |

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/converters` | List available converters |
| `POST` | `/convert/{type}` | Upload file, start conversion |
| `GET` | `/tasks/{id}` | Poll task status |
| `GET` | `/tasks/{id}/download` | Download completed file |

Conversion is asynchronous — poll `/tasks/{id}` until status is `completed`, then call `/tasks/{id}/download`.

## Adding Authentication

Authentication is not included by default. To add an SSO gate in front of the application, [Authelia](https://www.authelia.com/) works well as an nginx `auth_request` provider and can be added as an additional service in `docker-compose.prod.yml`.

## License

MIT
