
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
from academic.models import AcademicTerm, Section, Subject, SectionSubject, Program
from users.models import User 
from core.views import render_template, login_required, generate_csrf_token, parse_date_safely, redirect, parse_form_data
from transactions.models import Enrollment
from datetime import date
from fees.models import FeeSchedule
from sqlalchemy import or_
from sqlalchemy import text
from users.models import User, UserType 


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
        # Agrupamos por estudiante para tener una fila por proceso de inscripción
        enrollments = db.query(Enrollment).group_by(Enrollment.student_user_id).order_by(Enrollment.enrollment_id.desc()).all()
        
        all_payments = db.query(Payment).all()
        payment_map = { (p.student_user_id, p.program_id): p for p in all_payments }

        context = {
            'enrollments': enrollments,
            'payment_map': payment_map,
            'user_name': session.get('user_name')
        }
        
        return "200 OK", [('Content-type', 'text/html')], [
            render_template('transactions/enrollments_list.html', **context).encode('utf-8')
        ]
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
    """Vista para inscripción manual de estudiantes (solo administradores)"""
    
    print("\n" + "="*50)
    print("📍 ENROLLMENTS_CREATE - INICIO")
    print("="*50)
    
    db = SessionLocal()
    session = environ['beaker.session']
    
    try:
        # --- VERIFICACIÓN INICIAL DE LA BASE DE DATOS ---
        print("\n📊 VERIFICACIÓN DE BASE DE DATOS:")
        
        # 1. Verificar todas las tablas y sus registros
        tables = ['users', 'user_types', 'programs', 'academic_terms', 'subjects', 'sections']
        for table in tables:
            try:
                count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"  - Tabla {table}: {count} registros")
            except Exception as e:
                print(f"  - Tabla {table}: ERROR - {e}")
        
        # 2. Verificar tipos de usuario
        print("\n👥 TIPOS DE USUARIO:")
        user_types = db.query(UserType).all()
        if user_types:
            for ut in user_types:
                count = db.query(User).filter(User.user_type_id == ut.id).count()
                print(f"  - Tipo {ut.id}: {ut.name} - {count} usuarios")
        else:
            print("  ⚠️ No hay tipos de usuario definidos")
        
        # 3. Verificar TODOS los usuarios (sin filtro)
        print("\n👤 TODOS LOS USUARIOS:")
        all_users = db.query(User).all()
        print(f"  Total usuarios en BD: {len(all_users)}")
        for user in all_users[:5]:  # Mostrar primeros 5
            user_type_name = user.user_type.name if user.user_type else "SIN TIPO"
            print(f"  - ID: {user.id}, Tipo: {user.user_type_id} ({user_type_name}), "
                  f"Cédula: {user.national_id}, Nombre: {user.name} {user.last_name}")
        
        # 4. Verificar estudiantes (tipo 3)
        print("\n🎓 ESTUDIANTES (user_type_id = 3):")
        students_count = db.query(User).filter(User.user_type_id == 3).count()
        print(f"  Total estudiantes: {students_count}")
        
        if students_count > 0:
            students_sample = db.query(User).filter(User.user_type_id == 3).limit(3).all()
            for s in students_sample:
                print(f"  - {s.national_id} - {s.name} {s.last_name} (ID: {s.id})")
        else:
            print("  ⚠️ NO HAY ESTUDIANTES con user_type_id = 3")
            
            # Sugerencia: crear estudiante de prueba
            print("\n💡 SUGERENCIA: Ejecuta este script para crear un estudiante de prueba:")
            print("""
from db import SessionLocal
from users.models import User, UserType
import bcrypt

db = SessionLocal()

# Crear tipo estudiante si no existe
if not db.query(UserType).filter(UserType.id == 3).first():
    db.add(UserType(id=3, name="Estudiante"))
    db.commit()
    print("✅ Tipo estudiante creado")

# Crear estudiante de prueba
student = User(
    national_id="V-12345678",
    name="Juan",
    last_name="Pérez",
    email="juan.perez@test.com",
    password=bcrypt.hashpw("123456".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
    user_type_id=3
)
db.add(student)
db.commit()
print("✅ Estudiante creado")
db.close()
""")
        
        # 5. Verificar programas
        print("\n📚 PROGRAMAS:")
        programs = db.query(Program).all()
        print(f"  Total programas: {len(programs)}")
        for p in programs:
            subjects_count = db.query(Subject).filter(Subject.program_id == p.program_id).count()
            print(f"  - {p.name} (ID: {p.program_id}) - {subjects_count} materias")
        
        # 6. Verificar períodos académicos
        print("\n📅 PERÍODOS ACADÉMICOS:")
        terms = db.query(AcademicTerm).order_by(AcademicTerm.start_date.desc()).all()
        print(f"  Total períodos: {len(terms)}")
        for t in terms:
            print(f"  - {t.name} (ID: {t.term_id}): {t.start_date} a {t.end_date}")
        
        print("\n" + "="*50)
        
        # --- PROCESAMIENTO POST ---
        if environ['REQUEST_METHOD'] == 'POST':
            print("\n📝 PROCESANDO POST")
            
            request = Request(environ)
            
            target_student_id = request.form.get('student_id', type=int)
            program_id = request.form.get('program_id', type=int)
            term_id = request.form.get('term_id', type=int)
            bank_ref = request.form.get('bank_reference')
            file_item = request.files.get('voucher')
            
            print(f"  Datos recibidos:")
            print(f"    - student_id: {target_student_id}")
            print(f"    - program_id: {program_id}")
            print(f"    - term_id: {term_id}")
            print(f"    - bank_ref: {bank_ref}")
            print(f"    - file: {file_item.filename if file_item else 'None'}")
            
            # Validar existencia del estudiante
            student = db.query(User).filter(User.id == target_student_id).first()
            if not student:
                print(f"  ❌ Estudiante no encontrado: {target_student_id}")
                session['flash_message'] = "Error: Estudiante no seleccionado o no encontrado."
                return redirect('/transactions/enrollments/create')
            
            print(f"  ✅ Estudiante encontrado: {student.name} {student.last_name}")
            
            # Validar programa
            program = db.query(Program).filter(Program.program_id == program_id).first()
            if not program:
                print(f"  ❌ Programa no encontrado: {program_id}")
                session['flash_message'] = "Error: Programa no válido."
                return redirect('/transactions/enrollments/create')
            
            # Validar período
            term = db.query(AcademicTerm).filter(AcademicTerm.term_id == term_id).first()
            if not term:
                print(f"  ❌ Período no encontrado: {term_id}")
                session['flash_message'] = "Error: Período académico no válido."
                return redirect('/transactions/enrollments/create')
            
            # Buscar el costo configurado
            fee = db.query(FeeSchedule).filter(FeeSchedule.program_id == program_id).first()
            if not fee:
                print(f"  ❌ FeeSchedule no encontrado para programa {program_id}")
                session['flash_message'] = "Error: El programa no tiene un costo configurado."
                return redirect('/transactions/enrollments/create')
            
            # Procesar el archivo
            filename = None
            if file_item and file_item.filename:
                ext = os.path.splitext(file_item.filename)[1]
                filename = secure_filename(f"V_STU{target_student_id}_{bank_ref}{ext}")
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file_item.save(file_path)
                print(f"  ✅ Archivo guardado: {filename}")
            
            # Buscar sección con cupo
            section = db.query(Section).join(Section.subjects).join(SectionSubject.subject)\
                .filter(Subject.program_id == program_id)\
                .filter(Section.capacity > 0)\
                .order_by(asc(Section.section_id)).with_for_update().first()
            
            if not section:
                print(f"  ❌ No hay cupos disponibles para programa {program_id}")
                session['flash_message'] = "No hay cupos disponibles para este programa."
                return redirect('/transactions/enrollments/create')
            
            print(f"  ✅ Sección encontrada: {section.section_code} (cupo: {section.capacity})")
            
            # --- TRANSACCIÓN ---
            try:
                # Registrar pago
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
                print(f"  ✅ Pago registrado")
                
                # Inscribir materias
                subjects = db.query(Subject).filter(Subject.program_id == program_id).all()
                print(f"  📚 Materias a inscribir: {len(subjects)}")
                
                for sub in subjects:
                    enrollment = Enrollment(
                        student_user_id=target_student_id,
                        section_id=section.section_id,
                        subject_id=sub.subject_id,
                        term_id=term_id,
                        enrollment_date=datetime.now().date(),
                        status='Registered'
                    )
                    db.add(enrollment)
                    print(f"    - {sub.code} - {sub.name}")
                
                # Actualizar cupo y programa del estudiante
                section.capacity -= 1
                student.program_id = program_id
                
                db.commit()
                print(f"  ✅ TRANSACCIÓN COMPLETADA")
                
                session['flash_message'] = f"¡Éxito! {student.name} {student.last_name} inscrito en {program.name} para {term.name}"
                
            except Exception as e:
                db.rollback()
                print(f"  ❌ ERROR EN TRANSACCIÓN: {str(e)}")
                session['flash_message'] = f"Error al procesar la inscripción: {str(e)}"
            
            return redirect('/transactions/enrollments/list')
        
        # --- GET - Mostrar formulario ---
        print("\n📋 CARGANDO FORMULARIO GET")
        
        # Obtener estudiantes (SOLO tipo 3)
        available_students = db.query(User).filter(User.user_type_id == 4).all()
        print(f"  Estudiantes encontrados: {len(available_students)}")
        
        # Obtener programas
        programs = db.query(Program).all()
        print(f"  Programas encontrados: {len(programs)}")
        
        # Obtener períodos
        terms = db.query(AcademicTerm).order_by(AcademicTerm.start_date.desc()).all()
        print(f"  Períodos encontrados: {len(terms)}")
        
        # Verificar si hay datos para Select2
        if available_students:
            print(f"\n  📋 Datos para Select2 (primeros 5):")
            for s in available_students[:5]:
                print(f"    - ID: {s.id} | {s.national_id} - {s.name} {s.last_name}")
        else:
            print("\n  ⚠️ ADVERTENCIA: No hay estudiantes para mostrar en Select2")
        
        print("="*50 + "\n")
        
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
        print(f"\n❌ ERROR GENERAL: {str(e)}")
        import traceback
        traceback.print_exc()
        session['flash_message'] = f"Error crítico: {str(e)}"
        return redirect('/transactions/enrollments/list')
    finally:
        db.close()
        print("📌 ENROLLMENTS_CREATE - FIN\n")

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


