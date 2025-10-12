#!/usr/bin/env python3
"""
Create a test document in Google Drive to verify the integration is working.
"""

import sys
import os

# Set the Service Account key file
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/tmp/service-account-key.json'

# Import the utility functions
sys.path.insert(0, '/home/cardugarte/projects/adk-rag-agent')

from asistent.tools.google_workspace_utils import (
    ensure_user_folder,
    create_formatted_document,
    normalize_filename
)

def create_test_document():
    """Create a test document for a specific user."""

    # User to create document for
    user_email = "carlos@xplorers.ar"

    # Document details
    doc_title = "Contrato Test - Prueba Sistema"
    doc_content = """
CONTRATO DE PRUEBA DEL SISTEMA

PRIMERA: PARTES INTERVINIENTES
En la Ciudad de Buenos Aires, a los ____ días del mes de _______ de 2025, comparecen:
Por una parte: Juan Pérez, DNI 12.345.678, con domicilio en Calle Falsa 123, Ciudad de Buenos Aires.
Por otra parte: María García, DNI 87.654.321, con domicilio en Avenida Siempreviva 456, Ciudad de Buenos Aires.

SEGUNDA: OBJETO DEL CONTRATO
El presente contrato tiene como objeto la compra-venta de un inmueble ubicado en...

TERCERA: PRECIO Y FORMA DE PAGO
El precio total de la operación asciende a la suma de PESOS QUINIENTOS MIL ($500.000).

CUARTA: CONDICIONES GENERALES
Las partes acuerdan que este documento es una PRUEBA del sistema de generación automática de contratos.

Este documento fue generado automáticamente por el Agente Legal Inteligente para verificar la correcta integración con Google Drive y Google Docs.

Fecha de creación: """ + str(__import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    print("=" * 60)
    print("Creando Documento de Prueba")
    print("=" * 60)
    print(f"\nUsuario: {user_email}")
    print(f"Título: {doc_title}")

    try:
        # Step 1: Ensure user folder exists
        print("\n1. Verificando/creando carpeta del usuario...")
        user_folder_id = ensure_user_folder(user_email)
        print(f"   ✓ Carpeta del usuario: {user_folder_id}")

        # Step 2: Normalize filename
        base_name = normalize_filename(doc_title)
        print(f"\n2. Nombre normalizado: {base_name}")

        # Step 3: Create document
        print("\n3. Creando documento de Google Docs...")
        doc_id, doc_url = create_formatted_document(
            title=doc_title,
            content=doc_content,
            folder_id=user_folder_id,
            user_email=user_email
        )

        print("\n" + "=" * 60)
        print("✓ DOCUMENTO CREADO EXITOSAMENTE")
        print("=" * 60)
        print(f"\nDocument ID: {doc_id}")
        print(f"Document URL: {doc_url}")
        print(f"\nUbicación en Drive:")
        print(f"  Drive > Contratos Generados > {user_email} > {doc_title}")
        print("\n¡Abrí el link para ver el documento!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_test_document()
    sys.exit(0 if success else 1)
