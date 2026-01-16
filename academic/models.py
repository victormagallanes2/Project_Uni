from sqlalchemy import Column, Integer, String, ForeignKey, Date, DECIMAL, UniqueConstraint
from sqlalchemy.orm import relationship
from db import Base


class Program(Base):
    __tablename__ = 'programs'
    program_id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False, unique=True) # Ej: DOCTORADO EN CIENCIAS ADMINISTRATIVAS
    level = Column(String(50), nullable=False) # 'Doctorado', 'Maestría', 'Postgrado'
    total_credits = Column(Integer)
    subjects = relationship("Subject", back_populates="program")
    students = relationship("User", back_populates="program")

class Subject(Base):
    __tablename__ = 'subjects' # La tabla para las Materias
    subject_id = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey('programs.program_id'), nullable=False)
    code = Column(String(15), unique=True, nullable=False) # Código de la Materia (Ej: 60640, MCEM01)
    name = Column(String(150), nullable=False)
    credits = Column(Integer, nullable=False) # Unidades de Crédito (UC)
    
    program = relationship("Program", back_populates="subjects")
    sections = relationship("SectionSubject", back_populates="subject")
    enrollments = relationship("Enrollment", back_populates="subject")

class AcademicTerm(Base):
    __tablename__ = 'academic_terms'
    term_id = Column(Integer, primary_key=True)
    name = Column(String(25), nullable=False, unique=True) # Ej: '2025-I', '2024-II'
    start_date = Column(Date, nullable=False) # Inicio de clases
    end_date = Column(Date, nullable=False) # Fin de clases
    
    # Control de la OFERTA DE INSCRIPCIÓN (lo que habilita el Proceso 1)
    enrollment_start_date = Column(Date)
    enrollment_end_date = Column(Date)
    
    sections = relationship("Section", back_populates="term")

class Section(Base):
    __tablename__ = 'sections'
    section_id = Column(Integer, primary_key=True)
    term_id = Column(Integer, ForeignKey('academic_terms.term_id'), nullable=False)
    section_code = Column(String(20), unique=True, nullable=False)
    capacity = Column(Integer, nullable=False, default=30) 
    term = relationship("AcademicTerm", back_populates="sections")
    subjects = relationship("SectionSubject", back_populates="section")
    enrollments = relationship("Enrollment", back_populates="section")


class SectionSubject(Base):
    """ Esta tabla vincula qué materias se ven en qué sección """
    __tablename__ = 'section_subjects'
    id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey('sections.section_id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.subject_id'), nullable=False)
    professor_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # RELACIONES
    section = relationship("Section", back_populates="subjects")
    subject = relationship("Subject", back_populates="sections")
    professor = relationship("User")


class Prerequisite(Base):
    __tablename__ = 'prerequisites'
    main_subject_id = Column(Integer, ForeignKey('subjects.subject_id'), primary_key=True)
    required_subject_id = Column(Integer, ForeignKey('subjects.subject_id'), primary_key=True)
    type = Column(String(50))
    
    main_subject = relationship("Subject", foreign_keys=[main_subject_id])
    required_subject = relationship("Subject", foreign_keys=[required_subject_id])