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
            headers = [('Location', '/')] # Redirigir al dashboard o lista de usuarios
            return status, headers, [b'Redirecting...']

        else:
            # === LÓGICA PARA EL MÉTODO GET (Mostrar Formulario) ===
            html = render_template('users/users_create.html')
            return "200 OK", [('Content-type', 'text/html')], html

    except Exception as e:
        db.rollback()
        print(f"Error al procesar solicitud POST: {e}")
        # En caso de error (ej. Email duplicado), mostrar formulario con error
        error_msg = f"Error al guardar usuario. Email ya registrado: {e}"
        html = render_template('users/users_create.html', error=error_msg)
        return "500 Internal Server Error", [('Content-type', 'text/html')], html
        
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


