"""
OAuth authentication wrapper for ADK Web UI
Handles Google OAuth login and proxies to ADK Web
"""
import os
from flask import Flask, redirect, url_for, session, render_template, request
from authlib.integrations.flask_client import OAuth
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
from asistent.secrets import get_secret

app = Flask(__name__)
app.secret_key = get_secret("flask-secret-key")

# Trust proxy headers (Cloud Run uses X-Forwarded-* headers)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# OAuth configuration
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=get_secret("google-client-id"),
    client_secret=get_secret("google-client-secret"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)




def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Auth routes (must be before catch-all proxy)
@app.route('/login-page')
def login_page():
    """Show login page"""
    return render_template('login.html')

@app.route('/login')
def login():
    """Initiate Google OAuth login"""
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    """OAuth callback handler"""
    token = google.authorize_access_token()
    user_info = token.get('userinfo')

    if user_info:
        email = user_info.get('email')

        # Check if user is in whitelist
        allowed_users_str = get_secret("allowed-users-list")
        allowed_users = [email.strip() for email in allowed_users_str.split(",")]
        if email not in allowed_users:
            return render_template('unauthorized.html', email=email), 403

        # Store user in session
        session['user'] = {
            'email': email,
            'name': user_info.get('name'),
            'picture': user_info.get('picture')
        }

        return redirect('/')

    return 'Login failed', 400

@app.route('/logout')
def logout():
    """Logout user"""
    session.pop('user', None)
    return redirect('/login-page')

@app.route('/')
@login_required
def index_redirect():
    """Redirect root to /dev-ui/ with asistent preselected"""
    return redirect('/dev-ui/?app=asistent')

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
@login_required
def proxy_adk(path):
    """Proxy to ADK Web UI (running on port 8081 via supervisord)"""
    import requests
    from flask import Response

    # Build target URL (ADK Web is already running via supervisord)
    target_url = f'http://127.0.0.1:8081/{path}'

    # Forward query parameters
    if request.query_string:
        target_url += f'?{request.query_string.decode()}'

    # Forward request to ADK Web
    try:
        if request.method == 'GET':
            resp = requests.get(target_url, headers=dict(request.headers), stream=True)
        elif request.method == 'POST':
            resp = requests.post(target_url, headers=dict(request.headers),
                               data=request.get_data(), stream=True)
        else:
            resp = requests.request(request.method, target_url,
                                  headers=dict(request.headers),
                                  data=request.get_data(), stream=True)

        # Return response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                  if name.lower() not in excluded_headers]

        return Response(resp.iter_content(chunk_size=10*1024),
                       status=resp.status_code,
                       headers=headers)
    except requests.exceptions.ConnectionError:
        return render_template('loading.html'), 503

if __name__ == '__main__':
    # Start Flask app (ADK Web is started separately by supervisord)
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
