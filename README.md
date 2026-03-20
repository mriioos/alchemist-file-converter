# Alchemist File Converter

A self-hosted web application for converting documents, presentations, spreadsheets, and images between common formats. All processing happens server-side using LibreOffice — files never leave your infrastructure.

Built for people who are tired of uploading sensitive files to anonymous online converters, dealing with size limits, or being asked for their email just to download a file.

## Features

- **12 conversion types** — PDF, DOCX, PPTX, XLSX, HTML, JPG, PNG, and PDF/A
- **Multi-engine** — LibreOffice, Ghostscript, Poppler, and Pillow handle different conversions
- **Async task queue** — upload returns immediately with a task ID, poll for status, download when ready
- **Per-engine concurrency limits** — prevents resource contention (LibreOffice is single-threaded by design)
- **Fully containerized** — runs entirely in Docker, no host dependencies

## Supported Conversions

| From | To |
|---|---|
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
Astro frontend (static)
   │  calls /api/*
   ▼
FastAPI backend
   ├─ Converter registry (auto-discovers converters)
   ├─ Async task queue (per-engine semaphores)
   ├─ LibreOffice  (DOCX, PPTX, XLSX, HTML ↔ PDF)
   ├─ Ghostscript  (PDF → PDF/A)
   ├─ Poppler      (PDF → JPG)
   └─ Pillow       (JPG, PNG → PDF)
```

The frontend is a static Astro site. The backend is a FastAPI service that manages an async conversion queue. In production, a reverse proxy sits in front of both — serving the static frontend directly and forwarding `/api/*` to the backend.

## Project Structure

```
.
├── backend/                      # Python / FastAPI
│   ├── app/
│   │   ├── main.py               # App init, middleware, lifespan
│   │   ├── config.py             # Pydantic settings (FC_ prefix)
│   │   ├── models.py             # TaskInfo, TaskResponse, TaskStatus
│   │   ├── queue.py              # Async task queue with per-engine semaphores
│   │   ├── registry.py           # Auto-discovers BaseConverter subclasses
│   │   ├── routes/               # /convert and /tasks endpoints
│   │   └── converters/           # One file per conversion type
│   ├── tests/                    # Pytest unit and integration tests
│   ├── Dockerfile.dev
│   └── Dockerfile.prod
│
├── frontend/                     # Astro / Tailwind CSS
│   └── src/
│       ├── pages/index.astro     # Main UI — upload, poll, download
│       └── layouts/
│
├── docker-compose.dev.yml        # Backend + Astro dev server
├── docker-compose.prod.yml       # Author's personal production setup (see below)
├── nginx.prod.conf               # Nginx config (author's setup)
│
├── .env.config.dev               # Dev config (safe to commit)
├── .env.config.prod              # Prod config (author's setup, safe to commit)
└── .env.credentials.example      # Secrets template — copy to .env.credentials
```

## Running Locally (Development)

```bash
docker compose -f docker-compose.dev.yml up --build
```

- Frontend: http://localhost:4321
- Backend: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs

No authentication in dev — both services are directly accessible.

## Deploying to Production

> ⚠️ **Important:** The included `docker-compose.prod.yml` and `nginx.prod.conf` are the author's **personal production setup**. They include Nginx, Authelia (SSO), and Cloudflare Tunnel, and **will not work out of the box** without the corresponding infrastructure and credentials. They are provided as a reference, not a turnkey solution.

If you want to deploy your own instance, the recommended approach is to write your own compose file using the dev one as a starting point. The only hard requirements are:

- The backend must be reachable by the frontend at the path set in `PUBLIC_API_BASE`
- The backend should not be exposed publicly — put a reverse proxy in front of it
- The reverse proxy should serve the built Astro frontend (`frontend/dist/`) as static files and proxy `/api/*` to the backend

A minimal production setup needs only two services: the backend and an Nginx (or Caddy, Traefik, etc.) instance.

### Author's production stack (for reference)

- **Nginx** — reverse proxy, serves static frontend, proxies `/api/*` to backend
- **Authelia** — SSO authentication gate via Nginx `auth_request`
- **Cloudflare Tunnel** — exposes the service publicly without opening firewall ports

## Environment Variables

### Backend (`FC_` prefix)

| Variable | Default | Description |
|---|---|---|
| `FC_WORK_DIR` | `/tmp/conversions` | Where task files are stored |
| `FC_TASK_TTL_SECONDS` | `1800` | Auto-delete completed tasks after N seconds |
| `FC_MAX_UPLOAD_BYTES` | `52428800` | Max upload size (50 MB) |
| `FC_LIBREOFFICE_TIMEOUT` | `120` | LibreOffice subprocess timeout (seconds) |
| `FC_GHOSTSCRIPT_TIMEOUT` | `120` | Ghostscript subprocess timeout (seconds) |
| `FC_ENGINE_CONCURRENCY` | `{"libreoffice":1,"pillow":4,"poppler":4,"ghostscript":2}` | Per-engine parallel job limits |
| `FC_ROOT_PATH` | `""` | Set to `/api` in prod for correct OpenAPI paths |

### Frontend

| Variable | Description |
|---|---|
| `PUBLIC_API_BASE` | API base URL. `http://localhost:8000` in dev, `/api` in prod |

## API Overview

Conversion is asynchronous. Upload a file, get a task ID, poll for status, download when ready.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/converters` | List available converters and their options |
| `POST` | `/convert/{type}` | Upload a file and start conversion |
| `GET` | `/tasks/{id}` | Poll task status |
| `GET` | `/tasks/{id}/download` | Download the converted file |

### Adding a Converter

Drop a new file in `backend/app/converters/` that subclasses `BaseConverter`. It will be auto-discovered at startup and a route generated automatically — no manual wiring needed.

## License

MIT