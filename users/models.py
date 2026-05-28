from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from db import Base


class UserType(Base):
    __tablename__ = "user_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    users = relationship("User", back_populates="user_type")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    national_id = Column(String(15), unique=True, index=True)
    name = Column(String(50))
    last_name = Column(String(50))
    email = Column(String, unique=True, index=True)
    password = Column(String(100))
    user_type_id = Column(Integer, ForeignKey("user_types.id"), nullable=False, default=1)
    program_id = Column(Integer, ForeignKey("programs.program_id"), nullable=True)
    
    user_type = relationship("UserType", back_populates="users")
    program = relationship("Program", back_populates="students")
    enrollments = relationship("Enrollment", back_populates="student", foreign_keys="Enrollment.student_user_id")