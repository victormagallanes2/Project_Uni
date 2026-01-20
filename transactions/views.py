# transactions/views.py - Módulo de Transacciones: Pagos y Matrícula
import os
import datetime
from datetime import datetime, date
from werkzeug.wrappers import Request
from werkzeug.utils import secure_filename
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
from fees.models import FeeSchedule
from sqlalchemy import or_
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
        # Consultamos agrupando por estudiante para no repetir filas por materia
        # Usamos func.max para obtener la fecha más reciente de inscripción si hubiera varias
        enrollments = db.query(Enrollment).group_by(Enrollment.student_user_id).order_by(Enrollment.enrollment_id.desc()).all()
        
        # Mapeo de pagos (igual que antes)
        all_payments = db.query(Payment).all()
        payment_map = { (p.student_user_id, p.program_id): p for p in all_payments }

        context = {
            'enrollments': enrollments,
            'payment_map': payment_map,
            'user_name': session.get('user_name')
        }
        
        html = render_template('transactions/enrollments_list.html', **context)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
    
    except Exception as e:
        print(f"Error en enrollment_list: {e}")
        return "500 Internal Server Error", [('Content-type', 'text/plain')], [b"Error al cargar la lista"]
    finally:
        db.close()




# Configuración de carpetas
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'payments')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def parse_form_data_with_files(environ):
    # Werkzeug maneja el flujo de datos (stream) de forma segura
    stream, form, files = parse_form_data(environ)
    return form, files


@login_required
def enrollments_create(environ):
    db = SessionLocal()
    session = environ['beaker.session']
    
    try:
        # --- LÓGICA DE PROCESAMIENTO (POST) ---
        if environ['REQUEST_METHOD'] == 'POST':
            request = Request(environ)
            
            # Obtenemos datos del formulario (ahora el administrativo elige al estudiante)
            target_student_id = request.form.get('student_id', type=int)
            program_id = request.form.get('program_id', type=int)
            bank_ref = request.form.get('bank_reference')
            file_item = request.files.get('voucher')

            # Validar existencia del estudiante
            student = db.query(User).filter(User.id == target_student_id).first()
            if not student:
                session['flash_message'] = "Error: Estudiante no seleccionado o no encontrado."
                return redirect('/transactions/enrollments/create')

            # 1. Buscar el costo configurado (FeeSchedule)
            fee = db.query(FeeSchedule).filter(FeeSchedule.program_id == program_id).first()
            if not fee:
                session['flash_message'] = "Error: El programa no tiene un costo (FeeSchedule) configurado."
                return redirect('/transactions/enrollments/create')

            # 2. Procesar el archivo del Voucher
            filename = None
            if file_item and file_item.filename:
                ext = os.path.splitext(file_item.filename)[1]
                # Nombre de archivo seguro y único
                filename = secure_filename(f"V_STU{target_student_id}_{bank_ref}{ext}")
                file_item.save(os.path.join(UPLOAD_FOLDER, filename))

            # 3. Buscar Sección con cupo (Llenado secuencial)
            section = db.query(Section).join(Section.subjects).join(SectionSubject.subject)\
                .filter(Subject.program_id == program_id)\
                .filter(Section.capacity > 0)\
                .order_by(asc(Section.section_id)).with_for_update().first()

            if not section:
                session['flash_message'] = "No hay cupos disponibles para este programa."
                return redirect('/transactions/enrollments/create')

            # --- OPERACIÓN ATÓMICA ---
            # 4. Registrar Pago (Aprobado por ser administrativo)
            new_payment = Payment(
                student_user_id=target_student_id,
                program_id=program_id,
                concept_id=fee.concept_id,
                amount=fee.value_bs,
                bank_reference=bank_ref,
                proof_url=filename,
                payment_date=datetime.now(),
                status='Approved' 
            )
            db.add(new_payment)

            # 5. Inscribir materias del programa
            subjects = db.query(Subject).filter(Subject.program_id == program_id).all()
            for sub in subjects:
                db.add(Enrollment(
                    student_user_id=target_student_id,
                    section_id=section.section_id,
                    subject_id=sub.subject_id,
                    enrollment_date=datetime.now().date()
                ))

            # 6. Actualizar cupo y vincular programa al estudiante
            section.capacity -= 1
            student.program_id = program_id
            
            db.commit()
            session['flash_message'] = f"¡Éxito! {student.name} inscrito en {section.section_code}."
            return redirect('/transactions/enrollments/list')

        # --- LÓGICA DE CARGA (GET) ---
        # Filtramos usuarios que NO estén inscritos (program_id es None)
        available_students = db.query(User).all()
        programs = db.query(Program).all()
        
        context = {
            'students': available_students,
            'programs': programs,
            'user_name': session.get('user_name'),
            'flash_message': session.pop('flash_message', None)
        }
        
        html = render_template('transactions/enrollments_create.html', **context)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

    except Exception as e:
        db.rollback()
        print(f"Error en enrollment_create: {str(e)}")
        session['flash_message'] = f"Error crítico: {str(e)}"
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