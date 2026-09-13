from datetime import datetime, timezone

from sqlalchemy import create_engine, String, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

from app.config import settings

class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class ClothingItem(Base):
    """A single clothing item in the user's wardrobe."""

    __tablename__ = "clothing_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    image_url: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(50))
    color: Mapped[str] = mapped_column(String(50))
    hex_color: Mapped[str] = mapped_column(String(7), default="#000000")
    style: Mapped[str] = mapped_column(String(50))
    warmth_level: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        """Serialize this item into a plain dictionary for API responses."""

        return {
            "id": self.id,
            "image_url": self.image_url,
            "category": self.category,
            "color": self.color,
            "hex_color": self.hex_color,
            "style": self.style,
            "warmth_level": self.warmth_level,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<ClothingItem(id={self.id}, category={self.category}, color={self.color})>"

# ---------- Database connection ----------

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # SQLite-specific: allow multi-threaded access
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create all tables. Call once at application startup."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- CRUD operations ----------

def add_item(
    db: Session,
    image_url: str,
    category: str,
    color: str,
    style: str,
    warmth_level: int,
    hex_color: str = "#000000",
    description: str = "",
) -> ClothingItem:
    """Insert a new clothing item and return it with its generated id."""
    item = ClothingItem(
        image_url=image_url,
        category=category,
        color=color,
        hex_color=hex_color,
        style=style,
        warmth_level=warmth_level,
        description=description,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_all_items(db: Session, category: str | None = None) -> list[ClothingItem]:
    """Return all items, newest first. Optionally filter by category."""
    query = db.query(ClothingItem)
    if category:
        query = query.filter(ClothingItem.category == category)
    return query.order_by(ClothingItem.created_at.desc()).all()


def get_item_by_id(db: Session, item_id: int) -> ClothingItem | None:
    """Return a single item, or None if the id does not exist."""
    return db.query(ClothingItem).filter(ClothingItem.id == item_id).first()


def delete_item(db: Session, item_id: int) -> bool:
    """Delete an item. Returns True on success, False if the id was not found."""
    item = get_item_by_id(db, item_id)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def count_items(db: Session) -> int:
    """Return the total number of items in the wardrobe."""
    return db.query(ClothingItem).count()