import os

# ----------------------------------------------
# Funciones Auxiliares (Plantillas)
# ----------------------------------------------

# 1. Función para cargar Plantillas (Templates)

def render_template(template_name, context=None):
    """Carga y renderiza una plantilla HTML."""
    if context is None:
        context = {}
        
    # Asume que las plantillas están en el subdirectorio 'templates'
    # La ruta usa os.path.join para compatibilidad entre sistemas operativos
    template_path = os.path.join(os.getcwd(), 'templates', template_name)
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
            
        # Simula la sustitución de variables
        for key, value in context.items():
            template_content = template_content.replace(f"{{{{ {key} }}}}", str(value))
            
        return template_content.encode('utf-8')
    except FileNotFoundError:
        return b"<h1>Error 404: Plantilla no encontrada</h1>"

