"""
Fetches real book data from the Open Library API (free, no key needed)
and loads it into the `books` table so the recommendation engine has a
real catalog to work with instead of the 12-book starter list.

Run this from the project root, AFTER running `alembic upgrade head`
(so the `books` table exists), and after your .env / DATABASE_URL is
working (the same .env used by the FastAPI app):

    python seed_books.py

It is safe to re-run: existing book ids are skipped, so you can run it
again later to pull in more subjects or top up the catalog.
"""

import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone

from sqlalchemy import select

from kahaniya.database import SessionLocal, engine, Base
from kahaniya.models import Book

# ---------------------------------------------------------------------------
# Subject -> derived metadata mapping.
# Open Library's subject API doesn't give us mood/intent/pace data, so we
# derive sensible defaults per subject. This keeps every book usable by the
# existing rank_books() scoring in recommendations.py without hand-writing
# 1000 individual descriptions.
# ---------------------------------------------------------------------------
SUBJECT_CONFIG = {
    "fantasy": dict(kind="fiction", genres=["Fantasy"], themes=["adventure", "magic", "belonging"], moods=["curious", "hopeful", "restless"], intents=["escape for a while", "feel wonder"], intensity=2, complexity=2, pace="Immersive", tone="Imaginative and transporting", badge="A world to get lost in", color="#5f7c9c"),
    "science_fiction": dict(kind="fiction", genres=["Science fiction"], themes=["discovery", "the future", "survival"], moods=["curious", "restless", "hopeful"], intents=["escape for a while", "feel excited", "learn something new"], intensity=2, complexity=3, pace="Page-turning", tone="Big ideas, briskly told", badge="One very big problem", color="#d38a52"),
    "romance": dict(kind="fiction", genres=["Romance"], themes=["connection", "fresh starts", "vulnerability"], moods=["tender", "lonely", "comforted"], intents=["feel comforted", "feel hopeful"], intensity=1, complexity=1, pace="Cozy", tone="Warm and character-driven", badge="A soft place to land", color="#a36b49"),
    "mystery": dict(kind="fiction", genres=["Mystery"], themes=["secrets", "justice", "unraveling the truth"], moods=["curious", "restless"], intents=["escape for a while", "feel excited"], intensity=3, complexity=2, pace="Gripping", tone="Sharp, twisty, and hard to put down", badge="One more chapter", color="#4d5a6b"),
    "thriller": dict(kind="fiction", genres=["Thriller"], themes=["danger", "tension", "survival"], moods=["restless", "overwhelmed"], intents=["feel excited", "escape for a while"], intensity=4, complexity=2, pace="Relentless", tone="Tense and fast-moving", badge="Hold your breath", color="#6b3f3f"),
    "horror": dict(kind="fiction", genres=["Horror"], themes=["fear", "the unknown", "survival"], moods=["restless", "overwhelmed"], intents=["feel excited", "escape for a while"], intensity=5, complexity=2, pace="Unsettling", tone="Dark and atmospheric", badge="Not for the faint of heart", color="#3a2f3a"),
    "historical_fiction": dict(kind="fiction", genres=["Historical fiction"], themes=["memory", "resilience", "another era"], moods=["reflective", "curious"], intents=["make sense of things", "feel understood"], intensity=2, complexity=3, pace="Immersive", tone="Rich, grounded storytelling", badge="A window into the past", color="#9a5b45"),
    "literary_fiction": dict(kind="fiction", genres=["Literary fiction"], themes=["identity", "relationships", "meaning"], moods=["reflective", "lonely", "curious"], intents=["feel understood", "make sense of things"], intensity=2, complexity=3, pace="Thoughtful", tone="Observant and character-driven", badge="A closer look at being human", color="#597e91"),
    "young_adult_fiction": dict(kind="fiction", genres=["Young adult"], themes=["growing up", "friendship", "identity"], moods=["curious", "hopeful", "restless"], intents=["feel understood", "feel inspired"], intensity=2, complexity=1, pace="Quick", tone="Honest and energetic", badge="Coming of age", color="#c8a85e"),
    "humor": dict(kind="fiction", genres=["Humor"], themes=["everyday life", "absurdity", "connection"], moods=["restless", "tender"], intents=["feel comforted", "escape for a while"], intensity=1, complexity=1, pace="Light", tone="Funny and easygoing", badge="A little levity", color="#c9854b"),
    "adventure": dict(kind="fiction", genres=["Adventure"], themes=["exploration", "courage", "the unknown"], moods=["restless", "curious"], intents=["feel excited", "escape for a while"], intensity=3, complexity=2, pace="Page-turning", tone="Bold and propulsive", badge="Into the unknown", color="#d38a52"),
    "dystopia": dict(kind="fiction", genres=["Dystopian"], themes=["power", "survival", "society"], moods=["restless", "overwhelmed", "curious"], intents=["make sense of things", "feel excited"], intensity=4, complexity=3, pace="Gripping", tone="Urgent and thought-provoking", badge="A warning worth reading", color="#4d5a6b"),
    "self_help": dict(kind="nonfiction", genres=["Personal growth"], themes=["habits", "motivation", "change"], moods=["motivated", "stuck", "restless"], intents=["start something new", "feel inspired"], intensity=1, complexity=1, pace="Actionable", tone="Clear and encouraging", badge="A nudge in the right direction", color="#729084"),
    "psychology": dict(kind="nonfiction", genres=["Psychology"], themes=["the mind", "relationships", "self-understanding"], moods=["curious", "reflective", "overwhelmed"], intents=["make sense of things", "feel understood"], intensity=2, complexity=3, pace="Conversational", tone="Insightful and grounded", badge="Understanding the why", color="#6e8292"),
    "biography": dict(kind="nonfiction", genres=["Biography"], themes=["ambition", "resilience", "a life examined"], moods=["curious", "motivated", "reflective"], intents=["feel inspired", "learn something new"], intensity=2, complexity=2, pace="Absorbing", tone="Candid and revealing", badge="A life worth knowing", color="#c9854b"),
    "biography_autobiography": dict(kind="nonfiction", genres=["Memoir"], themes=["self-discovery", "resilience", "family"], moods=["reflective", "curious", "motivated"], intents=["feel inspired", "make sense of things"], intensity=3, complexity=2, pace="Gripping", tone="Personal and unflinching", badge="A life changed", color="#c9854b"),
    "philosophy": dict(kind="nonfiction", genres=["Philosophy"], themes=["meaning", "ethics", "how to live"], moods=["reflective", "curious"], intents=["make sense of things", "feel grounded"], intensity=1, complexity=4, pace="Unhurried", tone="Thoughtful and probing", badge="Big questions, patiently asked", color="#5f7c4f"),
    "business": dict(kind="nonfiction", genres=["Business"], themes=["strategy", "leadership", "ambition"], moods=["motivated", "curious"], intents=["learn something new", "feel inspired"], intensity=1, complexity=2, pace="Practical", tone="Direct and applicable", badge="Ideas you can use Monday", color="#729084"),
    "history": dict(kind="nonfiction", genres=["History"], themes=["the past", "power", "change over time"], moods=["curious", "reflective"], intents=["learn something new", "make sense of things"], intensity=2, complexity=3, pace="Detailed", tone="Well-researched and vivid", badge="How we got here", color="#9a5b45"),
    "true_crime": dict(kind="nonfiction", genres=["True crime"], themes=["justice", "the dark side of human nature"], moods=["restless", "curious"], intents=["feel excited", "make sense of things"], intensity=4, complexity=2, pace="Gripping", tone="Unflinching and investigative", badge="Stranger than fiction", color="#6b3f3f"),
    "poetry": dict(kind="nonfiction", genres=["Poetry"], themes=["feeling", "language", "the everyday made vivid"], moods=["tender", "reflective", "lonely"], intents=["feel understood", "slow down"], intensity=2, complexity=2, pace="Unhurried", tone="Spare and resonant", badge="Words that linger", color="#9a5b45"),
    "science": dict(kind="nonfiction", genres=["Science"], themes=["discovery", "how things work", "wonder"], moods=["curious", "hopeful"], intents=["learn something new", "feel wonder"], intensity=1, complexity=3, pace="Explanatory", tone="Clear and full of wonder", badge="How it all works", color="#5f7c9c"),
    "nature": dict(kind="nonfiction", genres=["Nature writing"], themes=["nature", "attention", "connection"], moods=["overwhelmed", "reflective", "curious"], intents=["slow down", "feel grounded"], intensity=1, complexity=2, pace="Unhurried", tone="Restorative and observant", badge="A slower way of seeing", color="#5f7c4f"),
    "cooking": dict(kind="nonfiction", genres=["Cooking"], themes=["craft", "comfort", "everyday ritual"], moods=["comforted", "curious"], intents=["feel comforted", "start something new"], intensity=1, complexity=1, pace="Practical", tone="Warm and hands-on", badge="Something good, made by hand", color="#c9854b"),
    "travel": dict(kind="nonfiction", genres=["Travel"], themes=["exploration", "new places", "perspective"], moods=["curious", "restless", "hopeful"], intents=["escape for a while", "feel inspired"], intensity=1, complexity=1, pace="Vivid", tone="Curious and observant", badge="Somewhere new", color="#5f7c9c"),
    "art": dict(kind="nonfiction", genres=["Art"], themes=["creativity", "perception", "craft"], moods=["curious", "reflective"], intents=["feel inspired", "slow down"], intensity=1, complexity=2, pace="Visual", tone="Thoughtful and visually rich", badge="Seeing things differently", color="#b76d61"),
    "spirituality": dict(kind="nonfiction", genres=["Spirituality"], themes=["meaning", "practice", "inner life"], moods=["reflective", "overwhelmed", "hopeful"], intents=["feel grounded", "slow down"], intensity=1, complexity=2, pace="Unhurried", tone="Calm and reflective", badge="A quieter mind", color="#5f7c4f"),
    "graphic_novels": dict(kind="fiction", genres=["Graphic novel"], themes=["storytelling", "art", "identity"], moods=["curious", "tender"], intents=["escape for a while", "feel understood"], intensity=2, complexity=1, pace="Quick", tone="Visual and expressive", badge="A story told in pictures", color="#c8a85e"),
    "classic_literature": dict(kind="fiction", genres=["Classics"], themes=["society", "human nature", "time"], moods=["reflective", "curious"], intents=["make sense of things", "learn something new"], intensity=2, complexity=4, pace="Deliberate", tone="Enduring and richly written", badge="A story that lasted", color="#597e91"),
    "personal_growth": dict(kind="nonfiction", genres=["Personal growth"], themes=["change", "confidence", "practice"], moods=["motivated", "stuck", "restless"], intents=["feel inspired", "start something new"], intensity=1, complexity=1, pace="Practical", tone="Encouraging and hands-on", badge="A nudge toward making", color="#b76d61"),
    "parenting": dict(kind="nonfiction", genres=["Parenting"], themes=["family", "patience", "growth"], moods=["overwhelmed", "hopeful", "motivated"], intents=["feel grounded", "learn something new"], intensity=1, complexity=1, pace="Practical", tone="Warm and practical", badge="A steadier hand", color="#c9854b"),
}

