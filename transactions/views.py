# transactions/views.py - Módulo de Transacciones: Pagos y Matrícula

import datetime
from urllib.parse import parse_qs
from sqlalchemy.orm import joinedload
from sqlalchemy import func, asc

# Importaciones CRÍTICAS
from db import SessionLocal 
from fees.models import FeeConcept, Payment, Enrollment # Asumo que Enrollment está aquí
from academic.models import AcademicTerm, Section, Subject, SectionSubject, Program
from users.models import User 
from core.views import render_template, login_required, generate_csrf_token, parse_date_safely, redirect, parse_form_data
from transactions.models import Enrollment
from users.models import User
from datetime import date
# =========================================================================
# CRUD de Pagos (Payment)
# =========================================================================

# C: Create (Registro por Estudiante)
@login_required
def payments_register(environ, student_user_id): 
    """Permite al estudiante registrar un pago contra un concepto."""
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']
    
    try:
        # Conceptos de pago que el estudiante debe usar (ej: Matrícula)
        concepts = db.query(FeeConcept).filter(FeeConcept.category != 'Degree Rights').order_by(FeeConcept.name).all() 
    except Exception:
        concepts = []
        
    context = {'csrf_token': csrf_token, 'error': None, 'form_data': {}, 'concepts': concepts}

    try:
        if method == 'POST':
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            form_data = parse_qs(environ['wsgi.input'].read(request_body_size).decode('utf-8'))
            context['form_data'] = {k: v[0] for k, v in form_data.items() if v}
            
            concept_id = form_data.get('concept_id', [''])[0]
            amount_str = form_data.get('amount', [''])[0].strip()
            payment_date_str = form_data.get('payment_date', [''])[0].strip()
            bank_reference = form_data.get('bank_reference', [''])[0].strip()
            proof_url = form_data.get('proof_url', [''])[0].strip() 
            
            if not all([concept_id, amount_str, payment_date_str, bank_reference, proof_url]):
                context['error'] = "Todos los campos son obligatorios."
            
            try:
                amount = float(amount_str)
                payment_date = parse_date_safely(payment_date_str)
                if amount <= 0: context['error'] = "El monto debe ser positivo."
            except ValueError:
                context['error'] = "Error en formato de Monto o Fecha."
            
            if context['error']:
                return "400 Bad Request", [('Content-type', 'text/html')], [render_template('transactions/payments_register.html', **context).encode('utf-8')]

            new_payment = Payment(
                student_user_id=student_user_id,
                concept_id=int(concept_id),
                amount=amount,
                payment_date=payment_date,
                bank_reference=bank_reference,
                proof_url=proof_url, 
                status='Pending Verification' 
            )
            db.add(new_payment)
            db.commit()
            
            session['flash_message'] = "Pago registrado exitosamente. Pendiente de verificación administrativa."
            return '302 Found', [('Location', f'/users/{student_user_id}/payments')], [b'Redirecting...']

        else:
            return "200 OK", [('Content-type', 'text/html')], [render_template('transactions/payments_register.html', **context).encode('utf-8')]

    except Exception as e:
        db.rollback()
        print(f"Error al registrar el pago: {e}")
        context['error'] = "Error interno al procesar el pago."
        return "500 Internal Server Error", [('Content-type', 'text/html')], [render_template('transactions/payments_register.html', **context).encode('utf-8')]
        
    finally:
        db.close()

# R: Read (Listado para Admin)
@login_required
def payments_list_admin(environ):
    """Muestra una lista de todos los pagos, priorizando los pendientes."""
    db = SessionLocal()
    session = environ['beaker.session']
    flash_message = session.pop('flash_message', None)
    
    try:
        payments = db.query(Payment)\
            .join(User, Payment.student_user_id == User.id)\
            .join(FeeConcept)\
            .order_by(Payment.status.asc(), Payment.payment_date)\
            .all()
        
        html = render_template('transactions/payments_admin_list.html', payments=payments, flash_message=flash_message)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
    finally:
        db.close()

