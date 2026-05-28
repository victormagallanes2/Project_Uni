# scripts/insert_all_subjects.py

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import SessionLocal
from sqlalchemy import text

def insert_doctorado(db):
    """Inserta las materias del Doctorado"""
    
    result = db.execute(text("SELECT program_id FROM programs WHERE name LIKE '%DOCTORADO%'"))
    program = result.first()
    
    if not program:
        print("❌ Programa Doctorado no encontrado")
        return
    
    program_id = program[0]
    print(f"\n📚 Insertando materias de DOCTORADO...")
    
    materias = [
        (1, "60640", "Epistemología de las Ciencias Administrativas", 4),
        (1, "60641", "Métodos I (Cuantitativos)", 3),
        (1, "60644", "Problematización de las Ciencias Administrativas", 3),
        (2, "60643", "Tecnologías para el Manejo de la Información", 3),
        (2, "60642", "Métodos II (Cualitativos)", 3),
        (2, "60648", "Seminario de Investigación I", 4),
        (3, "60655", "Estudio Independiente I", 3),
        (3, "60656", "Estudio Independiente II", 3),
        (3, "60649", "Seminario de Investigación II", 4),
        (4, "60657", "Estudio Independiente III", 3),
        (4, "60658", "Estudio Independiente IV", 3),
        (4, "60650", "Seminario de Investigación III", 4),
        (5, "60659", "Estudio Independiente V", 3),
        (5, "60651", "Seminario de Grado", 4),
        (7, "60664", "Presentación y Defensa de la Tesis Doctoral", 10),
    ]
    
    for periodo, codigo, nombre, creditos in materias:
        db.execute(
            text("INSERT OR IGNORE INTO subjects (code, name, credits, program_id) VALUES (:code, :name, :credits, :program_id)"),
            {"code": codigo, "name": nombre, "credits": creditos, "program_id": program_id}
        )
        
        result = db.execute(text("SELECT subject_id FROM subjects WHERE code = :code"), {"code": codigo})
        subject = result.first()
        
        if subject:
            db.execute(
                text("INSERT OR IGNORE INTO program_subjects (program_id, subject_id, period_number, is_mandatory) VALUES (:program_id, :subject_id, :period_number, 1)"),
                {"program_id": program_id, "subject_id": subject[0], "period_number": periodo}
            )
            print(f"  ✅ {codigo} - {nombre} (Período {periodo})")
    
    db.commit()
    print(f"✅ Doctorado completado")

def insert_maestria_th(db):
    """Inserta las materias de Maestría en Gerencia del Talento Humano"""
    
    result = db.execute(text("SELECT program_id FROM programs WHERE name LIKE '%TALENTO HUMANO%'"))
    program = result.first()
    
    if not program:
        print("❌ Programa Maestría Talento Humano no encontrado")
        return
    
    program_id = program[0]
    print(f"\n📚 Insertando materias de MAESTRÍA TALENTO HUMANO...")
    
    materias = [
        (1, "MCATV 01", "Comprensión de la realidad Nacional, Latinoamericana y Mundial", 2),
        (1, "MCATV 02", "Ética de la Profesión", 3),
        (1, "MCATV 03", "Metodología de la Investigación", 3),
        (2, "MCATV19", "Seminario de Investigación I", 3),
        (2, "MCATV12", "ELECTIVA I: Principios de Gerencia", 2),
        (2, "MCATV 04", "Teoría y Nuevas Perspectivas de la Administración", 3),
        (3, "MCATV05", "Gerencia Estratégica del Talento Humano", 3),
        (3, "MCATV 20", "Seminario de Investigación II", 3),
        (3, "MCATV18", "ELECTIVA II: La Organización y La Cultura Laboral", 2),
        (3, "MCATV07", "Planificación y Desarrollo del Talento Humano", 3),
        (4, "MCATV21", "Seminario de Trabajo de Grado", 3),
        (4, "MCATV06", "Comportamiento Organizacional", 3),
        (4, "MCATV18", "ELECTIVA III: Construcción y Validación De Instrumentos", 2),
        (5, "MCAT V25", "Trabajo de Grado", 6),
    ]
    
    for periodo, codigo, nombre, creditos in materias:
        db.execute(
            text("INSERT OR IGNORE INTO subjects (code, name, credits, program_id) VALUES (:code, :name, :credits, :program_id)"),
            {"code": codigo, "name": nombre, "credits": creditos, "program_id": program_id}
        )
        
        result = db.execute(text("SELECT subject_id FROM subjects WHERE code = :code"), {"code": codigo})
        subject = result.first()
        
        if subject:
            db.execute(
                text("INSERT OR IGNORE INTO program_subjects (program_id, subject_id, period_number, is_mandatory) VALUES (:program_id, :subject_id, :period_number, 1)"),
                {"program_id": program_id, "subject_id": subject[0], "period_number": periodo}
            )
            print(f"  ✅ {codigo} - {nombre} (Período {periodo})")
    
    db.commit()
    print(f"✅ Maestría Talento Humano completado")