# Fallback config for any subject not explicitly listed above.
DEFAULT_CONFIG = dict(kind="fiction", genres=["General"], themes=["life", "change"], moods=["curious", "reflective"], intents=["make sense of things"], intensity=2, complexity=2, pace="Steady", tone="Thoughtfully told", badge="Worth your time", color="#729084")

TARGET_TOTAL = 1000
PER_SUBJECT_LIMIT = 35
PAGE_SIZE = 12  # small pages — something in this network path truncates
                # responses around ~64KB, so keep each request well under that
USER_AGENT = "kahaniya-seed-script/1.0 (contact: local-dev)"


def _fetch_page(url: str, attempts: int = 3) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            wait = 1.0 * attempt
            print(f"    page attempt {attempt}/{attempts} failed ({exc}); retrying in {wait:.1f}s ...")
            time.sleep(wait)
    raise last_error  # give up after all attempts


def fetch_subject(subject_key: str, limit: int) -> list[dict]:
    """Fetch `limit` works for a subject using small paginated requests,
    since large single requests get truncated on this network."""
    works: list[dict] = []
    offset = 0
    while len(works) < limit:
        page_limit = min(PAGE_SIZE, limit - len(works))
        url = f"https://openlibrary.org/subjects/{subject_key}.json?limit={page_limit}&offset={offset}"
        try:
            data = _fetch_page(url)
        except Exception as exc:  # noqa: BLE001
            print(f"    Giving up on {subject_key} at offset {offset}: {exc}")
            break
        page_works = data.get("works", [])
        if not page_works:
            break  # no more results for this subject
        works.extend(page_works)
        offset += page_limit
        time.sleep(0.2)
    return works


