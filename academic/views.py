# academic/views.py - CRUD Completo para AcademicTerm y Section

import datetime
from urllib.parse import parse_qs

# Importaciones CRÍTICAS (Ajusta las rutas si tus modelos están en otro lugar)
from db import SessionLocal 
from academic.models import AcademicTerm, Subject, Section 
from users.models import User # Para obtener la lista de profesores
from core.views import render_template, login_required, generate_csrf_token, parse_date_safely 
from academic.models import Subject
from sqlalchemy.orm import joinedload
from academic.models import Program

# =========================================================================
# CRUD de Períodos Académicos (AcademicTerm)
# =========================================================================

# C: Create (Crear)
@login_required
def academic_terms_create(environ):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']
    context = {'csrf_token': csrf_token, 'error': None, 'term_data': {}}

    try:
        if method == 'POST':
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(request_body_size)
            form_data = parse_qs(request_body.decode('utf-8'))
            context['term_data'] = {k: v[0] for k, v in form_data.items() if v}

            # (Validación CSRF omitida por brevedad)
            
            name = form_data.get('name', [''])[0].strip()
            start_date = parse_date_safely(form_data.get('start_date', [''])[0])
            end_date = parse_date_safely(form_data.get('end_date', [''])[0])
            enroll_start = parse_date_safely(form_data.get('enrollment_start_date', [''])[0])
            enroll_end = parse_date_safely(form_data.get('enrollment_end_date', [''])[0])
            
            if not all([name, start_date, end_date, enroll_start, enroll_end]):
                context['error'] = "Error de validación: Todos los campos de fechas y nombre son obligatorios."
            elif enroll_end > start_date:
                context['error'] = "Error de lógica: El fin de inscripción debe ser anterior al inicio de clases."
            
            if context['error']:
                html = render_template('academic/academic_create.html', **context)
                return "400 Bad Request", [('Content-type', 'text/html')], [html.encode('utf-8')]

            new_term = AcademicTerm(name=name, start_date=start_date, end_date=end_date, enrollment_start_date=enroll_start, enrollment_end_date=enroll_end)
            db.add(new_term)
            db.commit()
            
            session['flash_message'] = f"Período Académico {name} creado con éxito."
            return '302 Found', [('Location', '/academic/list')], [b'Redirecting...']

        else:
            html = render_template('academic/academic_create.html', **context)
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

    except Exception as e:
        db.rollback()
        print(f"Error al crear el Período Académico: {e}")
        context['error'] = "Error de Base de Datos: El nombre del período ya existe o hay un problema con los datos."
        html = render_template('academic/academic_create.html', **context)
        return "500 Internal Server Error", [('Content-type', 'text/html')], [html.encode('utf-8')]
        
    finally:
        db.close()

# R: Read (Listar)
@login_required
def academic_terms_list(environ):
    db = SessionLocal()
    session = environ['beaker.session']
    flash_message = session.pop('flash_message', None)
    
    try:
        terms = db.query(AcademicTerm).order_by(AcademicTerm.start_date.desc()).all()
        html = render_template('academic/academic_list.html', terms=terms, flash_message=flash_message)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
    finally:
        db.close()

# U: Update (Actualizar)
@login_required
def academic_terms_edit(environ, term_id):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']
    
    try:
        term = db.query(AcademicTerm).filter(AcademicTerm.term_id == term_id).first()
        if not term:
            session['flash_message'] = "Error: Período Académico no encontrado."
            return '302 Found', [('Location', '/academic/list')], [b'Redirecting...']

        context = {'csrf_token': csrf_token, 'error': None, 'term': term}

        if method == 'POST':
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(request_body_size)
            form_data = parse_qs(request_body.decode('utf-8'))
            
            # (Validación CSRF)
            
            name = form_data.get('name', [term.name])[0].strip()
            start_date = parse_date_safely(form_data.get('start_date', [str(term.start_date)])[0])
            end_date = parse_date_safely(form_data.get('end_date', [str(term.end_date)])[0])
            enroll_start = parse_date_safely(form_data.get('enrollment_start_date', [str(term.enrollment_start_date)])[0])
            enroll_end = parse_date_safely(form_data.get('enrollment_end_date', [str(term.enrollment_end_date)])[0])
            
            if not all([name, start_date, end_date, enroll_start, enroll_end]):
                context['error'] = "Error: Todos los campos son obligatorios."
            elif enroll_end and start_date and enroll_end > start_date:
                context['error'] = "Error: El fin de inscripción debe ser anterior al inicio de clases."
            
            if context['error']:
                html = render_template('academic/academic_edit.html', **context)
                return "400 Bad Request", [('Content-type', 'text/html')], [html.encode('utf-8')]
            
            term.name = name
            term.start_date = start_date
            term.end_date = end_date
            term.enrollment_start_date = enroll_start
            term.enrollment_end_date = enroll_end
            
            db.commit()
            
            session['flash_message'] = f"Período Académico {name} actualizado con éxito."
            return '302 Found', [('Location', '/academic/list')], [b'Redirecting...']

        else:
            html = render_template('academic/academic_edit.html', **context)
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

    except Exception as e:
        db.rollback()
        print(f"Error al guardar los cambios del período: {e}")
        context['error'] = "Error de Base de Datos. Asegúrate de que el nombre del período no esté duplicado."
        html = render_template('academic/academic_edit.html', **context)
        return "500 Internal Server Error", [('Content-type', 'text/html')], [html.encode('utf-8')]
        
    finally:
        db.close()

