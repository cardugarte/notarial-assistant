
import os
import uvicorn
from google.adk.cli.adk_web_server import app as adk_app
from asistent.agent import root_agent
from asistent.auth_middleware import AuthMiddleware
from starlette.middleware.sessions import SessionMiddleware
from asistent.secrets import get_secret

# Load the ADK agent
adk_app.add_agent(root_agent)

# Get the underlying ASGI app from ADK
asgi_app = adk_app.app

# Wrap the ASGI app with our authentication middleware, then session middleware
app = AuthMiddleware(asgi_app)
app = SessionMiddleware(app, secret_key=get_secret("flask-secret-key"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
