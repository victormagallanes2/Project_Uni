import os
from core.views import render_template
from home.views import home
from authentication.views import login, logout
from users.views import users_list, users_create, users_edit, users_delete
from paste.urlparser import StaticURLParser
from paste.urlmap import URLMap 
import re
from urllib.parse import parse_qs
from db import SessionLocal, User
import bcrypt
from paste.urlmap import URLMap 
from beaker.middleware import SessionMiddleware


def app(environ, start_response):
    path = environ.get('PATH_INFO', '')
    method = environ.get('REQUEST_METHOD', 'GET')
    status, headers, body_content = '404 NOT FOUND', [('Content-type', 'text/html')], None 
    edit_match = re.match(r'^/users/edit/(\d+)$', path)
    delete_match = re.match(r'^/users/delete/(\d+)$', path)

    if edit_match:
        user_id = int(edit_match.group(1))
        status, headers, body_content = users_edit(environ, user_id)
    elif delete_match:
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
        body_content = render_template('404.html')  # <--- body_content es str aquí
        status = '404 NOT FOUND'
        headers = [('Content-type', 'text/html')]
    start_response(status, headers)
    if isinstance(body_content, str):
        return [body_content.encode('utf-8')]
    return body_content 

PROJECT_ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
STATIC_ROOT = os.path.join(PROJECT_ROOT_PATH, 'static')
static_app = StaticURLParser(STATIC_ROOT)

session_opts = {
    'session.type': 'file',
    'session.data_dir': os.path.join(PROJECT_ROOT_PATH, 'session_data'),
    'session.key': 'app_sess_id',
    'session.secret': 'una_clave_secreta_muy_larga_y_dificil',
    'session.auto': True
}

application = URLMap()
application['/static'] = static_app
app_with_session = SessionMiddleware(app, session_opts) 
application['/'] = app_with_session