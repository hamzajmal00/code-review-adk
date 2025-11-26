from database import SessionLocal
from models import Plan

def seed_plans():
    db = SessionLocal()

    exists = db.query(Plan).filter(Plan.slug == "free").first()
    if exists:
        print("Free plan already exists")
        return

    free_plan = Plan(
        name="Free",
        slug="free",
        monthly_pr_limit=5,
        monthly_token_limit=200000,
        is_active=True
    )

    db.add(free_plan)
    db.commit()
    print("Free plan created!")

if __name__ == "__main__":
    seed_plans()
