"""
ADK Agent Client - Handles interactive OAuth flow for local testing.

Based on official ADK documentation:
https://google.github.io/adk-docs/tools/authentication/#1-configuring-tools-with-authentication

This client demonstrates the complete OAuth2 flow:
1. Detect when agent requests authentication
2. Redirect user to authorization URL
3. Receive callback URL from user
4. Send auth response back to ADK
5. ADK handles token exchange automatically
"""
import asyncio
from typing import Optional

from google.adk.runner import Runner
from google.adk.session import InMemorySessionService
from google.genai import types

from asistent.agent import root_agent


def get_auth_request_function_call(event) -> Optional[types.FunctionCall]:
    """
    Extract auth request function call from event.

    Args:
        event: Event from agent execution

    Returns:
        FunctionCall if this is an auth request event, None otherwise
    """
    if not event.content or not event.content.parts:
        return None

    for part in event.content.parts:
        if (part and part.function_call
            and part.function_call.name == 'adk_request_credential'
            and event.long_running_tool_ids
            and part.function_call.id in event.long_running_tool_ids):
            return part.function_call

    return None


def get_auth_config(auth_request_function_call: types.FunctionCall):
    """
    Extract AuthConfig from auth request function call.

    Args:
        auth_request_function_call: Function call requesting authentication

    Returns:
        AuthConfig object
    """
    from google.adk.auth.auth_tool import AuthConfig

    if not auth_request_function_call.args:
        raise ValueError("No args in auth request function call")

    auth_config = auth_request_function_call.args.get('authConfig')
    if not auth_config:
        raise ValueError("No authConfig in function call args")

    if isinstance(auth_config, dict):
        return AuthConfig.model_validate(auth_config)

    return auth_config


async def run_agent_with_auth(user_message: str):
    """
    Run agent and handle interactive OAuth flow.

    This function:
    1. Sends a message to the agent
    2. Detects if authentication is required
    3. Guides user through OAuth flow
    4. Resumes agent execution after authentication

    Args:
        user_message: Message to send to the agent
    """
    # Initialize session service and runner
    session_service = InMemorySessionService()
    runner = Runner(root_agent, session_service=session_service)

    # Create session
    session = await session_service.create_session(user_id='user')

    # STEP 1: Run agent and detect auth request
    print(f"\n🤖 Enviando mensaje: {user_message}")
    events_async = runner.run_async(
        session_id=session.id,
        user_id='user',
        new_message=types.Content(parts=[types.Part(text=user_message)])
    )

    auth_request_function_call_id = None
    auth_config = None

    async for event in events_async:
        print(f"📨 Evento: {event}")

        if (auth_request_fc := get_auth_request_function_call(event)):
            print("\n🔐 Autenticación requerida por el agente")
            auth_request_function_call_id = auth_request_fc.id
            auth_config = get_auth_config(auth_request_fc)
            break

    if not auth_request_function_call_id:
        print("\n✅ Agente completó sin necesitar autenticación")
        return

    # STEP 2: Redirect user for authorization
    base_auth_uri = auth_config.exchanged_auth_credential.oauth2.auth_uri
    redirect_uri = 'http://localhost:8080/callback'  # Must match OAuth client config
    auth_request_uri = f"{base_auth_uri}&redirect_uri={redirect_uri}"

    print(f"\n🌐 Por favor visita esta URL para autorizar:")
    print(f"{auth_request_uri}\n")

    # STEP 3: Get callback URL from user
    auth_response_uri = input("📋 Pega la URL de callback completa aquí: ").strip()

    if not auth_response_uri:
        print("❌ No se proporcionó URL de callback. Abortando.")
        return

    # STEP 4: Send auth response back to ADK
    auth_config.exchanged_auth_credential.oauth2.auth_response_uri = auth_response_uri
    auth_config.exchanged_auth_credential.oauth2.redirect_uri = redirect_uri

    auth_content = types.Content(
        role='user',
        parts=[types.Part(
            function_response=types.FunctionResponse(
                id=auth_request_function_call_id,
                name='adk_request_credential',
                response=auth_config.model_dump()
            )
        )]
    )

    # STEP 5: Resume execution - ADK handles token exchange
    print("\n🔄 Enviando detalles de autenticación de vuelta al agente...")
    events_async_after_auth = runner.run_async(
        session_id=session.id,
        user_id='user',
        new_message=auth_content
    )

    print("\n--- Respuesta del Agente después de Autenticación ---")
    async for event in events_async_after_auth:
        print(event)


if __name__ == "__main__":
    print("🚀 Cliente ADK Agent - Testing Local con OAuth")
    print("=" * 50)

    message = input("\n💬 Ingresa tu mensaje al agente: ")
    asyncio.run(run_agent_with_auth(message))
