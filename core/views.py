import os
from jinja2 import Environment, FileSystemLoader
import secrets
import datetime
import urllib.parse


template_dir = 'templates'
loader = FileSystemLoader(template_dir)
env = Environment(loader=loader)



def parse_date_safely(date_str, format='%Y-%m-%d'):
    """Convierte una cadena a objeto date de forma segura."""
    try:
        return datetime.datetime.strptime(date_str, format).date()
    except (ValueError, TypeError):
        return None

def render_template(template_name, **context):
    template = env.get_template(template_name)
    return template.render(**context)


def generate_csrf_token():
    return secrets.token_hex(32)


def login_required(view_func):

    def wrapper(environ, *args, **kwargs):
        session = environ.get('beaker.session')
        if not session or not session.get('logged_in'):
            status = '302 Found'
            headers = [('Location', '/login')] 
            return status, headers, [b'Redirecting to login...']
        return view_func(environ, *args, **kwargs)
    return wrapper


def parse_form_data(environ):
    try:
        # Leemos el tamaño del contenido
        content_length = int(environ.get('CONTENT_LENGTH', 0))
    except (ValueError):
        content_length = 0

    # Leemos el cuerpo de la petición
    s = environ['wsgi.input'].read(content_length).decode('utf-8')
    
    # parse_qs convierte la cadena en un diccionario
    # El truco es que devuelve listas para cada campo, permitiendo capturar múltiples checkboxes
    raw_data = urllib.parse.parse_qs(s)
    
    # Creamos un objeto simple que tenga métodos get() y getall()
    class FormData:
        def __init__(self, data):
            self.data = data
        def get(self, key, default=None):
            return self.data.get(key, [default])[0]
        def getall(self, key):
            return self.data.get(key, [])
            
    return FormData(raw_data)


def redirect(location):
    """Genera una respuesta de redirección HTTP 302"""
    return "302 Found", [('Location', location)], [b""]