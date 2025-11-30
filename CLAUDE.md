# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Notarial Assistant is a Google Agent Development Kit (ADK) implementation specialized in Argentine notarial law. The agent provides capabilities for document editing from Google Docs, calendar management, email handling, and grammatical consistency detection.

## Key Commands

### Development

```bash
# Run the agent locally (web UI)
adk web

# Run in CLI mode
adk cli ./asistent

# Deploy to Google Cloud Run
adk deploy cloud_run \
  --project=escribania-mastropasqua \
  --region=us-central1 \
  --service_name=notarial-assistant \
  --app_name=asistent \
  --with_ui \
  ./asistent
```

### Environment Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Google Cloud authentication
gcloud auth application-default login
gcloud config set project escribania-mastropasqua
```

## Architecture

### Core Components

1. **Agent Configuration** (`asistent/agent.py`)
   - Defines `root_agent` with model configuration (gemini-2.5-flash)
   - Registers tools: Calendar, Docs, Gmail, Drive, get_current_date
   - Contains Spanish instruction prompt for notarial assistant behavior
   - **Critical constraint**: ADK requires single-line tool calls like `print(function(param='value'))` - no imports, variables, or multi-line code

2. **Package Initialization** (`asistent/__init__.py`)
   - Loads environment variables from `.env`
   - Initializes Vertex AI with `PROJECT_ID` and `LOCATION`
   - Exports `root_agent` for ADK entry point

3. **Configuration** (`asistent/config.py`)
   - Environment variables: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`

4. **Secrets Management** (`asistent/secrets.py`)
   - Retrieves OAuth credentials from Google Cloud Secret Manager
   - Secrets: `google-client-id`, `google-client-secret`

### Authentication & Google API Toolsets

**File**: `asistent/auth/auth_config.py`

- Creates filtered toolsets for Calendar, Docs, Gmail, and Drive APIs
- **Custom DriveToolset**: Extends `GoogleApiToolset` to provide Drive v3 operations (files.copy, files.get)
- Uses `tool_filter` to expose only required operations:
  - **Calendar**: insert, list, get, patch, delete events
  - **Docs**: create, get, batch_update documents
  - **Gmail**: send messages, create/send drafts
  - **Drive**: copy and get files
- Configures OAuth authentication via `configure_auth()` with credentials from Secret Manager

### Tools (`asistent/tools/`)

- **`get_current_date.py`**: Get current date/time (required before creating events with relative dates)

### Critical Workflows

#### Document Editing from Google Docs URL

When user provides a Google Docs URL:

1. **Fetch document**: `docs_documents_get(document_id='...')`
2. **Model processes mentally**: Apply changes, detect grammatical inconsistencies (gender, agreement)
3. **Present full edited text** to user for approval (Markdown format)
4. **After approval**:
   - Copy document: `drive_files_copy(file_id='...', name='...')`
   - Apply batch changes: `docs_documents_batch_update(document_id='...', requests=[...])`

**Why**: Preserves formatting, shows user complete result before creating document, applies all changes in single API call.

#### Calendar Event Creation with Relative Dates

When user says "tomorrow", "in 3 days", etc.:

1. **MUST call** `get_current_date()` first
2. Wait for response with current date
3. Calculate target date mentally
4. Create event with literal ISO string: `calendar_events_insert(calendar_id='escribania@mastropasqua.ar', start={'dateTime': '2025-10-14T10:00:00-03:00', 'timeZone': 'America/Argentina/Buenos_Aires'}, ...)`

**Critical**: Always use `calendar_id='escribania@mastropasqua.ar'` for this project.

#### Contract Clause Renumbering

When adding/removing clauses:

1. Perform modification
2. **Automatically renumber** all subsequent clauses (PRIMERA, SEGUNDA, TERCERA, etc.)
3. Update all cross-references to clause numbers
4. Run logical analysis to detect inconsistencies
5. Report completion to user

### Environment Variables

Required in `asistent/.env`:

```bash
GOOGLE_CLOUD_PROJECT=escribania-mastropasqua
GOOGLE_CLOUD_LOCATION=us-east4
GOOGLE_GENAI_USE_VERTEXAI=TRUE
```

### Dependencies

- **Core**: `google-adk>=1.16.0`, `google-cloud-aiplatform[adk,agent_engines]>=1.112.0`
- **Google Cloud**: `google-cloud-secret-manager`, `google-api-python-client`
- **Auth**: `authlib`, `google-auth`, `google-auth-httplib2`
- **Utilities**: `python-dotenv`, `pydantic`, `requests`, `PyYAML`

## Important Constraints

1. **ADK Tool Call Format**: Agent instructions must generate single-line Python like `print(function(param='value'))`. No imports, variables, or multi-line code allowed - ADK parser will fail with "Malformed function call".

2. **Never Create Documents Prematurely**: Agent should present Markdown drafts first, iterate with user, and only create Google Docs when user explicitly approves.

3. **Automatic Inconsistency Detection**: Agent must detect grammatical inconsistencies (gender, agreement) when editing documents and correct them automatically before presenting result.

4. **Clause Renumbering**: When adding/removing contract clauses, agent must automatically renumber all subsequent clauses and update cross-references.

5. **Calendar ID**: Always use `escribania@mastropasqua.ar` for calendar operations in this project.

## Project Structure

```
notarial-assistant/
├── asistent/               # Main agent package
│   ├── __init__.py        # Vertex AI initialization
│   ├── agent.py           # Root agent definition
│   ├── config.py          # Configuration constants
│   ├── secrets.py         # Secret Manager integration
│   ├── auth/
│   │   └── auth_config.py # Google API toolsets + OAuth
│   └── tools/
│       └── get_current_date.py
├── requirements.txt       # Python dependencies
└── README.md             # User documentation
```

## Testing and Debugging

- Use `adk web` for interactive testing with web UI
- Use `adk cli` for command-line interaction
- Check logs in background bash processes when deploying
- Verify OAuth flow works: credentials stored in `~/.config/gcloud/application_default_credentials.json`
