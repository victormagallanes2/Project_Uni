import os
from jinja2 import Environment, FileSystemLoader

# 1. Configuración del cargador de plantillas
# Asume que tus plantillas están en una carpeta llamada 'templates'
template_dir = 'templates'
loader = FileSystemLoader(template_dir)
env = Environment(loader=loader)

# Función de ayuda para renderizar
def render_template(template_name, **context):
    """Carga y renderiza una plantilla de Jinja2."""
    template = env.get_template(template_name)
    return template.render(**context)


def login_required(view_func):
    """
    Decorador que verifica si el usuario tiene una sesión activa.
    Si no está logueado, redirige a /login.
    """
    def wrapper(environ, *args, **kwargs):
        # 1. Acceder a la sesión de Beaker
        # El middleware de Beaker garantiza que esta clave exista
        session = environ.get('beaker.session')
        
        # 2. Verificar la autenticación
        if not session or not session.get('logged_in'):
            # Si no hay sesión o no está logueado, redirigir
            status = '302 Found'
            headers = [('Location', '/login')] 
            # Devolver una respuesta WSGI válida de redirección
            return status, headers, [b'Redirecting to login...']
        
        # 3. Si está logueado, ejecutar la función de vista original
        return view_func(environ, *args, **kwargs)
        
    return wrapper

