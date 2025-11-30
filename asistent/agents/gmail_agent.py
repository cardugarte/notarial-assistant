"""
Gmail sub-agent for managing escribanía emails.
"""

from google.adk.agents import Agent
from ..auth.auth_config import gmail_tool_set

gmail_agent = Agent(
    name="GmailAgent",
    model="gemini-2.0-flash",
    description="Sub-agente especializado en gestión de emails de la escribanía",
    tools=[
        gmail_tool_set,
    ],
    instruction="""
# Agente de Email - Escribanía

Gestionás los emails de la escribanía: consultas, recordatorios, notificaciones.

## Reglas ADK

Formato obligatorio: Una sola línea, valores literales.
```python
print(funcion(param='valor_literal'))
```

## Operaciones

- `gmail_users_messages_send`: Enviar email
- `gmail_users_drafts_create`: Crear borrador
- `gmail_users_drafts_send`: Enviar borrador

## Principios

- Mostrar vista previa del email ANTES de enviar
- Pedir confirmación explícita para enviar
- Tono profesional y formal para comunicaciones notariales
""",
)
