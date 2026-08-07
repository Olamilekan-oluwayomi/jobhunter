import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Allow a single DATABASE_URL to override everything. This is the standard
# convention most hosts (Vercel, Railway, Render, GitHub Actions services)
# use, and it also makes it trivial to point tests at SQLite without
# touching this file.
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    required = {
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "DB_HOST": os.getenv("DB_HOST"),
        "DB_PORT": os.getenv("DB_PORT"),
        "DB_NAME": os.getenv("DB_NAME"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing required database environment variables: "
            f"{', '.join(missing)}. Set DATABASE_URL directly, or set all "
            "of DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME."
        )

    DATABASE_URL = (
        f"postgresql://{required['DB_USER']}:"
        f"{required['DB_PASSWORD']}@"
        f"{required['DB_HOST']}:"
        f"{required['DB_PORT']}/"
        f"{required['DB_NAME']}"
    )

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)