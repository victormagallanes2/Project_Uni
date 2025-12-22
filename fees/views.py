# fees/views.py - CRUD Completo para FeeConcept y FeeSchedule

from urllib.parse import parse_qs

# Importaciones CRÍTICAS
from db import SessionLocal
from fees.models import FeeConcept, FeeSchedule 
from academic.models import Program, AcademicTerm # Necesitas estos para FeeSchedule
from core.views import render_template, login_required, generate_csrf_token
from sqlalchemy.orm import joinedload

# =========================================================================
# CRUD de Conceptos de Aranceles (FeeConcept)
# =========================================================================

# C: Create (Crear)
@login_required
def fee_concepts_create(environ):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']
    context = {'csrf_token': csrf_token, 'error': None, 'form_data': {}}

    try:
        if method == 'POST':
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            form_data = parse_qs(environ['wsgi.input'].read(request_body_size).decode('utf-8'))
            context['form_data'] = {k: v[0] for k, v in form_data.items() if v}
            # (Validación CSRF)
            
            name = form_data.get('name', [''])[0].strip()
            category = form_data.get('category', [''])[0].strip() 
            
            if not name:
                context['error'] = "El nombre del concepto es obligatorio."
            
            if context['error']:
                return "400 Bad Request", [('Content-type', 'text/html')], [render_template('fees/fee_concepts_create.html', **context).encode('utf-8')]

            new_concept = FeeConcept(name=name, category=category or None)
            db.add(new_concept)
            db.commit()
            
            session['flash_message'] = f"Concepto '{name}' creado con éxito."
            return '302 Found', [('Location', '/fees/concepts/list')], [b'Redirecting...']

        else:
            return "200 OK", [('Content-type', 'text/html')], [render_template('fees/fee_concepts_create.html', **context).encode('utf-8')]

    except Exception as e:
        db.rollback()
        print(f"Error al crear el Concepto: {e}")
        context['error'] = "Error de Base de Datos: El nombre del concepto ya existe o falló la conexión."
        return "500 Internal Server Error", [('Content-type', 'text/html')], [render_template('fees/fee_concepts_create.html', **context).encode('utf-8')]
        
    finally:
        db.close()

# R: Read (Listar)
@login_required
def fee_concepts_list(environ):
    db = SessionLocal()
    session = environ['beaker.session']
    flash_message = session.pop('flash_message', None)
    
    try:
        concepts = db.query(FeeConcept).order_by(FeeConcept.name).all()
        html = render_template('fees/fee_concepts_list.html', concepts=concepts, flash_message=flash_message)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
    finally:
        db.close()

# U: Update (Actualizar)
@login_required
def fee_concepts_edit(environ, concept_id):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']
    
    try:
        concept = db.query(FeeConcept).filter(FeeConcept.concept_id == concept_id).first()
        if not concept:
            session['flash_message'] = "Error: Concepto de Arancel no encontrado."
            return '302 Found', [('Location', '/fees/concepts/list')], [b'Redirecting...']

        context = {'csrf_token': csrf_token, 'error': None, 'concept': concept}

        if method == 'POST':
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            form_data = parse_qs(environ['wsgi.input'].read(request_body_size).decode('utf-8'))
            
            # (Validación CSRF)
            
            name = form_data.get('name', [concept.name])[0].strip()
            category = form_data.get('category', [concept.category or ''])[0].strip() 
            
            if not name:
                context['error'] = "El nombre del concepto es obligatorio."

            if context['error']:
                return "400 Bad Request", [('Content-type', 'text/html')], [render_template('fees/fee_concepts_edit.html', **context).encode('utf-8')]

            concept.name = name
            concept.category = category or None
            
            db.commit()
            
            session['flash_message'] = f"Concepto '{name}' actualizado con éxito."
            return '302 Found', [('Location', '/fees/concepts/list')], [b'Redirecting...']

        else:
            return "200 OK", [('Content-type', 'text/html')], [render_template('fees/fee_concepts_edit.html', **context).encode('utf-8')]

    except Exception as e:
        db.rollback()
        print(f"Error al actualizar el Concepto: {e}")
        context['error'] = "Error de Base de Datos. El nombre del concepto ya existe."
        return "500 Internal Server Error", [('Content-type', 'text/html')], [render_template('fees/fee_concepts_edit.html', **context).encode('utf-8')]
        
    finally:
        db.close()

