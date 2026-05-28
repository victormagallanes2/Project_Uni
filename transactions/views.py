
import os
import datetime
from datetime import datetime, date
from werkzeug.wrappers import Request
from werkzeug.utils import secure_filename
from urllib.parse import parse_qs
from sqlalchemy.orm import joinedload
from sqlalchemy import func, asc

from db import SessionLocal 
from fees.models import FeeConcept, Payment
from academic.models import AcademicTerm, Cohort, Subject, Program, StudentGrade, ProgramSubject
from users.models import User 
from core.views import render_template, login_required, generate_csrf_token, parse_date_safely, redirect, parse_form_data
from transactions.models import Enrollment
from datetime import date
from fees.models import FeeSchedule
from sqlalchemy import or_
from sqlalchemy import text
from users.models import User, UserType 


# transactions/views.py - Agregar

def api_available_subjects(environ):
    """API para obtener materias disponibles para un estudiante"""
    from urllib.parse import parse_qs
    import json
    
    db = SessionLocal()
    
    try:
        query_string = environ.get('QUERY_STRING', '')
        params = parse_qs(query_string)
        
        student_id = params.get('student_id', [None])[0]
        program_id = params.get('program_id', [None])[0]
        
        if not student_id or not program_id:
            result = {'error': 'Faltan parámetros', 'subjects': []}
            return "400 Bad Request", [('Content-type', 'application/json')], [json.dumps(result).encode('utf-8')]
        
        # Obtener materias disponibles y período actual
        available_subjects, current_period = get_available_subjects_for_student(
            db, int(student_id), int(program_id)
        )
        
        result = {
            'subjects': [{
                'subject_id': s.subject_id,
                'code': s.code,
                'name': s.name,
                'credits': s.credits
            } for s in available_subjects],
            'current_period': current_period
        }
        
        return "200 OK", [('Content-type', 'application/json')], [json.dumps(result).encode('utf-8')]
        
    except Exception as e:
        print(f"Error en API: {e}")
        result = {'error': str(e), 'subjects': []}
        return "500 Internal Server Error", [('Content-type', 'application/json')], [json.dumps(result).encode('utf-8')]
        
    finally:
        db.close()





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
    flash_message = session.pop('flash_message', None)
    
    try:
        # Agrupamos por estudiante para tener una fila por proceso de inscripción
        enrollments = db.query(Enrollment).group_by(Enrollment.student_user_id).order_by(Enrollment.enrollment_id.desc()).all()
        
        all_payments = db.query(Payment).all()
        payment_map = { (p.student_user_id, p.program_id): p for p in all_payments }

        context = {
            'enrollments': enrollments,
            'payment_map': payment_map,
            'user_name': session.get('user_name'),
            'flash_message': flash_message
        }
        
        return "200 OK", [('Content-type', 'text/html')], [
            render_template('transactions/enrollments_list.html', **context).encode('utf-8')
        ]
    finally:
        db.close()


def get_current_period_for_student(db, student_id, program_id):
    """Calcula en qué período del plan va el estudiante"""
    
    # Obtener materias aprobadas
    approved_count = db.query(StudentGrade).filter(
        StudentGrade.student_user_id == student_id,
        StudentGrade.status == 'Approved'
    ).count()
    
    # Obtener total de materias por período (promedio)
    subjects_per_period = db.query(
        ProgramSubject.period_number, 
        func.count(ProgramSubject.subject_id).label('count')
    ).filter(
        ProgramSubject.program_id == program_id
    ).group_by(ProgramSubject.period_number).all()
    
    # Calcular período actual basado en materias aprobadas
    cumulative = 0
    for period_data in subjects_per_period:
        cumulative += period_data.count
        if approved_count < cumulative:
            return period_data.period_number
    
    return 1



# Configuración de carpetas
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'payments')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def parse_form_data_with_files(environ):
    # Werkzeug maneja el flujo de datos (stream) de forma segura
    stream, form, files = parse_form_data(environ)
    return form, files


