import os
from datetime import datetime, timedelta
from jose import jwt

# ENV VARIABLES
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-this")
JWT_ALGO = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def create_jwt_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGO)
    return encoded_jwt

