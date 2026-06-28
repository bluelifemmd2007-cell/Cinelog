import os

from dotenv import load_dotenv

load_dotenv()


class Settings:

    TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE_URL: str = "https://image.tmdb.org/t/p/w342"


    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./cinelog.db")

    MIN_RATED_FOR_RECOMMENDATIONS: int = int(
        os.getenv("MIN_RATED_FOR_RECOMMENDATIONS", "3")
    )
    RECOMMENDATION_COUNT: int = int(os.getenv("RECOMMENDATION_COUNT", "5"))


settings = Settings()

if not settings.TMDB_API_KEY:
    print(
        "[WARNING] TMDB_API_KEY is not set. Searching for movies/shows will fail "
        "until you add a key to your .env file. Get a free key at "
        "https://www.themoviedb.org/settings/api"
    )

if not settings.GROQ_API_KEY:
    print(
        "[WARNING] GROQ_API_KEY is not set. AI recommendations will fail until "
        "you add a key to your .env file. Your watchlist will still work fine."
    )