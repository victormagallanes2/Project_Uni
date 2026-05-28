# scripts/create_fee_schedules.py

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import SessionLocal
from sqlalchemy import text

def create_fee_schedules():
    db = SessionLocal()
    
    # Obtener programas
    print("\n📋 Programas disponibles:")
    programs = db.execute(text("SELECT program_id, name FROM programs")).fetchall()
    for p in programs:
        print(f"   ID {p[0]}: {p[1]}")
    
    # Obtener conceptos
    concepts = db.execute(text("SELECT concept_id, code, name, amount_usd FROM fee_concepts")).fetchall()
    
    print("\n📋 Conceptos de pago:")
    for c in concepts:
        print(f"   {c[1]}: ${c[3]} - {c[2][:40]}...")
    
    # Conceptos específicos que necesitamos
    inscripcion = db.execute(text("SELECT concept_id FROM fee_concepts WHERE code = 'INS-001'")).first()
    uc_doctorado = db.execute(text("SELECT concept_id FROM fee_concepts WHERE code = 'UC-003'")).first()
    uc_maestria = db.execute(text("SELECT concept_id FROM fee_concepts WHERE code = 'UC-002'")).first()
    ingreso = db.execute(text("SELECT concept_id FROM fee_concepts WHERE code = 'ING-001'")).first()
    
    if not inscripcion:
        print("❌ Concepto INS-001 no encontrado")
        db.close()
        return
    
    print("\n📝 Creando tarifas por programa...")
    
    for program in programs:
        program_id = program[0]
        program_name = program[1]
        
        # Tarifa de inscripción para todos los programas
        db.execute(
            text("INSERT OR REPLACE INTO fee_schedules (concept_id, program_id, amount_usd) VALUES (:concept_id, :program_id, 20)"),
            {"concept_id": inscripcion[0], "program_id": program_id}
        )
        print(f"   ✅ {program_name[:35]}... - Inscripción: $20")
        
        # Tarifa de ingreso SEEA para todos
        if ingreso:
            db.execute(
                text("INSERT OR REPLACE INTO fee_schedules (concept_id, program_id, amount_usd) VALUES (:concept_id, :program_id, 180)"),
                {"concept_id": ingreso[0], "program_id": program_id}
            )
            print(f"   ✅ {program_name[:35]}... - Ingreso SEEA: $180")
        
        # Tarifa de UC según nivel
        if 'DOCTORADO' in program_name.upper() and uc_doctorado:
            db.execute(
                text("INSERT OR REPLACE INTO fee_schedules (concept_id, program_id, amount_usd) VALUES (:concept_id, :program_id, 5)"),
                {"concept_id": uc_doctorado[0], "program_id": program_id}
            )
            print(f"   ✅ {program_name[:35]}... - UC Doctorado: $5")
        
        elif ('MAESTRÍA' in program_name.upper() or 'MAESTRIA' in program_name.upper()) and uc_maestria:
            db.execute(
                text("INSERT OR REPLACE INTO fee_schedules (concept_id, program_id, amount_usd) VALUES (:concept_id, :program_id, 5)"),
                {"concept_id": uc_maestria[0], "program_id": program_id}
            )
            print(f"   ✅ {program_name[:35]}... - UC Maestría: $5")
    
    db.commit()
    
    # Verificar resultado
    result = db.execute(text("SELECT COUNT(*) FROM fee_schedules"))
    total = result.first()[0]
    print(f"\n✅ Total tarifas creadas: {total}")
    
    db.close()

if __name__ == "__main__":
    print("=" * 50)
    print("CREANDO TARIFAS POR PROGRAMA")
    print("=" * 50)
    create_fee_schedules()