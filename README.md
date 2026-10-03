# AI Wardrobe Assistant

[![CI](https://github.com/Huilin-Feng/wardrobe-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/Huilin-Feng/wardrobe-ai/actions/workflows/ci.yml)

**Live demo:** http://16.59.13.144 — a shared demo wardrobe running on AWS EC2.
There are no user accounts yet, so anything you upload is visible to every visitor.

> Photo-based wardrobe manager that recommends outfits from real-time weather, occasion and color harmony.

Upload a photo of a garment and a vision model identifies its category, color, style and
warmth level. Ask for an outfit and a deterministic scoring engine ranks the possible
combinations for today's weather and your occasion; only the shortlisted candidates are
sent to an LLM, which picks one and explains the choice in plain language. If the LLM call
fails, the app falls back to the scoring engine's own ranking.

Unlike a thin wrapper around an LLM, this project uses a custom scoring engine to
rank outfit candidates before passing only the top matches to the language model —
keeping recommendation quality controllable and API costs low.

---

## Architecture

### Request flow

```
Upload photo
  -> OpenAI Vision API: category, color (HEX), style, warmth level
  -> SQLite (SQLAlchemy ORM) for attributes, S3 for the photo

Get dressed (city, occasion)
  -> OpenWeatherMap: current temperature
  -> Shortlist: the 8 best items per category (at most 8 x 8 x 8 x 9 combinations)
  -> Score every combination: occasion 0.5 · temperature 0.3 · color harmony 0.2
  -> Top 3 outfits
  -> GPT-4o-mini: final pick + styling advice
     (falls back to the scoring ranking if the call fails)
```

### Deployment

```
Browser
  |  HTTP :80
  v
EC2 t3.micro (Elastic IP), Docker Compose
  |-- web: nginx
  |     |-- /                    -> React static build
  |     `-- /api/*, /uploads/*   -> api
  `-- api: FastAPI (bound to 127.0.0.1, never exposed publicly)
        |-- SQLite on a Docker volume
        |-- S3 private bucket     (IAM instance role, no stored keys)
        |-- OpenAI API
        `-- OpenWeatherMap API

Photos: GET /uploads/<file> -> 307 redirect to a 5-minute presigned S3 URL,
        so the browser downloads the image directly from S3.
```

Every push runs GitHub Actions CI: the pytest suite, the frontend production build,
and both Docker image builds.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2.0, Pydantic |
| Database | SQLite (on a Docker volume in production) |
| AI | OpenAI Vision API, GPT-4o-mini |
| External APIs | OpenWeatherMap |
| Frontend | React, Vite, Tailwind CSS |
| Infrastructure | Docker Compose, nginx, AWS (EC2, S3, IAM), Elastic IP |
| CI/CD | GitHub Actions |
| Testing | pytest |

---

## Roadmap

- [✅] Project setup, configuration management, database layer
- [✅] REST API endpoints (CRUD)
- [✅] Clothing recognition via OpenAI Vision API
- [✅] Weather integration
- [✅] Multi-dimensional scoring engine
- [✅] LLM recommendation layer
- [✅] React frontend
- [✅] Error handling and edge cases
- [✅] Docker containerization
- [✅] GitHub Actions CI pipeline
- [✅] AWS EC2 deployment behind nginx reverse proxy, with S3 image storage (IAM role, presigned URLs)

---

## Getting Started

You need an OpenAI API key and an OpenWeatherMap API key (free tier).

```bash
git clone https://github.com/Huilin-Feng/wardrobe-ai.git
cd wardrobe-ai
cp .env.example .env   # then fill in OPENAI_API_KEY and WEATHER_API_KEY
```

### Option A: Docker Compose (recommended)

```bash
docker compose up --build
```

Open http://localhost:8080.

### Option B: Run without Docker

Backend (Python 3.13):

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000/docs
```

Frontend (Node.js 24), in a second terminal:

```bash
cd frontend
npm ci
npm run dev                     # http://localhost:5173
```

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | — | Clothing recognition and styling advice |
| `WEATHER_API_KEY` | — | Current weather |
| `DATABASE_URL` | `sqlite:///./wardrobe.db` | SQLAlchemy connection string |
| `STORAGE_BACKEND` | `local` | `local` keeps photos on disk; `s3` moves them to a bucket |
| `S3_BUCKET` | — | Bucket name when `STORAGE_BACKEND=s3` |
| `AWS_REGION` | `us-east-2` | Region of the bucket |
| `WEB_PORT` | `8080` | Host port Docker Compose publishes the site on |

### Running Tests

```bash
pytest -q
```

The suite runs fully offline: OpenAI, OpenWeatherMap and S3 are all mocked, so no API
keys or AWS credentials are needed.

---

## Project Structure

```
wardrobe-ai/
├── app/
│   ├── config.py            # Settings loaded from .env
│   ├── database.py          # ORM models and CRUD operations
│   ├── models.py            # Pydantic request/response schemas
│   ├── clothing_analyzer.py # OpenAI Vision API integration
│   ├── weather_service.py   # OpenWeatherMap integration
│   ├── scoring_engine.py    # Multi-dimensional outfit scoring
│   ├── color_utils.py       # HSV color harmony calculations
│   ├── recommender.py       # LLM recommendation layer
│   ├── storage.py           # Local disk or S3 photo storage
│   └── main.py              # FastAPI application
├── frontend/                # React app, multi-stage Dockerfile, nginx.conf
├── scripts/                 # measure_tokens.py
├── tests/
├── .github/workflows/ci.yml
├── Dockerfile               # Backend image
├── compose.yaml
└── requirements.txt
```

---

## Design Decisions

**Why a scoring engine instead of sending the whole wardrobe to the LLM?**

Language models are unreliable at combinatorial optimization, and prompt size grows
linearly with wardrobe size. A deterministic scoring pass narrows the search space
first, so the LLM only handles what it does well — final judgment and natural language.

Measured with `python -m scripts.measure_tokens` (tiktoken, o200k_base, synthetic wardrobes):

| Wardrobe size | Whole wardrobe | Shortlist | Change |
|---|---|---|---|
| 6   | 280  | 476 | +70% |
| 20  | 590  | 495 | −16% |
| 50  | 1244 | 471 | −62% |
| 100 | 2316 | 473 | −80% |

The shortlist prompt stays at ~475 tokens no matter how large the wardrobe gets, while
sending the whole wardrobe grows linearly. Below roughly 15 items the shortlist is
actually larger, because candidates repeat garments and carry scores.

**Why a tie-breaker on average temperature fit?**

An outfit's temperature score is the score of its least suitable garment: one wrong
piece ruins the outfit. But taking the minimum hides differences between the other
garments, and testing at 31 °C produced several outfits with identical totals. Ties are
now broken by the average temperature fit across all garments, and totals are compared
rounded to six decimals so floating-point noise cannot decide the order.

**Why put nginx in front of the API?**

Vite bakes the API address into the JavaScript at build time, and that code runs in the
visitor's browser — so `localhost` would point at the visitor's own machine. nginx serves
the React build and forwards `/api` and `/uploads` to FastAPI, which gives the frontend a
single origin (no CORS) and keeps the backend off the public network.

**Why an IAM role and presigned URLs for photos?**

The EC2 instance assumes a role that can only read, write and delete objects in one
bucket. boto3 picks up its temporary, auto-rotating credentials, so no AWS keys exist in
the code or on the server. The bucket stays private; the API answers `/uploads/<file>`
with a redirect to a presigned URL that expires after five minutes, and the image bytes
go straight from S3 to the browser instead of through the small EC2 instance.

**Why make storage switchable?**

`STORAGE_BACKEND` defaults to `local`, so development, tests and CI never need AWS. Only
the production server sets it to `s3`.

**Why return booleans instead of raising HTTP exceptions in the data layer?**

The database layer stays protocol-agnostic. The API layer translates domain results
into HTTP status codes, so the same functions can be reused by CLI tools or
background jobs.

---

## Known Limitations and Next Steps

- **No authentication:** the demo is a single shared wardrobe. Next: user accounts and per-user data isolation.
- **HTTP only:** next is a domain name with HTTPS (Let's Encrypt).
- **Orphaned photos:** deleting an item removes its database row but not its photo.
- **Full-size images:** photos are served at 2–5 MB each; generating thumbnails would cut page weight substantially.
- **Single-instance SQLite:** fine for one server; scaling out would mean moving to PostgreSQL (e.g. Amazon RDS).
- Outfit history and a feedback loop for personalized ranking.