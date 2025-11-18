import os
from core.views import render_template
from home.views import home
from authentication.views import login, logout
from users.views import users_list, users_create, users_edit, users_delete
from paste.urlparser import StaticURLParser
from paste.urlmap import URLMap 
import re
from urllib.parse import parse_qs
from db import SessionLocal, User # Asumiendo que tu modelo y sesión están aquí
import bcrypt
from paste.urlmap import URLMap 
from beaker.middleware import SessionMiddleware
# ----------------------------------------------
# 1. Aplicación WSGI Dinámica (Maneja el enrutamiento)
# ----------------------------------------------


def app(environ, start_response):
    """
    Función principal que maneja las solicitudes dinámicas (rutas y lógica).
    """
    path = environ.get('PATH_INFO', '')
    method = environ.get('REQUEST_METHOD', 'GET')
    
    # Inicialización, aunque las rutas deberían asignar estos valores.
    status, headers, body_content = '404 NOT FOUND', [('Content-type', 'text/html')], None 

    # 1. RUTA DINÁMICA DE EDICIÓN (users/edit/{id})
    edit_match = re.match(r'^/users/edit/(\d+)$', path)
    delete_match = re.match(r'^/users/delete/(\d+)$', path)
    
    if edit_match:
        # Captura el ID del usuario
        user_id = int(edit_match.group(1))
        status, headers, body_content = users_edit(environ, user_id)

    elif delete_match:
        # Captura el ID del usuario para ELIMINACIÓN
        user_id = int(delete_match.group(1))
        status, headers, body_content = users_delete(environ, user_id)

    elif path == '/' or path == '/home':
        status, headers, body_content = home(environ)
        
    elif path == '/login':
        status, headers, body_content = login(environ)

    elif path == '/logout':
        status, headers, body_content = logout(environ)

    elif path == '/users/create':
        status, headers, body_content = users_create(environ)

    elif path == '/users/list':
        status, headers, body_content = users_list(environ)
        
    else:
        # 404 Not Found
        body_content = render_template('404.html')  # <--- body_content es str aquí
        status = '404 NOT FOUND'
        headers = [('Content-type', 'text/html')]

    # 2. Enviar cabeceras
    start_response(status, headers)
    
    # 3. Devolver el cuerpo de la respuesta (Iterable de bytes)
    # CORRECCIÓN FINAL: Normalizamos el retorno.
    if isinstance(body_content, str):
        # Si es una cadena (solo debería ser el 404), la codificamos.
        return [body_content.encode('utf-8')]
    
    # Si ya es una lista de bytes (list[bytes]), la devolvemos directamente.
    # Esto maneja todas las respuestas de las vistas (200, 302, 400, 500).
    return body_content 


# ----------------------------------------------
# 2. CONFIGURACIÓN DEL MIDDLEWARE ESTÁTICO 
# ----------------------------------------------

# Ruta BASE del proyecto confirmada por el usuario
PROJECT_ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

# Define la ruta ABSOLUTA de la carpeta 'static'
STATIC_ROOT = os.path.join(PROJECT_ROOT_PATH, 'static')

# Crea la aplicación WSGI para servir archivos estáticos. 
static_app = StaticURLParser(STATIC_ROOT)


session_opts = {
    'session.type': 'file',
    'session.data_dir': os.path.join(PROJECT_ROOT_PATH, 'session_data'), # Donde guarda los archivos de sesión
    'session.key': 'app_sess_id',  # Nombre de la cookie de sesión
    'session.secret': 'una_clave_secreta_muy_larga_y_dificil', # ¡CAMBIA ESTO EN PRODUCCIÓN!
    'session.auto': True # Guarda la sesión automáticamente si fue accedida
}

# 3. PUNTO DE ENTRADA FINAL PARA EL SERVIDOR
application = URLMap()
application['/static'] = static_app
app_with_session = SessionMiddleware(app, session_opts) 

# Asignamos la aplicación envuelta a la ruta raíz
application['/'] = app_with_session