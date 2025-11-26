from database import SessionLocal
from crud.installation_crud import create_installation
from models import User, Plan


def test_installation_crud():
    db = SessionLocal()

    # STEP 1 — Seed plan
    plan = Plan(name="Free", slug="free", monthly_pr_limit=5)
    db.add(plan)
    db.commit()
    db.refresh(plan)

    # STEP 2 — Seed user
    user = User(
        github_user_id=222,
        github_username="usman",
        plan_id=plan.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # STEP 3 — Test installation create
    inst = create_installation(
        db=db,
        installation_id=999,
        account_login="usman",
        account_type="User",
        user_id=user.id
    )

    assert inst.installation_id == 999
    assert inst.user_id == user.id
