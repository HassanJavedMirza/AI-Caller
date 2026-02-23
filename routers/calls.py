import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import json
from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from schemas  import BulkUploadResult, InvoiceCreate, InvoiceOut, InvoiceUpdate
import models
import auth_utils

router = APIRouter(prefix="/invoices", tags=["Invoices"])


def _mark_overdue(db: Session):
    today = date.today()
    db.query(models.Invoice).filter(
        models.Invoice.status == "unpaid",
        models.Invoice.due_date < today,
    ).update({"status": "overdue"}, synchronize_session=False)
    db.commit()


@router.get("/stats/summary")
def invoice_stats(
    db: Session = Depends(get_db),
    _:  models.Admin = Depends(auth_utils.get_current_admin),
):
    _mark_overdue(db)
    from sqlalchemy import func
    rows = db.query(models.Invoice.status, func.count(models.Invoice.invoice_id)).group_by(models.Invoice.status).all()
    stats = {r[0]: r[1] for r in rows}
    total = sum(stats.values())
    return {"total": total, "unpaid": stats.get("unpaid",0), "overdue": stats.get("overdue",0), "paid": stats.get("paid",0), "processing": stats.get("processing",0)}


@router.get("/", response_model=list[InvoiceOut])
def list_invoices(
    skip:      int = Query(0,   ge=0),
    limit:     int = Query(100, ge=1, le=500),
    status:    str = Query(None),
    client_id: int = Query(None),
    db:        Session = Depends(get_db),
    _:         models.Admin = Depends(auth_utils.get_current_admin),
):
    _mark_overdue(db)
    q = db.query(models.Invoice)
    if status:
        q = q.filter(models.Invoice.status == status)
    if client_id:
        q = q.filter(models.Invoice.client_id == client_id)
    return q.offset(skip).limit(limit).all()


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db:         Session = Depends(get_db),
    _:          models.Admin = Depends(auth_utils.get_current_admin),
):
    _mark_overdue(db)
    inv = db.query(models.Invoice).filter(models.Invoice.invoice_id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return inv


@router.post("/", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    db:      Session = Depends(get_db),
    _:       models.Admin = Depends(auth_utils.get_current_admin),
):
    if not db.query(models.Client).filter(models.Client.client_id == payload.client_id).first():
        raise HTTPException(status_code=404, detail="Client not found")
    inv = models.Invoice(**payload.model_dump())
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


@router.patch("/{invoice_id}", response_model=InvoiceOut)
def update_invoice(
    invoice_id: int,
    payload:    InvoiceUpdate,
    db:         Session = Depends(get_db),
    _:          models.Admin = Depends(auth_utils.get_current_admin),
):
    inv = db.query(models.Invoice).filter(models.Invoice.invoice_id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(inv, field, value)
    db.commit()
    db.refresh(inv)
    return inv


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    invoice_id: int,
    db:         Session = Depends(get_db),
    _:          models.Admin = Depends(auth_utils.get_current_admin),
):
    inv = db.query(models.Invoice).filter(models.Invoice.invoice_id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    db.delete(inv)
    db.commit()


@router.post("/bulk-upload", response_model=BulkUploadResult)
def bulk_upload_invoices(
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

    required = {"client_id", "amount", "due_date"}
    if not required.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"File must contain columns: {required}")

    valid_statuses = {"unpaid", "paid", "overdue", "processing"}

    for idx, row in df.iterrows():
        row_num = idx + 2
        try:
            client_id  = int(row["client_id"])
            amount     = float(row["amount"])
            due_date   = date.fromisoformat(row["due_date"])
            currency   = row.get("currency") or "USD"
            row_status = row.get("status") or "unpaid"
            if row_status not in valid_statuses:
                raise ValueError(f"Invalid status '{row_status}'")
            if not db.query(models.Client).filter(models.Client.client_id == client_id).first():
                raise ValueError(f"Client ID {client_id} does not exist")
            inv = models.Invoice(client_id=client_id, amount=amount, currency=currency, due_date=due_date, status=row_status)
            db.add(inv)
            db.flush()
            inserted += 1
        except Exception as exc:
            db.rollback()
            errors.append(f"Row {row_num}: {str(exc)}")
            skipped += 1

    db.commit()
    return BulkUploadResult(inserted=inserted, skipped=skipped, errors=errors)