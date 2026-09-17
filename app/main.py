import os
import shutil
import uuid
from pathlib import Path

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
from app.models import ClothingCreate, ClothingResponse
from app.clothing_analyzer import ClothingAnalysisError, analyze_clothing
from app.weather_service import CityNotFoundError, WeatherServiceError, get_weather


app = FastAPI(
    title="AI Wardrobe Assistant",
    description="Outfit recommendation engine with multi-dimensional scoring",
    version="0.1.0",
)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@app.on_event("startup")
def on_startup() -> None:
    """Create tables and make sure the upload directory exists."""
    init_db()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)


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