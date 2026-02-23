import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import json
import pandas as pd

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from schemas  import BulkUploadResult, ClientCreate, ClientOut, ClientUpdate
import models
import auth_utils

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.get("/", response_model=list[ClientOut])
def list_clients(
    skip:  int = Query(0,   ge=0),
    limit: int = Query(100, ge=1, le=500),
    db:    Session = Depends(get_db),
    _:     models.Admin = Depends(auth_utils.get_current_admin),
):
    return db.query(models.Client).offset(skip).limit(limit).all()


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: int,
    db:        Session = Depends(get_db),
    _:         models.Admin = Depends(auth_utils.get_current_admin),
):
    client = db.query(models.Client).filter(models.Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.post("/", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    db:      Session = Depends(get_db),
    _:       models.Admin = Depends(auth_utils.get_current_admin),
):
    client = models.Client(**payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    payload:   ClientUpdate,
    db:        Session = Depends(get_db),
    _:         models.Admin = Depends(auth_utils.get_current_admin),
):
    client = db.query(models.Client).filter(models.Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    db:        Session = Depends(get_db),
    _:         models.Admin = Depends(auth_utils.get_current_admin),
):
    client = db.query(models.Client).filter(models.Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(client)
    db.commit()


@router.post("/bulk-upload", response_model=BulkUploadResult)
def bulk_upload_clients(
    file: UploadFile = File(...),
    db:   Session = Depends(get_db),
    _:    models.Admin = Depends(auth_utils.get_current_admin),
):
    content  = file.file.read()
    ext      = file.filename.rsplit(".", 1)[-1].lower()
    inserted = 0
    skipped  = 0
    errors   = []

    try:
        if ext == "csv":
            df = pd.read_csv(io.BytesIO(content), dtype=str).fillna("")
        elif ext == "json":
            data = json.loads(content)
            df   = pd.DataFrame(data if isinstance(data, list) else [data])
        else:
            raise HTTPException(status_code=400, detail="Only .csv and .json files are supported")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {exc}")

    required = {"full_name", "phone_number"}
    if not required.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"File must contain columns: {required}")

    for idx, row in df.iterrows():
        row_num = idx + 2
        try:
            if not row.get("full_name") or not row.get("phone_number"):
                errors.append(f"Row {row_num}: full_name and phone_number are required")
                skipped += 1
                continue
            extra = {col: row[col] for col in df.columns if col not in {"full_name","phone_number","email","timezone"} and row.get(col)}
            client = models.Client(
                full_name    = row["full_name"].strip(),
                phone_number = row["phone_number"].strip(),
                email        = row.get("email") or None,
                timezone     = row.get("timezone") or "UTC",
                extra_data   = extra or None,
            )
            db.add(client)
            db.flush()
            inserted += 1
        except Exception as exc:
            db.rollback()
            errors.append(f"Row {row_num}: {str(exc)}")
            skipped += 1

    db.commit()
    return BulkUploadResult(inserted=inserted, skipped=skipped, errors=errors)