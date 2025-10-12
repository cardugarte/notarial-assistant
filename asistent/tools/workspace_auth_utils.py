"""
Shared authentication utilities for Google Workspace tools.

Implements ADK-native OAuth2 authentication following the official 6-step pattern:
https://google.github.io/adk-docs/tools/authentication/#journey-2-building-custom-tools-functiontool-requiring-authentication

This module provides reusable functions for:
- Creating AuthConfig
- Loading/caching credentials from tool_context.state
- Converting ADK credentials to google.oauth2.Credentials
- Refreshing expired tokens
"""

import logging
from typing import Optional

from google.adk.auth.auth_config import AuthConfig
from google.adk.auth.auth_credential import ExchangedCredential
from google.adk.tools.tool_context import ToolContext
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from ..auth.auth_config import get_google_oauth_auth_scheme, get_google_oauth_credential

logger = logging.getLogger(__name__)

# Token cache key for storing credentials in ADK session state
# SHARED across all Google Workspace tools
TOKEN_CACHE_KEY = "google_workspace_tokens"


def get_auth_config() -> AuthConfig:
    """
    Create AuthConfig with Google OAuth2 scheme and credentials.

    Returns:
        AuthConfig: Configured authentication for Google Workspace APIs
    """
    return AuthConfig(
        auth_scheme=get_google_oauth_auth_scheme(),
        auth_credential=get_google_oauth_credential()
    )


def load_cached_credentials(tool_context: ToolContext) -> Optional[Credentials]:
    """
    Load cached OAuth2 credentials from tool context state.

    STEP 1: Check cached credentials in tool_context.state

    This function:
    1. Retrieves cached tokens from session state
    2. Reconstructs google.oauth2.Credentials object
    3. Checks if token is still valid
    4. Attempts to refresh if expired
    5. Updates cache with refreshed token

    Args:
        tool_context: Tool context containing session state

    Returns:
        Credentials if cached and valid, None otherwise
    """
    cached_tokens = tool_context.state.get(TOKEN_CACHE_KEY)

    if not cached_tokens:
        logger.debug("No cached credentials found in session state")
        return None

    try:
        # Reconstruct Credentials from cached token data
        creds = Credentials(
            token=cached_tokens.get("token"),
            refresh_token=cached_tokens.get("refresh_token"),
            token_uri=cached_tokens.get("token_uri"),
            client_id=cached_tokens.get("client_id"),
            client_secret=cached_tokens.get("client_secret"),
            scopes=cached_tokens.get("scopes")
        )

        # Check if token is still valid
        if creds.valid:
            logger.info("Using cached credentials from session state")
            return creds

        # Try to refresh if expired
        if creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            creds.refresh(Request())
            # Update cache with refreshed token
            cache_credentials(tool_context, creds)
            return creds

        logger.warning("Cached credentials are invalid and cannot be refreshed")
        return None

    except Exception as e:
        logger.error(f"Error loading cached credentials: {e}")
        return None


def credential_to_google_creds(
    exchanged_credential: ExchangedCredential,
    auth_config: AuthConfig
) -> Credentials:
    """
    Convert ADK ExchangedCredential to google.oauth2.Credentials.

    STEP 4: ADK has handled token exchange automatically

    This function bridges the gap between ADK's credential format
    and the google.oauth2.credentials.Credentials format expected
    by Google API client libraries.

    Args:
        exchanged_credential: Credential from ADK after OAuth2 exchange
        auth_config: Auth configuration with OAuth2 settings

    Returns:
        google.oauth2.Credentials: Ready to use with Google APIs
    """
    oauth2_cred = auth_config.auth_credential.oauth2

    return Credentials(
        token=exchanged_credential.access_token,
        refresh_token=exchanged_credential.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=oauth2_cred.client_id,
        client_secret=oauth2_cred.client_secret,
        scopes=list(get_google_oauth_auth_scheme().flows.authorizationCode.scopes.keys())
    )


def cache_credentials(tool_context: ToolContext, creds: Credentials) -> None:
    """
    Cache credentials in tool context session state.

    STEP 5: Cache credentials in tool_context.state

    Stores all necessary token information in the session state
    so subsequent tool calls can reuse the credentials without
    requiring re-authentication.

    Args:
        tool_context: Tool context to store credentials
        creds: Google OAuth2 credentials to cache
    """
    tool_context.state[TOKEN_CACHE_KEY] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes
    }
    logger.info("Cached credentials in session state")


def clear_cached_credentials(tool_context: ToolContext) -> None:
    """
    Clear cached credentials from tool context state.

    Use this when credentials become invalid (e.g., after 401/403 errors)
    to force re-authentication on the next tool call.

    Args:
        tool_context: Tool context containing session state
    """
    tool_context.state.pop(TOKEN_CACHE_KEY, None)
    logger.info("Cleared cached credentials from session state")


def get_user_email(tool_context: ToolContext, default: str = "default_user") -> str:
    """
    Get user email from tool context state.

    Tries multiple locations:
    1. app:user_email (recommended ADK pattern)
    2. user_email (backward compatibility)
    3. default value if not found

    Args:
        tool_context: Tool context containing session state
        default: Default email to use if not found

    Returns:
        User email address
    """
    user_email = tool_context.state.get("app:user_email")

    if not user_email:
        user_email = tool_context.state.get("user_email")

    if not user_email:
        logger.warning(f"User email not found in state, using default: {default}")
        return default

    return user_email