def get_available_subjects_for_student(db, student_id, program_id):
    """Retorna las materias que el estudiante puede inscribir en su período actual"""
    
    # 1. Obtener el período actual del estudiante según materias aprobadas
    current_period = get_current_period_for_student(db, student_id, program_id)
    
    # 2. Obtener materias del programa para este período
    program_subjects = db.query(ProgramSubject).filter(
        ProgramSubject.program_id == program_id,
        ProgramSubject.period_number == current_period
    ).all()
    program_subject_ids = [ps.subject_id for ps in program_subjects]
    
    # 3. Obtener materias ya aprobadas
    approved_subjects = db.query(StudentGrade.subject_id).filter(
        StudentGrade.student_user_id == student_id,
        StudentGrade.status == 'Approved'
    ).all()
    approved_ids = [s.subject_id for s in approved_subjects]
    
    # 4. Obtener materias actualmente inscritas
    current_enrollments = db.query(Enrollment.subject_id).filter(
        Enrollment.student_user_id == student_id,
        Enrollment.status == 'Registered'
    ).all()
    enrolled_ids = [e.subject_id for e in current_enrollments]
    
    # 5. Filtrar materias disponibles
    available = []
    for ps in program_subjects:
        if ps.subject_id not in approved_ids and ps.subject_id not in enrolled_ids:
            available.append(ps.subject)
    
    return available, current_period

def get_current_period_for_student(db, student_id, program_id):
    """Calcula en qué período del plan va el estudiante según materias aprobadas"""
    
    # Obtener materias aprobadas
    approved_count = db.query(StudentGrade).filter(
        StudentGrade.student_user_id == student_id,
        StudentGrade.status == 'Approved'
    ).count()
    
    # Obtener total de materias por período
    subjects_per_period = db.query(
        ProgramSubject.period_number, 
        func.count(ProgramSubject.subject_id).label('count')
    ).filter(
        ProgramSubject.program_id == program_id
    ).group_by(ProgramSubject.period_number).all()
    
    # Si no hay materias configuradas, retornar período 1
    if not subjects_per_period:
        return 1
    
    # Calcular período actual basado en materias aprobadas
    cumulative = 0
    for period_data in subjects_per_period:
        cumulative += period_data.count
        if approved_count < cumulative:
            return period_data.period_number
    
    # Si ya aprobó todas, retornar el último período
    return subjects_per_period[-1].period_number


