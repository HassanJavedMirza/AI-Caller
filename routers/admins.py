import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas  import AdminCreate, AdminOut
import models
import auth_utils

router = APIRouter(prefix="/admins", tags=["Admins"])


@router.get("/", response_model=list[AdminOut])
def list_admins(
    db: Session = Depends(get_db),
    _:  models.Admin = Depends(auth_utils.get_current_admin),
):
    return db.query(models.Admin).all()


@router.post("/", response_model=AdminOut, status_code=status.HTTP_201_CREATED)
def create_admin(
    payload: AdminCreate,
    db:      Session = Depends(get_db),
    _:       models.Admin = Depends(auth_utils.get_current_admin),
):
    if db.query(models.Admin).filter(models.Admin.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(models.Admin).filter(models.Admin.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    admin = models.Admin(
        username      = payload.username,
        email         = payload.email,
        password_hash = auth_utils.hash_password(payload.password),
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@router.delete("/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin(
    admin_id:      int,
    db:            Session = Depends(get_db),
    current_admin: models.Admin = Depends(auth_utils.get_current_admin),
):
    if admin_id == current_admin.admin_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    admin = db.query(models.Admin).filter(models.Admin.admin_id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    db.delete(admin)
    db.commit()