import os
from core.views import render_template
from home.views import home
from authentication.views import login
from users.views import users_list

from paste.urlparser import StaticURLParser
from paste.urlmap import URLMap # ¡Importamos URLMap!


# ----------------------------------------------
# 1. Aplicación WSGI Dinámica (Maneja el enrutamiento)
# ----------------------------------------------

def app(environ, start_response):
    """
    Función principal que maneja las solicitudes dinámicas (rutas y lógica).
    """
    path = environ.get('PATH_INFO', '')
    method = environ.get('REQUEST_METHOD', 'GET')
    status, headers, body_content = None, None, None
    
    # 1. Enrutamiento (Routing)
    if path == '/' or path == '/home':
        status, headers, body_content = home(environ)
        
    elif path == '/login':
        status, headers, body_content = login(environ)

    elif path == '/users':
        status, headers, body_content = users_list(environ)
        
    else:
        # 404 Not Found
        body_content = render_template('404.html') 
        status = '404 NOT FOUND'
        headers = [('Content-type', 'text/html')]

    # 2. Enviar cabeceras
    start_response(status, headers)
    
    # 3. Devolver el cuerpo de la respuesta (Iterable de bytes)
    if isinstance(body_content, bytes):
        return [body_content]
    elif isinstance(body_content, str):
        return [body_content.encode('utf-8')]

    return [body_content] 


# ----------------------------------------------
# 2. CONFIGURACIÓN DEL MIDDLEWARE ESTÁTICO 
# ----------------------------------------------

# Ruta BASE del proyecto confirmada por el usuario
PROJECT_ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

# Define la ruta ABSOLUTA de la carpeta 'static'
STATIC_ROOT = os.path.join(PROJECT_ROOT_PATH, 'static')

# Crea la aplicación WSGI para servir archivos estáticos. 
static_app = StaticURLParser(STATIC_ROOT)

# 3. PUNTO DE ENTRADA FINAL PARA EL SERVIDOR
# SOLUCIÓN DEL BUG: Inicializamos URLMap vacío y asignamos las rutas.
# Esto asegura que el constructor no confunda el diccionario con el manejador de 404.
application = URLMap()
application['/static'] = static_app
application['/'] = app