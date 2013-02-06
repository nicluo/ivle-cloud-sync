from dropbox.session import DropboxSession
from flask import g, redirect, render_template, request, session, url_for

from ivlemods import app
from ivlemods.ivle import IvleClient
from ivlemods.database import db_session
from ivlemods.models import User

@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])


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
    else:
        ivle_email = client.get('UserEmail_Get')
        ivle_name = client.get('UserName_Get')
        user = User(ivle_uid=ivle_uid, ivle_email=ivle_email,
            ivle_name=ivle_name, ivle_token=ivle_token)
        db_session.add(user)
    db_session.commit()
    session['user_id'] = user.user_id
    return redirect(url_for('associate'))


@app.route('/associate')
def associate():
    return render_template('associate.html', user=g.user)

@app.route('/auth/dropbox/login')
def dropbox_login():
    dropbox_session = DropboxSession(app.config['DROPBOX_APP_KEY'],
        app.config['DROPBOX_APP_SECRET'], app.config['DROPBOX_ACCESS_TYPE'])
    request_token = dropbox_session.obtain_request_token()
    session['dropbox_request_token_key'] = request_token.key
    session['dropbox_request_token_secret'] = request_token.secret
    return redirect(dropbox_session.build_authorize_url(request_token,
        oauth_callback=url_for('dropbox_callback', _external=True)))


@app.route('/auth/dropbox/callback')
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
    return redirect(url_for('associate'))


@app.route('/auth/dropbox/logout')
def dropbox_logout():
    g.user.dropbox_key = None
    g.user.dropbox_secret = None
    db_session.commit()
    return redirect(url_for('associate'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))