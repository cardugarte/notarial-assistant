"""
ADK Web Server - Production deployment script for Cloud Run.

This launches the ADK web interface with OAuth authentication for end users.
The UI will be accessible at your Cloud Run URL with Google OAuth login.

Usage:
    python run_adk_web.py
"""
import os
import sys

# Add current directory to path so asistent module can be imported
sys.path.insert(0, os.path.dirname(__file__))

# Import after path is set
from google.adk.cli.adk_web_server import run_adk_web_server

if __name__ == "__main__":
    # Get port from environment (Cloud Run sets PORT env var)
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"🚀 Starting ADK Web Server on {host}:{port}")
    print(f"📦 Project: {os.environ.get('GOOGLE_CLOUD_PROJECT')}")
    print(f"📍 Location: {os.environ.get('GOOGLE_CLOUD_LOCATION')}")

    # Run ADK web server
    # The "." means it will look for agents in the current directory
    # It will find the "asistent" folder which contains agent.py
    run_adk_web_server(
        agents_dir=".",
        host=host,
        port=port,
        reload=False,  # Disable reload in production
        log_level="info"
    )
