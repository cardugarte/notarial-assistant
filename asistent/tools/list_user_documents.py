"""
Tool for listing documents saved in a user's Google Drive folder.

Implements ADK-native OAuth2 authentication following the official 6-step pattern:
https://google.github.io/adk-docs/tools/authentication/#journey-2-building-custom-tools-functiontool-requiring-authentication
"""

import logging
from typing import Optional

from google.adk.auth.auth_tool import AuthConfig
from google.adk.auth.auth_credential import AuthCredential
from google.adk.tools.tool_context import ToolContext
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..auth.auth_config import get_google_oauth_auth_scheme, get_google_oauth_credential

logger = logging.getLogger(__name__)

# Token cache key - MUST be the same as save_document_to_drive.py
TOKEN_CACHE_KEY = "google_workspace_tokens"


def _get_auth_config() -> AuthConfig:
    """
    Create AuthConfig with Google OAuth2 scheme and credentials.

    Returns:
        AuthConfig: Configured authentication for Google Workspace APIs
    """
    return AuthConfig(
        auth_scheme=get_google_oauth_auth_scheme(),
        auth_credential=get_google_oauth_credential()
    )


def _load_cached_credentials(tool_context: ToolContext) -> Optional[Credentials]:
    """
    Load cached OAuth2 credentials from tool context state.

    STEP 1: Check cached credentials in tool_context.state

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
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            # Update cache with refreshed token
            _cache_credentials(tool_context, creds)
            return creds

        logger.warning("Cached credentials are invalid and cannot be refreshed")
        return None

    except Exception as e:
        logger.error(f"Error loading cached credentials: {e}")
        return None


def _credential_to_google_creds(
    exchanged_credential: AuthCredential,
    auth_config: AuthConfig
) -> Credentials:
    """
    Convert ADK ExchangedCredential to google.oauth2.Credentials.

    STEP 4: ADK has handled token exchange automatically

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


