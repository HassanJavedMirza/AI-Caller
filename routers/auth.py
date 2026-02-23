import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas  import LoginRequest, TokenResponse
import models
import auth_utils

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    admin = (
        db.query(models.Admin)
        .filter(models.Admin.username == payload.username)
        .first()
    )
    if not admin or not auth_utils.verify_password(payload.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = auth_utils.create_access_token(data={"sub": admin.username})
    return TokenResponse(access_token=token)


@router.get("/me", tags=["Auth"])
def get_me(current_admin: models.Admin = Depends(auth_utils.get_current_admin)):
    return {
        "admin_id": current_admin.admin_id,
        "username": current_admin.username,
        "email":    current_admin.email,
    }