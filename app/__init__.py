from dropbox.session import DropboxSession
from flask import Flask, g, redirect, render_template, request, session, url_for

from app.ivle import IvleClient
from app.database import db_session
from app.models import User

app = Flask(__name__, instance_relative_config=True)
app.secret_key = '\x03\xe2\x1aF\xf3\xe4\xd4j\xfe\x83k\xe7\x89\x7f\xb4]v\x10#\xac\tv\xd5\xa0'
app.config.from_pyfile('application.cfg', silent=True)

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


APP_KEY = 'br678pfbbwqbi1y'
APP_SECRET = '***REMOVED***'
ACCESS_TYPE = 'app_folder'

@app.route('/auth/dropbox/login')
def dropbox_login():
    dropbox_session = DropboxSession(APP_KEY, APP_SECRET, ACCESS_TYPE)
    request_token = dropbox_session.obtain_request_token()
    session['dropbox_request_token_key'] = request_token.key
    session['dropbox_request_token_secret'] = request_token.secret
    return redirect(dropbox_session.build_authorize_url(request_token,
        oauth_callback=url_for('dropbox_callback', _external=True)))


@app.route('/auth/dropbox/callback')
def dropbox_callback():
    dropbox_session = DropboxSession(APP_KEY, APP_SECRET, ACCESS_TYPE)
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
    pass


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))