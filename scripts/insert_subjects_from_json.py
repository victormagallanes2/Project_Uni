# scripts/insert_subjects_from_json.py

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from db import SessionLocal

def insert_doctorado(db):
    """Inserta las materias del Doctorado"""
    
    result = db.execute(text("SELECT program_id, name FROM programs WHERE name LIKE '%DOCTORADO%'"))
    program = result.first()
    
    if not program:
        print("❌ Programa Doctorado no encontrado")
        return
    
    program_id = program[0]
    print(f"📚 Insertando materias para: {program[1]}")
    
    materias_doctorado = [
        # Período 1
        {"codigo": "60640", "nombre": "Epistemología de las Ciencias Administrativas", "creditos": 4, "periodo": 1},
        {"codigo": "60641", "nombre": "Métodos I (Cuantitativos)", "creditos": 3, "periodo": 1},
        {"codigo": "60644", "nombre": "Problematización de las Ciencias Administrativas", "creditos": 3, "periodo": 1},
        # Período 2
        {"codigo": "60643", "nombre": "Tecnologías para el Manejo de la Información", "creditos": 3, "periodo": 2},
        {"codigo": "60642", "nombre": "Métodos II (Cualitativos)", "creditos": 3, "periodo": 2},
        {"codigo": "60648", "nombre": "Seminario de Investigación I", "creditos": 4, "periodo": 2},
        # Período 3
        {"codigo": "60655", "nombre": "Estudio Independiente I", "creditos": 3, "periodo": 3},
        {"codigo": "60656", "nombre": "Estudio Independiente II", "creditos": 3, "periodo": 3},
        {"codigo": "60649", "nombre": "Seminario de Investigación II", "creditos": 4, "periodo": 3},
        # Período 4
        {"codigo": "60657", "nombre": "Estudio Independiente III", "creditos": 3, "periodo": 4},
        {"codigo": "60658", "nombre": "Estudio Independiente IV", "creditos": 3, "periodo": 4},
        {"codigo": "60650", "nombre": "Seminario de Investigación III", "creditos": 4, "periodo": 4},
        # Período 5
        {"codigo": "60659", "nombre": "Estudio Independiente V", "creditos": 3, "periodo": 5},
        {"codigo": "60651", "nombre": "Seminario de Grado", "creditos": 4, "periodo": 5},
        # Período 7
        {"codigo": "60664", "nombre": "Presentación y Defensa de la Tesis Doctoral", "creditos": 10, "periodo": 7},
    ]
    
    # Limpiar relaciones existentes para este programa
    db.execute(text("DELETE FROM program_subjects WHERE program_id = :program_id"), {"program_id": program_id})
    
    for materia in materias_doctorado:
        result = db.execute(text("SELECT subject_id FROM subjects WHERE code = :code"), {"code": materia["codigo"]})
        subject = result.first()
        
        if not subject:
            db.execute(
                text("INSERT INTO subjects (code, name, credits, program_id) VALUES (:code, :name, :credits, :program_id)"),
                {"code": materia["codigo"], "name": materia["nombre"], "credits": materia["creditos"], "program_id": program_id}
            )
            db.flush()
            subject_id = db.execute(text("SELECT last_insert_rowid()")).scalar()
            print(f"  ✅ Creada: {materia['codigo']} - {materia['nombre']}")
        else:
            subject_id = subject[0]
            print(f"  ⏭️ Ya existe: {materia['codigo']}")
        
        db.execute(
            text("INSERT INTO program_subjects (program_id, subject_id, period_number, is_mandatory) VALUES (:program_id, :subject_id, :period_number, 1)"),
            {"program_id": program_id, "subject_id": subject_id, "period_number": materia["periodo"]}
        )
    
    db.commit()
    print(f"✅ Doctorado completado\n")

