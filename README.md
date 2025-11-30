# Notarial Assistant

A Google Agent Development Kit (ADK) implementation of an intelligent assistant specialized in Argentine notarial law. The agent provides document editing capabilities from Google Docs, calendar management, email handling, and automatic grammatical consistency detection.

## Overview

The Notarial Assistant helps notaries and their staff with:

- **Document Editing**: Read and modify Google Docs contracts, detecting and correcting grammatical inconsistencies automatically
- **Calendar Management**: Schedule appointments, manage deadlines, and track procedures
- **Email Handling**: Send notifications, reminders, and correspondence
- **Legal Analysis**: Detect inconsistencies in contracts (identity, capacity, amounts, dates)
- **Clause Renumbering**: Automatically renumber clauses when adding/removing sections

## Key Features

### Intelligent Document Editing

When you provide a Google Docs URL, the assistant will:

1. Fetch and analyze the complete document
2. Apply requested changes (name substitutions, date updates, etc.)
3. **Automatically detect and correct** grammatical inconsistencies:
   - Gender agreement: "El SR CARLOS" → "La SRA ANDREA"
   - Adjective agreement: "soltero" → "soltera"
   - Pronoun agreement: "el compareciente" → "la compareciente"
4. Present the complete edited text for your approval
5. Create the final document only after explicit confirmation

### Automatic Clause Renumbering

When adding or removing contract clauses:
- Clauses are automatically renumbered (PRIMERA, SEGUNDA, TERCERA...)
- All cross-references are updated accordingly
- No manual renumbering required

## Prerequisites

- A Google Cloud account with billing enabled
- A Google Cloud project with the Vertex AI API enabled
- OAuth credentials configured in Google Cloud Secret Manager
- Python 3.9+ environment

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/notarial-assistant.git
   cd notarial-assistant
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Create `asistent/.env`:
   ```bash
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_LOCATION=us-east4
   GOOGLE_GENAI_USE_VERTEXAI=TRUE
   ```

5. **Set up Google Cloud authentication**:
   ```bash
   gcloud auth application-default login
   gcloud config set project your-project-id
   ```

## Running the Agent

### Web UI (Recommended)
```bash
adk web
```

### CLI Mode
```bash
adk cli ./asistent
```

### Deploy to Cloud Run
```bash
adk deploy cloud_run \
  --project=your-project-id \
  --region=us-central1 \
  --service_name=notarial-assistant \
  --app_name=asistent \
  --with_ui \
  ./asistent
```

## Usage Examples

### Edit a Contract

```
User: Tengo este documento https://docs.google.com/document/d/ABC123/edit
      Cambiá CARLOS TORO por ANDREA GOMEZ

Agent: [Fetches document, applies changes, detects gender inconsistencies]

📄 Documento Editado - Vista Previa Completa

PODER ESPECIAL

En la Ciudad de Buenos Aires... comparece La SRA ANDREA GOMEZ,
de nacionalidad argentina, soltera, mayor de edad...

✅ Cambios aplicados:
- CARLOS TORO → ANDREA GOMEZ
- El SR → La SRA
- soltero → soltera
- el compareciente → la compareciente

📋 ¿Aprobás este texto?

User: Sí, perfecto

Agent: ✅ Documento creado exitosamente: [URL]
```

### Schedule an Appointment

```
User: Creá un turno para mañana a las 10:00 para firma de escritura

Agent: [Gets current date, calculates tomorrow, creates event]

🗓️ Turno creado:
- Fecha: 15/10/2025 10:00 - 11:00
- Título: Firma de escritura
- Calendario: escribania@mastropasqua.ar
```

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
├── CLAUDE.md             # AI assistant instructions
└── README.md             # This file
```

## Troubleshooting

- **Authentication Problems**: Run `gcloud auth application-default login` again
- **API Errors**: Ensure Vertex AI API is enabled: `gcloud services enable aiplatform.googleapis.com`
- **OAuth Issues**: Verify secrets are configured in Secret Manager (`google-client-id`, `google-client-secret`)

## Additional Resources

- [Google Agent Development Kit (ADK)](https://github.com/google/adk-python)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Google Cloud Authentication Guide](https://cloud.google.com/docs/authentication)