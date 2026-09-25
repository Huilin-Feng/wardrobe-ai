# AI Wardrobe Assistant

> AI-powered outfit recommendation engine with multi-dimensional scoring

An intelligent wardrobe manager that recognizes clothing items from uploaded photos
and recommends outfits based on real-time weather, occasion, and color harmony.

Unlike a thin wrapper around an LLM, this project uses a custom scoring engine to
rank outfit candidates before passing only the top matches to the language model —
keeping recommendation quality controllable and API costs low.

**Status:** In active development

---

## Architecture

```
Upload photo
     |
     v
OpenAI Vision API  ->  extract category, color (HEX), style, warmth level
     |
     v
Database (SQLAlchemy ORM)
     |
     v
Scoring Engine  ->  temperature fit x occasion match x color harmony
     |
     v
Top 3 candidates
     |
     v
LLM  ->  final selection + natural language styling advice
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2.0 |
| Database | SQLite (dev), PostgreSQL (production) |
| AI | OpenAI Vision API, GPT-4o-mini |
| External APIs | OpenWeatherMap |
| Frontend | Streamlit |
| Infrastructure | Docker, AWS (EC2, S3) |
| CI/CD | GitHub Actions |
| Testing | pytest |

---

## Roadmap

- [✅] Project setup, configuration management, database layer
- [✅] REST API endpoints (CRUD)
- [✅] Clothing recognition via OpenAI Vision API
- [✅] Weather integration
- [✅] Multi-dimensional scoring engine
- [ ] LLM recommendation layer
- [ ] Streamlit frontend
- [ ] Error handling and edge cases
- [ ] Docker containerization
- [ ] GitHub Actions CI pipeline
- [ ] AWS deployment with S3 image storage

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- An OpenAI API key
- An OpenWeatherMap API key (free tier)

### Installation

```bash
git clone https://github.com/Huilin-Feng/wardrobe-ai.git
cd wardrobe-ai

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
```

Then open `.env` and fill in your API keys:

```
OPENAI_API_KEY=sk-...
WEATHER_API_KEY=...
DATABASE_URL=sqlite:///./wardrobe.db
```

### Running Tests

```bash
pytest -v
```

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
│   └── main.py              # FastAPI application
├── tests/
├── uploads/
├── requirements.txt
└── README.md
```

---

## Design Decisions

**Why a scoring engine instead of sending the whole wardrobe to the LLM?**

Language models are unreliable at combinatorial optimization, and prompt size grows
linearly with wardrobe size. A deterministic scoring pass narrows the search space
first, so the LLM only handles what it does well — final judgment and natural language.

**Why return booleans instead of raising HTTP exceptions in the data layer?**

The database layer stays protocol-agnostic. The API layer translates domain results
into HTTP status codes, so the same functions can be reused by CLI tools or
background jobs.

---

## Future Improvements

- User authentication and multi-user data isolation
- Fashion trend analysis module
- Outfit history and feedback loop for personalized ranking
- Mobile client
