"""
Tool for listing documents saved in a user's Google Drive folder.
"""

import logging

from google.adk.tools.tool_context import ToolContext

from .google_workspace_utils import (
    ensure_user_folder,
    get_drive_service,
    list_documents_in_folder,
)

logger = logging.getLogger(__name__)


def list_user_documents(
    tool_context: ToolContext,
    document_type: str = "",
) -> dict:
    """
    List all documents saved in the user's Google Drive folder.

    This tool retrieves all Google Docs that have been created and saved
    to the user's personal folder. Optionally filter by document type.

    Args:
        tool_context (ToolContext): Tool context to access user session state
        document_type (str, optional): Filter by document type (e.g., "compra-venta")
            If empty, returns all documents

    Returns:
        dict: Status and list of documents
            - status (str): "success" or "error"
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
        # Step 1: Get user email from tool context state (ADK official pattern)
        # Try app-scoped state first (recommended ADK pattern with 'app:' prefix)
        user_email = tool_context.state.get("app:user_email")

        # Fallback: try without prefix (backward compatibility)
        if not user_email:
            user_email = tool_context.state.get("user_email")

        # If still not found, log detailed debug info and fail
        if not user_email:
            logger.error("User email not found in tool context state")
            logger.error(f"Available state keys: {list(tool_context.state.keys())}")
            logger.error(f"ToolContext type: {type(tool_context)}")
            logger.error(f"ToolContext attributes: {dir(tool_context)}")

            return {
                "status": "error",
                "message": "Usuario no autenticado. No se pudo identificar el email del usuario.",
            }

        logger.info(f"Listing documents for user: {user_email}")
        if document_type:
            logger.info(f"Filtering by type: {document_type}")

        # Step 2: Ensure user folder exists
        user_folder_id = ensure_user_folder(user_email)

        # Step 3: List all documents in user folder
        all_documents = list_documents_in_folder(user_folder_id, user_email)

        # Step 5: Filter by document type if specified
        if document_type:
            # Normalize the filter type
            filter_type = document_type.lower().replace(" ", "-")

            documents = [
                doc
                for doc in all_documents
                if filter_type in doc["name"].lower()
            ]
        else:
            documents = all_documents

        # Step 6: Format document metadata for response
        formatted_documents = []
        for doc in documents:
            formatted_documents.append(
                {
                    "id": doc["id"],
                    "name": doc["name"],
                    "url": doc["webViewLink"],
                    "created": doc.get("createdTime", ""),
                    "modified": doc.get("modifiedTime", ""),
                }
            )

        count = len(formatted_documents)
        logger.info(f"Found {count} document(s)")

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

    except Exception as e:
        error_msg = f"Error al listar documentos: {str(e)}"
        logger.error(error_msg)
        return {
            "status": "error",
            "message": error_msg,
            "document_type": document_type,
        }
