from core.views import render_template

def home(environ):
    html = render_template('index.html')
    return "200 OK", [('Content-type', 'text/html')], html