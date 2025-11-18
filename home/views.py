from core.views import render_template, login_required


@login_required
def home(environ):
    session = environ.get('beaker.session')
    user_name = session.get('user_name', 'Invitado')
    html = render_template('index.html', title='Página Principal', user_name=user_name)
    status = "200 OK"
    headers = [('Content-type', 'text/html; charset=utf-8')]
    return status, headers, html