# U: Update (Verificación por Admin)
@login_required 
def payments_verify(environ, payment_id):
    """Permite al administrador cambiar el estado de un pago (Verified, Rejected)."""
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']

    try:
        payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
        
        if not payment:
            session['flash_message'] = "Error: Pago no encontrado."
            return '302 Found', [('Location', '/payments/admin/list')], [b'Redirecting...']

        context = {'csrf_token': csrf_token, 'error': None, 'payment': payment, 'statuses': ['Verified', 'Rejected', 'Pending Verification', 'Completed']}

        if method == 'POST':
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            form_data = parse_qs(environ['wsgi.input'].read(request_body_size).decode('utf-8'))
            
            new_status = form_data.get('status', [''])[0].strip()
            
            if new_status not in context['statuses']:
                context['error'] = "Estatus de pago inválido."
            
            if context['error']:
                return "400 Bad Request", [('Content-type', 'text/html')], [render_template('transactions/payments_verify.html', **context).encode('utf-8')]

            payment.status = new_status
            db.commit()
            
            session['flash_message'] = f"Pago {payment_id} actualizado a '{new_status}' con éxito."
            return '302 Found', [('Location', '/payments/admin/list')], [b'Redirecting...']

        else:
            html = render_template('transactions/payments_verify.html', **context)
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

    except Exception as e:
        db.rollback()
        print(f"Error al verificar el pago: {e}")
        session['flash_message'] = "Error interno al intentar verificar el pago."
        return "302 Found", [('Location', '/payments/admin/list')], [b'Redirecting...']
        
    finally:
        db.close()

# =========================================================================
# CRUD de Matrícula (Enrollment)
# =========================================================================

