import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .base_model import Base

load_dotenv()

# Get current environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


DATABASE_URLS = {
    "development": os.getenv("DATABASE_URL"),
    "staging": os.getenv("STAGING_DATABASE_URL"),
    "production": os.getenv("PRODUCTION_DATABASE_URL")
}

DATABASE_URL = DATABASE_URLS.get(ENVIRONMENT)

if not DATABASE_URL:
    raise ValueError(f"No database URL configured for environment: {ENVIRONMENT}")


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Creates a new database session for each request"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_environment():
    """Utility function to get current environment"""
    return ENVIRONMENT