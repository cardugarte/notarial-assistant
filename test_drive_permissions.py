#!/usr/bin/env python3
"""
Test script to verify Google Drive and Docs API permissions.
This script attempts to:
1. Authenticate with Application Default Credentials (Service Account)
2. List files in Drive (basic read permission test)
3. Create a test Google Doc (write permission test)
"""

import sys
from google.auth import default
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def test_drive_permissions():
    """Test if Service Account can access Google Drive."""
    print("=" * 60)
    print("Testing Google Drive & Docs API Permissions")
    print("=" * 60)

    try:
        # Step 1: Get credentials with Domain-Wide Delegation
        print("\n1. Authenticating with Application Default Credentials + Domain-Wide Delegation...")
        credentials, project = default()

        # Use Domain-Wide Delegation to act as a user
        test_user = "escribania@mastropasqua.ar"  # Change this to test with different users
        scopes = [
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file'
        ]

        if hasattr(credentials, 'with_subject'):
            credentials = credentials.with_scopes(scopes).with_subject(test_user)
            print(f"   ✓ Using Domain-Wide Delegation as: {test_user}")
        else:
            print(f"   ⚠ Credentials don't support delegation, using default")

        print(f"   ✓ Project: {project}")
        print(f"   ✓ Credentials type: {type(credentials).__name__}")

        # Step 2: Build Drive service
        print("\n2. Building Google Drive service...")
        drive_service = build('drive', 'v3', credentials=credentials)
        print("   ✓ Drive service created")

        # Step 3: Build Docs service
        print("\n3. Building Google Docs service...")
        docs_service = build('docs', 'v1', credentials=credentials)
        print("   ✓ Docs service created")

        # Step 4: Test listing files (requires drive.readonly scope minimum)
        print("\n4. Testing Drive file listing (read permission)...")
        try:
            results = drive_service.files().list(
                pageSize=5,
                fields="files(id, name, mimeType)"
            ).execute()
            files = results.get('files', [])
            print(f"   ✓ Successfully listed {len(files)} file(s)")
            if files:
                for file in files[:3]:
                    print(f"     - {file['name']} ({file['mimeType']})")
        except HttpError as e:
            print(f"   ✗ ERROR listing files: {e}")
            print(f"   This likely means the Service Account doesn't have Drive access")
            return False

        # Step 5: Find the "Contratos Generados" folder
        print("\n5. Finding 'Contratos Generados' folder...")
        try:
            folder_query = "name='Contratos Generados' and mimeType='application/vnd.google-apps.folder'"
            folder_results = drive_service.files().list(
                q=folder_query,
                fields="files(id, name)"
            ).execute()
            folders = folder_results.get('files', [])

            if not folders:
                print("   ✗ ERROR: 'Contratos Generados' folder not found")
                print("   Please create this folder and share it with the Service Account")
                return False

            root_folder_id = folders[0]['id']
            print(f"   ✓ Found folder ID: {root_folder_id}")
        except HttpError as e:
            print(f"   ✗ ERROR finding folder: {e}")
            return False

        # Step 6: Create user folder inside "Contratos Generados"
        print("\n6. Creating user folder (test-user@example.com)...")
        test_user_email = "test-user@example.com"
        try:
            # Check if user folder already exists
            user_folder_query = f"name='{test_user_email}' and '{root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
            user_folder_results = drive_service.files().list(
                q=user_folder_query,
                fields="files(id, name)"
            ).execute()
            user_folders = user_folder_results.get('files', [])

            if user_folders:
                user_folder_id = user_folders[0]['id']
                print(f"   ✓ User folder already exists: {user_folder_id}")
            else:
                # Create user folder
                file_metadata = {
                    'name': test_user_email,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [root_folder_id]
                }
                user_folder = drive_service.files().create(
                    body=file_metadata,
                    fields='id'
                ).execute()
                user_folder_id = user_folder['id']
                print(f"   ✓ Created user folder: {user_folder_id}")
        except HttpError as e:
            print(f"   ✗ ERROR creating user folder: {e}")
            print(f"   Error details: {e.error_details if hasattr(e, 'error_details') else 'N/A'}")
            return False

        # Step 7: Test creating a document inside the user folder
        print("\n7. Testing Google Doc creation inside user folder...")
        try:
            doc = docs_service.documents().create(
                body={'title': 'Test Document - Permission Check'}
            ).execute()
            doc_id = doc['documentId']
            print(f"   ✓ Successfully created document: {doc_id}")

            # Move the document to the user folder
            print("\n8. Moving document to user folder...")
            drive_service.files().update(
                fileId=doc_id,
                addParents=user_folder_id,
                fields='id, parents, webViewLink'
            ).execute()
            print("   ✓ Document moved to user folder")

            # Try to get the document to verify it exists
            doc_info = drive_service.files().get(
                fileId=doc_id,
                fields='name, webViewLink, parents'
            ).execute()
            print(f"   ✓ Document name: {doc_info['name']}")
            print(f"   ✓ Document URL: {doc_info['webViewLink']}")
            print(f"   ✓ Full path: Contratos Generados/{test_user_email}/{doc_info['name']}")

            # Clean up - delete the test document
            print("\n9. Cleaning up test document...")
            drive_service.files().delete(fileId=doc_id).execute()
            print("   ✓ Test document deleted")

            # Optionally clean up user folder (uncomment if needed)
            # print("\n10. Cleaning up user folder...")
            # drive_service.files().delete(fileId=user_folder_id).execute()
            # print("   ✓ User folder deleted")

        except HttpError as e:
            print(f"   ✗ ERROR creating document: {e}")
            print(f"   Error details: {e.error_details if hasattr(e, 'error_details') else 'N/A'}")

            if e.resp.status == 403:
                print("\n   DIAGNOSIS: Permission Denied (403)")
                print("   The Service Account doesn't have permission to create documents.")
                print("\n   SOLUTIONS:")
                print("   1. Share a Drive folder with the Service Account:")
                print(f"      Email: {credentials.service_account_email if hasattr(credentials, 'service_account_email') else '997298514042-compute@developer.gserviceaccount.com'}")
                print("      Permission: Editor")
                print("\n   2. Or enable Domain-Wide Delegation for the Service Account")
                return False
            return False

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED - Service Account has proper permissions")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_drive_permissions()
    sys.exit(0 if success else 1)
