# crud/repo_crud.py

from sqlalchemy.orm import Session
from models import Repository


def add_repository(db: Session, installation_id: int, repo_full_name: str, is_active: bool = True):
    repo = Repository(
        installation_id=installation_id,
        repo_full_name=repo_full_name,
        is_active=is_active
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


def get_repositories_by_installation(db: Session, installation_id: int):
    return db.query(Repository)\
             .filter(Repository.installation_id == installation_id)\
             .all()


def deactivate_repository(db: Session, repo_id: int):
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        return None

    repo.is_active = False
    db.commit()
    db.refresh(repo)
    return repo



def upsert_repository(db: Session, installation_id: int, repo_full_name: str, is_active=True):
    repo = db.query(Repository).filter(
        Repository.installation_id == installation_id,
        Repository.repo_full_name == repo_full_name
    ).first()

    if repo:
        # update existing repo
        repo.is_active = is_active
        db.commit()
        db.refresh(repo)
        return repo

    # create new repo
    repo = Repository(
        installation_id=installation_id,
        repo_full_name=repo_full_name,
        is_active=is_active
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo