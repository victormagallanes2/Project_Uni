from core.views import render_template, login_required, generate_csrf_token
from urllib.parse import parse_qs
from db import SessionLocal
from users.models import User, UserType
import bcrypt


#@login_required
def users_create(environ):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    
    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']
    
    try:
        user_types = db.query(UserType).order_by(UserType.name).all()
    except Exception as e:
        print(f"Error al consultar tipos de usuario: {e}")
        user_types = [] 

    error_msg = None
    
    try:
        if method == 'POST':
            try:
                request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            except ValueError:
                request_body_size = 0
                
            request_body = environ['wsgi.input'].read(request_body_size)
            form_data = parse_qs(request_body.decode('utf-8'))
            
            form_token = form_data.get('csrf_token', [''])[0]
            session_token = session.get('csrf_token')

            if not session_token or form_token != session_token:
                error_msg = "Error de seguridad (CSRF). Inténtalo de nuevo."
                
                if 'csrf_token' in session:
                    del session['csrf_token']
                    
                html = render_template('users/users_create.html', error=error_msg, csrf_token=csrf_token, user_types=user_types)
                return "403 Forbidden", [('Content-type', 'text/html')], [html.encode('utf-8')]
                
            if 'csrf_token' in session:
                del session['csrf_token']
                
            name = form_data.get('name', [''])[0].strip()
            last_name = form_data.get('last_name', [''])[0].strip()
            email = form_data.get('email', [''])[0].strip()
            password = form_data.get('password', [''])[0]
            confirm_password = form_data.get('confirm_password', [''])[0]
            user_type_id = form_data.get('user_type_id', ['1'])[0] 
            
            if password != confirm_password:
                error_msg = "Error de validación: Las contraseñas no coinciden."
            
            elif not all([name, last_name, email, password, confirm_password]):
                error_msg = "Error de validación: Todos los campos son obligatorios."
            
            if error_msg:
                html = render_template('users/users_create.html', 
                                       error=error_msg, 
                                       csrf_token=csrf_token,
                                       user_types=user_types)
                return "400 Bad Request", [('Content-type', 'text/html')], [html.encode('utf-8')]

            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
            
            new_user = User(
                name=name,
                last_name=last_name,
                email=email,
                password=hashed_password,
                user_type_id=int(user_type_id)
            )
            db.add(new_user)
            db.commit()
            
            session['flash_message'] = f"Usuario {name} creado con éxito."
            status = '302 Found'
            headers = [('Location', '/users/list')]
            return status, headers, [b'Redirecting...']

        else:
            html = render_template('users/users_create.html', 
                                   csrf_token=csrf_token,
                                   user_types=user_types)
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

    except Exception as e:
        db.rollback()
        error_msg = f"Error al crear usuario: {e}"
        print(error_msg)
        
        html = render_template('users/users_create.html', 
                               error="Error de Base de Datos (email duplicado o campo faltante).", 
                               csrf_token=csrf_token,
                               user_types=user_types) 
        return "500 Internal Server Error", [('Content-type', 'text/html')], [html.encode('utf-8')]
        
    finally:
        db.close()


@login_required
def users_list(environ):
    session = environ['beaker.session']
    db = SessionLocal()
    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']
    flash_message = session.pop('flash_message', None) 
    try:
        users = db.query(User).all()
        html = render_template('users/users_list.html', 
                               users=users,
                               csrf_token=csrf_token,
                               flash_message=flash_message)
        return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

    except Exception as e:
        print(f"Error al cargar lista de usuarios: {e}")
        error_html = render_template('500.html', error=str(e))
        return "500 Internal Server Error", [('Content-type', 'text/html')], [error_html.encode('utf-8')]

    finally:
        db.close()


