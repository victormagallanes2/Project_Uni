# scripts/import_fees.py

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import SessionLocal
from sqlalchemy import text

def import_fee_concepts():
    db = SessionLocal()
    
    concepts_data = [
        ("ING-001", "INGRESO AL SISTEMA DE ESTUDIOS Y EXPERIENCIA ACREDITABLES (SEEA)", 180, "INGRESO"),
        ("ING-002", "ASESORIAS / TUTORIAS / COORDINACIÓN DE APRENDIZAJE", 30, "INGRESO"),
        ("PRE-001", "PREINSCRIPCIÓN DE PROGRAMAS REGULARES CONDUCENTES A GRADOS", 10, "PREINSCRIPCION"),
        ("REI-001", "REINGRESOS POSTGRADO Y EDUCACIÓN AVANZADA", 30, "REINGRESO"),
        ("INS-001", "INSCRIPCIONES EN PROGRAMAS CONDUCENTES A GRADO ACADÉMICO", 20, "INSCRIPCION"),
        ("INS-002", "RECARGO POR INSCRIPCIÓN FUERA DE LAPSO", 20, "INSCRIPCION"),
        ("INS-003", "SEMINARIO DE INDUCCIÓN", 10, "INSCRIPCION"),
        ("INS-004", "RENOVACIÓN DE INSCRIPCIÓN (REGULAR)", 5, "INSCRIPCION"),
        ("TEG-001", "INSCRIPCIÓN TRABAJO ESPECIAL DE GRADO ESPECIALIZACIÓN", 10, "TRABAJO_GRADO"),
        ("TEG-002", "INSCRIPCIÓN TRABAJO DE GRADO MAESTRÍA", 10, "TRABAJO_GRADO"),
        ("TEG-003", "INSCRIPCIÓN TESIS DOCTORAL", 10, "TRABAJO_GRADO"),
        ("UC-001", "UNIDAD CRÉDITO DE ESPECIALIZACIÓN", 5, "UC"),
        ("UC-002", "UNIDAD CRÉDITO DE MAESTRÍA", 5, "UC"),
        ("UC-003", "UNIDAD CRÉDITO DE DOCTORADO", 5, "UC"),
        ("ACR-001", "ACREDITACIÓN: EVALUACIÓN DE EXPEDIENTE, CONSTANCIA, REPORTE Y DICTAMEN", 200, "ACREDITACION"),
        ("TUT-001", "ASESORÍAS- TUTURÍAS ESPECIALIZACIÓN", 30, "TUTORIA"),
        ("TUT-002", "ASESORÍAS- TUTORÍAS MAESTRÍAS", 30, "TUTORIA"),
        ("TUT-003", "ASESORÍAS - TUTORÍAS DOCTORADO", 50, "TUTORIA"),
        ("DEF-001", "DEFENSA DE TRABAJO DE GRADO - SEEA", 10, "DEFENSA"),
        ("DEF-002", "DEFENSA DE TRABAJO DE GRADO Y TESIS DOCTORAL", 30, "DEFENSA"),
        ("GRA-001", "DERECHO A GRADO", 50, "DERECHO_GRADO"),
    ]
    
    print("📝 Importando conceptos de aranceles...")
    
    for code, name, amount, category in concepts_data:
        result = db.execute(text("SELECT concept_id FROM fee_concepts WHERE code = :code"), {"code": code})
        existing = result.first()
        
        if not existing:
            db.execute(
                text("""
                    INSERT INTO fee_concepts (code, name, amount_usd, category, requires_verification) 
                    VALUES (:code, :name, :amount, :category, 1)
                """),
                {"code": code, "name": name, "amount": amount, "category": category}
            )
            print(f"  ✅ Agregado: {code} - ${amount}")
        else:
            db.execute(
                text("UPDATE fee_concepts SET amount_usd = :amount WHERE code = :code"),
                {"code": code, "amount": amount}
            )
            print(f"  ⏭️ Actualizado: {code} - ${amount}")
    
    db.commit()
    print(f"\n✅ Total conceptos: {len(concepts_data)}")
    db.close()

def create_fee_schedules():
    db = SessionLocal()
    
    result = db.execute(text("SELECT program_id, name FROM programs"))
    programs = result.fetchall()
    
    print("\n📝 Programas disponibles:")
    for p in programs:
        print(f"   ID {p[0]}: {p[1]}")
    
    # Obtener conceptos
    inscripcion = db.execute(text("SELECT concept_id FROM fee_concepts WHERE code = 'INS-001'")).first()
    uc_doctorado = db.execute(text("SELECT concept_id FROM fee_concepts WHERE code = 'UC-003'")).first()
    uc_maestria = db.execute(text("SELECT concept_id FROM fee_concepts WHERE code = 'UC-002'")).first()
    
    if not inscripcion:
        print("❌ Concepto INS-001 no encontrado")
        db.close()
        return
    
    print("\n📝 Creando schedules de pago...")
    
    for program in programs:
        program_id = program[0]
        program_name = program[1]
        
        if inscripcion:
            db.execute(
                text("""
                    INSERT OR REPLACE INTO fee_schedules (concept_id, program_id, amount_usd) 
                    VALUES (:concept_id, :program_id, 20)
                """),
                {"concept_id": inscripcion[0], "program_id": program_id}
            )
            print(f"  ✅ {program_name[:40]}... - Inscripción: $20")
        
        if 'DOCTORADO' in program_name.upper() and uc_doctorado:
            db.execute(
                text("""
                    INSERT OR REPLACE INTO fee_schedules (concept_id, program_id, amount_usd) 
                    VALUES (:concept_id, :program_id, 5)
                """),
                {"concept_id": uc_doctorado[0], "program_id": program_id}
            )
            print(f"  ✅ {program_name[:40]}... - UC: $5")
        
        elif ('MAESTRÍA' in program_name.upper() or 'MAESTRIA' in program_name.upper()) and uc_maestria:
            db.execute(
                text("""
                    INSERT OR REPLACE INTO fee_schedules (concept_id, program_id, amount_usd) 
                    VALUES (:concept_id, :program_id, 5)
                """),
                {"concept_id": uc_maestria[0], "program_id": program_id}
            )
            print(f"  ✅ {program_name[:40]}... - UC: $5")
    
    db.commit()
    db.close()
    print("\n✅ Schedules creados")

if __name__ == "__main__":
    print("=" * 50)
    print("IMPORTANDO ARANCELES")
    print("=" * 50)
    import_fee_concepts()
    create_fee_schedules()