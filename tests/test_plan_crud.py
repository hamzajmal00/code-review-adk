from database import SessionLocal
from models import Plan
from crud.plan_crud import get_plan_by_slug

def test_plan_crud():
    db = SessionLocal()

    # wipe existing data
    db.query(Plan).delete()
    db.commit()

    plan = Plan(
        name="Free",
        slug="free",
        monthly_pr_limit=5
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    fetched = get_plan_by_slug(db, "free")

    assert fetched is not None
    assert fetched.name == "Free"
    assert fetched.monthly_pr_limit == 5
