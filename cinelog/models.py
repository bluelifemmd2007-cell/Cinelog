from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TMDBSearchResult(BaseModel):
    tmdb_id: int
    media_type: str  
    title: str
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    poster_url: Optional[str] = None
    release_year: Optional[str] = None
    genres: List[str] = []


class SearchResponse(BaseModel):
    results: List[TMDBSearchResult]


class AddToWatchlistRequest(BaseModel):
    tmdb_id: int
    media_type: str = Field(..., pattern="^(movie|tv)$")
    status: str = Field(default="want_to_watch", pattern="^(watched|watching|want_to_watch)$")
    user_rating: Optional[int] = Field(default=None, ge=1, le=10)


class UpdateWatchlistRequest(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(watched|watching|want_to_watch)$")
    user_rating: Optional[int] = Field(default=None, ge=1, le=10)


class WatchlistItemOut(BaseModel):
    id: int
    tmdb_id: int
    media_type: str
    title: str
    overview: Optional[str]
    poster_path: Optional[str]
    poster_url: Optional[str] = None
    release_year: Optional[str]
    genres: List[str]
    status: str
    user_rating: Optional[int]
    added_at: datetime

    class Config:
        from_attributes = True


class RecommendationItem(BaseModel):
    title: str
    media_type: str
    release_year: Optional[str] = None
    tmdb_id: Optional[int] = None
    poster_url: Optional[str] = None
    overview: Optional[str] = None
    reason: str  


class RecommendationResponse(BaseModel):
    recommendations: List[RecommendationItem]
    based_on_summary: str  