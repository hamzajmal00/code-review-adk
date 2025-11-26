from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from database import get_db
from crud.user_crud import get_user_by_github_id

SECRET_KEY = "super-secret-key-change-this"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        github_user_id = payload.get("github_user_id")

        if github_user_id is None:
            raise HTTPException(401, "Invalid token (missing github_user_id)")

        user = get_user_by_github_id(db, github_user_id)
        if not user:
            raise HTTPException(401, "User not found")

        return user  # <-- RETURN ORM MODEL

    except JWTError:
        raise HTTPException(401, "Could not validate credentials")
