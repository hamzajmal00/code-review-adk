from database import SessionLocal
from crud.repo_crud import add_repository, get_repositories_by_installation, deactivate_repository
from models import User, Installation, Plan


def test_repo_crud():
    db = SessionLocal()

    # STEP 1 — Seed plan
    plan = Plan(name="Free", slug="free", monthly_pr_limit=5)
    db.add(plan)
    db.commit()
    db.refresh(plan)

    # STEP 2 — Seed user
    user = User(
        github_user_id=333,
        github_username="ali",
        plan_id=plan.id
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # STEP 3 — Seed installation
    inst = Installation(
        installation_id=777,
        account_login="ali",
        account_type="User",
        user_id=user.id
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)

    # STEP 4 — Add repo
    repo = add_repository(db, installation_id=inst.id, repo_full_name="ali/my-app")
    assert repo.repo_full_name == "ali/my-app"

    # STEP 5 — Fetch repos
    repos = get_repositories_by_installation(db, inst.id)
    assert len(repos) == 1

    # STEP 6 — Deactivate repo
    updated = deactivate_repository(db, repo.id)
    assert updated.is_active is False
