# crud/installation_crud.py

from sqlalchemy.orm import Session
from models import Installation


def create_installation(
    db: Session,
    installation_id: int,
    account_login: str,
    account_type: str,
    user_id: int
):
    """Create installation record when GitHub App is installed."""
    inst = Installation(
        installation_id=installation_id,
        account_login=account_login,
        account_type=account_type,
        user_id=user_id,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def get_installation_by_installation_id(db: Session, installation_id: int):
    """Fetch installation by GitHub installation_id"""
    return db.query(Installation).filter(
        Installation.installation_id == installation_id
    ).first()


def get_installations_by_user(db: Session, user_id: int):
    """Get all installations owned by a user"""
    return db.query(Installation).filter(
        Installation.user_id == user_id
    ).all()

def create_or_update_installation(db: Session, installation_id: int, login: str, account_type: str):
    inst = get_installation_by_installation_id(db, installation_id)

    if inst:
        inst.account_login = login
        inst.account_type = account_type
        db.commit()
        db.refresh(inst)
        return inst

    inst = Installation(
        installation_id=installation_id,
        account_login=login,
        account_type=account_type,
        user_id=None
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst

def link_installations_to_user(db: Session, user_id: int):
    """Assign all unassigned installations to this user."""
    unlinked = db.query(Installation).filter(Installation.user_id.is_(None)).all()

    for inst in unlinked:
        inst.user_id = user_id

    db.commit()
    return len(unlinked)