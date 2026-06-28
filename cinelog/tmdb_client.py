from typing import Optional

import httpx

from config import settings
from models import TMDBSearchResult


class TMDBError(Exception):
    """Raised when a TMDB API call fails."""



def _poster_url(poster_path: Optional[str]) -> Optional[str]:
    if not poster_path:
        return None
    return f"{settings.TMDB_IMAGE_BASE_URL}{poster_path}"



_GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
    10759: "Action & Adventure", 10762: "Kids", 10763: "News",
    10764: "Reality", 10765: "Sci-Fi & Fantasy", 10766: "Soap",
    10767: "Talk", 10768: "War & Politics",
}


def _genre_names(genre_ids: list) -> list:
    return [_GENRE_MAP[g] for g in genre_ids if g in _GENRE_MAP]


def _normalize_result(item: dict, fallback_media_type: Optional[str] = None) -> Optional[TMDBSearchResult]:
    media_type = item.get("media_type", fallback_media_type)
    if media_type not in ("movie", "tv"):
        return None  

    is_movie = media_type == "movie"
    title = item.get("title") if is_movie else item.get("name")
    if not title:
        return None

    date_field = item.get("release_date") if is_movie else item.get("first_air_date")
    release_year = date_field[:4] if date_field else None

    return TMDBSearchResult(
        tmdb_id=item["id"],
        media_type=media_type,
        title=title,
        overview=item.get("overview"),
        poster_path=item.get("poster_path"),
        poster_url=_poster_url(item.get("poster_path")),
        release_year=release_year,
        genres=_genre_names(item.get("genre_ids", [])),
    )


async def _get(path: str, params: dict) -> dict:
    if not settings.TMDB_API_KEY:
        raise TMDBError(
            "TMDB_API_KEY is not configured. Add it to your .env file."
        )

    params = {**params, "api_key": settings.TMDB_API_KEY}
    url = f"{settings.TMDB_BASE_URL}{path}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise TMDBError(
                f"TMDB API returned an error: {exc.response.status_code} "
                f"{exc.response.text[:200]}"
            ) from exc
        except httpx.RequestError as exc:
            raise TMDBError(f"Failed to reach TMDB API: {exc}") from exc

    return response.json()


async def search_multi(query: str) -> list[TMDBSearchResult]:
    """Searches both movies and TV shows matching the query."""
    data = await _get("/search/multi", {"query": query, "include_adult": "false"})
    results = []
    for item in data.get("results", []):
        normalized = _normalize_result(item)
        if normalized:
            results.append(normalized)
    return results


async def search_by_title_and_type(title: str, media_type: str) -> Optional[TMDBSearchResult]:
    """
    Used by the recommender: given an AI-suggested title, finds the best
    matching real TMDB entry of the specified type. Returns None if
    nothing reasonable is found (the AI may invent a title that doesn't
    exist, especially at higher temperature).
    """
    endpoint = "/search/movie" if media_type == "movie" else "/search/tv"
    data = await _get(endpoint, {"query": title})
    results = data.get("results", [])
    if not results:
        return None
    return _normalize_result(results[0], fallback_media_type=media_type)


async def get_details(tmdb_id: int, media_type: str) -> dict:

    endpoint = f"/movie/{tmdb_id}" if media_type == "movie" else f"/tv/{tmdb_id}"
    data = await _get(endpoint, {})

    is_movie = media_type == "movie"
    title = data.get("title") if is_movie else data.get("name")
    date_field = data.get("release_date") if is_movie else data.get("first_air_date")
    release_year = date_field[:4] if date_field else None
    genre_names = [g["name"] for g in data.get("genres", [])]

    return {
        "tmdb_id": tmdb_id,
        "media_type": media_type,
        "title": title,
        "overview": data.get("overview"),
        "poster_path": data.get("poster_path"),
        "poster_url": _poster_url(data.get("poster_path")),
        "release_year": release_year,
        "genres": genre_names,
    }