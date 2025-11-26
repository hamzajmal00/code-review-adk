from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# example:
# DATABASE_URL = "postgresql://postgres:admin@localhost:5432/fastauth"

# Fallback to SQLite if DATABASE_URL is not set
if not DATABASE_URL:
    import warnings
    warnings.warn(
        "DATABASE_URL environment variable is not set. "
        "Falling back to SQLite for development. "
        "For production, please set DATABASE_URL to a PostgreSQL connection string."
    )
    DATABASE_URL = "sqlite:///./code_reviewer.db"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
