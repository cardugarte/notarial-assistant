"""
ADK-native authentication configuration for Google Workspace APIs.
Based on official ADK documentation:
https://google.github.io/adk-docs/tools/authentication/
"""
from fastapi.openapi.models import OAuth2, OAuthFlows, OAuthFlowAuthorizationCode
from google.adk.auth.auth_credential import AuthCredential, AuthCredentialTypes, OAuth2Auth
from ..secrets import get_secret

# Google Workspace OAuth2 scopes
GOOGLE_DRIVE_SCOPES = {
    "https://www.googleapis.com/auth/drive.file": "Create and manage files created by this app",
    "https://www.googleapis.com/auth/documents": "Create and edit Google Docs documents"
}

def get_google_oauth_auth_scheme() -> OAuth2:
    """
    Get OAuth2 authentication scheme for Google Workspace APIs.

    Returns:
        OAuth2 scheme configured for Google with Drive and Docs scopes
    """
    return OAuth2(
        flows=OAuthFlows(
            authorizationCode=OAuthFlowAuthorizationCode(
                authorizationUrl="https://accounts.google.com/o/oauth2/v2/auth",
                tokenUrl="https://oauth2.googleapis.com/token",
                scopes=GOOGLE_DRIVE_SCOPES
            )
        )
    )

def get_google_oauth_credential() -> AuthCredential:
    """
    Get OAuth2 credential configuration from Secret Manager.

    Returns:
        AuthCredential with client_id and client_secret from Secret Manager
    """
    return AuthCredential(
        auth_type=AuthCredentialTypes.OAUTH2,
        oauth2=OAuth2Auth(
            client_id=get_secret("google-client-id"),
            client_secret=get_secret("google-client-secret")
        )
    )
