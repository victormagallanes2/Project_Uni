# scripts/backup_users.py

import sqlite3
import json
import os

# Ruta: el JSON se guardará en la misma carpeta que el script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_PATH = os.path.join(SCRIPT_DIR, 'backup_users.json')
DB_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), 'mydatabase.db')  # BD en la raíz

def backup_users():
    """Exporta usuarios y tipos a un archivo JSON"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Base de datos no encontrada en {DB_PATH}")
        return None
    
    print(f"📂 Usando base de datos: {DB_PATH}")
    print(f"📂 Backup se guardará en: {BACKUP_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verificar qué tablas existen
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\n📋 Tablas encontradas: {tables}")
    
    # Detectar nombre correcto
    type_table = None
    if 'user_types' in tables:
        type_table = 'user_types'
    elif 'user_type' in tables:
        type_table = 'user_type'
    else:
        print("❌ No se encontró la tabla de tipos de usuario")
        conn.close()
        return None
    
    print(f"✅ Usando tabla: {type_table}")
    
    # Backup de tipos de usuario
    cursor.execute(f"SELECT id, name FROM {type_table}")
    user_types = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    
    # Backup de usuarios
    if 'users' in tables:
        cursor.execute("""
            SELECT id, national_id, name, last_name, email, password, user_type_id, program_id 
            FROM users
        """)
        users = []
        for row in cursor.fetchall():
            users.append({
                "id": row[0],
                "national_id": row[1],
                "name": row[2],
                "last_name": row[3],
                "email": row[4],
                "password": row[5],
                "user_type_id": row[6],
                "program_id": row[7] if len(row) > 7 else None
            })
    else:
        users = []
    
    # Guardar backup
    backup_data = {
        "type_table_name": type_table,
        "user_types": user_types,
        "users": users
    }
    
    with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Backup creado en '{BACKUP_PATH}':")
    print(f"   - {len(user_types)} tipos de usuario")
    print(f"   - {len(users)} usuarios")
    
    conn.close()
    return backup_data

if __name__ == "__main__":
    print("=" * 50)
    print("BACKUP DE USUARIOS")
    print("=" * 50)
    backup_users()