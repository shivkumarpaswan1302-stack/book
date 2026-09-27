from typing import Any

from .catalog import get_books


def rank_books(preferences: dict[str, Any]) -> list[dict[str, Any]]:
    """Rank the catalog with transparent feature matching."""
    ranked: list[dict[str, Any]] = []
    mood = preferences.get("mood", "")
    intent = preferences.get("intent", "")
    kind = preferences.get("kind", "any")
    depth = preferences.get("depth", "balanced")
    minutes = int(preferences.get("minutes", 30))

    for book in get_books():
        score = 0
        reasons: list[str] = []
        if mood in book["moods"]:
            score += 5
            reasons.append(f"It meets your {mood} mood with a {book['tone'].lower()} feel.")
        if intent in book["intents"]:
            score += 4
            reasons.append(f"It fits your wish to {intent}.")
        if kind != "any":
            score += 3 if book["kind"] == kind else -2
        if depth == "light":
            score += max(0, 4 - book["complexity"])
            score -= max(0, book["intensity"] - 2)
        elif depth == "deep":
            score += book["complexity"] + (1 if book["intensity"] >= 3 else 0)
        # `minutes` is the reading-time budget the user has in mind, while
        # book["minutes"] is the full book's estimated reading time — these
        # are on very different scales (e.g. 30 vs 300+), so compare them as
        # a ratio instead of a hard "fits within" threshold. That threshold
        # almost never fired for realistic inputs (every book takes longer
        # than a typical 30-minute budget), which meant the time preference
        # barely affected results and mostly just penalized every book.
        time_ratio = book["minutes"] / max(minutes, 5)
        if time_ratio <= 2:
            score += 3
            reasons.append("It's a quick fit for the time you have right now.")
        elif time_ratio <= 5:
            score += 1
        elif time_ratio <= 10:
            score -= 1
        else:
            score -= 3
            reasons.append("Heads up: this one is a longer commitment than your time budget.")
        if not reasons:
            reasons.append(f"A {book['pace'].lower()} read with themes of {', '.join(book['themes'][:2])}.")
        ranked.append({**book, "score": score, "reasons": reasons[:2]})

    return sorted(ranked, key=lambda item: (item["score"], item["rating"]), reverse=True)