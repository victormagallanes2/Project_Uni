from core.views import render_template
from db import SessionLocal, User
from urllib.parse import parse_qs
import bcrypt


def login(environ):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    
    try:
        # 1. Obtener el objeto de sesión de Beaker
        session = environ['beaker.session'] 

        if method == 'POST':
            # === LÓGICA DE AUTENTICACIÓN (POST) ===
            
            # Obtener datos del cuerpo de la solicitud
            try:
                request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            except ValueError:
                request_body_size = 0
            
            request_body = environ['wsgi.input'].read(request_body_size)
            form_data = parse_qs(request_body.decode('utf-8'))

            email = form_data.get('email', [''])[0].strip()
            print(f"DEBUG: Email a buscar en la DB: '{email}'")
            password_input = form_data.get('password', [''])[0]

            
            # 2. Buscar al usuario por email
            user = db.query(User).filter(User.email == email).first()
            if user:
                print(f"DEBUG: Usuario encontrado. ID: {user.id}, Email: {user.email}")
            else:
                print(f"DEBUG: Usuario NO encontrado para el email: {email}")
            is_authenticated = False
            
            # 3. Verificar la Contraseña
            if user:
                # Convertir la contraseña hasheada almacenada y la contraseña de entrada a bytes para bcrypt
                stored_hash = user.password.encode('utf-8')
                input_bytes = password_input.encode('utf-8')
                
                # bcrypt.checkpw verifica el hash de forma segura
                if bcrypt.checkpw(input_bytes, stored_hash):
                    is_authenticated = True

            if is_authenticated:
                # 4. ÉXITO: Establecer la Sesión (Loguear al usuario)
                session['user_id'] = user.id
                session['user_name'] = user.name
                session['logged_in'] = True
                
                # Redirigir al dashboard protegido
                status = '302 Found'
                headers = [('Location', '/')] 
                return status, headers, [b'Redirecting to dashboard...']
            
            else:
                # 5. ERROR: Credenciales inválidas
                error_msg = "Credenciales inválidas. Por favor, inténtalo de nuevo."
                html = render_template('authentication/login.html', error=error_msg, last_email=email)
                return "401 Unauthorized", [('Content-type', 'text/html')], [html.encode('utf-8')]
                
        else:
            # === LÓGICA MOSTRAR FORMULARIO (GET) ===
            # Redirigir si ya está logueado
            if session.get('logged_in'):
                status = '302 Found'
                headers = [('Location', '/')] 
                return status, headers, [b'Redirecting to dashboard...']
                
            html = render_template('authentication/login.html')
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

    except Exception as e:
        print(f"Error al intentar iniciar sesión: {e}")
        error_msg = "Ocurrió un error interno. Inténtalo más tarde."
        html = render_template('authentication/login.html', error=error_msg)
        return "500 Internal Server Error", [('Content-type', 'text/html')], [html.encode('utf-8')]
        
    finally:
        db.close()


def logout(environ):
    """
    Cierra la sesión del usuario y lo redirige a la página de inicio.
    """
    try:
        # 1. Acceder al objeto de sesión de Beaker
        session = environ['beaker.session'] 
        
        # 2. Invalidar/Borrar la sesión
        # El método .delete() elimina todos los datos de la sesión del servidor
        session.delete() 
        
        # 3. Redirigir a la página de login o inicio
        status = '302 Found'
        headers = [('Location', '/login')] # Redirigir siempre a la página de login
        
        return status, headers, [b'Redirecting to login...']

    except Exception as e:
        # En caso de error (ej: si la sesión ya había expirado), simplemente redirigir
        print(f"Error al cerrar sesión: {e}")
        status = '302 Found'
        headers = [('Location', '/login')] 
        return status, headers, [b'Redirecting...']