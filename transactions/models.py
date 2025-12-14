from sqlalchemy import Column, Integer, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from db import Base
# from app.database import Base # Usar tu importación real

class Enrollment(Base):
    __tablename__ = 'enrollments'
    enrollment_id = Column(Integer, primary_key=True)
    student_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.section_id'), nullable=False)
    payment_id = Column(Integer, ForeignKey('payments.payment_id'), nullable=True) # Pago asociado
    enrollment_date = Column(Date, nullable=False)
    status = Column(String(50), default='Registered') # Estatus de la inscripción
    
    student = relationship("User", foreign_keys=[student_user_id])
    section = relationship("Section", back_populates="enrollments")
    payment = relationship("Payment")
    
    # Restricción: No se permite doble inscripción en la misma sección
    __table_args__ = (UniqueConstraint('student_user_id', 'section_id', name='uq_student_section'),)