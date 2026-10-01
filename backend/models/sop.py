from sqlalchemy import Column, Integer, String, Text, DateTime
from database import Base
from datetime import datetime

class SOP(Base):
    __tablename__ = 'sops'
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    number = Column(String, nullable=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    normative_refs = Column(Text, nullable=True)
    scope = Column(Text, nullable=True)
    terms = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    procedure = Column(Text, nullable=True)
    quality_control = Column(Text, nullable=True)
    documentation = Column(Text, nullable=True)
    status = Column(String, default='draft')
    approval_order = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