# D: Delete (Eliminar)
@login_required
def academic_terms_delete(environ, term_id):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']

    try:
        term = db.query(AcademicTerm).filter(AcademicTerm.term_id == term_id).first()
        
        if not term:
            session['flash_message'] = "Error: Período Académico no encontrado."
            return '302 Found', [('Location', '/academic/list')], [b'Redirecting...']

        if method == 'POST':
            # (Validación CSRF)
            
            db.delete(term)
            db.commit()
            
            session['flash_message'] = f"Período Académico {term.name} eliminado con éxito."
            return '302 Found', [('Location', '/academic/list')], [b'Redirecting...']
        
        else:
            html = render_template('academic/academic_confirm_delete.html', term=term, csrf_token=csrf_token)
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
            
    except Exception as e:
        db.rollback()
        print(f"Error al eliminar período: {e}")
        if "IntegrityError" in str(e):
            flash_msg = "Error: No se puede eliminar. Existen secciones u otra data asociada a este período."
        else:
            flash_msg = "Error interno al intentar eliminar el período."

        session['flash_message'] = flash_msg
        return '302 Found', [('Location', '/academic/list')], [b'Redirecting...']
        
    finally:
        db.close()


# =========================================================================
# CRUD de Oferta de Secciones (Section)
# =========================================================================

# C: Create (Crear)
@login_required
def sections_create(environ):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']
    
    # Cargar datos para los SELECT
    subjects = db.query(Subject).order_by(Subject.name).all()
    terms = db.query(AcademicTerm).order_by(AcademicTerm.start_date.desc()).all()
    # Asume que el user_type_id=2 es el rol de Profesor
    professors = db.query(User).filter(User.user_type_id == 2).order_by(User.last_name).all() 
    
    context = {'csrf_token': csrf_token, 'error': None, 'form_data': {}, 'subjects': subjects, 'terms': terms, 'professors': professors}

    try:
        if method == 'POST':
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            form_data = parse_qs(environ['wsgi.input'].read(request_body_size).decode('utf-8'))
            context['form_data'] = {k: v[0] for k, v in form_data.items() if v}
            # (Validación CSRF)
            
            subject_id = form_data.get('subject_id', [''])[0]
            term_id = form_data.get('term_id', [''])[0]
            professor_user_id = form_data.get('professor_user_id', [''])[0]
            section_code = form_data.get('section_code', [''])[0].strip()
            capacity_str = form_data.get('capacity', [''])[0].strip()
            
            if not all([subject_id, term_id, professor_user_id, section_code, capacity_str]):
                context['error'] = "Todos los campos son obligatorios."
            
            try:
                capacity = int(capacity_str)
                if capacity <= 0: context['error'] = "La capacidad debe ser un número entero positivo."
            except ValueError:
                context['error'] = "La capacidad debe ser un número válido."

            if context['error']:
                return "400 Bad Request", [('Content-type', 'text/html')], [render_template('academic/sections_create.html', **context).encode('utf-8')]

            new_section = Section(subject_id=int(subject_id), term_id=int(term_id), professor_user_id=int(professor_user_id), section_code=section_code, capacity=capacity)
            db.add(new_section)
            db.commit()
            
            session['flash_message'] = f"Oferta de Sección '{section_code}' creada con éxito."
            return '302 Found', [('Location', '/academic/sections/list')], [b'Redirecting...']

        else:
            return "200 OK", [('Content-type', 'text/html')], [render_template('academic/sections_create.html', **context).encode('utf-8')]

    except Exception as e:
        db.rollback()
        print(f"Error al crear la Sección: {e}")
        context['error'] = "Error de Base de Datos: El código de sección o la combinación de datos ya existe."
        return "500 Internal Server Error", [('Content-type', 'text/html')], [render_template('academic/sections_create.html', **context).encode('utf-8')]
        
    finally:
        db.close()

