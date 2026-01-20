from sqlalchemy import Column, Integer, String, ForeignKey, DECIMAL, DateTime
from sqlalchemy.orm import relationship
from transactions.models import Enrollment
from db import Base
from datetime import datetime


class FeeConcept(Base):
    __tablename__ = 'fee_concepts'
    concept_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True) # Ej: INSCRIPCIONES EN PROGRAMAS CONDUNCENTES A GRADO ACADÉMICO
    
class FeeSchedule(Base):
    __tablename__ = 'fee_schedules'
    schedule_id = Column(Integer, primary_key=True)
    concept_id = Column(Integer, ForeignKey('fee_concepts.concept_id'), nullable=False)
    program_id = Column(Integer, ForeignKey('programs.program_id'), nullable=False)
    term_id = Column(Integer, ForeignKey('academic_terms.term_id'))
    value_bs = Column(DECIMAL(12, 2), nullable=False)
    concept = relationship("FeeConcept")
    program = relationship("Program")
    term = relationship("AcademicTerm")

class Payment(Base):
    __tablename__ = 'payments'
    
    payment_id = Column(Integer, primary_key=True)
    student_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    program_id = Column(Integer, ForeignKey('programs.program_id'), nullable=True)
    concept_id = Column(Integer, ForeignKey('fee_concepts.concept_id'), nullable=False)
    amount = Column(DECIMAL(12, 2), nullable=False)
    payment_date = Column(DateTime, default=datetime.now, nullable=False)
    proof_url = Column(String(255))
    bank_reference = Column(String(50))
    invoice_url = Column(String(255))
    status = Column(String(50), default='Pending Verification') 
    student = relationship("User", foreign_keys=[student_user_id], back_populates="payments")
    program = relationship("Program")
    concept = relationship("FeeConcept")