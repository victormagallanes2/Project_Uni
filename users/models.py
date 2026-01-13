from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    national_id = Column(String(15), unique=True, index=True)
    name = Column(String(50))
    last_name = Column(String(50))
    email = Column(String, unique=True, index=True)
    password = Column(String(100))
    user_type_id = Column(Integer, ForeignKey("user_types.id"), nullable=False, default=1)
    user_type = relationship("UserType", back_populates="users")
    enrollments = relationship("Enrollment", back_populates="student")

    def __repr__(self):
        return f"User(id={self.id}, email='{self.email}', type_id={self.user_type_id})"


class UserType(Base):
    __tablename__ = "user_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    users = relationship("User", back_populates="user_type")

    def __repr__(self):
        return f"UserType(id={self.id}, name='{self.name}')"