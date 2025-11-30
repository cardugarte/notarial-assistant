"""
Configuration settings for the Notarial Assistant.

Vertex AI initialization is performed in the package's __init__.py
"""

import os

# Vertex AI settings
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION")
