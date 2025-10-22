from core.views import render_template
from home.views import home
from users.views import users

# ----------------------------------------------
# Aplicación WSGI (La Interfaz que Gunicorn necesita)
# ----------------------------------------------

def application(environ, start_response):
    """
    Función principal de la aplicación WSGI.
    Gunicorn llamará a esta función para cada solicitud HTTP.
    """
    path = environ.get('PATH_INFO', '')
    method = environ.get('REQUEST_METHOD', 'GET')
    status, headers, body_content = None, None, None
    
    # 1. Enrutamiento (Routing)
    if path == '/' or path == '/home':
        # Ruta principal
        status, headers, body_content = home(environ)
        
    elif path == '/users':
        # Ruta de users
        status, headers, body_content = users(environ)
        
    else:
        # 404 Not Found
        body_content = render_template('templates/404.html') 
        status = '404 NOT FOUND'
        headers = [('Content-type', 'text/html')]

    # 2. Enviar cabeceras
    start_response(status, headers)
    # Asegura que el cuerpo es un iterable de bytes
    if isinstance(body_content, bytes):
        return [body_content]
    elif isinstance(body_content, str):
        return [body_content.encode('utf-8')]

    # 3. Devolver el cuerpo de la respuesta
    return [body_content]