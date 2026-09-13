import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import (
    Base,
    add_item,
    get_all_items,
    get_item_by_id,
    delete_item,
    count_items,
)


@pytest.fixture
def db():
    """Provide a fresh in-memory database for each test."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def sample_item_data():
    """A plain white T-shirt used across tests."""
    return {
        "image_url": "uploads/white_tshirt.jpg",
        "category": "top",
        "color": "white",
        "hex_color": "#FFFFFF",
        "style": "casual",
        "warmth_level": 1,
        "description": "A plain white cotton T-shirt",
    }


# ---------- Create ----------

def test_add_item_returns_item_with_id(db, sample_item_data):
    item = add_item(db, **sample_item_data)
    assert item.id is not None
    assert item.category == "top"
    assert item.warmth_level == 1


def test_add_item_sets_created_at(db, sample_item_data):
    item = add_item(db, **sample_item_data)
    assert item.created_at is not None


def test_add_item_uses_default_hex_color(db):
    item = add_item(
        db,
        image_url="uploads/x.jpg",
        category="top",
        color="unknown",
        style="casual",
        warmth_level=2,
    )
    assert item.hex_color == "#000000"


def test_add_multiple_items_get_different_ids(db, sample_item_data):
    item1 = add_item(db, **sample_item_data)
    item2 = add_item(db, **sample_item_data)
    assert item1.id != item2.id


# ---------- Read ----------

def test_get_all_items_empty_wardrobe(db):
    assert get_all_items(db) == []


def test_get_all_items_returns_all(db, sample_item_data):
    add_item(db, **sample_item_data)
    add_item(db, **sample_item_data)
    assert len(get_all_items(db)) == 2


def test_get_all_items_filter_by_category(db, sample_item_data):
    add_item(db, **sample_item_data)
    add_item(db, **{**sample_item_data, "category": "bottom"})
    add_item(db, **{**sample_item_data, "category": "shoes"})

    tops = get_all_items(db, category="top")
    assert len(tops) == 1
    assert tops[0].category == "top"


def test_get_all_items_filter_nonexistent_category(db, sample_item_data):
    add_item(db, **sample_item_data)
    assert get_all_items(db, category="hat") == []


def test_get_item_by_id_found(db, sample_item_data):
    created = add_item(db, **sample_item_data)
    found = get_item_by_id(db, created.id)
    assert found is not None
    assert found.id == created.id


def test_get_item_by_id_not_found(db):
    assert get_item_by_id(db, 9999) is None


# ---------- Delete ----------

def test_delete_item_success(db, sample_item_data):
    item = add_item(db, **sample_item_data)
    assert delete_item(db, item.id) is True
    assert get_item_by_id(db, item.id) is None


def test_delete_nonexistent_item_returns_false(db):
    assert delete_item(db, 9999) is False


def test_delete_item_only_removes_target(db, sample_item_data):
    item1 = add_item(db, **sample_item_data)
    item2 = add_item(db, **sample_item_data)
    delete_item(db, item1.id)
    assert get_item_by_id(db, item2.id) is not None


# ---------- Count ----------

def test_count_items_empty(db):
    assert count_items(db) == 0


def test_count_items_after_add_and_delete(db, sample_item_data):
    item = add_item(db, **sample_item_data)
    add_item(db, **sample_item_data)
    assert count_items(db) == 2
    delete_item(db, item.id)
    assert count_items(db) == 1


# ---------- Serialization ----------

def test_to_dict_contains_all_fields(db, sample_item_data):
    item = add_item(db, **sample_item_data)
    data = item.to_dict()
    expected_keys = {
        "id", "image_url", "category", "color",
        "hex_color", "style", "warmth_level", "description", "created_at",
    }
    assert set(data.keys()) == expected_keys