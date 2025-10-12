"""
Deploy ADK agent to Vertex AI Agent Engine.

Official documentation:
https://google.github.io/adk-docs/deploy/agent-engine/

Agent Engine is a fully managed auto-scaling service specifically designed
for deploying and managing AI agents built with ADK.

Features:
- Automatic session management (VertexAiSessionService)
- Built-in auto-scaling
- Optimized for agent workloads
- Integrated monitoring and tracing
"""
import vertexai
from vertexai import agent_engines

from asistent.agent import root_agent

# ==============================================================================
# CONFIGURATION - Update with your values
# ==============================================================================

PROJECT_ID = "your-gcp-project-id"
LOCATION = "us-central1"  # Must be a supported region for Agent Engine
                          # See: https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview#supported-regions
STAGING_BUCKET = "gs://your-staging-bucket-name"

# ==============================================================================
# DEPLOYMENT
# ==============================================================================

print("🔧 Initializing Vertex AI...")
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET
)

print("📦 Wrapping agent in AdkApp...")
# Agent Engine automatically uses VertexAiSessionService for persistent sessions
app = agent_engines.AdkApp(
    agent=root_agent,
    enable_tracing=True  # Enable Cloud Trace integration
)

print("🚀 Deploying to Agent Engine...")
print("   This may take several minutes...")

remote_app = agent_engines.create(
    agent_engine=app,
    requirements=[
        "google-cloud-aiplatform[adk,agent_engines]>=1.112.0",
        "google-api-python-client>=2.157.0",
        "google-cloud-secret-manager>=2.22.0",
        "google-cloud-storage>=2.18.0",
    ]
)

print("\n" + "=" * 70)
print("✅ DEPLOYMENT SUCCESSFUL!")
print("=" * 70)
print(f"\n📦 Resource Name:")
print(f"   {remote_app.resource_name}")
print(f"\n🌐 View in Google Cloud Console:")
print(f"   https://console.cloud.google.com/vertex-ai/agents/agent-engines?project={PROJECT_ID}")
print(f"\n📝 To test your deployed agent:")
print(f"   python test_deployed_agent.py")
print("\n" + "=" * 70)