# R: Read (Listar)
@login_required
def sections_list(environ):
    db = SessionLocal()
    session = environ['beaker.session']
    flash_message = session.pop('flash_message', None)
    
    try:
        # Consulta que incluye las relaciones para mostrar el nombre del profesor, materia y período
        sections = db.query(Section).join(Subject).join(AcademicTerm).join(User).order_by(AcademicTerm.start_date.desc(), Subject.name).all()
        
        html = render_template('academic/sections_list.html', sections=sections, flash_message=flash_message)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
    finally:
        db.close()

# U: Update (Actualizar)
@login_required
def sections_edit(environ, section_id):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']
    
    subjects = db.query(Subject).order_by(Subject.name).all()
    terms = db.query(AcademicTerm).order_by(AcademicTerm.start_date.desc()).all()
    professors = db.query(User).filter(User.user_type_id == 2).order_by(User.last_name).all() 
    
    try:
        section = db.query(Section).filter(Section.section_id == section_id).first()
        if not section:
            session['flash_message'] = "Error: Sección no encontrada."
            return '302 Found', [('Location', '/academic/sections/list')], [b'Redirecting...']

        context = {'csrf_token': csrf_token, 'error': None, 'section': section, 'subjects': subjects, 'terms': terms, 'professors': professors}

        if method == 'POST':
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            form_data = parse_qs(environ['wsgi.input'].read(request_body_size).decode('utf-8'))
            
            # (Validación CSRF)
            
            subject_id = form_data.get('subject_id', [str(section.subject_id)])[0]
            term_id = form_data.get('term_id', [str(section.term_id)])[0]
            professor_user_id = form_data.get('professor_user_id', [str(section.professor_user_id)])[0]
            section_code = form_data.get('section_code', [section.section_code])[0].strip()
            capacity_str = form_data.get('capacity', [str(section.capacity)])[0].strip()
            
            if not all([subject_id, term_id, professor_user_id, section_code, capacity_str]):
                context['error'] = "Todos los campos son obligatorios."
            
            try:
                capacity = int(capacity_str)
                if capacity <= 0: context['error'] = "La capacidad debe ser un número entero positivo."
            except ValueError:
                context['error'] = "La capacidad debe ser un número válido."

            if context['error']:
                return "400 Bad Request", [('Content-type', 'text/html')], [render_template('academic/sections_edit.html', **context).encode('utf-8')]

            section.subject_id = int(subject_id)
            section.term_id = int(term_id)
            section.professor_user_id = int(professor_user_id)
            section.section_code = section_code
            section.capacity = capacity
            
            db.commit()
            
            session['flash_message'] = f"Sección {section_code} actualizada con éxito."
            return '302 Found', [('Location', '/academic/sections/list')], [b'Redirecting...']

        else:
            return "200 OK", [('Content-type', 'text/html')], [render_template('academic/sections_edit.html', **context).encode('utf-8')]

    except Exception as e:
        db.rollback()
        print(f"Error al actualizar la Sección: {e}")
        context['error'] = "Error de Base de Datos. El código de sección o la combinación de datos ya existe."
        return "500 Internal Server Error", [('Content-type', 'text/html')], [render_template('academic/sections_edit.html', **context).encode('utf-8')]
        
    finally:
        db.close()

# D: Delete (Eliminar)
@login_required
def sections_delete(environ, section_id):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']

    try:
        section = db.query(Section).filter(Section.section_id == section_id).first()
        
        if not section:
            session['flash_message'] = "Error: Sección no encontrada."
            return '302 Found', [('Location', '/academic/sections/list')], [b'Redirecting...']

        if method == 'POST':
            # (Validación CSRF)
            
            db.delete(section)
            db.commit()
            
            session['flash_message'] = f"Sección {section.section_code} eliminada con éxito."
            return '302 Found', [('Location', '/academic/sections/list')], [b'Redirecting...']
        
        else:
            html = render_template('academic/sections_confirm_delete.html', section=section, csrf_token=csrf_token)
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
            
    except Exception as e:
        db.rollback()
        print(f"Error al eliminar sección: {e}")
        if "IntegrityError" in str(e):
            flash_msg = "Error: No se puede eliminar. Existen matrículas (Enrollments) asociadas a esta sección."
        else:
            flash_msg = "Error interno al intentar eliminar la sección."

        session['flash_message'] = flash_msg
        return '302 Found', [('Location', '/academic/sections/list')], [b'Redirecting...']
        
    finally:
        db.close()


