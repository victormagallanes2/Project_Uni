import datetime
from urllib.parse import parse_qs
# Asegúrate de importar tus modelos
from academic.models import AcademicTerm 
# Asume que estos existen en tu proyecto
from db import SessionLocal 
from core.views import render_template, login_required, generate_csrf_token

# Función auxiliar para manejar la conversión de fechas
def parse_date_safely(date_str, format='%Y-%m-%d'):
    try:
        return datetime.datetime.strptime(date_str, format).date()
    except (ValueError, TypeError):
        return None

@login_required
def academic_terms_create(environ):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']
    error_msg = None
    
    # Inicializar contexto para el render
    context = {'csrf_token': csrf_token, 'error': None, 'term_data': {}}

    try:
        if method == 'POST':
            # --- Lectura y Validación CSRF ---
            try:
                request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            except ValueError:
                request_body_size = 0
            request_body = environ['wsgi.input'].read(request_body_size)
            form_data = parse_qs(request_body.decode('utf-8'))
            
            # Recopilar datos para repoblar el formulario en caso de error
            context['term_data'] = {k: v[0] for k, v in form_data.items() if v}

            form_token = form_data.get('csrf_token', [''])[0]
            session_token = session.get('csrf_token')

            if not session_token or form_token != session_token:
                error_msg = "Error de seguridad (CSRF). Inténtalo de nuevo."
                # [Manejo de error CSRF y re-render]
                # ... (similar a tu users_create) ...
            
            if 'csrf_token' in session:
                del session['csrf_token']
            
            # --- Extracción y Validación de Datos ---
            name = form_data.get('name', [''])[0].strip()
            
            start_date = parse_date_safely(form_data.get('start_date', [''])[0])
            end_date = parse_date_safely(form_data.get('end_date', [''])[0])
            enroll_start = parse_date_safely(form_data.get('enrollment_start_date', [''])[0])
            enroll_end = parse_date_safely(form_data.get('enrollment_end_date', [''])[0])
            
            if not all([name, start_date, end_date, enroll_start, enroll_end]):
                error_msg = "Error de validación: Todos los campos de fechas y nombre son obligatorios."
            
            # Lógica de Fechas (el fin de inscripción debe ser antes del inicio de clases)
            if not error_msg and enroll_end > start_date:
                error_msg = "Error de lógica: El fin de inscripción debe ser anterior al inicio de clases."
            
            if error_msg:
                context['error'] = error_msg
                html = render_template('academic/academic_terms_create.html', **context)
                return "400 Bad Request", [('Content-type', 'text/html')], [html.encode('utf-8')]

            # --- Transacción DB ---
            new_term = AcademicTerm(
                name=name,
                start_date=start_date,
                end_date=end_date,
                enrollment_start_date=enroll_start,
                enrollment_end_date=enroll_end
            )
            db.add(new_term)
            db.commit()
            
            session['flash_message'] = f"Período Académico {name} creado con éxito."
            status = '302 Found'
            headers = [('Location', '/academic/terms/list')]
            return status, headers, [b'Redirecting...']

        else:
            # GET request
            html = render_template('academic/academic_terms_create.html', **context)
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

    except Exception as e:
        db.rollback()
        error_msg = f"Error al crear el Período Académico: {e}"
        # Manejo de error de unicidad (nombre duplicado)
        context['error'] = "Error de Base de Datos: El nombre del período ya existe o hay un problema con los datos."
        print(error_msg)
        html = render_template('academic/academic_terms_create.html', **context)
        return "500 Internal Server Error", [('Content-type', 'text/html')], [html.encode('utf-8')]
        
    finally:
        db.close()

@login_required
def academic_terms_list(environ):
    # Lógica similar a users_list, pero consultando AcademicTerm
    db = SessionLocal()
    session = environ['beaker.session']
    flash_message = session.pop('flash_message', None)
    
    try:
        # Ordenar por fecha de inicio para mostrar el más reciente primero
        terms = db.query(AcademicTerm).order_by(AcademicTerm.start_date.desc()).all()
        html = render_template('academic/academic_terms_list.html', 
                               terms=terms, 
                               flash_message=flash_message)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
    finally:
        db.close()

# Se omiten users_edit y users_delete por ser muy similares a tu implementación de User
# Solo se cambiaría el modelo a AcademicTerm y el filtro a AcademicTerm.term_id == term_id