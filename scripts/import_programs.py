# scripts/import_programs.py

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import SessionLocal
from sqlalchemy import text

def import_programs():
    db = SessionLocal()
    
    programs_data = [
        ("DOCTORADO EN CIENCIAS ADMINISTRATIVAS", "Doctorado", 55),
        ("MAESTRÍA EN CIENCIAS ADMINISTRATIVAS MENCIÓN: GERENCIA DEL TALENTO HUMANO", "Maestría", 41),
        ("MAESTRÍA EN CIENCIAS DE LA EDUCACIÓN", "Maestría", 41),
    ]
    
    print("📝 Importando programas académicos...")
    
    for name, level, total_credits in programs_data:
        result = db.execute(text("SELECT program_id FROM programs WHERE name = :name"), {"name": name})
        existing = result.first()
        
        if not existing:
            db.execute(
                text("""
                    INSERT INTO programs (name, level, total_credits) 
                    VALUES (:name, :level, :total_credits)
                """),
                {"name": name, "level": level, "total_credits": total_credits}
            )
            print(f"  ✅ Agregado: {name}")
        else:
            print(f"  ⏭️ Ya existe: {name}")
    
    db.commit()
    db.close()
    print("\n✅ Programas importados")

if __name__ == "__main__":
    print("=" * 50)
    print("IMPORTANDO PROGRAMAS")
    print("=" * 50)
    import_programs()