import json
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, nullable=False, index=True)
    media_type = Column(String, nullable=False)  

    title = Column(String, nullable=False)
    overview = Column(Text, nullable=True)
    poster_path = Column(String, nullable=True)
    release_year = Column(String, nullable=True)
    genres_json = Column(Text, nullable=True)  

    status = Column(String, nullable=False, default="want_to_watch")
    
    user_rating = Column(Integer, nullable=True)  

    added_at = Column(DateTime, default=datetime.utcnow)

    @property
    def genres(self) -> list:
        if not self.genres_json:
            return []
        return json.loads(self.genres_json)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()