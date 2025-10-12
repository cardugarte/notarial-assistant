"""
Test deployed agent in Vertex AI Agent Engine.

This script demonstrates how to interact with an agent deployed to Agent Engine:
1. Connect to the deployed agent using its resource name
2. Create a remote session
3. Send queries and receive responses

Documentation:
https://google.github.io/adk-docs/deploy/agent-engine/#test-deployed-agent
"""
import asyncio

from vertexai import agent_engines

# ==============================================================================
# CONFIGURATION - Update with your deployed agent's resource name
# ==============================================================================

# Get this from deploy_agent_engine.py output or Cloud Console
RESOURCE_NAME = "projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_RESOURCE_ID"

# Format: "projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{RESOURCE_ID}"
# Note: PROJECT_NUMBER is different from PROJECT_ID
# Find it in: https://console.cloud.google.com/vertex-ai/agents/agent-engines

# ==============================================================================
# TEST FUNCTIONS
# ==============================================================================


async def test_deployed_agent():
    """Test the deployed agent with sample queries."""

    print("🔌 Connecting to deployed agent...")
    print(f"   Resource: {RESOURCE_NAME}")

    # Get deployed agent
    remote_app = agent_engines.get(RESOURCE_NAME)

    print("\n📝 Creating remote session...")
    # Create session on Agent Engine
    session = await remote_app.async_create_session(user_id="test_user")
    print(f"   Session ID: {session['id']}")
    print(f"   App Name: {session['app_name']}")

    # Test queries
    test_queries = [
        "Lista los corpus disponibles",
        "¿Qué información tienes sobre contratos de compra-venta?",
    ]

    for query in test_queries:
        print("\n" + "=" * 70)
        print(f"💬 Query: {query}")
        print("=" * 70)

        print("\n📨 Streaming response:")
        async for event in remote_app.async_stream_query(
            user_id="test_user",
            session_id=session["id"],
            message=query
        ):
            # Print each event
            if event.get("content"):
                parts = event["content"].get("parts", [])
                for part in parts:
                    if "text" in part:
                        print(f"🤖 {part['text']}")
                    elif "function_call" in part:
                        print(f"🔧 Tool: {part['function_call']['name']}")

    print("\n" + "=" * 70)
    print("✅ Testing complete!")
    print("=" * 70)


async def test_oauth_flow():
    """
    Test agent with a tool that requires OAuth (e.g., save_document_to_drive).

    Note: For OAuth to work with deployed agents, you need to:
    1. Set up OAuth consent screen in Google Cloud Console
    2. Configure authorized redirect URIs
    3. Handle the OAuth callback in your application

    This is more complex with deployed agents and typically requires
    a web application to handle the OAuth flow.
    """
    print("\n🔐 Testing OAuth flow...")
    print("   Note: OAuth with deployed agents requires additional setup")
    print("   See: https://google.github.io/adk-docs/tools/authentication/")

    # TODO: Implement OAuth testing
    # This requires a web server to handle OAuth callbacks
    pass


if __name__ == "__main__":
    print("🧪 ADK Agent - Testing Deployed Agent")
    print("=" * 70)

    if "YOUR_PROJECT" in RESOURCE_NAME or "YOUR_RESOURCE" in RESOURCE_NAME:
        print("\n❌ ERROR: Please update RESOURCE_NAME in this script")
        print("   Get the resource name from deploy_agent_engine.py output")
        print("   or from Google Cloud Console")
    else:
        asyncio.run(test_deployed_agent())
