# scripts/restore_users.py

import sqlite3
import json
import os
import sys

# Ruta: el JSON está en la misma carpeta que el script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_PATH = os.path.join(SCRIPT_DIR, 'backup_users.json')
DB_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), 'mydatabase.db')  # BD en la raíz

def restore_users():
    """Restaura usuarios y tipos desde el backup"""
    
    if not os.path.exists(BACKUP_PATH):
        print(f"❌ No se encontró {BACKUP_PATH}")
        return
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Base de datos no encontrada en {DB_PATH}")
        print("   Asegúrate de ejecutar 'alembic upgrade head' primero")
        return
    
    print(f"📂 Usando backup: {BACKUP_PATH}")
    print(f"📂 Usando base de datos: {DB_PATH}")
    
    with open(BACKUP_PATH, 'r', encoding='utf-8') as f:
        backup = json.load(f)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verificar qué tablas existen
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\n📋 Tablas disponibles: {tables}")
    
    # Detectar nombre correcto de la tabla de tipos
    type_table = None
    if 'user_types' in tables:
        type_table = 'user_types'
    elif 'user_type' in tables:
        type_table = 'user_type'
    else:
        print("❌ No se encontró la tabla de tipos de usuario")
        print("   Debes ejecutar 'alembic upgrade head' primero")
        conn.close()
        return
    
    print(f"✅ Usando tabla: {type_table}")
    
    # Restaurar tipos de usuario
    print("\n📝 Restaurando tipos de usuario...")
    for ut in backup['user_types']:
        cursor.execute(
            f"INSERT OR REPLACE INTO {type_table} (id, name) VALUES (?, ?)",
            (ut['id'], ut['name'])
        )
        print(f"   ✅ {ut['name']}")
    
    # Restaurar usuarios
    print("\n📝 Restaurando usuarios...")
    for user in backup['users']:
        cursor.execute("""
            INSERT OR REPLACE INTO users 
            (id, national_id, name, last_name, email, password, user_type_id, program_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user['id'], user['national_id'], user['name'], 
            user['last_name'], user['email'], user['password'],
            user['user_type_id'], user.get('program_id')
        ))
        print(f"   ✅ {user['name']} {user['last_name']}")
    
    conn.commit()
    
    # Verificar resultados
    cursor.execute(f"SELECT COUNT(*) FROM {type_table}")
    type_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n✅ Restauración completada:")
    print(f"   - {type_count} tipos de usuario")
    print(f"   - {user_count} usuarios")

if __name__ == "__main__":
    print("=" * 50)
    print("RESTAURANDO USUARIOS")
    print("=" * 50)
    restore_users()