from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.sop import SOP
from schemas.sop import SOPApproval, SOPCreate, SOPResponse

router = APIRouter()

@router.get('/', response_model=List[SOPResponse])
def get_sops(category: str = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if skip < 0 or limit < 1 or limit > 500:
        raise HTTPException(status_code=422, detail='Invalid pagination parameters')
    q = db.query(SOP)
    if category:
        q = q.filter(SOP.category == category)
    return q.offset(skip).limit(limit).all()

@router.get('/{sop_id}', response_model=SOPResponse)
def get_sop(sop_id: int, db: Session = Depends(get_db)):
    sop = db.query(SOP).filter(SOP.id == sop_id).first()
    if not sop:
        raise HTTPException(status_code=404, detail='SOP not found')
    return sop

@router.post('/', response_model=SOPResponse)
def create_sop(sop: SOPCreate, db: Session = Depends(get_db)):
    db_sop = SOP(**sop.model_dump(exclude={'status'}), status='draft')
    db.add(db_sop)
    db.commit()
    db.refresh(db_sop)
    return db_sop

@router.put('/{sop_id}', response_model=SOPResponse)
def update_sop(sop_id: int, sop: SOPCreate, db: Session = Depends(get_db)):
    db_sop = db.query(SOP).filter(SOP.id == sop_id).first()
    if not db_sop:
        raise HTTPException(status_code=404, detail='SOP not found')
    if db_sop.status == 'approved':
        raise HTTPException(status_code=409, detail='Approved SOPs are immutable; create a new revision')
    for k, v in sop.model_dump().items():
        if k not in {'status', 'key'}:
            setattr(db_sop, k, v)
    db.commit()
    db.refresh(db_sop)
    return db_sop

@router.post('/{sop_id}/approve')
def approve_sop(sop_id: int, approval: SOPApproval, db: Session = Depends(get_db)):
    sop = db.query(SOP).filter(SOP.id == sop_id).first()
    if not sop:
        raise HTTPException(status_code=404, detail='SOP not found')
    if sop.status == 'approved':
        raise HTTPException(status_code=409, detail='SOP is already approved; create a new revision')
    sop.status = 'approved'
    sop.approval_order = f'{approval.order_number} от {approval.order_date.strftime("%d.%m.%Y")}'
    db.commit()
    return {'status': 'approved', 'order': sop.approval_order}
