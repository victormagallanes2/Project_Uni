from core.views import render_template, generate_csrf_token
from db import SessionLocal
from urllib.parse import parse_qs
from users.models import User
import bcrypt


def login(environ):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session'] 
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
                    
                html = render_template('authentication/login.html', error=error_msg, csrf_token=csrf_token)
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
                status = '302 Found'
                headers = [('Location', '/dashboard')]
                return status, headers, [b'Redirecting to dashboard...']
            
            else:
                error_msg = "Credenciales inválidas. Por favor, inténtalo de nuevo."
                session['csrf_token'] = generate_csrf_token() 
                new_csrf_token = session['csrf_token']
                
                html = render_template('authentication/login.html', 
                                       error=error_msg, 
                                       last_email=email, 
                                       csrf_token=new_csrf_token)
                return "401 Unauthorized", [('Content-type', 'text/html')], [html.encode('utf-8')]
                
        else:
            if session.get('logged_in'):
                status = '302 Found'
                headers = [('Location', '/dashboard')]
                return status, headers, [b'Redirecting to dashboard...']
            html = render_template('authentication/login.html', csrf_token=csrf_token)
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

    except Exception as e:
        print(f"Error al intentar iniciar sesión: {e}")
        # ... (Manejo de error 500) ...
        error_msg = "Ocurrió un error interno. Inténtalo más tarde."
        html = render_template('authentication/login.html', error=error_msg)
        return "500 Internal Server Error", [('Content-type', 'text/html')], [html.encode('utf-8')]
        
    finally:
        db.close()


def logout(environ):
    try:
        session = environ['beaker.session'] 
        session.delete() 
        status = '302 Found'
        headers = [('Location', '/login')]
        
        return status, headers, [b'Redirecting to login...']

    except Exception as e:
        print(f"Error al cerrar sesión: {e}")
        status = '302 Found'
        headers = [('Location', '/login')] 
        return status, headers, [b'Redirecting...']