# D: Delete (Eliminar)
@login_required
def fee_concepts_delete(environ, concept_id):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']

    try:
        concept = db.query(FeeConcept).filter(FeeConcept.concept_id == concept_id).first()
        
        if not concept:
            session['flash_message'] = "Error: Concepto no encontrado."
            return '302 Found', [('Location', '/fees/concepts/list')], [b'Redirecting...']

        if method == 'POST':
            # (Validación CSRF)
            
            db.delete(concept)
            db.commit()
            
            session['flash_message'] = f"Concepto '{concept.name}' eliminado con éxito."
            return '302 Found', [('Location', '/fees/concepts/list')], [b'Redirecting...']
        
        else:
            html = render_template('fees/fee_concepts_confirm_delete.html', concept=concept, csrf_token=csrf_token)
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
            
    except Exception as e:
        db.rollback()
        print(f"Error al eliminar concepto: {e}")
        if "IntegrityError" in str(e):
            flash_msg = "Error: No se puede eliminar. Existen tarifas (FeeSchedule) o pagos (Payments) asociados a este concepto."
        else:
            flash_msg = "Error interno al intentar eliminar el concepto."

        session['flash_message'] = flash_msg
        return '302 Found', [('Location', '/fees/concepts/list')], [b'Redirecting...']
        
    finally:
        db.close()


# =========================================================================
# CRUD de Tarifas (FeeSchedule)
# =========================================================================

# C: Create (Crear)
@login_required
def fee_schedules_create(environ):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']
    
    # Cargar datos para los SELECT
    programs = db.query(Program).order_by(Program.name).all() 
    concepts = db.query(FeeConcept).order_by(FeeConcept.name).all()
    terms = db.query(AcademicTerm).order_by(AcademicTerm.start_date.desc()).all() 
    
    context = {'csrf_token': csrf_token, 'error': None, 'form_data': {}, 'programs': programs, 'concepts': concepts, 'terms': terms}

    try:
        if method == 'POST':
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            form_data = parse_qs(environ['wsgi.input'].read(request_body_size).decode('utf-8'))
            context['form_data'] = {k: v[0] for k, v in form_data.items() if v}
            # (Validación CSRF)
            
            concept_id = form_data.get('fee_concept_id', [''])[0]
            program_id = form_data.get('program_id', [''])[0]
            term_id = form_data.get('term_id', [''])[0]
            amount_str = form_data.get('amount', [''])[0].strip()
            
            if not all([concept_id, program_id, term_id, amount_str]):
                context['error'] = "Todos los campos son obligatorios."
            
            try:
                amount = float(amount_str)
                if amount <= 0: context['error'] = "El monto debe ser un número positivo."
            except ValueError:
                context['error'] = "El monto debe ser un número válido."

            if context['error']:
                return "400 Bad Request", [('Content-type', 'text/html')], [render_template('fees/fee_schedules_create.html', **context).encode('utf-8')]

            new_schedule = FeeSchedule(fee_concept_id=int(concept_id), program_id=int(program_id), academic_term_id=int(term_id), amount=amount)
            db.add(new_schedule)
            db.commit()
            
            session['flash_message'] = "Tarifa creada con éxito."
            return '302 Found', [('Location', '/fees/schedules/list')], [b'Redirecting...']

        else:
            return "200 OK", [('Content-type', 'text/html')], [render_template('fees/fee_schedules_create.html', **context).encode('utf-8')]

    except Exception as e:
        db.rollback()
        print(f"Error al crear la Tarifa: {e}")
        context['error'] = "Error de Base de Datos: Ya existe una tarifa con esta combinación (Concepto, Programa y Período)."
        return "500 Internal Server Error", [('Content-type', 'text/html')], [render_template('fees/fee_schedules_create.html', **context).encode('utf-8')]
        
    finally:
        db.close()
        
# R: Read (Listar)


