from core.views import render_template
from urllib.parse import parse_qs
from db import SessionLocal, User # Ajusta la ruta a tu modelo
import bcrypt


def users_create(environ):
    """
    Maneja las solicitudes GET (muestra el formulario) y 
    POST (procesa la creación del usuario).
    """
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal() # Abrir la sesión de DB
    
    try:
        if method == 'POST':
            # === LÓGICA PARA EL MÉTODO POST (Crear Usuario) ===
            
            # 1. Obtener los datos del cuerpo
            try:
                request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            except (ValueError):
                request_body_size = 0
            
            request_body = environ['wsgi.input'].read(request_body_size)
            form_data = parse_qs(request_body.decode('utf-8'))

            # 2. Extraer y limpiar datos (Usamos .get(..., [''])[0] para extraer el primer elemento)
            name = form_data.get('name', [''])[0]
            last_name = form_data.get('last_name', [''])[0]
            email = form_data.get('email', [''])[0]
            password = form_data.get('password', [''])[0]
            confirm_password = form_data.get('confirm_password', [''])[0]
            
            # --- Validación (¡Simplificada para el ejemplo!) ---
            if password != confirm_password:
                # Mostrar el formulario de nuevo con un mensaje de error
                error_msg = "Error: Las contraseñas no coinciden."
                html = render_template('users/users_create.html', error=error_msg)
                return "400 Bad Request", [('Content-type', 'text/html')], html

            # 3. Hasheo de la Contraseña
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

            # 4. Guardar en DB
            new_user = User(
                name=name,
                last_name=last_name,
                email=email,
                password=hashed_password.decode('utf-8')
            )
            db.add(new_user)
            db.commit()
            
            # 5. Redirección exitosa (Post-Redirect-Get Pattern)
            status = '302 Found'
            headers = [('Location', '/users/list')] # Redirigir al dashboard o lista de usuarios
            return status, headers, [b'Redirecting...']

        else:
            # === LÓGICA PARA EL MÉTODO GET (Mostrar Formulario) ===
            html = render_template('users/users_create.html')
            return "200 OK", [('Content-type', 'text/html')], html

    except Exception as e:
        db.rollback()
        
        # 1. Identificar el error para mostrar un mensaje amigable
        if "UNIQUE constraint failed" in str(e):
            error_msg = "Error: El correo electrónico ya está registrado."
        else:
            print(f"Error al procesar solicitud POST: {e}")
            error_msg = f"Error interno del servidor: {e}"
        
        # 2. Renderizar la plantilla con el mensaje de error
        html = render_template('users/users_create.html', error=error_msg)
        
        # 3. Codificar la cadena de texto (html) a bytes ANTES de retornar
        body_content = [html.encode('utf-8')]
        
        # 4. Retornar el estado y la lista de bytes
        return "500 Internal Server Error", [('Content-type', 'text/html')], body_content
        
    finally:
        db.close()


def users_list(environ):
    # 1. Abrir sesión de base de datos
    db = SessionLocal()
    
    try:
        # 2. Consultar todos los usuarios
        # Nota: Usamos .all() para obtener la lista de objetos User
        users = db.query(User).all()
        
        # 3. Renderizar la plantilla, pasando la lista de usuarios
        # La clave 'users' estará disponible en el HTML
        html = render_template('users/users_list.html', users=users)
        
        # 4. Retornar la respuesta WSGI
        return "200 OK", [('Content-type', 'text/html')], html

    except Exception as e:
        print(f"Error al cargar lista de usuarios: {e}")
        # En caso de error, puedes devolver una página de error 500
        error_html = render_template('500.html', error=str(e))
        return "500 Internal Server Error", [('Content-type', 'text/html')], error_html

    finally:
        # 5. Cerrar la sesión de base de datos (¡Crucial!)
        db.close()


def users_edit(environ, user_id):
    method = environ.get('REQUEST_METHOD', 'GET')
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            # 404 - Retorno en lista de bytes
            status = '404 Not Found'
            headers = [('Content-type', 'text/html')]
            html = render_template('404.html')
            return status, headers, [html.encode('utf-8')] 
            
        
        if method == 'POST':
            # === LÓGICA POST (Actualización) ===
            try:
                request_body_size = int(environ.get('CONTENT_LENGTH', 0))
            except ValueError:
                request_body_size = 0
            
            request_body = environ['wsgi.input'].read(request_body_size)
            form_data = parse_qs(request_body.decode('utf-8'))

            # 1. Extraer datos
            name = form_data.get('name', [''])[0]
            last_name = form_data.get('last_name', [''])[0]
            email = form_data.get('email', [''])[0]
            password = form_data.get('password', [''])[0]
            confirm_password = form_data.get('confirm_password', [''])[0]
            
            # 2. Actualizar campos simples
            user.name = name
            user.last_name = last_name
            user.email = email
            
            # 3. Lógica de Cambio de Contraseña
            if password:
                if password != confirm_password:
                    error_msg = "Error: Las nuevas contraseñas no coinciden."
                    html = render_template('users/users_edit.html', user=user, error=error_msg)
                    # ERROR de Validación - Retorno en lista de bytes
                    return "400 Bad Request", [('Content-type', 'text/html')], [html.encode('utf-8')]
                
                # Hashear y actualizar
                salt = bcrypt.gensalt()
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
                user.password = hashed_password.decode('utf-8')
            
            # 4. Guardar cambios
            db.commit()
            
            # 5. Redirección exitosa (Correcto: lista de bytes [b'..'])
            status = '302 Found'
            headers = [('Location', '/users/list')] 
            return status, headers, [b'Redirecting...']
        
        else: # Manejo explícito del GET
            # === LÓGICA GET (Mostrar Formulario) ===
            html = render_template('users/users_edit.html', user=user)
            # ÉXITO GET - Retorno en lista de bytes
            return "200 OK", [('Content-type', 'text/html')], [html.encode('utf-8')]

    except Exception as e:
        db.rollback()
        # Manejo de error 500 - Retorno en lista de bytes
        print(f"Error al cargar usuario para edición: {e}")
        error_html = render_template('500.html', error=str(e))
        return "500 Internal Server Error", [('Content-type', 'text/html')], [error_html.encode('utf-8')]
        
    finally:
        db.close()

def users_delete(environ, user_id):
    """
    Busca un usuario por ID, lo elimina de la DB y redirige.
    """
    db = SessionLocal()
    
    try:
        # 1. Buscar al usuario por ID
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            # Si el usuario no existe, redirigir sin hacer nada o mostrar un 404
            status = '302 Found'
            headers = [('Location', '/users/list')] # Redirigir a la lista
            return status, headers, [b'Redirecting...']

        # 2. Eliminar el usuario
        db.delete(user)
        db.commit()
        
        # 3. Redirección exitosa
        status = '302 Found'
        headers = [('Location', '/users/list')] 
        return status, headers, [b'Redirecting...']

    except Exception as e:
        db.rollback()
        print(f"Error al eliminar usuario {user_id}: {e}")
        # En caso de error, redirigir a la lista con un posible error flash
        status = '302 Found'
        headers = [('Location', '/users/list')] 
        return status, headers, [b'Redirecting...']
        
    finally:
        db.close()


