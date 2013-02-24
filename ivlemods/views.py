from functools import wraps

from dropbox.session import DropboxSession
from flask import g, redirect, render_template, request, session, url_for

from ivlemods import app
from ivlemods.ivle import IvleClient
from ivlemods.database import db_session
from ivlemods.poll_ivle_folders import poll_ivle_folders
from ivlemods.models import IVLEFolder, User

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' in session:
            g.user = User.query.get(session['user_id'])
            if g.user:
                return f(*args, **kwargs)
        return redirect(url_for('ivle_login'))
    return decorated_function


@app.teardown_request
def shutdown_session(exception=None):
    db_session.remove()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/auth/ivle/login')
def ivle_login():
    return redirect(
        IvleClient.build_authorize_url(url_for('ivle_callback', _external=True)))


@app.route('/auth/ivle/callback')
def ivle_callback():
    ivle_token = request.args.get('token')
    client = IvleClient(ivle_token)
    ivle_uid = client.get('UserID_Get')
    user = User.query.filter(User.ivle_uid == ivle_uid).first()
    if user:
        user.ivle_token = ivle_token
        db_session.commit()
        session['user_id'] = user.user_id
        return redirect(url_for('settings'))
    else:
        ivle_email = client.get('UserEmail_Get')
        ivle_name = client.get('UserName_Get')
        user = User(ivle_uid=ivle_uid, ivle_email=ivle_email,
            ivle_name=ivle_name, ivle_token=ivle_token)
        db_session.add(user)
        db_session.commit()
        poll_ivle_folders.delay(user.user_id)
        session['user_id'] = user.user_id
        return redirect(url_for('associate'))


@app.route('/associate')
@login_required
def associate():
    return render_template('associate.html', user=g.user)


@app.route('/settings')
@login_required
def settings():
    ivle_folders = g.user.ivle_folders.order_by(IVLEFolder.path).all()
    modules = {}
    for folder in ivle_folders:
        directories = folder.path.split('/')
        module_name = directories[0]
        if module_name not in modules:
            modules[module_name] = [{
                                        'directory': module_name,
                                        'nesting_level': 0
                                    }]
        modules[module_name].append({
            'directory': directories[-1],
            'nesting_level': len(directories) - 1
        })
    return render_template('settings.html', user=g.user, modules=modules)


@app.route('/auth/dropbox/login')
@login_required
def dropbox_login():
    dropbox_session = DropboxSession(app.config['DROPBOX_APP_KEY'],
        app.config['DROPBOX_APP_SECRET'], app.config['DROPBOX_ACCESS_TYPE'])
    request_token = dropbox_session.obtain_request_token()
    session['dropbox_request_token_key'] = request_token.key
    session['dropbox_request_token_secret'] = request_token.secret
    return redirect(dropbox_session.build_authorize_url(request_token,
        oauth_callback=url_for('dropbox_callback', _external=True)))


@app.route('/auth/dropbox/callback')
@login_required
def dropbox_callback():
    dropbox_session = DropboxSession(app.config['DROPBOX_APP_KEY'],
        app.config['DROPBOX_APP_SECRET'], app.config['DROPBOX_ACCESS_TYPE'])
    dropbox_session.set_request_token(session['dropbox_request_token_key'],
        session['dropbox_request_token_secret'])
    access_token = dropbox_session.obtain_access_token()
    g.user.dropbox_key = access_token.key
    g.user.dropbox_secret = access_token.secret
    db_session.commit()
    session.pop('dropbox_request_token_key', None)
    session.pop('dropbox_request_token_secret', None)
    return redirect(url_for('settings'))


@app.route('/auth/dropbox/logout')
@login_required
def dropbox_logout():
    g.user.dropbox_key = None
    g.user.dropbox_secret = None
    db_session.commit()
    return redirect(url_for('settings'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))
