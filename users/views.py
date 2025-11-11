from core.views import render_template


def users_create(environ):
    html = render_template('users/users_create.html')
    return "200 OK", [('Content-type', 'text/html')], html


def users_list(environ):
    html = render_template('users/users_list.html')
    return "200 OK", [('Content-type', 'text/html')], html


