from sqlalchemy import Column, String, Integer, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from db import Base

class Enrollment(Base):
    __tablename__ = 'enrollments'
    enrollment_id = Column(Integer, primary_key=True)
    student_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    cohort_id = Column(Integer, ForeignKey('cohorts.cohort_id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.subject_id'), nullable=False)
    term_id = Column(Integer, ForeignKey('academic_terms.term_id'), nullable=False)
    
    enrollment_date = Column(Date, nullable=False)
    status = Column(String(50), default='Registered')
    
    student = relationship("User", back_populates="enrollments", foreign_keys=[student_user_id])
    cohort = relationship("Cohort", back_populates="enrollments")
    subject = relationship("Subject", back_populates="enrollments")
    term = relationship("AcademicTerm")

    __table_args__ = (UniqueConstraint('student_user_id', 'cohort_id', 'subject_id', 'term_id', 
                                       name='uq_student_cohort_subject_term'),)