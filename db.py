from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base 
from sqlalchemy.orm import relationship
from typing import Generator


Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    last_name = Column(String(50))
    email = Column(String, unique=True, index=True)
    password = Column(String(100))
    user_type_id = Column(Integer, ForeignKey("user_types.id"), nullable=False, default=1)
    user_type = relationship("UserType", back_populates="users")

    def __repr__(self):
        return f"User(id={self.id}, email='{self.email}', type_id={self.user_type_id})"


class UserType(Base):
    __tablename__ = "user_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    users = relationship("User", back_populates="user_type")

    def __repr__(self):
        return f"UserType(id={self.id}, name='{self.name}')"


DATABASE_URL = "sqlite:///./mydatabase.db"
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} 
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[SessionLocal, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()