from database import SessionLocal
from crud.user_crud import get_user_by_github_id, create_user
from models import Plan


def test_user_crud():
    db = SessionLocal()

    # STEP 1: Seed plan (required for user)
    plan = Plan(name="Free", slug="free", monthly_pr_limit=5)
    db.add(plan)
    db.commit()
    db.refresh(plan)

    # STEP 2: Create a user
    user = create_user(
        db=db,
        username="abdul",
        github_user_id=111,
        email="abdul@test.com",
        avatar_url="http://avatar",
        plan_id=plan.id
    )

    assert user.github_username == "abdul"

    # STEP 3: Fetch using CRUD
    fetched = get_user_by_github_id(db, 111)

    assert fetched is not None
    assert fetched.github_username == "abdul"
