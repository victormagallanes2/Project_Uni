Instalacion en entorno de pruebas

Crear entorno virtual y activarlo:

    Set-ExecutionPolicy Bypass -Scope Process -Force
    mi_entorno\Scripts\activate
    cd .\Project_Uni\

instalar las dependencias con pip

    pip install requierements.txt

Crear o actualizar bases de datos:

    alembic revision --autogenerate -m "Esquema Inicial"
    alembic upgrade head


Iniciar servidor de pruebas:

    waitress-serve --listen=127.0.0.1:8000 app:application

