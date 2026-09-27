from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .catalog import get_books
from .recommendations import rank_books

router = APIRouter(prefix="/api")


class RecommendationRequest(BaseModel):
    mood: str = Field(min_length=1, max_length=40)
    intent: str = Field(min_length=1, max_length=80)
    kind: Literal["any", "fiction", "nonfiction"] = "any"
    minutes: int = Field(default=30, ge=5, le=1440)
    depth: Literal["light", "balanced", "deep"] = "balanced"


@router.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "catalog": "database", "book_count": len(get_books())}


@router.get("/books")
def list_books() -> list[dict[str, object]]:
    return get_books()


@router.post("/recommendations")
def recommendations(preferences: RecommendationRequest) -> list[dict[str, object]]:
    return rank_books(preferences.model_dump())