def deterministic_jitter(seed: str, low: float, high: float) -> float:
    """Small reproducible pseudo-random value so ratings/minutes vary
    without needing a real random module (same book -> same value)."""
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    fraction = int(digest[:8], 16) / 0xFFFFFFFF
    return round(low + fraction * (high - low), 1)


def build_book_row(work: dict, subject_key: str, config: dict) -> dict | None:
    title = (work.get("title") or "").strip()
    authors = work.get("authors") or []
    author = ", ".join(a.get("name", "") for a in authors if a.get("name")) or "Unknown"
    if not title:
        return None

    key = work.get("key", "")  # e.g. "/works/OL12345W"
    book_id = key.strip("/").replace("/", "-") or hashlib.md5(f"{title}-{author}".encode()).hexdigest()[:16]
    cover_id = work.get("cover_id")
    cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if isinstance(cover_id, int) and cover_id > 0 else None

    year = work.get("first_publish_year")
    rating = deterministic_jitter(book_id, 3.6, 4.7)
    minutes_base = 260 if config["kind"] == "nonfiction" else 320
    minutes = int(minutes_base + deterministic_jitter(book_id + "m", -80, 120))

    def article(word: str) -> str:
        return "An" if word[:1].lower() in "aeiou" else "A"

    genre_label = config["genres"][0]
    pace_label = config["pace"].lower()
    description = (
        f"{article(genre_label)} {genre_label.lower()} book exploring {', '.join(config['themes'][:2])}. "
        f"{article(pace_label)} {pace_label} read for when you're in a {config['moods'][0]} mood."
    )

    return {
        "id": book_id,
        "title": title,
        "author": author,
        "isbn": None,
        "cover_url": cover_url,
        "kind": config["kind"],
        "genres": config["genres"],
        "themes": config["themes"],
        "moods": config["moods"],
        "intents": config["intents"],
        "intensity": config["intensity"],
        "complexity": config["complexity"],
        "minutes": minutes,
        "pace": config["pace"],
        "description": description,
        "tone": config["tone"],
        "rating": rating,
        "year": year,
        "badge": config["badge"],
        "color": config["color"],
    }