@login_required
def enrollments_create(environ):
    db = SessionLocal()
    session = environ['beaker.session']
    
    try:
        if environ['REQUEST_METHOD'] == 'POST':
            request = Request(environ)
            
            target_student_id = request.form.get('student_id', type=int)
            program_id = request.form.get('program_id', type=int)
            term_id = request.form.get('term_id', type=int)
            selected_subjects = request.form.getlist('subjects')
            bank_ref = request.form.get('bank_reference')
            file_item = request.files.get('voucher')
            
            student = db.query(User).filter(User.id == target_student_id).first()
            if not student:
                session['flash_message'] = "Error: Estudiante no seleccionado o no encontrado."
                return redirect('/transactions/enrollments/create')
            
            program = db.query(Program).filter(Program.program_id == program_id).first()
            if not program:
                session['flash_message'] = "Error: Programa no válido."
                return redirect('/transactions/enrollments/create')
            
            term = db.query(AcademicTerm).filter(AcademicTerm.term_id == term_id).first()
            if not term:
                session['flash_message'] = "Error: Período académico no válido."
                return redirect('/transactions/enrollments/create')
            
            if not selected_subjects:
                session['flash_message'] = "Error: Debe seleccionar al menos una materia."
                return redirect('/transactions/enrollments/create')
            
            # Obtener materias disponibles automáticamente
            available_subjects, current_period = get_available_subjects_for_student(db, target_student_id, program_id)
            available_ids = [s.subject_id for s in available_subjects]
            
            for subject_id in selected_subjects:
                if int(subject_id) not in available_ids:
                    session['flash_message'] = "Error: Una de las materias seleccionadas no está disponible."
                    return redirect('/transactions/enrollments/create')
            
            fee = db.query(FeeSchedule).filter(FeeSchedule.program_id == program_id).first()
            if not fee:
                session['flash_message'] = "Error: El programa no tiene un costo configurado."
                return redirect('/transactions/enrollments/create')
            
            filename = None
            if file_item and file_item.filename:
                ext = os.path.splitext(file_item.filename)[1]
                filename = secure_filename(f"V_STU{target_student_id}_{bank_ref}{ext}")
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file_item.save(file_path)
            
            cohort = db.query(Cohort).filter(
                Cohort.program_id == program_id,
                Cohort.capacity > 0
            ).order_by(asc(Cohort.cohort_id)).with_for_update().first()
            
            if not cohort:
                session['flash_message'] = "No hay cupos disponibles para este programa."
                return redirect('/transactions/enrollments/create')
            
            try:
                new_payment = Payment(
                    student_user_id=target_student_id,
                    program_id=program_id,
                    concept_id=fee.concept_id,
                    amount=fee.value_bs,
                    bank_reference=bank_ref,
                    proof_url=filename,
                    payment_date=datetime.now(),
                    status='Pending Verification'
                )
                db.add(new_payment)
                
                for subject_id in selected_subjects:
                    enrollment = Enrollment(
                        student_user_id=target_student_id,
                        cohort_id=cohort.cohort_id,
                        subject_id=int(subject_id),
                        term_id=term_id,
                        enrollment_date=datetime.now().date(),
                        status='Registered'
                    )
                    db.add(enrollment)
                
                cohort.capacity -= 1
                student.program_id = program_id
                
                db.commit()
                
                period_text = f"Período {current_period} del plan"
                session['flash_message'] = f"¡Éxito! {student.name} {student.last_name} inscrito en {len(selected_subjects)} materias ({period_text}) para {term.name}"
                
            except Exception as e:
                db.rollback()
                session['flash_message'] = f"Error al procesar la inscripción: {str(e)}"
            
            return redirect('/transactions/enrollments/list')
        
        # GET - Mostrar formulario
        available_students = db.query(User).filter(User.user_type_id == 4).all()
        programs = db.query(Program).all()
        terms = db.query(AcademicTerm).order_by(AcademicTerm.start_date.desc()).all()
        
        context = {
            'students': available_students,
            'programs': programs,
            'terms': terms,
            'user_name': session.get('user_name'),
            'flash_message': session.pop('flash_message', None),
            'csrf_token': session.get('csrf_token', '')
        }
        
        html = render_template('transactions/enrollments_create.html', **context)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
        
    except Exception as e:
        db.rollback()
        session['flash_message'] = f"Error crítico: {str(e)}"
        return redirect('/transactions/enrollments/list')
    finally:
        db.close()


