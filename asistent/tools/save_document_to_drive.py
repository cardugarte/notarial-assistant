"""
Tool for saving approved legal contracts to Google Drive as formatted Google Docs.

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

# Token cache key for storing credentials in ADK session state
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


def _normalize_filename(title: str) -> str:
    """
    Normalize a document title to a valid filename.

    Args:
        title: The document title

    Returns:
        Normalized filename (without extension)
    """
    import re

    # Convert to lowercase
    filename = title.lower()

    # Replace spaces with hyphens
    filename = filename.replace(' ', '-')

    # Remove accents
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ñ': 'n', 'ü': 'u'
    }
    for old, new in replacements.items():
        filename = filename.replace(old, new)

    # Remove special characters (keep letters, numbers, hyphens)
    filename = re.sub(r'[^a-z0-9-]', '', filename)

    # Remove consecutive hyphens
    filename = re.sub(r'-+', '-', filename)

    # Remove leading/trailing hyphens
    filename = filename.strip('-')

    return filename


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


def _get_next_version_name(drive_service, folder_id: str, base_name: str) -> str:
    """
    Find existing versions and return the next version name.

    Args:
        drive_service: Authenticated Google Drive service
        folder_id: The folder to search in
        base_name: The base filename (without version)

    Returns:
        The versioned filename
    """
    logger.info(f"Checking for existing versions of: {base_name}")

    # Search for files with similar names
    query = (
        f"name contains '{base_name}' and "
        f"'{folder_id}' in parents and "
        f"mimeType='application/vnd.google-apps.document' and "
        f"trashed=false"
    )

    results = drive_service.files().list(
        q=query,
        fields="files(name)",
        spaces='drive'
    ).execute()

    files = results.get('files', [])

    if not files:
        logger.info(f"No existing versions found, using base name: {base_name}")
        return base_name

    # Extract version numbers
    versions = []
    for file in files:
        name = file['name']

        if name == base_name:
            versions.append(1)
            continue

        if '-v' in name:
            try:
                version_str = name.split('-v')[-1]
                version_num = int(version_str)
                versions.append(version_num)
            except (ValueError, IndexError):
                continue

    if not versions:
        return base_name

    next_version = max(versions) + 1
    versioned_name = f"{base_name}-v{next_version}"

    logger.info(f"Found {len(versions)} existing version(s), using: {versioned_name}")
    return versioned_name


def _create_document(
    creds: Credentials,
    title: str,
    content: str,
    doc_type: str,
    tool_context: ToolContext
) -> dict:
    """
    Create a formatted Google Doc using authenticated credentials.

    STEP 6: Make authenticated API call

    Args:
        creds: Authenticated Google OAuth2 credentials
        title: Document title
        content: Document content
        doc_type: Type/category of document
        tool_context: Tool context for state management

    Returns:
        Success response with document details

    Raises:
        HttpError: If API call fails
    """
    try:
        # Build Google API services
        docs_service = build('docs', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)

        # Get user email from credentials
        # TODO: May need to call userinfo API to get email
        user_email = tool_context.state.get("app:user_email") or tool_context.state.get("user_email")
        if not user_email:
            # Extract from token or make userinfo call
            logger.warning("User email not in state, using default folder logic")
            user_email = "default_user"

        # Get root folder from config
        from ..secrets import get_drive_root_folder_id
        root_folder_id = get_drive_root_folder_id()

        # Ensure user folder exists
        user_folder_id = _ensure_user_folder(drive_service, user_email, root_folder_id)

        # Generate normalized base filename
        base_name = _normalize_filename(title)

        # Get next version name
        versioned_name = _get_next_version_name(drive_service, user_folder_id, base_name)

        logger.info(f"Creating document: {versioned_name}")

        # Create blank document
        doc = docs_service.documents().create(
            body={'title': versioned_name}
        ).execute()

        doc_id = doc['documentId']
        logger.info(f"Created blank document with ID: {doc_id}")

        # Insert content
        requests = [
            {
                'insertText': {
                    'location': {'index': 1},
                    'text': content
                }
            }
        ]

        if requests:
            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            logger.info(f"Inserted content into document {doc_id}")

        # Move to user folder
        drive_service.files().update(
            fileId=doc_id,
            addParents=user_folder_id,
            fields='id, parents, webViewLink'
        ).execute()
        logger.info(f"Moved document to folder {user_folder_id}")

        # Get shareable link
        file = drive_service.files().get(
            fileId=doc_id,
            fields='webViewLink'
        ).execute()

        doc_url = file['webViewLink']
        logger.info(f"Document created successfully: {doc_url}")

        # Store document info in context state
        if "saved_documents" not in tool_context.state:
            tool_context.state["saved_documents"] = []

        tool_context.state["saved_documents"].append({
            "document_id": doc_id,
            "document_title": versioned_name,
            "document_type": doc_type,
            "document_url": doc_url,
        })

        return {
            "status": "success",
            "message": f"Documento guardado exitosamente como '{versioned_name}'",
            "document_id": doc_id,
            "document_url": doc_url,
            "version": versioned_name,
            "folder": user_email,
        }

    except HttpError as e:
        # Handle authentication errors (401/403) by clearing cache
        if e.resp.status in [401, 403]:
            logger.warning(f"Authentication error ({e.resp.status}), clearing cached credentials")
            tool_context.state.pop(TOKEN_CACHE_KEY, None)
            raise
        raise


def save_document_to_drive(
    document_title: str,
    document_content: str,
    document_type: str,
    tool_context: ToolContext,
) -> dict:
    """
    Save an approved legal contract to Google Drive as a formatted Google Doc.

    Implements ADK-native OAuth2 authentication following the official 6-step pattern:
    1. Check cached credentials in tool_context.state
    2. Check auth response from client via tool_context.get_auth_response()
    3. Request authentication via tool_context.request_credential()
    4. ADK handles token exchange automatically
    5. Cache credentials in tool_context.state
    6. Make authenticated API call

    This tool creates a new Google Doc with rich formatting and saves it to the
    user's personal folder in Drive. If a document with the same name already exists,
    a new version is created automatically (e.g., -v2, -v3).

    Args:
        document_title (str): Descriptive title for the document
            Example: "Contrato Compra-Venta Juan Pérez"
        document_content (str): Full contract text to be saved
        document_type (str): Type/category of contract
            Examples: "compra-venta", "locacion", "poder", "certificacion"
        tool_context (ToolContext): Tool context to access user session state

    Returns:
        dict: Status and document information
            - status (str): "success", "pending", or "error"
            - message (str): Descriptive message
            - document_id (str): Google Docs document ID (on success)
            - document_url (str): Shareable link to document (on success)
            - version (str): Version name of created document (on success)
            - folder (str): User's folder name (on success)

    Example:
        result = save_document_to_drive(
            document_title="Contrato Compra-Venta Juan Pérez",
            document_content="CONTRATO DE COMPRA-VENTA\\n\\nPRIMERA: ...",
            document_type="compra-venta",
            tool_context=context
        )

        # Returns:
        # {
        #     "status": "success",
        #     "message": "Documento guardado exitosamente como 'contrato-compra-venta-juan-perez-v2'",
        #     "document_id": "1abc...",
        #     "document_url": "https://docs.google.com/document/d/1abc.../edit",
        #     "version": "contrato-compra-venta-juan-perez-v2",
        #     "folder": "user@example.com"
        # }
    """
    try:
        # STEP 1: Check cached credentials
        logger.debug("Step 1: Checking cached credentials")
        creds = _load_cached_credentials(tool_context)

        if creds and creds.valid:
            logger.info("Using valid cached credentials")
            return _create_document(creds, document_title, document_content, document_type, tool_context)

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
            return _create_document(creds, document_title, document_content, document_type, tool_context)

        # STEP 3: Request authentication
        logger.info("No valid credentials found, requesting authentication from user")
        tool_context.request_credential(auth_config)

        return {
            "status": "pending",
            "message": "Se requiere autenticación. Por favor, autoriza el acceso a Google Drive y Docs.",
            "document_title": document_title,
            "document_type": document_type
        }

    except HttpError as e:
        error_msg = f"Error de API de Google: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "document_title": document_title,
            "document_type": document_type,
        }
    except Exception as e:
        error_msg = f"Error al guardar documento: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "document_title": document_title,
            "document_type": document_type,
        }