def _cache_credentials(tool_context: ToolContext, creds: Credentials) -> None:
    """
    Cache credentials in tool context session state.

    STEP 5: Cache credentials in tool_context.state

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


def _ensure_user_folder(drive_service, user_email: str, root_folder_id: str) -> str:
    """
    Ensure a user folder exists in the Drive root folder.

    Args:
        drive_service: Authenticated Google Drive service
        user_email: User's email address (used as folder name)
        root_folder_id: Parent folder ID

    Returns:
        The folder ID
    """
    logger.info(f"Ensuring folder for user: {user_email}")

    # Search for existing user folder
    query = (
        f"name='{user_email}' and "
        f"'{root_folder_id}' in parents and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"trashed=false"
    )

    results = drive_service.files().list(
        q=query,
        fields="files(id, name)",
        spaces='drive'
    ).execute()

    folders = results.get('files', [])

    if folders:
        logger.info(f"Found existing folder for {user_email}: {folders[0]['id']}")
        return folders[0]['id']

    # Create folder if it doesn't exist
    logger.info(f"Creating new folder for {user_email}")
    file_metadata = {
        'name': user_email,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [root_folder_id]
    }

    folder = drive_service.files().create(
        body=file_metadata,
        fields='id'
    ).execute()

    logger.info(f"Created folder for {user_email}: {folder['id']}")
    return folder['id']


def _list_documents(
    creds: Credentials,
    document_type: str,
    tool_context: ToolContext
) -> dict:
    """
    List documents in user's Drive folder using authenticated credentials.

    STEP 6: Make authenticated API call

    Args:
        creds: Authenticated Google OAuth2 credentials
        document_type: Filter by document type (empty for all)
        tool_context: Tool context for state management

    Returns:
        Success response with list of documents

    Raises:
        HttpError: If API call fails
    """
    try:
        # Build Google API service
        drive_service = build('drive', 'v3', credentials=creds)

        # Get user email from credentials
        # TODO: May need to call userinfo API to get email
        user_email = tool_context.state.get("app:user_email") or tool_context.state.get("user_email")
        if not user_email:
            logger.warning("User email not in state, using default folder logic")
            user_email = "default_user"

        # Get root folder from config
        from ..secrets import get_drive_root_folder_id
        root_folder_id = get_drive_root_folder_id()

        # Ensure user folder exists
        user_folder_id = _ensure_user_folder(drive_service, user_email, root_folder_id)

        logger.info(f"Listing documents in folder: {user_folder_id}")
        if document_type:
            logger.info(f"Filtering by type: {document_type}")

        # List all documents in user folder
        query = (
            f"'{user_folder_id}' in parents and "
            f"mimeType='application/vnd.google-apps.document' and "
            f"trashed=false"
        )

        results = drive_service.files().list(
            q=query,
            fields="files(id, name, createdTime, modifiedTime, webViewLink)",
            orderBy="modifiedTime desc",
            spaces='drive'
        ).execute()

        all_documents = results.get('files', [])
        logger.info(f"Found {len(all_documents)} total document(s)")

        # Filter by document type if specified
        if document_type:
            filter_type = document_type.lower().replace(" ", "-")
            documents = [
                doc for doc in all_documents
                if filter_type in doc["name"].lower()
            ]
        else:
            documents = all_documents

        # Format document metadata
        formatted_documents = []
        for doc in documents:
            formatted_documents.append({
                "id": doc["id"],
                "name": doc["name"],
                "url": doc["webViewLink"],
                "created": doc.get("createdTime", ""),
                "modified": doc.get("modifiedTime", ""),
            })

        count = len(formatted_documents)
        logger.info(f"Returning {count} filtered document(s)")

        # Build appropriate message
        if count == 0:
            if document_type:
                message = f"No se encontraron documentos del tipo '{document_type}'"
            else:
                message = "No se encontraron documentos guardados"
        elif count == 1:
            message = "Encontrado 1 documento"
        else:
            message = f"Encontrados {count} documentos"

        return {
            "status": "success",
            "message": message,
            "count": count,
            "documents": formatted_documents,
            "folder": user_email,
        }

    except HttpError as e:
        # Handle authentication errors (401/403) by clearing cache
        if e.resp.status in [401, 403]:
            logger.warning(f"Authentication error ({e.resp.status}), clearing cached credentials")
            tool_context.state.pop(TOKEN_CACHE_KEY, None)
            raise
        raise


def list_user_documents(
    tool_context: ToolContext,
    document_type: str = "",
) -> dict:
    """
    List all documents saved in the user's Google Drive folder.

    Implements ADK-native OAuth2 authentication following the official 6-step pattern:
    1. Check cached credentials in tool_context.state
    2. Check auth response from client via tool_context.get_auth_response()
    3. Request authentication via tool_context.request_credential()
    4. ADK handles token exchange automatically
    5. Cache credentials in tool_context.state
    6. Make authenticated API call

    This tool retrieves all Google Docs that have been created and saved
    to the user's personal folder. Optionally filter by document type.

    Args:
        tool_context (ToolContext): Tool context to access user session state
        document_type (str, optional): Filter by document type (e.g., "compra-venta")
            If empty, returns all documents

    Returns:
        dict: Status and list of documents
            - status (str): "success", "pending", or "error"
            - message (str): Descriptive message
            - documents (list): List of document metadata (on success)
            - count (int): Number of documents found (on success)

    Example:
        result = list_user_documents(
            tool_context=context,
            document_type="compra-venta"
        )

        # Returns:
        # {
        #     "status": "success",
        #     "message": "Encontrados 3 documento(s)",
        #     "count": 3,
        #     "documents": [
        #         {
        #             "id": "1abc...",
        #             "name": "contrato-compra-venta-juan-perez-v2",
        #             "url": "https://docs.google.com/document/d/1abc.../edit",
        #             "created": "2025-10-11T15:30:00Z",
        #             "modified": "2025-10-11T16:45:00Z"
        #         },
        #         ...
        #     ]
        # }
    """
    try:
        # STEP 1: Check cached credentials
        logger.debug("Step 1: Checking cached credentials")
        creds = _load_cached_credentials(tool_context)

        if creds and creds.valid:
            logger.info("Using valid cached credentials")
            return _list_documents(creds, document_type, tool_context)

        # STEP 2: Check auth response from client
        logger.debug("Step 2: Checking for auth response from client")
        auth_config = _get_auth_config()
        exchanged_credential = tool_context.get_auth_response(auth_config)

        if exchanged_credential:
            logger.info("Received exchanged credential from ADK")
            # STEP 4: ADK has already handled token exchange
            creds = _credential_to_google_creds(exchanged_credential, auth_config)

            # STEP 5: Cache credentials
            _cache_credentials(tool_context, creds)

            # STEP 6: Make authenticated API call
            return _list_documents(creds, document_type, tool_context)

        # STEP 3: Request authentication
        logger.info("No valid credentials found, requesting authentication from user")
        tool_context.request_credential(auth_config)

        return {
            "status": "pending",
            "message": "Se requiere autenticación. Por favor, autoriza el acceso a Google Drive y Docs.",
            "document_type": document_type
        }

    except HttpError as e:
        error_msg = f"Error de API de Google: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "document_type": document_type,
        }
    except Exception as e:
        error_msg = f"Error al listar documentos: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "document_type": document_type,
        }