# C: Create (Selección de Secciones y Matrícula por Estudiante)
@login_required
def enrollment_choose_sections(environ, student_user_id):
    """Permite al estudiante elegir secciones y formalizar su matrícula."""
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session: session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']
    
    context = {'csrf_token': csrf_token, 'error': None, 'sections': [], 'student': None, 'verified_payment': None}

    try:
        student = db.query(User).filter(User.id == student_user_id).first()
        context['student'] = student
        current_date = datetime.date.today()

        # 1. Verificar si hay un pago de matrícula "Verified" para un periodo activo (Enrollment Fee)
        verified_payment = db.query(Payment) \
            .join(FeeConcept) \
            .join(AcademicTerm) \
            .filter(Payment.student_user_id == student_user_id) \
            .filter(Payment.status == 'Verified') \
            .filter(FeeConcept.category == 'Enrollment Fee') \
            .filter(AcademicTerm.enrollment_start_date <= current_date) \
            .filter(AcademicTerm.enrollment_end_date >= current_date) \
            .order_by(Payment.payment_date.desc()) \
            .first()
        
        context['verified_payment'] = verified_payment

        if not verified_payment:
            context['error'] = "Debe tener un pago de Matrícula verificado para un período activo para poder inscribirse."
        
        if not context['error']:
            # 2. Obtener secciones disponibles y cupos
            enrollments_count = db.query(Enrollment.section_id, func.count(Enrollment.enrollment_id).label('occupied')) \
                .group_by(Enrollment.section_id) \
                .subquery()

            available_sections = db.query(Section) \
                .outerjoin(enrollments_count, Section.section_id == enrollments_count.c.section_id) \
                .filter(Section.term_id == verified_payment.academic_term_id) \
                .options(joinedload(Section.subject), joinedload(Section.professor)) \
                .all()

            sections_with_availability = []
            for section in available_sections:
                occupied = db.query(Enrollment).filter(Enrollment.section_id == section.section_id, Enrollment.status == 'Active').count()
                remaining = section.capacity - occupied
                if remaining > 0:
                    sections_with_availability.append({
                        'section': section,
                        'remaining_capacity': remaining
                    })
            
            context['sections'] = sections_with_availability
        
        if method == 'POST':
            if context['error']: # No debería llegar aquí si hay error, pero por seguridad
                return "403 Forbidden", [('Content-type', 'text/html')], [render_template('transactions/enrollment_choose_sections.html', **context).encode('utf-8')]
                
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            form_data = parse_qs(environ['wsgi.input'].read(request_body_size).decode('utf-8'))
            
            selected_section_ids = [int(sid) for sid in form_data.get('sections', []) if sid.isdigit()]
            
            if not selected_section_ids:
                context['error'] = "Debe seleccionar al menos una sección."
                return "400 Bad Request", [('Content-type', 'text/html')], [render_template('transactions/enrollment_choose_sections.html', **context).encode('utf-8')]
            
            new_enrollments = []
            sections_to_enroll = db.query(Section).filter(Section.section_id.in_(selected_section_ids)).all()

            for section in sections_to_enroll:
                # Verificar capacidad final y si ya está inscrito
                occupied_count = db.query(Enrollment).filter(Enrollment.section_id == section.section_id, Enrollment.status == 'Active').count()
                
                if occupied_count >= section.capacity:
                    context['error'] = f"Error de cupo: La sección {section.section_code} ya está llena."
                    db.rollback()
                    return "400 Bad Request", [('Content-type', 'text/html')], [render_template('transactions/enrollment_choose_sections.html', **context).encode('utf-8')]

                existing_enrollment = db.query(Enrollment).filter(
                    Enrollment.student_user_id == student_user_id,
                    Enrollment.section_id == section.section_id
                ).first()
                
                if not existing_enrollment:
                    new_enrollment = Enrollment(
                        student_user_id=student_user_id,
                        section_id=section.section_id,
                        enrollment_date=current_date,
                        status='Active'
                    )
                    new_enrollments.append(new_enrollment)
            
            if new_enrollments:
                db.add_all(new_enrollments)
                # Marcar el pago de matrícula como "Completed"
                verified_payment.status = 'Completed' 
                db.commit()
            
            session['flash_message'] = f"Matrícula completada en {len(new_enrollments)} secciones con éxito."
            return '302 Found', [('Location', f'/users/{student_user_id}/enrollments')], [b'Redirecting...']

        else:
            return "200 OK", [('Content-type', 'text/html')], [render_template('transactions/enrollment_choose_sections.html', **context).encode('utf-8')]

    except Exception as e:
        db.rollback()
        print(f"Error al formalizar la Matrícula: {e}")
        context['error'] = f"Error interno del servidor: {e}"
        return "500 Internal Server Error", [('Content-type', 'text/html')], [render_template('transactions/enrollment_choose_sections.html', **context).encode('utf-8')]
        
    finally:
        db.close()

@login_required
def enrollments_list(environ):
    db = SessionLocal()
    session = environ['beaker.session']
    
    try:
        # Consultamos agrupando por estudiante para mostrar una sola fila por inscripción
        enrollments = db.query(Enrollment).options(
            joinedload(Enrollment.student).joinedload(User.program),
            joinedload(Enrollment.section)
        ).group_by(Enrollment.student_user_id).all() 
        # Al agrupar por student_user_id, colapsamos las materias en un solo registro de vista
        
        context = {
            'enrollments': enrollments,
            'user_name': session.get('user_name'),
            'flash_message': session.pop('flash_message', None)
        }
        
        html = render_template('transactions/enrollments_list.html', **context)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
    finally:
        db.close()