def insert_maestria_administracion(db):
    """Inserta las materias de la Maestría en Administración"""
    
    result = db.execute(text("SELECT program_id, name FROM programs WHERE name LIKE '%Maestria en administracion%'"))
    program = result.first()
    
    if not program:
        print("❌ Programa Maestría en Administración no encontrado")
        return
    
    program_id = program[0]
    print(f"📚 Insertando materias para: {program[1]}")
    
    materias = [
        # Período 1
        {"codigo": "ADM01", "nombre": "Gerencia Estratégica", "creditos": 3, "periodo": 1},
        {"codigo": "ADM02", "nombre": "Metodología de la Investigación", "creditos": 3, "periodo": 1},
        {"codigo": "ADM03", "nombre": "Ética Empresarial", "creditos": 2, "periodo": 1},
        # Período 2
        {"codigo": "ADM04", "nombre": "Gestión del Talento Humano", "creditos": 3, "periodo": 2},
        {"codigo": "ADM05", "nombre": "Finanzas Corporativas", "creditos": 3, "periodo": 2},
        {"codigo": "ADM06", "nombre": "Marketing Estratégico", "creditos": 3, "periodo": 2},
        # Período 3
        {"codigo": "ADM07", "nombre": "Seminario de Investigación", "creditos": 3, "periodo": 3},
        {"codigo": "ADM08", "nombre": "Trabajo de Grado", "creditos": 6, "periodo": 3},
    ]
    
    # Limpiar relaciones existentes para este programa
    db.execute(text("DELETE FROM program_subjects WHERE program_id = :program_id"), {"program_id": program_id})
    
    for materia in materias:
        result = db.execute(text("SELECT subject_id FROM subjects WHERE code = :code"), {"code": materia["codigo"]})
        subject = result.first()
        
        if not subject:
            db.execute(
                text("INSERT INTO subjects (code, name, credits, program_id) VALUES (:code, :name, :credits, :program_id)"),
                {"code": materia["codigo"], "name": materia["nombre"], "credits": materia["creditos"], "program_id": program_id}
            )
            db.flush()
            subject_id = db.execute(text("SELECT last_insert_rowid()")).scalar()
            print(f"  ✅ Creada: {materia['codigo']} - {materia['nombre']}")
        else:
            subject_id = subject[0]
            print(f"  ⏭️ Ya existe: {materia['codigo']}")
        
        db.execute(
            text("INSERT INTO program_subjects (program_id, subject_id, period_number, is_mandatory) VALUES (:program_id, :subject_id, :period_number, 1)"),
            {"program_id": program_id, "subject_id": subject_id, "period_number": materia["periodo"]}
        )
    
    db.commit()
    print(f"✅ Maestría en Administración completado\n")

def main():
    db = SessionLocal()
    
    print("=" * 50)
    print("INSERTANDO MATERIAS DESDE DOCUMENTOS")
    print("=" * 50)
    
    print("\n📋 Programas encontrados en la base de datos:")
    for p in db.execute(text("SELECT program_id, name FROM programs")).fetchall():
        print(f"  ID: {p[0]} - {p[1]}")
    
    print("\n")
    
    insert_doctorado(db)
    insert_maestria_administracion(db)
    
    # Verificar resultados
    print("\n📊 Verificando resultados:")
    
    # Contar materias por programa
    result = db.execute(text("""
        SELECT p.name, COUNT(s.subject_id) as total_materias
        FROM programs p
        LEFT JOIN subjects s ON s.program_id = p.program_id
        GROUP BY p.program_id
    """))
    for row in result:
        print(f"  {row[0]}: {row[1]} materias")
    
    # Contar relaciones program_subjects
    result = db.execute(text("""
        SELECT p.name, COUNT(ps.id) as total_asignaciones
        FROM programs p
        LEFT JOIN program_subjects ps ON ps.program_id = p.program_id
        GROUP BY p.program_id
    """))
    for row in result:
        print(f"  {row[0]}: {row[1]} materias asignadas a períodos")
    
    db.commit()
    db.close()
    print("\n🎉 PROCESO COMPLETADO")

if __name__ == "__main__":
    main()