@login_required
def subjects_list(environ):
    db = SessionLocal()
    subjects = db.query(Subject).order_by(Subject.name).all()
    html = render_template('academic/subjects_list.html', subjects=subjects)
    db.close()
    return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]


@login_required
def subjects_create(environ):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: 
        session['csrf_token'] = generate_csrf_token()

    programs = db.query(Program).all()
    context = {'csrf_token': session['csrf_token'], 'programs': programs, 'error': None}

    if method == 'POST':
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            form_data = parse_qs(environ['wsgi.input'].read(request_body_size).decode('utf-8'))
            
            # Capturamos todos los campos requeridos por tu modelo
            name = form_data.get('name', [''])[0].strip()
            code = form_data.get('code', [''])[0].strip()
            program_id = form_data.get('program_id', [''])[0].strip()
            credits_str = form_data.get('credits', [''])[0].strip() # <--- NUEVO

            # Validación de campos vacíos
            if not all([name, code, program_id, credits_str]):
                context['error'] = "Todos los campos son obligatorios (Programa, Código, Nombre y Créditos)."
                return "400 Bad Request", [('Content-type', 'text/html')], [render_template('academic/subjects_create.html', **context).encode('utf-8')]

            # Creamos el objeto con la estructura exacta de tu modelo
            new_subject = Subject(
                name=name,
                code=code,
                program_id=int(program_id),
                credits=int(credits_str) # <--- AHORA SÍ SE GUARDA
            )
            
            db.add(new_subject)
            db.commit()
            
            session['flash_message'] = f"Materia '{name}' registrada correctamente."
            return '302 Found', [('Location', '/academic/subjects/list')], [b'Redirecting...']
            
        except Exception as e:
            db.rollback()
            context['error'] = f"Error de base de datos: {str(e)}"
            return "500 Internal Server Error", [('Content-type', 'text/html')], [render_template('academic/subjects_create.html', **context).encode('utf-8')]
        finally:
            db.close()
    else:
        html = render_template('academic/subjects_create.html', **context)
        db.close()
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]


@login_required
def subjects_edit(environ, subject_id):
    """Edita una materia existente."""
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    # 1. Buscar la materia y cargar sus relaciones
    subject = db.query(Subject).filter(Subject.subject_id == subject_id).first()
    if not subject:
        return "404 Not Found", [('Content-type', 'text/plain')], [b"Materia no encontrada"]

    # 2. Cargar programas para el desplegable del formulario
    programs = db.query(Program).all()
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    
    context = {
        'csrf_token': session['csrf_token'],
        'subject': subject,
        'programs': programs,
        'error': None
    }

    if method == 'POST':
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            form_data = parse_qs(environ['wsgi.input'].read(request_body_size).decode('utf-8'))
            
            # Actualizar campos del modelo
            subject.name = form_data.get('name', [subject.name])[0].strip()
            subject.code = form_data.get('code', [subject.code])[0].strip()
            subject.program_id = int(form_data.get('program_id', [subject.program_id])[0])
            subject.credits = int(form_data.get('credits', [subject.credits])[0])

            db.commit()
            session['flash_message'] = f"Materia '{subject.name}' actualizada correctamente."
            return '302 Found', [('Location', '/academic/subjects/list')], [b'Redirecting...']
            
        except Exception as e:
            db.rollback()
            context['error'] = f"Error al actualizar: {str(e)}"
            return "500 Internal Server Error", [('Content-type', 'text/html')], [render_template('academic/subjects_edit.html', **context).encode('utf-8')]
        finally:
            db.close()
    else:
        html = render_template('academic/subjects_edit.html', **context)
        db.close()
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

def subjects_delete(environ, subject_id):
    if environ.get('REQUEST_METHOD') != 'POST':
        return "405 Method Not Allowed", [('Content-type', 'text/plain')], [b"Metodo no permitido"]
    
    db = SessionLocal()
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    
    if subject:
        try:
            db.delete(subject)
            db.commit()
        except Exception:
            db.rollback()
            # Aquí podrías manejar si la materia tiene secciones amarradas
    
    db.close()
    return "302 Found", [('Location', '/academic/subjects/list')], []


