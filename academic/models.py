from sqlalchemy import Column, Integer, String, ForeignKey, Date, DECIMAL, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from db import Base


class Program(Base):
    __tablename__ = 'programs'
    program_id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False, unique=True)
    level = Column(String(50), nullable=False)
    total_credits = Column(Integer)
    
    subjects = relationship("Subject", back_populates="program")
    students = relationship("User", back_populates="program")
    cohorts = relationship("Cohort", back_populates="program")


class Subject(Base):
    __tablename__ = 'subjects'
    subject_id = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey('programs.program_id'), nullable=False)
    code = Column(String(15), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    credits = Column(Integer, nullable=False)
    
    program = relationship("Program", back_populates="subjects")
    enrollments = relationship("Enrollment", back_populates="subject")


class AcademicTerm(Base):
    __tablename__ = 'academic_terms'
    term_id = Column(Integer, primary_key=True)
    name = Column(String(25), nullable=False, unique=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    enrollment_start_date = Column(Date)
    enrollment_end_date = Column(Date)
    
    cohorts = relationship("Cohort", back_populates="term")


class Cohort(Base):
    """Grupo de estudiantes que cursan juntos"""
    __tablename__ = 'cohorts'
    
    cohort_id = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey('programs.program_id'), nullable=False)
    term_id = Column(Integer, ForeignKey('academic_terms.term_id'), nullable=False)
    cohort_code = Column(String(20), unique=True, nullable=False)
    capacity = Column(Integer, nullable=False, default=30)
    current_enrollment = Column(Integer, default=0)
    
    program = relationship("Program", back_populates="cohorts")
    term = relationship("AcademicTerm", back_populates="cohorts")
    enrollments = relationship("Enrollment", back_populates="cohort")


class Prerequisite(Base):
    __tablename__ = 'prerequisites'
    main_subject_id = Column(Integer, ForeignKey('subjects.subject_id'), primary_key=True)
    required_subject_id = Column(Integer, ForeignKey('subjects.subject_id'), primary_key=True)
    type = Column(String(50))
    
    main_subject = relationship("Subject", foreign_keys=[main_subject_id])
    required_subject = relationship("Subject", foreign_keys=[required_subject_id])


class ProgramSubject(Base):
    __tablename__ = 'program_subjects'
    id = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey('programs.program_id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.subject_id'), nullable=False)
    period_number = Column(Integer, nullable=False)
    is_elective = Column(Boolean, default=False)
    is_mandatory = Column(Boolean, default=True)
    
    program = relationship("Program")
    subject = relationship("Subject")


class StudentGrade(Base):
    __tablename__ = 'student_grades'
    grade_id = Column(Integer, primary_key=True)
    student_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.subject_id'), nullable=False)
    term_id = Column(Integer, ForeignKey('academic_terms.term_id'), nullable=False)
    grade = Column(String(5))
    numeric_grade = Column(DECIMAL(5,2))
    status = Column(String(20), default='In Progress')
    approval_date = Column(Date)
    
    student = relationship("User", foreign_keys=[student_user_id])
    subject = relationship("Subject")
    term = relationship("AcademicTerm")