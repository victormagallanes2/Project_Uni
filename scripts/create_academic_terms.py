# scripts/create_academic_terms.py

import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import SessionLocal
from sqlalchemy import text

def create_academic_terms():
    db = SessionLocal()
    
    # Definir períodos según la comunidad
    # Febrero-junio (Período 1) y Octubre-diciembre (Período 2)
    
    terms_data = [
        # Año 2025
        {"name": "2025-1", "start_date": "2025-02-01", "end_date": "2025-06-30", 
         "enrollment_start": "2025-01-15", "enrollment_end": "2025-01-31"},
        {"name": "2025-2", "start_date": "2025-10-01", "end_date": "2025-12-20", 
         "enrollment_start": "2025-09-15", "enrollment_end": "2025-09-30"},
        
        # Año 2026
        {"name": "2026-1", "start_date": "2026-02-01", "end_date": "2026-06-30", 
         "enrollment_start": "2026-01-15", "enrollment_end": "2026-01-31"},
        {"name": "2026-2", "start_date": "2026-10-01", "end_date": "2026-12-20", 
         "enrollment_start": "2026-09-15", "enrollment_end": "2026-09-30"},
        
        # Año 2027
        {"name": "2027-1", "start_date": "2027-02-01", "end_date": "2027-06-30", 
         "enrollment_start": "2027-01-15", "enrollment_end": "2027-01-31"},
        {"name": "2027-2", "start_date": "2027-10-01", "end_date": "2027-12-20", 
         "enrollment_start": "2027-09-15", "enrollment_end": "2027-09-30"},
        
        # Año 2028
        {"name": "2028-1", "start_date": "2028-02-01", "end_date": "2028-06-30", 
         "enrollment_start": "2028-01-15", "enrollment_end": "2028-01-31"},
        {"name": "2028-2", "start_date": "2028-10-01", "end_date": "2028-12-20", 
         "enrollment_start": "2028-09-15", "enrollment_end": "2028-09-30"},
        
        # Año 2029
        {"name": "2029-1", "start_date": "2029-02-01", "end_date": "2029-06-30", 
         "enrollment_start": "2029-01-15", "enrollment_end": "2029-01-31"},
        {"name": "2029-2", "start_date": "2029-10-01", "end_date": "2029-12-20", 
         "enrollment_start": "2029-09-15", "enrollment_end": "2029-09-30"},
        
        # Año 2030
        {"name": "2030-1", "start_date": "2030-02-01", "end_date": "2030-06-30", 
         "enrollment_start": "2030-01-15", "enrollment_end": "2030-01-31"},
        {"name": "2030-2", "start_date": "2030-10-01", "end_date": "2030-12-20", 
         "enrollment_start": "2030-09-15", "enrollment_end": "2030-09-30"},
    ]
    
    print("📅 Creando períodos académicos...")
    
    for term in terms_data:
        existing = db.execute(
            text("SELECT term_id FROM academic_terms WHERE name = :name"),
            {"name": term["name"]}
        ).first()
        
        if not existing:
            db.execute(
                text("""
                    INSERT INTO academic_terms 
                    (name, start_date, end_date, enrollment_start_date, enrollment_end_date) 
                    VALUES (:name, :start_date, :end_date, :enrollment_start, :enrollment_end)
                """),
                {
                    "name": term["name"],
                    "start_date": term["start_date"],
                    "end_date": term["end_date"],
                    "enrollment_start": term["enrollment_start"],
                    "enrollment_end": term["enrollment_end"]
                }
            )
            print(f"  ✅ Creado: {term['name']} ({term['start_date']} al {term['end_date']})")
        else:
            print(f"  ⏭️ Ya existe: {term['name']}")
    
    db.commit()
    
    # Verificar resultado
    result = db.execute(text("SELECT COUNT(*) FROM academic_terms"))
    total = result.first()[0]
    print(f"\n✅ Total períodos académicos: {total}")
    
    db.close()

if __name__ == "__main__":
    print("=" * 50)
    print("CREANDO PERÍODOS ACADÉMICOS")
    print("=" * 50)
    create_academic_terms()