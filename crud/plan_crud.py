# crud/plan_crud.py

from sqlalchemy.orm import Session
from models import Plan


def get_plan_by_slug(db: Session, slug: str):
    return db.query(Plan).filter(Plan.slug == slug).first()
