import json
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import tmdb_client
from config import settings
from database import SessionLocal, WatchlistItem, init_db
from models import (
    AddToWatchlistRequest,
    RecommendationResponse,
    SearchResponse,
    UpdateWatchlistRequest,
    WatchlistItemOut,
)
from recommender import RecommenderError, generate_recommendations

app = FastAPI(
    title="CineLog",
    description="Personal watchlist tracker with AI-powered recommendations.",
    version="1.0.0",
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

init_db()


@app.on_event("startup")
def on_startup():
    init_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _with_poster_url(item: WatchlistItem) -> WatchlistItemOut:
    out = WatchlistItemOut.model_validate(item)
    if item.poster_path:
        out.poster_url = f"{settings.TMDB_IMAGE_BASE_URL}{item.poster_path}"
    return out


@app.get("/")
def serve_app():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def status():
    return {
        "tmdb_configured": bool(settings.TMDB_API_KEY),
        "ai_recommendations_available": bool(settings.GROQ_API_KEY),
    }


@app.get("/api/search", response_model=SearchResponse)
async def search(q: str = Query(..., min_length=1)):

    try:
        results = await tmdb_client.search_multi(q)
    except tmdb_client.TMDBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return SearchResponse(results=results)


@app.get("/api/watchlist", response_model=list[WatchlistItemOut])
def list_watchlist(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    query = db.query(WatchlistItem)
    if status_filter:
        query = query.filter(WatchlistItem.status == status_filter)
    items = query.order_by(WatchlistItem.added_at.desc()).all()
    return [_with_poster_url(i) for i in items]


@app.post("/api/watchlist", response_model=WatchlistItemOut, status_code=201)
async def add_to_watchlist(payload: AddToWatchlistRequest, db: Session = Depends(get_db)):
    existing = (
        db.query(WatchlistItem)
        .filter(
            WatchlistItem.tmdb_id == payload.tmdb_id,
            WatchlistItem.media_type == payload.media_type,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="This title is already in your watchlist.")

    try:
        details = await tmdb_client.get_details(payload.tmdb_id, payload.media_type)
    except tmdb_client.TMDBError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    item = WatchlistItem(
        tmdb_id=details["tmdb_id"],
        media_type=details["media_type"],
        title=details["title"],
        overview=details["overview"],
        poster_path=details["poster_path"],
        release_year=details["release_year"],
        genres_json=json.dumps(details["genres"]),
        status=payload.status,
        user_rating=payload.user_rating,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _with_poster_url(item)


@app.patch("/api/watchlist/{item_id}", response_model=WatchlistItemOut)
def update_watchlist_item(
    item_id: int, payload: UpdateWatchlistRequest, db: Session = Depends(get_db)
):
    item = db.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if payload.status is not None:
        item.status = payload.status
    if payload.user_rating is not None:
        item.user_rating = payload.user_rating

    db.commit()
    db.refresh(item)
    return _with_poster_url(item)


@app.delete("/api/watchlist/{item_id}", status_code=204)
def delete_watchlist_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(WatchlistItem).filter(WatchlistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()


@app.get("/api/recommend", response_model=RecommendationResponse)
async def recommend(db: Session = Depends(get_db)):
    """Generate AI recommendations based on the user's rated watch history."""
    rated_items = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.status == "watched", WatchlistItem.user_rating.isnot(None))
        .all()
    )

    if len(rated_items) < settings.MIN_RATED_FOR_RECOMMENDATIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Rate at least {settings.MIN_RATED_FOR_RECOMMENDATIONS} watched titles "
                f"first (you have {len(rated_items)}) so we have enough to base "
                "recommendations on."
            ),
        )

    all_titles = [i.title for i in db.query(WatchlistItem).all()]

    try:
        result = await generate_recommendations(rated_items, all_titles)
    except RecommenderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return result
