from typing import Any

from sqlalchemy import select

from .database import SessionLocal
from .models import Book

# Small starter list kept as a safety net so the app still works
# before the `books` table has been seeded.
FALLBACK_BOOKS: list[dict[str, Any]] = [
    {"id": "midnight-library", "title": "The Midnight Library", "author": "Matt Haig", "isbn": "9780525559474", "kind": "fiction", "genres": ["Literary fiction", "Fantasy"], "themes": ["second chances", "belonging", "possibility"], "moods": ["hopeful", "reflective", "comforted"], "intents": ["feel hopeful", "make sense of things", "escape for a while"], "intensity": 2, "complexity": 2, "minutes": 300, "pace": "Steady", "description": "Between life and death there is a library, and within that library, the shelves go on forever. Every book offers a chance to try another life you could have lived.", "tone": "A gentle, hopeful thought experiment", "rating": 4.3, "year": 2020, "badge": "A little perspective", "color": "#487d68"},
    {"id": "atomic-habits", "title": "Atomic Habits", "author": "James Clear", "isbn": "9780735211292", "kind": "nonfiction", "genres": ["Personal growth", "Psychology"], "themes": ["habits", "motivation", "small changes"], "moods": ["motivated", "stuck", "restless"], "intents": ["start something new", "feel inspired", "learn something new"], "intensity": 1, "complexity": 1, "minutes": 300, "pace": "Actionable", "description": "A practical framework for getting a little better every day by changing the systems around your goals, one small habit at a time.", "tone": "Clear, encouraging, and easy to put into practice", "rating": 4.4, "year": 2018, "badge": "Small changes, real momentum", "color": "#729084"},
]

_BOOK_COLUMNS = [
    "id", "title", "author", "isbn", "cover_url", "kind", "genres", "themes", "moods",
    "intents", "intensity", "complexity", "minutes", "pace", "description",
    "tone", "rating", "year", "badge", "color",
]

_cache: list[dict[str, Any]] | None = None


def _book_to_dict(book: Book) -> dict[str, Any]:
    return {column: getattr(book, column) for column in _BOOK_COLUMNS}


def get_books(refresh: bool = False) -> list[dict[str, Any]]:
    """Return the full catalog, loading it from the database once and
    caching it in memory (the catalog changes rarely, so this avoids
    hitting the database on every recommendation request)."""
    global _cache
    if _cache is None or refresh:
        with SessionLocal() as db:
            rows = db.execute(select(Book)).scalars().all()
        _cache = [_book_to_dict(row) for row in rows] or FALLBACK_BOOKS
    return _cache


# Backwards-compatible name used elsewhere in the codebase.
BOOKS = get_books()
