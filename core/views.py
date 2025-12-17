import os
from jinja2 import Environment, FileSystemLoader
import secrets
import datetime


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