@login_required
def users_edit(environ, user_id):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']

    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']
    try:
        user_types = db.query(UserType).order_by(UserType.name).all()
    except Exception as e:
        print(f"Error al consultar tipos de usuario: {e}")
        user_types = []

    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            status = '404 Not Found'
            headers = [('Content-type', 'text/html')]
            html = render_template('404.html')
            return status, headers, [html.encode('utf-8')]
        if method == 'POST':
            try:
                request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            except ValueError:
                request_body_size = 0
            request_body = environ['wsgi.input'].read(request_body_size)
            form_data = parse_qs(request_body.decode('utf-8'))
            form_token = form_data.get('csrf_token', [''])[0]
            session_token = session.get('csrf_token')

            if not session_token or form_token != session_token:
                print("ALERTA DE SEGURIDAD: Falló la verificación CSRF en users_edit.")
                error_msg = "Error de seguridad (CSRF). Por favor, intenta recargar la página."
                if 'csrf_token' in session:
                    del session['csrf_token']
                    
                html = render_template('users/users_edit.html', user=user, error=error_msg, csrf_token=csrf_token, user_types=user_types)
                return "403 Forbidden", [('Content-type', 'text/html')], [html.encode('utf-8')]
            
            if 'csrf_token' in session:
                del session['csrf_token']

            name = form_data.get('name', [user.name])[0].strip()
            last_name = form_data.get('last_name', [''])[0].strip()
            email = form_data.get('email', [user.email])[0].strip()
            password = form_data.get('password', [''])[0]
            confirm_password = form_data.get('confirm_password', [''])[0]
            user_type_id = form_data.get('user_type_id', [str(user.user_type_id)])[0]
            error_msg = None
            user.name = name
            user.last_name = last_name
            user.email = email
            user.user_type_id = int(user_type_id)
            
            if password:
                if password != confirm_password:
                    error_msg = "Error: Las nuevas contraseñas no coinciden."
                
                if not error_msg:
                    salt = bcrypt.gensalt()
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
                    user.password = hashed_password.decode('utf-8')
            
            if error_msg:
                html = render_template('users/users_edit.html', 
                                       user=user, 
                                       error=error_msg,
                                       csrf_token=csrf_token,
                                       user_types=user_types)
                return "400 Bad Request", [('Content-type', 'text/html')], [html.encode('utf-8')]
            db.commit()
            session['flash_message'] = f"Usuario {user.name} actualizado con éxito."
            status = '302 Found'
            headers = [('Location', '/users/list')]
            return status, headers, [b'Redirecting...']
        else:
            html = render_template('users/users_edit.html', user=user, csrf_token=csrf_token, user_types=user_types)
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

    except Exception as e:
        db.rollback()
        print(f"Error al guardar los cambios del usuario: {e}")
        
        if "IntegrityError" in str(e):
            display_error = "El email ya existe en el sistema. Por favor, utiliza otro."
        else:
            display_error = "Ocurrió un error inesperado al guardar los datos."

        error_html = render_template('users/users_edit.html', user=user, error=display_error, csrf_token=csrf_token, user_types=user_types)
        return "500 Internal Server Error", [('Content-type', 'text/html')], [error_html.encode('utf-8')]
        
    finally:
        db.close()


@login_required 
def users_delete(environ, user_id):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    session = environ['beaker.session']
    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf_token()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            session['flash_message'] = "Error: Usuario no encontrado."
            status = '302 Found'
            headers = [('Location', '/users/list')]
            return status, headers, [b'Redirecting...']

        if method == 'POST':
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            request_body = environ['wsgi.input'].read(request_body_size)
            form_data = parse_qs(request_body.decode('utf-8'))
            form_token = form_data.get('csrf_token', [''])[0]
            session_token = session.get('csrf_token')

            if not session_token or form_token != session_token:
                session['flash_message'] = "Error de seguridad (CSRF)."
                status = '403 Forbidden'
                headers = [('Location', '/users/list')]
                return status, headers, [b'Forbidden']

            if 'csrf_token' in session:
                del session['csrf_token']
            db.delete(user)
            db.commit()
            session['flash_message'] = f"Usuario {user.name} eliminado con éxito."
            status = '302 Found'
            headers = [('Location', '/users/list')]
            return status, headers, [b'Redirecting...']
        
        else:
            html = render_template('users/users_confirm_delete.html', 
                                   user=user, 
                                   csrf_token=session.get('csrf_token'))
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]
            
    except Exception as e:
        db.rollback()
        print(f"Error al eliminar usuario: {e}")
        session['flash_message'] = "Error interno al intentar eliminar el usuario."
        status = '302 Found'
        headers = [('Location', '/users/list')]
        return status, headers, [b'Redirecting...']
        
    finally:
        db.close()


