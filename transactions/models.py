from sqlalchemy import Column, String, Integer, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from db import Base
# from app.database import Base # Usar tu importación real

class Enrollment(Base):
    __tablename__ = 'enrollments'
    enrollment_id = Column(Integer, primary_key=True)
    student_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('sections.section_id'), nullable=False)
    # Agregamos subject_id aquí para saber exactamente qué materia inscribió dentro de esa sección
    subject_id = Column(Integer, ForeignKey('subjects.subject_id'), nullable=False)
    
    enrollment_date = Column(Date, nullable=False)
    status = Column(String(50), default='Registered')
    
    # RELACIONES
    student = relationship("User", back_populates="enrollments")
    section = relationship("Section", back_populates="enrollments")
    subject = relationship("Subject", back_populates="enrollments")

    # Restricción: Un alumno no puede inscribir la misma MATERIA en la misma SECCIÓN dos veces
    __table_args__ = (UniqueConstraint('student_user_id', 'section_id', 'subject_id', name='uq_student_section_subject'),)