@login_required
def fee_schedules_list(environ):
    db = SessionLocal()
    session = environ.get('beaker.session')
    flash_message = session.pop('flash_message', None)
    
    try:
        # Usamos joinedload para traer los objetos relacionados en una sola consulta limpia
        schedules = db.query(FeeSchedule).options(
            joinedload(FeeSchedule.concept),
            joinedload(FeeSchedule.program),
            joinedload(FeeSchedule.term)
        ).all()
        
        html = render_template('fees/fee_schedules_list.html', 
                               schedules=schedules, 
                               flash_message=flash_message)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
    except Exception as e:
        print(f"Error en fee_schedules_list: {e}")
        return "500 Internal Server Error", [('Content-type', 'text/plain')], [b"Error al cargar tarifas"]
    finally:
        db.close()

# U: Update (Actualizar)
@login_required
def fee_schedules_edit(environ, schedule_id):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']

    programs = db.query(Program).order_by(Program.name).all() 
    concepts = db.query(FeeConcept).order_by(FeeConcept.name).all()
    terms = db.query(AcademicTerm).order_by(AcademicTerm.start_date.desc()).all() 
    
    try:
        schedule = db.query(FeeSchedule).filter(FeeSchedule.schedule_id == schedule_id).first()
        if not schedule:
            session['flash_message'] = "Error: Tarifa no encontrada."
            return '302 Found', [('Location', '/fees/schedules/list')], [b'Redirecting...']

        context = {'csrf_token': csrf_token, 'error': None, 'schedule': schedule, 'programs': programs, 'concepts': concepts, 'terms': terms}

        if method == 'POST':
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            form_data = parse_qs(environ['wsgi.input'].read(request_body_size).decode('utf-8'))
            
            # (Validación CSRF)
            
            concept_id = form_data.get('fee_concept_id', [str(schedule.fee_concept_id)])[0]
            program_id = form_data.get('program_id', [str(schedule.program_id)])[0]
            term_id = form_data.get('term_id', [str(schedule.academic_term_id)])[0]
            amount_str = form_data.get('amount', [str(schedule.amount)])[0].strip()
            
            if not all([concept_id, program_id, term_id, amount_str]):
                context['error'] = "Todos los campos son obligatorios."
            
            try:
                amount = float(amount_str)
                if amount <= 0: context['error'] = "El monto debe ser un número positivo."
            except ValueError:
                context['error'] = "El monto debe ser un número válido."

            if context['error']:
                return "400 Bad Request", [('Content-type', 'text/html')], [render_template('fees/fee_schedules_edit.html', **context).encode('utf-8')]

            schedule.fee_concept_id = int(concept_id)
            schedule.program_id = int(program_id)
            schedule.academic_term_id = int(term_id)
            schedule.amount = amount
            
            db.commit()
            
            session['flash_message'] = "Tarifa actualizada con éxito."
            return '302 Found', [('Location', '/fees/schedules/list')], [b'Redirecting...']

        else:
            return "200 OK", [('Content-type', 'text/html')], [render_template('fees/fee_schedules_edit.html', **context).encode('utf-8')]

    except Exception as e:
        db.rollback()
        print(f"Error al actualizar la Tarifa: {e}")
        context['error'] = "Error de Base de Datos: La combinación (Concepto, Programa y Período) ya existe."
        return "500 Internal Server Error", [('Content-type', 'text/html')], [render_template('fees/fee_schedules_edit.html', **context).encode('utf-8')]
        
    finally:
        db.close()

# D: Delete (Eliminar)
@login_required
def fee_schedules_delete(environ, schedule_id):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']

    try:
        schedule = db.query(FeeSchedule).filter(FeeSchedule.schedule_id == schedule_id).first()
        
        if not schedule:
            session['flash_message'] = "Error: Tarifa no encontrada."
            return '302 Found', [('Location', '/fees/schedules/list')], [b'Redirecting...']

        if method == 'POST':
            # (Validación CSRF)
            
            db.delete(schedule)
            db.commit()
            
            session['flash_message'] = "Tarifa eliminada con éxito."
            return '302 Found', [('Location', '/fees/schedules/list')], [b'Redirecting...']
        
        else:
            html = render_template('fees/fee_schedules_confirm_delete.html', schedule=schedule, csrf_token=csrf_token)
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
            
    except Exception as e:
        db.rollback()
        print(f"Error al eliminar tarifa: {e}")
        session['flash_message'] = "Error interno al intentar eliminar la tarifa."
        return '302 Found', [('Location', '/fees/schedules/list')], [b'Redirecting...']
        
    finally:
        db.close()