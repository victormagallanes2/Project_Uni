import os
import datetime
from datetime import datetime, date
from werkzeug.wrappers import Request
from werkzeug.utils import secure_filename
from urllib.parse import parse_qs
from sqlalchemy.orm import joinedload
from sqlalchemy import func, asc, or_
from db import SessionLocal
from users.models import User
from core.views import render_template, login_required, generate_csrf_token, parse_date_safely, redirect, parse_form_data
from transactions.models import Enrollment
from academic.models import AcademicTerm, Section, Subject, SectionSubject, Program
from urllib.parse import parse_qs
import bcrypt
from fees.models import FeeSchedule, Payment, FeeConcept
from werkzeug.security import generate_password_hash, check_password_hash



def web(environ):
    session = environ.get('beaker.session')
    user_name = session.get('user_name') if session else None
    message = session.pop('flash_message', None)
    html = render_template(
        'index.html', 
        title='Página Principal', 
        user_name=user_name,
        session=session,
        flash_message=message
    )
    return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]



# Configuración de carpetas
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'payments')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@login_required
def student_enrollment_self(environ):
    db = SessionLocal()
    session = environ['beaker.session']
    user_id = int(session.get('user_id'))
    
    request = Request(environ)
    
    try:
        student = db.query(User).filter(User.id == user_id).first()
        
        # Verificar inscripción activa
        if student.program_id:
            session['flash_message'] = "⚠️ Ya tienes una inscripción activa."
            return redirect('/')

        # Obtener períodos con inscripción abierta
        current_date = date.today()
        active_terms = db.query(AcademicTerm).filter(
            AcademicTerm.enrollment_start_date <= current_date,
            AcademicTerm.enrollment_end_date >= current_date
        ).all()

        if request.method == 'POST':
            program_id = request.form.get('program_id', type=int)
            term_id = request.form.get('term_id', type=int)  # <--- NUEVO
            bank_ref = request.form.get('bank_reference')
            file_item = request.files.get('voucher')

            # Validaciones
            if not term_id:
                session['flash_message'] = "❌ Debe seleccionar un período académico."
                return redirect('/web/enrollments/create')

            if not file_item or file_item.filename == '':
                session['flash_message'] = "❌ Debes adjuntar la foto del comprobante."
                return redirect('/web/enrollments/create')

            # Verificar que el período esté activo
            selected_term = db.query(AcademicTerm).get(term_id)
            if not (selected_term.enrollment_start_date <= current_date <= selected_term.enrollment_end_date):
                session['flash_message'] = "❌ El período seleccionado no está disponible para inscripción."
                return redirect('/web/enrollments/create')

            fee = db.query(FeeSchedule).filter(FeeSchedule.program_id == program_id).first()
            if not fee:
                session['flash_message'] = "❌ Este programa no tiene costo configurado."
                return redirect('/web/enrollments/create')
            
            # Guardar archivo
            ext = os.path.splitext(file_item.filename)[1].lower()
            filename = secure_filename(f"STU_{user_id}_REF_{bank_ref}{ext}")
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file_item.save(file_path)

            # Buscar sección con cupo para este período
            section = db.query(Section).filter(
                Section.term_id == term_id,  # <--- FILTRAR POR PERÍODO
                Section.capacity > 0
            ).order_by(asc(Section.section_id)).with_for_update().first()

            if not section:
                session['flash_message'] = "❌ Cupos agotados para este período."
                return redirect('/web/enrollments/create')

            # --- Transacción ---
            new_payment = Payment(
                student_user_id=user_id,
                program_id=program_id,
                concept_id=fee.concept_id,
                amount=fee.value_bs,
                bank_reference=bank_ref,
                proof_url=filename,
                status='Pending Verification'
            )
            db.add(new_payment)

            # Inscribir materias
            subjects = db.query(Subject).filter(Subject.program_id == program_id).all()
            for sub in subjects:
                enrollment = Enrollment(
                    student_user_id=user_id,
                    section_id=section.section_id,
                    subject_id=sub.subject_id,
                    term_id=term_id,  # <--- NUEVO
                    enrollment_date=datetime.now().date(),
                    status='Pending'  # Pendiente hasta verificar pago
                )
                db.add(enrollment)

            section.capacity -= 1
            student.program_id = program_id
            db.commit()

            session['flash_message'] = "✅ ¡Solicitud de inscripción enviada! Pendiente de validación."
            return redirect('/web/enrollments/create')

        # GET - Mostrar formulario
        programs = db.query(Program).all()
        
        return "200 OK", [('Content-type', 'text/html')], [
            render_template('web/enrollment_self.html', 
                           student=student, 
                           programs=programs,
                           terms=active_terms,  # <--- NUEVO: Pasar períodos al template
                           flash_message=session.pop('flash_message', None)).encode('utf-8')
        ]
        
    except Exception as e:
        db.rollback()
        print(f"ERROR EN INSCRIPCIÓN: {str(e)}")
        session['flash_message'] = "❌ Error en el proceso. Contacte al administrador."
        return redirect('/web/enrollments/create')
    finally:
        db.close()


