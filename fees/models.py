from sqlalchemy import Column, Integer, String, ForeignKey, DECIMAL, DateTime
from sqlalchemy.orm import relationship
from db import Base


class FeeConcept(Base):
    __tablename__ = 'fee_concepts'
    concept_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True) # Ej: INSCRIPCIONES EN PROGRAMAS CONDUNCENTES A GRADO ACADÉMICO
    category = Column(String(50)) 
    
class FeeSchedule(Base):
    __tablename__ = 'fee_schedules'
    schedule_id = Column(Integer, primary_key=True)
    concept_id = Column(Integer, ForeignKey('fee_concepts.concept_id'), nullable=False)
    program_level = Column(String(50))
    term_id = Column(Integer, ForeignKey('academic_terms.term_id'))
    value_bs = Column(DECIMAL(12, 2), nullable=False) # Valor en Bolívares
    
    concept = relationship("FeeConcept")

class Payment(Base):
    __tablename__ = 'payments'
    payment_id = Column(Integer, primary_key=True)
    student_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    concept_id = Column(Integer, ForeignKey('fee_concepts.concept_id'), nullable=False)
    amount = Column(DECIMAL(12, 2), nullable=False)
    payment_date = Column(DateTime, nullable=False)
    proof_url = Column(String(255)) # Enlace al comprobante subido por el alumno
    invoice_url = Column(String(255)) # Enlace a la factura/comprobante generado por el sistema
    bank_reference = Column(String(50)) # Referencia bancaria (tomado de tu CSV)
    status = Column(String(50), default='Pending Verification') # Estatus clave para el proceso
    
    student = relationship("User", foreign_keys=[student_user_id])
    concept = relationship("FeeConcept")
