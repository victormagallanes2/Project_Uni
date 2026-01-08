import os
import re
from core.views import render_template
from home.views import home
from authentication.views import login, logout
from users.views import users_list, users_create, users_edit, users_delete

from academic.views import (
    academic_terms_list, academic_terms_create, academic_terms_edit, academic_terms_delete,
    sections_list, sections_create, sections_edit, sections_delete,
    subjects_list, subjects_create, subjects_edit, subjects_delete,
    programs_list, programs_create, programs_edit, programs_delete
)
from fees.views import (
    fee_concepts_list, fee_concepts_create, fee_concepts_edit, fee_concepts_delete,
    fee_schedules_list, fee_schedules_create, fee_schedules_edit, fee_schedules_delete
)
from transactions.views import (
    payments_register, payments_list_admin, payments_verify,
    enrollment_choose_sections, enrollments_list, enrollments_create
)
# ---------------------------

from paste.urlparser import StaticURLParser
from paste.urlmap import URLMap 
from beaker.middleware import SessionMiddleware

def app(environ, start_response):
    path = environ.get('PATH_INFO', '')
    method = environ.get('REQUEST_METHOD', 'GET')
    status, headers, body_content = '404 NOT FOUND', [('Content-type', 'text/html')], None 
    session = environ.get('beaker.session')

    # --- EXPRESIONES REGULARES PARA RUTAS CON ID ---
    # Usuarios
    u_edit_match = re.match(r'^/users/edit/(\d+)$', path)
    u_delete_match = re.match(r'^/users/delete/(\d+)$', path)
    
    # Academic Terms
    term_edit_match = re.match(r'^/academic/edit/(\d+)$', path)
    term_delete_match = re.match(r'^/academic/delete/(\d+)$', path)

    #materias
    subj_edit_match = re.match(r'^/academic/subjects/edit/(\d+)$', path)
    subj_delete_match = re.match(r'^/academic/subjects/delete/(\d+)$', path)
    
    # Sections
    sec_edit_match = re.match(r'^/academic/sections/edit/(\d+)$', path)
    sec_delete_match = re.match(r'^/academic/sections/delete/(\d+)$', path)
    
    # Fee Concepts
    concept_edit_match = re.match(r'^/fees/concepts/edit/(\d+)$', path)
    concept_delete_match = re.match(r'^/fees/concepts/delete/(\d+)$', path)
    
    # Fee Schedules
    sched_edit_match = re.match(r'^/fees/schedules/edit/(\d+)$', path)
    sched_delete_match = re.match(r'^/fees/schedules/delete/(\d+)$', path)
    
    # Payments & Enrollment
    pay_register_match = re.match(r'^/payments/register/(\d+)$', path) # Recibe student_user_id
    pay_verify_match = re.match(r'^/payments/verify/(\d+)$', path)     # Recibe payment_id
    enroll_choose_match = re.match(r'^/enrollment/choose/(\d+)$', path) # Recibe student_user_id
    enroll_list_match = re.match(r'^/enrollment/list/(\d+)$', path)   # Recibe student_user_id

    prog_edit_match = re.match(r'^/academic/programs/edit/(\d+)$', path)
    prog_delete_match = re.match(r'^/academic/programs/delete/(\d+)$', path)

    # =========================================================================
    # LÓGICA DE ENRUTAMIENTO (Routing)
    # =========================================================================

    # --- RUTAS DE USUARIOS ---
    if u_edit_match:
        status, headers, body_content = users_edit(environ, int(u_edit_match.group(1)))
    elif u_delete_match:
        status, headers, body_content = users_delete(environ, int(u_delete_match.group(1)))
    elif path == '/users/create':
        status, headers, body_content = users_create(environ)
    elif path == '/users/list':
        status, headers, body_content = users_list(environ)

    # --- RUTAS ACADEMIC TERMS ---
    elif path == '/academic/list':
        status, headers, body_content = academic_terms_list(environ)
    elif path == '/academic/create':
        status, headers, body_content = academic_terms_create(environ)
    elif term_edit_match:
        status, headers, body_content = academic_terms_edit(environ, int(term_edit_match.group(1)))
    elif term_delete_match:
        status, headers, body_content = academic_terms_delete(environ, int(term_delete_match.group(1)))

    # --- RUTAS SECTIONS ---
    elif path == '/academic/sections/list':
        status, headers, body_content = sections_list(environ)
    elif path == '/academic/sections/create':
        status, headers, body_content = sections_create(environ)
    elif sec_edit_match:
        status, headers, body_content = sections_edit(environ, int(sec_edit_match.group(1)))
    elif sec_delete_match:
        status, headers, body_content = sections_delete(environ, int(sec_delete_match.group(1)))

    # --- RUTAS DE MATERIAS (Añadir al bloque if/elif) ---
    elif path == '/academic/subjects/list':
        status, headers, body_content = subjects_list(environ)
    elif path == '/academic/subjects/create':
        status, headers, body_content = subjects_create(environ)
    elif subj_edit_match:
        status, headers, body_content = subjects_edit(environ, int(subj_edit_match.group(1)))
    elif subj_delete_match:
        status, headers, body_content = subjects_delete(environ, int(subj_edit_match.group(1)))

    # --- RUTAS FEE CONCEPTS ---
    elif path == '/fees/concepts/list':
        status, headers, body_content = fee_concepts_list(environ)
    elif path == '/fees/concepts/create':
        status, headers, body_content = fee_concepts_create(environ)
    elif concept_edit_match:
        status, headers, body_content = fee_concepts_edit(environ, int(concept_edit_match.group(1)))
    elif concept_delete_match:
        status, headers, body_content = fee_concepts_delete(environ, int(concept_delete_match.group(1)))

    # --- RUTAS FEE SCHEDULES ---
    elif path == '/fees/schedules/list':
        status, headers, body_content = fee_schedules_list(environ)
    elif path == '/fees/schedules/create':
        status, headers, body_content = fee_schedules_create(environ)
    elif sched_edit_match:
        status, headers, body_content = fee_schedules_edit(environ, int(sched_edit_match.group(1)))
    elif sched_delete_match:
        status, headers, body_content = fee_schedules_delete(environ, int(sched_delete_match.group(1)))

    # --- RUTAS PAYMENTS & ENROLLMENT ---
    elif pay_register_match:
        status, headers, body_content = payments_register(environ, int(pay_register_match.group(1)))
    elif path == '/payments/admin/list':
        status, headers, body_content = payments_list_admin(environ)
    elif pay_verify_match:
        status, headers, body_content = payments_verify(environ, int(pay_verify_match.group(1)))
    elif enroll_choose_match:
        status, headers, body_content = enrollment_choose_sections(environ, int(enroll_choose_match.group(1)))
    #elif enroll_list_match:
        #status, headers, body_content = enrollment_list_student(environ, int(enroll_list_match.group(1)))
    elif path == '/enrollments/list':
        status, headers, body_content = enrollments_list(environ)
    elif path == '/enrollments/create':
        status, headers, body_content = enrollments_create(environ)

    # --- RUTAS DE PROGRAMAS ACADÉMICOS ---
    elif path == '/academic/programs/list':
        status, headers, body_content = programs_list(environ)

    elif path == '/academic/programs/create':
        status, headers, body_content = programs_create(environ)

    elif prog_edit_match:
        # Pasamos el ID capturado por el regex a la función
        status, headers, body_content = programs_edit(environ, int(prog_edit_match.group(1)))

    elif prog_delete_match:
        status, headers, body_content = programs_delete(environ, int(prog_delete_match.group(1)))

    # --- RUTAS HOME & AUTH ---
    elif path == '/' or path == '/home':
        status, headers, body_content = home(environ)
    elif path == '/login':
        status, headers, body_content = login(environ)
    elif path == '/logout':
        status, headers, body_content = logout(environ)
    
    # --- 404 NOT FOUND ---
    else:
        body_content = render_template('404.html')
        status = '404 NOT FOUND'

    start_response(status, headers)
    if isinstance(body_content, str):
        return [body_content.encode('utf-8')]
    return body_content 

# Configuración de estáticos y middleware (Se mantiene igual)
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