@login_required
def enrollments_create(environ):
    db = SessionLocal()
    session = environ['beaker.session']
    user_id = int(session.get('user_id')) # ID del usuario logueado
    
    try:
        # 1. Buscamos al estudiante (necesario tanto para GET como para POST)
        student = db.query(User).filter(User.id == user_id).first()
        
        if not student:
            session['flash_message'] = "Error: Usuario no encontrado."
            return redirect('/transactions/enrollments/list')

        # --- LÓGICA DE PROCESAMIENTO (POST) ---
        if environ['REQUEST_METHOD'] == 'POST':
            form_data = parse_form_data(environ)
            program_id = int(form_data.get('program_id'))
            
            # A. VALIDACIÓN: ¿Ya está inscrito en este u otro programa?
            already_enrolled = db.query(Enrollment).filter(
                Enrollment.student_user_id == user_id
            ).first()

            if already_enrolled:
                session['flash_message'] = "Usted ya posee una inscripción activa en el sistema."
                return redirect('/transactions/enrollments/list')

            # B. BÚSQUEDA SECUENCIAL DE SECCIÓN (Llenado por orden de ID)
            # Buscamos secciones que tengan materias de ese programa y cupo > 0
            section = db.query(Section).join(Section.subjects).join(SectionSubject.subject)\
                .filter(Subject.program_id == program_id)\
                .filter(Section.capacity > 0)\
                .order_by(asc(Section.section_id))\
                .with_for_update().first() # Bloqueo de fila para evitar sobrecupo

            if not section:
                session['flash_message'] = "No hay cupos disponibles para el programa seleccionado en este momento."
                return redirect('/transactions/enrollments/create')

            # C. OBTENER TODAS LAS MATERIAS DEL PROGRAMA
            subjects = db.query(Subject).filter(Subject.program_id == program_id).all()
            
            if not subjects:
                session['flash_message'] = "Error: El programa seleccionado no tiene materias configuradas."
                return redirect('/transactions/enrollments/create')

            # D. EJECUTAR INSCRIPCIÓN MASIVA
            for subject in subjects:
                new_reg = Enrollment(
                    student_user_id=user_id,
                    section_id=section.section_id,
                    subject_id=subject.subject_id,
                    enrollment_date=date.today(),
                    status='Registered'
                )
                db.add(new_reg)

            # E. ACTUALIZACIÓN FINAL
            section.capacity -= 1 # Descontamos 1 cupo de la sección
            student.program_id = program_id # Vinculamos al alumno con la carrera
            
            db.commit()
            session['flash_message'] = f"¡Éxito! Inscrito en {section.section_code} para el programa seleccionado."
            return redirect('/transactions/enrollments/list')

        # --- LÓGICA DE CARGA DEL FORMULARIO (GET) ---
        programs = db.query(Program).all()
        
        context = {
            'student': student,  # Pasamos el objeto student para evitar el error de Jinja2
            'programs': programs,
            'user_name': session.get('user_name'),
            'flash_message': session.pop('flash_message', None)
        }
        
        # IMPORTANTE: Asegúrate de que la ruta del template sea exacta a la de tu proyecto
        html = render_template('transactions/enrollments_create.html', **context)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

    except Exception as e:
        db.rollback()
        print(f"Error en enrollment_create: {str(e)}")
        session['flash_message'] = "Ocurrió un error interno al procesar la solicitud."
        return redirect('/transactions/enrollments/list')
    finally:
        db.close()


@login_required
def enrollments_delete(environ, enrollment_id):
    db = SessionLocal()
    session = environ['beaker.session']
    
    # Extraer el ID de la inscripción desde la URL (dependiendo de tu enrutador)
    # Por ejemplo, si tu URL es /delete/5
    path_parts = environ['PATH_INFO'].split('/')
    enrollment_id = int(path_parts[-1])

    try:
        # 1. Buscar la inscripción para saber la sección
        target = db.query(Enrollment).filter(Enrollment.enrollment_id == enrollment_id).first()
        
        if target:
            section_id = target.section_id
            student_id = target.student_user_id
            
            # 2. Borrar TODAS las materias de ese alumno en esa sección
            db.query(Enrollment).filter(
                Enrollment.student_user_id == student_id,
                Enrollment.section_id == section_id
            ).delete()
            
            # 3. DEVOLVER EL CUPO (+1)
            section = db.query(Section).filter(Section.section_id == section_id).first()
            if section:
                section.capacity += 1
            
            db.commit()
            session['flash_message'] = "Inscripción anulada y cupo devuelto exitosamente."
        
        return redirect('/transactions/enrollments/list')

    except Exception as e:
        db.rollback()
        print(f"Error al eliminar: {e}")
        return redirect('/transactions/enrollments/list')
    finally:
        db.close()