def insert_maestria_edu(db):
    """Inserta las materias de Maestría en Ciencias de la Educación"""
    
    result = db.execute(text("SELECT program_id FROM programs WHERE name LIKE '%EDUCACIÓN%'"))
    program = result.first()
    
    if not program:
        print("❌ Programa Maestría Educación no encontrado")
        return
    
    program_id = program[0]
    print(f"\n📚 Insertando materias de MAESTRÍA EDUCACIÓN...")
    
    materias = [
        (1, "MCEM01", "Comprensión de la Realidad Nacional Latinoamericana y Mundial", 2),
        (1, "MCEM02", "Ética de la profesión", 3),
        (1, "MCEM03", "Metodología de la Investigación", 3),
        (2, "MCEM04", "Teoría y Práctica de la Enseñanza", 3),
        (2, "MCEM05", "Procesos Socio afectivos", 3),
        (2, "MCEM17", "Seminario de Investigación I", 3),
        (3, "MCEM06", "Teoría y Modelos de Aprendizaje", 3),
        (3, "MCEM08", "Electiva I: Investigación Cualitativa", 2),
        (3, "MCEM18", "Seminario de Investigación II", 3),
        (4, "MCEM07", "Teorías Curriculares", 3),
        (4, "MCEM14", "Electiva II: Investigación Acción participativa (IAP)", 2),
        (4, "MCEM19", "Seminario de Trabajo de Grado", 3),
        (5, "MCEM12", "Electiva III: Intervención Comunitaria", 2),
        (6, "MCEM22", "Trabajo de Grado", 6),
    ]
    
    for periodo, codigo, nombre, creditos in materias:
        db.execute(
            text("INSERT OR IGNORE INTO subjects (code, name, credits, program_id) VALUES (:code, :name, :credits, :program_id)"),
            {"code": codigo, "name": nombre, "credits": creditos, "program_id": program_id}
        )
        
        result = db.execute(text("SELECT subject_id FROM subjects WHERE code = :code"), {"code": codigo})
        subject = result.first()
        
        if subject:
            db.execute(
                text("INSERT OR IGNORE INTO program_subjects (program_id, subject_id, period_number, is_mandatory) VALUES (:program_id, :subject_id, :period_number, 1)"),
                {"program_id": program_id, "subject_id": subject[0], "period_number": periodo}
            )
            print(f"  ✅ {codigo} - {nombre} (Período {periodo})")
    
    db.commit()
    print(f"✅ Maestría Educación completado")

def main():
    db = SessionLocal()
    
    print("=" * 50)
    print("INSERTANDO TODAS LAS MATERIAS")
    print("=" * 50)
    
    # Mostrar programas existentes
    result = db.execute(text("SELECT program_id, name FROM programs"))
    print("\n📋 Programas encontrados:")
    for row in result:
        print(f"   ID {row[0]}: {row[1]}")
    
    insert_doctorado(db)
    insert_maestria_th(db)
    insert_maestria_edu(db)
    
    # Resumen final
    result = db.execute(text("SELECT COUNT(*) FROM subjects"))
    total_materias = result.first()[0]
    result = db.execute(text("SELECT COUNT(*) FROM program_subjects"))
    total_asignaciones = result.first()[0]
    
    print(f"\n📊 RESUMEN FINAL:")
    print(f"   Total materias: {total_materias}")
    print(f"   Total asignaciones programa-materia: {total_asignaciones}")
    
    db.close()
    print("\n🎉 PROCESO COMPLETADO")

if __name__ == "__main__":
    main()