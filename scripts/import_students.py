# scripts/import_students.py

import sys
import os
import bcrypt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import SessionLocal
from sqlalchemy import text

# Datos extraídos de LISTAS DE PARTICIPANTES.pdf
DOCTORADO_STUDENTS = [
    (4.764276, "Julio Simón", "Duarte Ugueto"),
    (7.207661, "Janeth Iraida", "Arias Murillo"),
    (7.213217, "Adan Enrique", "Camarillo Millano"),
    (7.215237, "Maria Eugenia", "Zapata"),
    (7.256084, "Juan José", "Gónzalez Perdomo"),
    (7.260246, "Luis Fernando", "Hurtado Dovale"),
    (8.672116, "Pedro Jesús", "Ochoa Guerrero"),
    (9.438443, "Julio Rafael", "Sanoja Laguado"),
    (9.654843, "Edgar Alberto", "Crespo Gutierrez"),
    (9.658531, "Yajindi Canaán", "Bastidas Angarita"),
    (9.674497, "Felix Enrique", "Serrano Trujillo"),
    (9.692423, "Yelitza Leonor", "Amarista de Durán"),
    (10.752084, "José Felipe", "Cabeza"),
    (11.181058, "Eysbell Esthela", "Carrasquel Pérez"),
    (11.503601, "Katiuska Karin", "Ochoa Chacón"),
    (11.988333, "Maritza Alexandra", "Pérez Pinto"),
    (12.477137, "Carmén Luisa", "Hernández Díaz"),
    (13.518997, "Jenny Del Mar", "Salom Salazar"),
    (12.567446, "Yurima Nohemi", "Gonzalez Bolivar"),
    (14.492788, "Ana Yormedis", "Martinez Oleaga"),
    (14.578588, "Millers Manuel", "Calle Mejias"),
    (14.959875, "Verónica", "Navarrete Blanco"),
    (14.691781, "Pedro Luis", "Gonzalez Rivera"),
    (16.128480, "Freddy José", "Sevilla Muñoz"),
    (16.763656, "Flor Cecilia", "Castillo Ordoñez"),
    (17.274698, "Dario José", "Maldonado Crain"),
    (17.426593, "Javier Eduardo", "Rivas"),
    (17.470525, "Yelitza Esther", "Toro Figueredo"),
    (18.693241, "Albis Nohelis", "Uzcategui Velasquez"),
    (20.056031, "Blanco Rojas", "Blanco Gamalier"),
    (23.792041, "José Atilio", "D'Elia González"),
    (25.850671, "Julier Joseph", "Reimi Mijares"),
    (20.334520, "Josmary Alejandra", "Rodríguez Martinez"),
]

def import_students():
    db = SessionLocal()
    
    # Verificar tipo de usuario Alumno
    result = db.execute(text("SELECT id FROM user_types WHERE id = 4"))
    student_type = result.first()
    
    if not student_type:
        print("❌ Tipo de usuario 'Alumno' (ID 4) no encontrado")
        db.close()
        return
    
    total_imported = 0
    total_skipped = 0
    
    print("\n📚 Importando estudiantes de DOCTORADO...")
    for national_id, name, last_name in DOCTORADO_STUDENTS:
        national_id_str = str(int(national_id)) if '.' not in str(national_id) else str(national_id)
        
        result = db.execute(text("SELECT id FROM users WHERE national_id = :national_id"), {"national_id": national_id_str})
        existing = result.first()
        
        if not existing:
            email = f"{name.lower()}.{last_name.lower()}@unesr.edu.ve".replace(" ", "").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            temp_password = national_id_str.replace(".", "")
            hashed = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            db.execute(
                text("""
                    INSERT INTO users (national_id, name, last_name, email, password, user_type_id) 
                    VALUES (:national_id, :name, :last_name, :email, :password, :user_type_id)
                """),
                {"national_id": national_id_str, "name": name, "last_name": last_name, "email": email, "password": hashed, "user_type_id": 4}
            )
            total_imported += 1
            print(f"  ✅ {name} {last_name} - {national_id_str}")
        else:
            total_skipped += 1
    
    db.commit()
    
    print(f"\n📊 Resumen:")
    print(f"   ✅ Importados: {total_imported} estudiantes")
    print(f"   ⏭️ Omitidos: {total_skipped}")
    
    db.close()

if __name__ == "__main__":
    print("=" * 50)
    print("IMPORTANDO ESTUDIANTES")
    print("=" * 50)
    import_students()