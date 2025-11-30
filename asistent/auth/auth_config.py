"""
This module configures the authentication for Google API toolsets.
Uses lazy loading for credentials to improve startup time.
"""

import logging
from functools import lru_cache
from google.adk.tools.google_api_tool import CalendarToolset, DocsToolset, GmailToolset, GoogleApiToolset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_credentials():
    """Lazy load credentials from Secret Manager (cached)."""
    from ..secrets import get_secret
    client_id = get_secret("google-client-id")
    client_secret = get_secret("google-client-secret")
    return client_id, client_secret


def _configure_toolset(toolset):
    """Configure a toolset with OAuth credentials."""
    client_id, client_secret = _get_credentials()
    if client_id and client_secret:
        toolset.configure_auth(client_id=client_id, client_secret=client_secret)
    else:
        logger.warning(f"OAuth credentials not found for {toolset.__class__.__name__}")
    return toolset


# Custom DriveToolset implementation
class DriveToolset(GoogleApiToolset):
    """Custom toolset for Google Drive API v3."""
    def __init__(self, tool_filter: list = None):
        super().__init__("drive", "v3", tool_filter=tool_filter)


# Tool filters
GMAIL_TOOLS = ["gmail_users_messages_send", "gmail_users_drafts_create", "gmail_users_drafts_send"]
DOCS_TOOLS = ["docs_documents_create", "docs_documents_get", "docs_documents_batch_update"]
CALENDAR_TOOLS = ["calendar_events_insert", "calendar_events_list", "calendar_events_get", "calendar_events_patch", "calendar_events_delete"]
DRIVE_TOOLS = ["drive_files_copy", "drive_files_get"]


# Lazy-initialized toolsets (credentials loaded on first use)
def _create_docs_toolset():
    return _configure_toolset(DocsToolset(tool_filter=DOCS_TOOLS))

def _create_drive_toolset():
    return _configure_toolset(DriveToolset(tool_filter=DRIVE_TOOLS))

def _create_calendar_toolset():
    return _configure_toolset(CalendarToolset(tool_filter=CALENDAR_TOOLS))

def _create_gmail_toolset():
    return _configure_toolset(GmailToolset(tool_filter=GMAIL_TOOLS))


# Export toolsets - created on import but credentials loaded lazily
docs_tool_set = _create_docs_toolset()
drive_tool_set = _create_drive_toolset()
calendar_tool_set = _create_calendar_toolset()
gmail_tool_set = _create_gmail_toolset()

logger.info("Google API toolsets initialized.")