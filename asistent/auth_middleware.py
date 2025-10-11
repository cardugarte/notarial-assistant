
import os
from starlette.applications import Starlette
from starlette.responses import RedirectResponse, HTMLResponse
from starlette.routing import Route
from authlib.integrations.starlette_client import OAuth
from asistent.secrets import get_secret

# --- HTML Templates ---
LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Login</title>
    <style>
        body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f0f2f5; margin: 0; }
        .login-container { text-align: center; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .google-btn {
            display: inline-block; background: white; color: #444; border-radius: 5px; border: thin solid #888;
            box-shadow: 1px 1px 1px grey; white-space: nowrap; padding: 10px 24px; font-size: 16px; cursor: pointer;
        }
        .google-btn:hover { box-shadow: 2px 2px 3px grey; }
        .google-icon-wrapper { display: inline-block; vertical-align: middle; margin-right: 12px; }
        .google-icon { width: 24px; height: 24px; }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>Acceso al Agente RAG</h1>
        <p>Por favor, inicie sesión con su cuenta de Google.</p>
        <a href="/login" class="google-btn">
            <span class="google-icon-wrapper">
                <img class="google-icon" src="https://developers.google.com/identity/images/g-logo.png" alt="Google sign-in">
            </span>
            <span>Iniciar sesión con Google</span>
        </a>
    </div>
</body>
</html>
"""

UNAUTHORIZED_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Acceso Denegado</title>
    <style>
        body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f0f2f5; margin: 0; }
        .container { text-align: center; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        h1 { color: #d9534f; }
        p { color: #333; }
        a { color: #007bff; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Acceso Denegado</h1>
        <p>El usuario <strong>{email}</strong> no está autorizado para acceder a esta aplicación.</p>
        <p><a href="/logout">Intentar con otra cuenta</a></p>
    </div>
</body>
</html>
"""

# --- OAuth and Auth Logic ---
oauth = OAuth()
oauth.register(
    name='google',
    client_id=get_secret("google-client-id"),
    client_secret=get_secret("google-client-secret"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

async def login(request):
    redirect_uri = request.url_for('authorize')
    return await oauth.google.authorize_redirect(request, redirect_uri)

async def authorize(request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')

    if user_info:
        email = user_info.get('email')
        allowed_users_str = get_secret("allowed-users-list")
        allowed_users = [e.strip() for e in allowed_users_str.split(",")]

        if email not in allowed_users:
            return HTMLResponse(UNAUTHORIZED_PAGE_HTML.format(email=email), status_code=403)

        request.session['user'] = user_info
        return RedirectResponse(url='/')

    return HTMLResponse("Login failed", status_code=400)

async def logout(request):
    request.session.pop('user', None)
    return RedirectResponse(url='/login-page')

async def login_page(request):
    return HTMLResponse(LOGIN_PAGE_HTML)

# --- Auth Middleware ---
class AuthMiddleware:
    def __init__(self, app):
        self.app = app
        self.auth_app = Starlette(routes=[
            Route('/login-page', endpoint=login_page),
            Route('/login', endpoint=login),
            Route('/authorize', endpoint=authorize),
            Route('/logout', endpoint=logout),
        ])

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Handle auth routes separately
        path = scope['path']
        if path.startswith(('/login', '/logout', '/authorize', '/login-page')):
            await self.auth_app(scope, receive, send)
            return

        # Check session for all other routes
        if "user" not in scope['session']:
            response = RedirectResponse(url='/login-page', status_code=307)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
