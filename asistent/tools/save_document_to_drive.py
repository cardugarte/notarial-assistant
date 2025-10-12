"""
Tool for saving approved legal contracts to Google Drive as formatted Google Docs.
"""

import logging

from google.adk.tools.tool_context import ToolContext

from .google_workspace_utils import (
    create_formatted_document,
    ensure_user_folder,
    get_docs_service,
    get_drive_service,
    get_next_version_name,
    normalize_filename,
)

logger = logging.getLogger(__name__)


def save_document_to_drive(
    document_title: str,
    document_content: str,
    document_type: str,
    tool_context: ToolContext,
) -> dict:
    """
    Save an approved legal contract to Google Drive as a formatted Google Doc.

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
            - status (str): "success" or "error"
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
        #     "folder": "carlos@xplorers.ar"
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
                "message": "Usuario no autenticado. No se pudo identificar el email del usuario. Por favor, asegúrate de estar logueado correctamente.",
            }

        logger.info(f"Saving document for user: {user_email}")
        logger.info(f"Document title: {document_title}")
        logger.info(f"Document type: {document_type}")

        # Step 2: Ensure user folder exists (create if needed)
        user_folder_id = ensure_user_folder(user_email)

        # Step 3: Generate normalized base filename
        base_name = normalize_filename(document_title)

        # Step 4: Get next version name (handles versioning automatically)
        versioned_name = get_next_version_name(user_folder_id, base_name, user_email)

        # Step 5: Create formatted Google Doc
        doc_id, doc_url = create_formatted_document(
            title=versioned_name,
            content=document_content,
            folder_id=user_folder_id,
            user_email=user_email
        )

        # Step 7: Store document info in context state (for potential future reference)
        if "saved_documents" not in tool_context.state:
            tool_context.state["saved_documents"] = []

        tool_context.state["saved_documents"].append(
            {
                "document_id": doc_id,
                "document_title": versioned_name,
                "document_type": document_type,
                "document_url": doc_url,
            }
        )

        logger.info(f"Document saved successfully: {versioned_name}")

        return {
            "status": "success",
            "message": f"Documento guardado exitosamente como '{versioned_name}'",
            "document_id": doc_id,
            "document_url": doc_url,
            "version": versioned_name,
            "folder": user_email,
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