def student_login(environ):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    flash_msg = session.pop('flash_message', None)
    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf_token() 
    csrf_token = session['csrf_token']

    try:
        if method == 'POST':
            try:
                request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            except ValueError:
                request_body_size = 0
            
            request_body = environ['wsgi.input'].read(request_body_size)
            form_data = parse_qs(request_body.decode('utf-8')) # Aquí form_data se define
            form_token = form_data.get('csrf_token', [''])[0]
            session_token = session.get('csrf_token')

            if not session_token or form_token != session_token:
                print("ALERTA DE SEGURIDAD: Falló la verificación CSRF.")
                error_msg = "Error de seguridad (CSRF). Inténtalo de nuevo."
                if 'csrf_token' in session:
                    del session['csrf_token']
                    
                html = render_template('web/student_login.html', error=error_msg, csrf_token=csrf_token)
                return "403 Forbidden", [('Content-type', 'text/html')], [html.encode('utf-8')]

            if 'csrf_token' in session:
                del session['csrf_token']

            email = form_data.get('email', [''])[0].strip()
            password_input = form_data.get('password', [''])[0]
            user = db.query(User).filter(User.email == email).first()
            is_authenticated = False
            if user:
                stored_hash = user.password.encode('utf-8')
                input_bytes = password_input.encode('utf-8')
                
                if bcrypt.checkpw(input_bytes, stored_hash):
                    is_authenticated = True

            if is_authenticated:
                session['user_id'] = user.id
                session['user_name'] = user.name
                session['logged_in'] = True
                session['flash_message'] = f"¡Bienvenido, {user.name}!"
                status = '302 Found'
                headers = [('Location', '/')]
                return status, headers, [b'Redirecting to dashboard...']
            
            else:
                error_msg = "Credenciales inválidas. Por favor, inténtalo de nuevo."
                session['csrf_token'] = generate_csrf_token() 
                new_csrf_token = session['csrf_token']
                
                html = render_template('web/student_login.html', 
                                       error=error_msg, 
                                       last_email=email, 
                                       csrf_token=new_csrf_token,
                                       flash_message=flash_msg)
                return "401 Unauthorized", [('Content-type', 'text/html')], [html.encode('utf-8')]
                
        else:
            if session.get('logged_in'):
                status = '302 Found'
                headers = [('Location', '/')]
                return status, headers, [b'Redirecting to dashboard...']
            html = render_template('web/student_login.html', csrf_token=csrf_token, flash_message=flash_msg)
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

    except Exception as e:
        print(f"Error al intentar iniciar sesión: {e}")
        # ... (Manejo de error 500) ...
        error_msg = "Ocurrió un error interno. Inténtalo más tarde."
        html = render_template('web/student_login.html', error=error_msg, flash_message=flash_msg)
        return "500 Internal Server Error", [('Content-type', 'text/html')], [html.encode('utf-8')]
        
    finally:
        db.close()


def student_logout(environ):
    try:
        session = environ['beaker.session'] 
        
        # 1. Limpiamos los datos del usuario (quita el user_name, id, etc.)
        session.clear() 
        
        # 2. Guardamos el mensaje de éxito en la sesión limpia
        session['flash_message'] = "Has cerrado sesión exitosamente. ¡Vuelve pronto!"
        session.save() # Es importante guardar los cambios
        
        status = '302 Found'
        headers = [('Location', '/')]
        
        return status, headers, [b'Redirecting to home...']

    except Exception as e:
        print(f"Error al cerrar sesión: {e}")
        status = '302 Found'
        headers = [('Location', '/')] 
        return status, headers, [b'Redirecting...']




def student_register(environ):
    db = SessionLocal()
    session = environ['beaker.session']
    request = Request(environ)
    
    if request.method == 'POST':
        try:
            # Captura de datos
            name = request.form.get('name')
            last_name = request.form.get('last_name')
            national_id = request.form.get('national_id')
            email = request.form.get('email')
            password = request.form.get('password')

            # 1. Validar si la cédula o el email ya existen
            user_exists = db.query(User).filter(
                or_(User.national_id == national_id, User.email == email)
            ).first()

            if user_exists:
                session['flash_message'] = "❌ El correo o la cédula ya se encuentran registrados."
                return redirect('/register')

            # 2. Encriptación con Bcrypt
            # Convertimos a bytes, generamos salt y creamos el hash
            password_bytes = password.encode('utf-8')
            salt = bcrypt.gensalt(rounds=12) # 12 rounds es el estándar de seguridad actual
            hashed_password = bcrypt.hashpw(password_bytes, salt)

            # 3. Crear el nuevo usuario (Rol Estudiante = 2)
            new_user = User(
                name=name,
                last_name=last_name,
                national_id=national_id,
                email=email,
                password=hashed_password.decode('utf-8'), # Guardamos como string en la DB
                user_type_id=3,
            )
            
            db.add(new_user)
            db.commit()
            
            session['flash_message'] = "✅ ¡Registro exitoso! Ya puedes iniciar sesión."
            return redirect('/student_login')

        except Exception as e:
            db.rollback()
            print(f"Error en registro: {e}")
            session['flash_message'] = "❌ Error interno. Inténtalo más tarde."
            return redirect('/register')
        finally:
            db.close()

    # GET: Mostrar formulario
    return "200 OK", [('Content-type', 'text/html')], [
        render_template('web/register.html', 
                       flash_message=session.pop('flash_message', None)).encode('utf-8')
    ]