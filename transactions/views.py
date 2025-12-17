# transactions/views.py - Módulo de Transacciones: Pagos y Matrícula

import datetime
from urllib.parse import parse_qs
from sqlalchemy.orm import joinedload
from sqlalchemy import func

# Importaciones CRÍTICAS
from db import SessionLocal 
from fees.models import FeeConcept, Payment, Enrollment # Asumo que Enrollment está aquí
from academic.models import AcademicTerm, Section, Subject # Necesario para Enrollment
from users.models import User 
from core.views import render_template, login_required, generate_csrf_token, parse_date_safely 


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


# R: Read (Listado Estudiante)
@login_required
def enrollment_list_student(environ, student_user_id):
    """Muestra las secciones en las que está inscrito un estudiante."""
    db = SessionLocal()
    session = environ['beaker.session']
    flash_message = session.pop('flash_message', None)
    
    try:
        enrollments = db.query(Enrollment) \
            .filter(Enrollment.student_user_id == student_user_id) \
            .options(joinedload(Enrollment.section).joinedload(Section.subject)) \
            .order_by(Enrollment.enrollment_date.desc()) \
            .all()
        
        html = render_template('transactions/enrollment_list_student.html', enrollments=enrollments, flash_message=flash_message)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
    finally:
        db.close()

# R: Read (Listado Admin)
@login_required
def enrollment_list_admin(environ):
    """Muestra todas las matrículas del sistema."""
    db = SessionLocal()
    session = environ['beaker.session']
    flash_message = session.pop('flash_message', None)
    
    try:
        enrollments = db.query(Enrollment) \
            .options(
                joinedload(Enrollment.student),
                joinedload(Enrollment.section).joinedload(Section.subject),
                joinedload(Enrollment.section).joinedload(Section.term)
            ) \
            .order_by(Enrollment.enrollment_date.desc()) \
            .all()
        
        html = render_template('transactions/enrollment_list_admin.html', enrollments=enrollments, flash_message=flash_message)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
    finally:
        db.close()