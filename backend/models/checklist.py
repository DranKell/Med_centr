from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class ChecklistInspection(Base):
    __tablename__ = 'checklist_inspections'

    id = Column(Integer, primary_key=True, index=True)
    template_key = Column(String(120), nullable=False, index=True)
    template_title = Column(String(300), nullable=False)
    responsible = Column(String(200), nullable=False)
    performed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    overall_note = Column(Text, nullable=True)
    items_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)