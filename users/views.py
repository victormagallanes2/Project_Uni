from core.views import render_template

def users(environ):
    html = render_template('users.html')
    return "200 OK", [('Content-type', 'text/html')], html