@login_required
def enrollments_edit(environ, enrollment_id):
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf_token()
    
    try:
        # Buscar la inscripción con todas sus relaciones
        enrollment = db.query(Enrollment).options(
            joinedload(Enrollment.student),
            joinedload(Enrollment.subject).joinedload(Subject.program),
            joinedload(Enrollment.term),
            joinedload(Enrollment.section)
        ).filter(Enrollment.enrollment_id == enrollment_id).first()
        
        if not enrollment:
            session['flash_message'] = "Error: Inscripción no encontrada."
            return redirect('/transactions/enrollments/list')
        
        # Buscar el pago asociado
        payment = db.query(Payment).filter(
            Payment.student_user_id == enrollment.student_user_id,
            Payment.program_id == enrollment.subject.program_id
        ).first()
        
        if environ['REQUEST_METHOD'] == 'POST':
            request = Request(environ)
            
            program_id = request.form.get('program_id', type=int)
            term_id = request.form.get('term_id', type=int)
            bank_reference = request.form.get('bank_reference')
            payment_status = request.form.get('payment_status')
            
            # Si cambió el programa
            if program_id != enrollment.subject.program_id:
                # Buscar nueva sección con cupo
                new_section = db.query(Section).join(Section.subjects).join(SectionSubject.subject)\
                    .filter(Subject.program_id == program_id)\
                    .filter(Section.capacity > 0)\
                    .order_by(asc(Section.section_id)).with_for_update().first()
                
                if not new_section:
                    session['flash_message'] = "No hay cupos disponibles para el nuevo programa."
                    return redirect(f'/transactions/enrollments/{enrollment_id}/edit')
                
                # Actualizar todas las materias a la nueva sección
                db.query(Enrollment).filter(
                    Enrollment.student_user_id == enrollment.student_user_id,
                    Enrollment.term_id == enrollment.term_id
                ).update({'section_id': new_section.section_id})
                
                # Liberar cupo de la sección anterior
                old_section = db.query(Section).filter(Section.section_id == enrollment.section_id).first()
                if old_section:
                    old_section.capacity += 1
                
                new_section.capacity -= 1
                enrollment.student.program_id = program_id
            
            # Actualizar período
            if term_id != enrollment.term_id:
                db.query(Enrollment).filter(
                    Enrollment.student_user_id == enrollment.student_user_id,
                    Enrollment.term_id == enrollment.term_id
                ).update({'term_id': term_id})
            
            # Actualizar pago
            if payment:
                payment.bank_reference = bank_reference
                payment.status = payment_status
            else:
                # Crear nuevo pago si no existe
                fee = db.query(FeeSchedule).filter(FeeSchedule.program_id == program_id).first()
                if fee:
                    new_payment = Payment(
                        student_user_id=enrollment.student_user_id,
                        program_id=program_id,
                        concept_id=fee.concept_id,
                        amount=fee.value_bs,
                        bank_reference=bank_reference,
                        payment_date=datetime.now(),
                        status=payment_status
                    )
                    db.add(new_payment)
            
            db.commit()
            session['flash_message'] = "Inscripción actualizada exitosamente."
            return redirect('/transactions/enrollments/list')
        
        # GET - Mostrar formulario
        programs = db.query(Program).all()
        terms = db.query(AcademicTerm).order_by(AcademicTerm.start_date.desc()).all()
        
        context = {
            'enrollment': enrollment,
            'payment': payment,
            'programs': programs,
            'terms': terms,
            'csrf_token': session['csrf_token'],
            'flash_message': session.pop('flash_message', None),
            'user_name': session.get('user_name')
        }
        
        html = render_template('transactions/enrollments_edit.html', **context)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
        
    except Exception as e:
        db.rollback()
        print(f"Error en enrollments_edit: {e}")
        session['flash_message'] = f"Error: {str(e)}"
        return redirect('/transactions/enrollments/list')
    finally:
        db.close()



@login_required
def enrollments_delete(environ, enrollment_id):
    db = SessionLocal()
    session = environ['beaker.session']
    
    # Extraer el ID de la inscripción desde la URL
    path_parts = environ['PATH_INFO'].split('/')
    enrollment_id = int(path_parts[-1])

    try:
        # 1. Buscar la inscripción para identificar al alumno y la sección
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

            # 4. LIMPIAR EL PROGRAM_ID DEL USUARIO (Lo que solicitaste)
            user = db.query(User).filter(User.id == student_id).first()
            if user:
                user.program_id = None # O user.program_id = "" según tu BD
            
            db.commit()
            session['flash_message'] = "Inscripción anulada, cupo devuelto y perfil del alumno liberado."
        
        return redirect('/transactions/enrollments/list')

    except Exception as e:
        db.rollback()
        print(f"Error al eliminar: {e}")
        return redirect('/transactions/enrollments/list')
    finally:
        db.close()


