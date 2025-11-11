from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base 
from typing import Generator

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String(100)) 

    def __repr__(self):
        return f"User(id={self.id}, email='{self.email}')"


DATABASE_URL = "sqlite:///./mydatabase.db"
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} 
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



def create_tables():
    """Crea todas las tablas definidas en Base.metadata."""
    Base.metadata.create_all(bind=engine)

def get_db() -> Generator[SessionLocal, None, None]:
    """
    Función de dependencia para obtener una sesión de base de datos.
    Abre una sesión y garantiza que se cierre al finalizar.
    """
    db = SessionLocal()
    try:
        # 'yield db' permite que la sesión se use dentro de la lógica de la aplicación
        yield db
    finally:
        # Se asegura de que la sesión se cierre, liberando recursos.
        db.close()

# -----------------------------------------------------------
# 4. INICIALIZACIÓN (Opcional, ejecutar solo una vez)
# -----------------------------------------------------------

# Descomenta la siguiente línea y ejecuta este archivo ('python db.py') 
# UNA SOLA VEZ para crear el archivo 'mydatabase.db' antes de iniciar la app.
# create_tables()