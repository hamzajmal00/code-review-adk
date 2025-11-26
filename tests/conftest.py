import pytest
from database import SessionLocal
from models import Plan, User, Installation, Repository


@pytest.fixture(autouse=True)
def clean_db():
    db = SessionLocal()

    # Order matters because of FK constraints
    db.query(Repository).delete()
    db.query(Installation).delete()
    db.query(User).delete()
    db.query(Plan).delete()

    db.commit()
    db.close()

    yield
