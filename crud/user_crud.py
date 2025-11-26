# crud/user_crud.py

from sqlalchemy.orm import Session
from models import User, Plan
from crud.plan_crud import get_plan_by_slug


def get_user_by_github_id(db: Session, github_user_id: int):
    return db.query(User).filter(User.github_user_id == github_user_id).first()



def create_user(db, github_user_id, username, email, avatar_url, plan_id=None):
    
    # 🔹 Always default to FREE plan if no plan_id is passed
    if not plan_id:
        free_plan = get_plan_by_slug(db, "free")
        plan_id = free_plan.id

    user = User(
        github_user_id=github_user_id,
        github_username=username,
        email=email,
        avatar_url=avatar_url,
        plan_id=plan_id
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_installation(db: Session, installation_id: int):
    from models import Installation
    inst = db.query(Installation).filter(Installation.installation_id == installation_id).first()
    if inst:
        return inst.user
    return None


def increment_pr_usage(db: Session, user: User):
    user.pr_used_this_period += 1
    db.commit()

def assign_default_plan(db, user):
    free_plan = db.query(Plan).filter(Plan.slug == "free").first()
    if not free_plan:
        raise Exception("Default plan 'free' not found")

    user.plan_id = free_plan.id
    db.commit()
    db.refresh(user)
    return user

def update_user_pr_count(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    # increment usage
    user.monthly_pr_count = (user.monthly_pr_count or 0) + 1
    db.commit()
    db.refresh(user)
    return user

def increment_user_pr_usage(db: Session, user_id: int) -> User | None:
    """Increase user's PR usage for current period by 1."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    current = user.pr_used_this_period or 0
    user.pr_used_this_period = current + 1
    db.commit()
    db.refresh(user)
    return user