def main() -> None:
    # Make sure the table exists even if someone runs this before alembic.
    Base.metadata.create_all(bind=engine, tables=[Book.__table__])

    with SessionLocal() as db:
        existing_books = {book.id: book for book in db.execute(select(Book)).scalars().all()}
    existing_ids = set(existing_books)

    collected: dict[str, dict] = {}
    cover_updates: dict[str, str] = {}
    subjects = list(SUBJECT_CONFIG.items())

    for subject_key, config in subjects:
        print(f"Fetching subject: {subject_key} ...")
        try:
            works = fetch_subject(subject_key, PER_SUBJECT_LIMIT)
        except Exception as exc:  # noqa: BLE001
            print(f"  Skipped {subject_key}: {exc}")
            continue

        for work in works:
            row = build_book_row(work, subject_key, config)
            if not row:
                continue
            if row["id"] in existing_ids:
                if not existing_books[row["id"]].cover_url and row["cover_url"]:
                    cover_updates[row["id"]] = row["cover_url"]
                continue
            if row["id"] in collected:
                continue
            collected[row["id"]] = row

        time.sleep(0.3)  # be polite to the public API

    new_rows = list(collected.values())[: max(0, TARGET_TOTAL - len(existing_ids))]
    print(f"Prepared {len(new_rows)} new books and {len(cover_updates)} cover updates (already had {len(existing_ids)}).")

    if not new_rows and not cover_updates:
        print("Nothing new to insert.")
        return

    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        for row in new_rows:
            db.add(Book(created_at=now, **row))
        if cover_updates:
            existing_to_update = db.execute(
                select(Book).where(Book.id.in_(cover_updates))
            ).scalars()
            for book in existing_to_update:
                book.cover_url = cover_updates[book.id]
        db.commit()

    print(f"Inserted {len(new_rows)} books and updated {len(cover_updates)} covers. Total catalog size is now {len(existing_ids) + len(new_rows)}.")


if __name__ == "__main__":
    main()