@login_required
def programs_list(environ):
    """Lista todos los programas registrados."""
    db = SessionLocal()
    session = environ['beaker.session']
    flash_message = session.pop('flash_message', None)
    
    try:
        # Usamos joinedload para traer las materias y poder contarlas en el HTML
        programs = db.query(Program).options(joinedload(Program.subjects)).all()
        
        html = render_template('academic/programs_list.html', 
                               programs=programs, 
                               flash_message=flash_message)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
    finally:
        db.close()

@login_required
def programs_create(environ):
    """Crea un nuevo programa (Carrera/Postgrado)."""
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: 
        session['csrf_token'] = generate_csrf_token()
    
    context = {'csrf_token': session['csrf_token'], 'error': None}

    if method == 'POST':
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            form_data = parse_qs(environ['wsgi.input'].read(request_body_size).decode('utf-8'))
            
            name = form_data.get('name', [''])[0].strip()
            level = form_data.get('level', [''])[0].strip()
            total_credits = form_data.get('total_credits', ['0'])[0].strip()

            if not name or not level:
                context['error'] = "El nombre y el nivel son obligatorios."
                return "400 Bad Request", [('Content-type', 'text/html')], [render_template('academic/programs_create.html', **context).encode('utf-8')]

            new_program = Program(
                name=name,
                level=level,
                total_credits=int(total_credits) if total_credits.isdigit() else 0
            )
            
            db.add(new_program)
            db.commit()
            
            session['flash_message'] = f"Programa '{name}' creado exitosamente."
            return '302 Found', [('Location', '/academic/programs/list')], [b'Redirecting...']
            
        except Exception as e:
            db.rollback()
            context['error'] = f"Error al guardar: {str(e)}"
            return "500 Internal Server Error", [('Content-type', 'text/html')], [render_template('academic/programs_create.html', **context).encode('utf-8')]
        finally:
            db.close()
    else:
        html = render_template('academic/programs_create.html', **context)
        db.close()
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

@login_required
def programs_edit(environ, program_id):
    """Edita un programa existente."""
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    program = db.query(Program).filter(Program.program_id == program_id).first()
    if not program:
        return "404 Not Found", [('Content-type', 'text/plain')], [b"Programa no encontrado"]

    context = {'csrf_token': session.get('csrf_token'), 'program': program, 'error': None}

    if method == 'POST':
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            form_data = parse_qs(environ['wsgi.input'].read(request_body_size).decode('utf-8'))
            
            program.name = form_data.get('name', [program.name])[0].strip()
            program.level = form_data.get('level', [program.level])[0].strip()
            credits_str = form_data.get('total_credits', ['0'])[0].strip()
            program.total_credits = int(credits_str) if credits_str.isdigit() else 0

            db.commit()
            session['flash_message'] = "Programa actualizado correctamente."
            return '302 Found', [('Location', '/academic/programs/list')], [b'Redirecting...']
        except Exception as e:
            db.rollback()
            context['error'] = f"Error: {str(e)}"
            return "500 Internal Server Error", [('Content-type', 'text/html')], [render_template('academic/programs_edit.html', **context).encode('utf-8')]
        finally:
            db.close()
    else:
        html = render_template('academic/programs_edit.html', **context)
        db.close()
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

@login_required
def programs_delete(environ, program_id):
    """Elimina un programa si no tiene dependencias críticas (o según lógica de negocio)."""
    if environ.get('REQUEST_METHOD') != 'POST':
        return "405 Method Not Allowed", [('Content-type', 'text/plain')], [b"Metodo no permitido"]
        
    db = SessionLocal()
    session = environ['beaker.session']
    try:
        program = db.query(Program).filter(Program.program_id == program_id).first()
        if program:
            # Nota: Si hay materias asociadas, SQLAlchemy lanzará un error de integridad
            # a menos que tengas configurado el cascade delete.
            db.delete(program)
            db.commit()
            session['flash_message'] = "Programa eliminado."
        return '302 Found', [('Location', '/academic/programs/list')], [b'Redirecting...']
    except Exception as e:
        db.rollback()
        session['flash_message'] = "No se puede eliminar: el programa tiene materias o tarifas asociadas."
        return '302 Found', [('Location', '/academic/programs/list')], [b'Redirecting...']
    finally:
        db.close()