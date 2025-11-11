from core.views import render_template


def login(environ):
    html = render_template('authentication/login.html', title='login')
    status = "200 OK"
    headers = [('Content-type', 'text/html; charset=utf-8')]
    return status, headers, html