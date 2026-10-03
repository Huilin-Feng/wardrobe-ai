import os
import shutil
import uuid
from pathlib import Path
from app.recommender import recommend_outfit
from app.scoring_engine import IncompleteWardrobeError, generate_outfit_candidates

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import (
    add_item,
    count_items,
    delete_item,
    get_all_items,
    get_db,
    get_item_by_id,
    init_db,
)
from app.models import ClothingCreate, ClothingResponse, RecommendRequest
from app.clothing_analyzer import ClothingAnalysisError, analyze_clothing
from app.weather_service import CityNotFoundError, WeatherServiceError, get_weather
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from fastapi.responses import RedirectResponse
from app.storage import get_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts (before yield) and once when it stops (after)."""
    init_db()
    yield

app = FastAPI(
    title="AI Wardrobe Assistant",
    description="Outfit recommendation engine with multi-dimensional scoring",
    version="0.1.0",
    lifespan = lifespan,
)

# The browser blocks cross-origin responses unless the server explicitly allows
# the origin. The React dev server runs on a different port, so it must be listed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uploads are always written here first, because the analyzer reads from disk.
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

# Photos are served at /uploads/<file>. Locally they come straight off the disk;
# with S3 the API answers with a short-lived presigned URL and the browser
# downloads the image directly from the private bucket.
if settings.storage_backend == "s3":

    @app.get("/uploads/{filename}")
    def get_upload(filename: str) -> RedirectResponse:
        return RedirectResponse(get_storage().presigned_url(filename))

else:
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}



@app.get("/")
def root() -> dict:
    """Health check."""
    return {"status": "ok", "service": "AI Wardrobe Assistant"}


@app.get("/api/clothing", response_model=list[ClothingResponse])
def list_clothing(category: str | None = None, db: Session = Depends(get_db)):
    """List all clothing items, newest first. Optionally filter by category."""
    return get_all_items(db, category=category)


@app.get("/api/clothing/count")
def clothing_count(db: Session = Depends(get_db)) -> dict:
    """Return how many items are in the wardrobe."""
    return {"count": count_items(db)}


@app.get("/api/clothing/{item_id}", response_model=ClothingResponse)
def get_clothing(item_id: int, db: Session = Depends(get_db)):
    """Fetch a single clothing item by id."""
    item = get_item_by_id(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Clothing item not found")
    return item


@app.post("/api/clothing", response_model=ClothingResponse, status_code=201)
def create_clothing(payload: ClothingCreate, db: Session = Depends(get_db)):
    """Create an item from JSON. Vision-based upload comes in Day 3."""
    return add_item(
        db,
        image_url=payload.image_url,
        category=payload.category,
        color=payload.color,
        style=payload.style,
        warmth_level=payload.warmth_level,
        hex_color=payload.hex_color,
        description=payload.description,
    )


@app.post("/api/clothing/upload", response_model=ClothingResponse, status_code=201)
def upload_clothing(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload an image, analyze it with the Vision API, and store the result."""
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    stored_name = f"{uuid.uuid4().hex}{extension}"
    stored_path = os.path.join(settings.upload_dir, stored_name)

    with open(stored_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        attributes = analyze_clothing(stored_path)
    except ClothingAnalysisError as error:
        os.remove(stored_path)
        raise HTTPException(status_code=502, detail=str(error)) from error

    # Locally this is a no-op; with S3 it moves the file into the bucket.
    try:
        get_storage().persist(stored_path)
    except Exception as error:
        if os.path.exists(stored_path):
            os.remove(stored_path)
        raise HTTPException(status_code=502, detail="Could not store the photo") from error

    return add_item(db, image_url=stored_path, **attributes)


@app.delete("/api/clothing/{item_id}", status_code=204)
def remove_clothing(item_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a clothing item."""
    if not delete_item(db, item_id):
        raise HTTPException(status_code=404, detail="Clothing item not found")

@app.get("/api/weather")
def weather(city: str, db: Session = Depends(get_db)) -> dict:
    """Return current weather for a city."""
    try:
        return get_weather(city)
    except CityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except WeatherServiceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

@app.post("/api/recommend")
def recommend(payload: RecommendRequest, db: Session = Depends(get_db)) -> dict:
    """Recommend an outfit for the current weather in a city and an occasion."""
    # Weather is critical: without a temperature there is nothing to score.
    try:
        weather_data = get_weather(payload.city)
    except CityNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except WeatherServiceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    wardrobe = [item.to_dict() for item in get_all_items(db)]

    try:
        candidates = generate_outfit_candidates(
            wardrobe, weather_data["temp_celsius"], payload.occasion
        )
    except IncompleteWardrobeError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Add at least one item in each missing category",
                "missing": error.missing,
            },
        ) from error

    # The LLM is optional: recommend_outfit never fails, it degrades instead.
    items_by_id = {item["id"]: item for item in wardrobe}
    result = recommend_outfit(candidates, items_by_id, weather_data, payload.occasion)

    return {"weather": weather_data, "occasion": payload.occasion, **result}