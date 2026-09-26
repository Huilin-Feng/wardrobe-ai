from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ClothingResponse(BaseModel):
    """Shape of a clothing item returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    category: str
    color: str
    hex_color: str
    style: str
    warmth_level: int
    description: str
    created_at: datetime


class ClothingCreate(BaseModel):
    """Payload for manually creating an item (used before Vision API is wired up)."""

    image_url: str
    category: str = Field(description="top, bottom, outerwear, shoes, or accessory")
    color: str
    style: str
    warmth_level: int = Field(ge=1, le=5, description="1 = lightest, 5 = warmest")
    hex_color: str = "#000000"
    description: str = ""

# Must match VALID_OCCASIONS in scoring_engine; a test enforces this.
Occasion = Literal["casual", "work", "date", "formal", "workout"]


class RecommendRequest(BaseModel):
    """Payload for requesting an outfit recommendation."""

    city: str = Field(min_length=1, description="City name for the weather lookup")
    occasion: Occasion