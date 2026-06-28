import json
import re
from collections import Counter
from typing import List

import httpx

import tmdb_client
from config import settings
from database import WatchlistItem
from models import RecommendationItem, RecommendationResponse

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are a knowledgeable film and TV recommendation expert. Given a "
    "summary of someone's watch history and ratings, you suggest REAL "
    "movies or TV shows (that actually exist) that they have not seen "
    "yet, tailored to their demonstrated taste. You respond with ONLY a "
    "single valid JSON object, no markdown fences, no extra commentary."
)


class RecommenderError(Exception):
    """Raised when recommendation generation fails."""


def _build_taste_summary(rated_items: List[WatchlistItem]) -> str:
    """Builds a compact text summary of genres and ratings for the prompt."""
    lines = []
    genre_scores = Counter()
    genre_counts = Counter()

    for item in rated_items:
        rating = item.user_rating or 0
        lines.append(
            f"- {item.title} ({item.media_type}, {item.release_year or '?'}): "
            f"rated {rating}/10, genres: {', '.join(item.genres) or 'unknown'}"
        )
        for genre in item.genres:
            genre_scores[genre] += rating
            genre_counts[genre] += 1

    avg_by_genre = {
        g: round(genre_scores[g] / genre_counts[g], 1) for g in genre_counts
    }
    top_genres = sorted(avg_by_genre.items(), key=lambda kv: -kv[1])[:5]
    genre_line = ", ".join(f"{g} (avg {v}/10)" for g, v in top_genres)

    return (
        "Rated watch history:\n" + "\n".join(lines) +
        f"\n\nHighest-rated genres on average: {genre_line}"
    )


def _build_user_prompt(rated_items: List[WatchlistItem], already_have_titles: List[str]) -> str:
    taste_summary = _build_taste_summary(rated_items)
    exclude_list = ", ".join(already_have_titles)
    return (
        f"{taste_summary}\n\n"
        f"Already in their list (do NOT recommend any of these again): {exclude_list}\n\n"
        f"Suggest {settings.RECOMMENDATION_COUNT} real movies or TV shows this person "
        "hasn't seen, based on their taste pattern above. For each, give a short, "
        "specific reason tied to their actual rating history (not generic praise).\n\n"
        "Respond with ONLY this JSON shape, no other text:\n"
        "{\n"
        '  "taste_summary": "One sentence describing their taste pattern.",\n'
        '  "suggestions": [\n'
        '    {"title": "Exact Title", "media_type": "movie", "reason": "Why, referencing their history."},\n'
        "    ...\n"
        "  ]\n"
        "}"
    )


def _extract_json(raw_text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip(), flags=re.MULTILINE)
    return json.loads(cleaned)


async def _call_groq(user_prompt: str) -> dict:
    if not settings.GROQ_API_KEY:
        raise RecommenderError(
            "GROQ_API_KEY is not configured. Add it to your .env file to enable "
            "AI recommendations."
        )

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.6,
        "max_tokens": 1000,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(GROQ_API_URL, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RecommenderError(
                f"Groq API returned an error: {exc.response.status_code} "
                f"{exc.response.text[:200]}"
            ) from exc
        except httpx.RequestError as exc:
            raise RecommenderError(f"Failed to reach Groq API: {exc}") from exc

    data = response.json()
    try:
        raw_text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise RecommenderError(f"Unexpected Groq response shape: {data}") from exc

    try:
        return _extract_json(raw_text)
    except json.JSONDecodeError as exc:
        raise RecommenderError(
            f"Model did not return valid JSON. Raw output: {raw_text[:300]}"
        ) from exc


async def generate_recommendations(
    rated_items: List[WatchlistItem], already_have_titles: List[str]
) -> RecommendationResponse:
    if not rated_items:
        raise RecommenderError(
            "No rated items yet. Rate a few movies/shows as 'watched' first so "
            "we have something to base recommendations on."
        )

    prompt = _build_user_prompt(rated_items, already_have_titles)
    parsed = await _call_groq(prompt)

    taste_summary = parsed.get("taste_summary", "")
    suggestions = parsed.get("suggestions", [])

    verified_recommendations: List[RecommendationItem] = []
    for suggestion in suggestions:
        title = suggestion.get("title")
        media_type = suggestion.get("media_type", "movie")
        reason = suggestion.get("reason", "")
        if not title:
            continue

        try:
            tmdb_match = await tmdb_client.search_by_title_and_type(title, media_type)
        except tmdb_client.TMDBError:
            tmdb_match = None

        if tmdb_match is None:
            continue

        verified_recommendations.append(
            RecommendationItem(
                title=tmdb_match.title,
                media_type=tmdb_match.media_type,
                release_year=tmdb_match.release_year,
                tmdb_id=tmdb_match.tmdb_id,
                poster_url=tmdb_match.poster_url,
                overview=tmdb_match.overview,
                reason=reason,
            )
        )

    return RecommendationResponse(
        recommendations=verified_recommendations,
        based_on_summary=taste_summary,
    )