import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.checklist import ChecklistInspection
from schemas.checklist import ChecklistInspectionCreate, ChecklistInspectionResponse
from services.checklist_catalog import CHECKLIST_TEMPLATES, get_template

router = APIRouter()


@router.get('/templates')
def list_templates():
    return CHECKLIST_TEMPLATES


@router.get('/inspections', response_model=list[ChecklistInspectionResponse])
def list_inspections(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if skip < 0 or limit < 1 or limit > 500:
        raise HTTPException(status_code=422, detail='Invalid pagination parameters')
    rows = db.query(ChecklistInspection).order_by(ChecklistInspection.performed_at.desc()).offset(skip).limit(limit).all()
    return [inspection_response(row) for row in rows]


@router.get('/inspections/{inspection_id}', response_model=ChecklistInspectionResponse)
def get_inspection(inspection_id: int, db: Session = Depends(get_db)):
    row = db.query(ChecklistInspection).filter(ChecklistInspection.id == inspection_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail='Checklist inspection not found')
    return inspection_response(row)


@router.post('/inspections', response_model=ChecklistInspectionResponse, status_code=201)
def create_inspection(payload: ChecklistInspectionCreate, db: Session = Depends(get_db)):
    template = get_template(payload.template_key)
    if template is None:
        raise HTTPException(status_code=404, detail='Checklist template not found')

    allowed_keys = {item[0] for item in template['items']}
    submitted_keys = [item.item_key for item in payload.items]
    if len(submitted_keys) != len(set(submitted_keys)) or set(submitted_keys) != allowed_keys:
        raise HTTPException(status_code=422, detail='Inspection must include each template item exactly once')
    if any(item.status == 'unchecked' for item in payload.items):
        raise HTTPException(status_code=422, detail='Every checklist item must be reviewed before saving')

    row = ChecklistInspection(
        template_key=template['key'],
        template_title=template['title'],
        responsible=payload.responsible,
        performed_at=payload.performed_at,
        overall_note=payload.overall_note,
        items_json=json.dumps([item.model_dump() for item in payload.items], ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return inspection_response(row)


def inspection_response(row: ChecklistInspection) -> dict:
    return {
        'id': row.id,
        'template_key': row.template_key,
        'template_title': row.template_title,
        'responsible': row.responsible,
        'performed_at': row.performed_at,
        'overall_note': row.overall_note,
        'items': json.loads(row.items_json),
    }