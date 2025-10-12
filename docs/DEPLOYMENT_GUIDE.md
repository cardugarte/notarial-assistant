# ADK Agent Deployment Guide

This guide explains how to deploy and test the Legal RAG Agent using Vertex AI Agent Engine.

## Overview

The agent has been migrated to use **ADK native authentication** and can be deployed to:

- **Agent Engine** (Recommended) - Fully managed, auto-scaling, built for agents
- **Cloud Run** - More flexible but requires more setup

This guide focuses on Agent Engine deployment.

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **Vertex AI API** enabled
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```

3. **Google Cloud CLI** installed and authenticated
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

4. **GCS Bucket** for staging
   ```bash
   gsutil mb gs://your-staging-bucket
   ```

5. **Python Environment** with dependencies installed
   ```bash
   pip install -r requirements.txt
   ```

## Deployment Steps

### Step 1: Configure OAuth Credentials

1. Go to [Google Cloud Console > APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)

2. Create OAuth 2.0 Client ID:
   - Application type: **Web application**
   - Authorized redirect URIs: Add callback URL(s)

3. Store credentials in Secret Manager:
   ```bash
   # Create secrets
   echo -n "YOUR_CLIENT_ID" | gcloud secrets create google-client-id --data-file=-
   echo -n "YOUR_CLIENT_SECRET" | gcloud secrets create google-client-secret --data-file=-
   ```

### Step 2: Update Deployment Configuration

Edit `deploy_agent_engine.py`:

```python
PROJECT_ID = "your-actual-project-id"
LOCATION = "us-central1"  # Or your preferred region
STAGING_BUCKET = "gs://your-actual-staging-bucket"
```

### Step 3: Deploy to Agent Engine

**Option A: Using Python script**

```bash
python deploy_agent_engine.py
```

**Option B: Using ADK CLI**

```bash
adk deploy agent_engine \
    --project=your-project-id \
    --region=us-central1 \
    --staging_bucket=gs://your-bucket \
    --display_name="Legal RAG Agent" \
    .
```

Deployment takes ~5-10 minutes. You'll receive a resource name like:
```
projects/123456789/locations/us-central1/reasoningEngines/987654321
```

### Step 4: Test Deployed Agent

1. Update `test_deployed_agent.py` with your resource name

2. Run tests:
   ```bash
   python test_deployed_agent.py
   ```

## Testing OAuth Flow

### Local Testing

For local development and OAuth testing:

```bash
python client/agent_client.py
```

This will:
1. Start the agent locally
2. Detect when OAuth is needed
3. Guide you through the authorization flow
4. Complete the tool execution

### Deployed Agent OAuth

OAuth with deployed agents requires additional setup:

1. **Web Application**: Create a web app to handle OAuth callbacks
2. **Session Persistence**: Agent Engine automatically persists sessions
3. **Token Management**: ADK handles token refresh automatically

See [ADK Authentication Guide](https://google.github.io/adk-docs/tools/authentication/) for details.

## Monitoring and Debugging

### View Agent in Console

```
https://console.cloud.google.com/vertex-ai/agents/agent-engines?project=YOUR_PROJECT_ID
```

### Check Logs

```bash
gcloud logging read "resource.type=aiplatform.googleapis.com/ReasoningEngine" \
    --project=YOUR_PROJECT_ID \
    --limit=50
```

### Enable Tracing

Agent Engine deployment includes `enable_tracing=True` for Cloud Trace integration:

```
https://console.cloud.google.com/traces?project=YOUR_PROJECT_ID
```

## Troubleshooting

### Deployment Fails

1. **Check APIs enabled**:
   ```bash
   gcloud services list --enabled
   ```

2. **Verify bucket access**:
   ```bash
   gsutil ls gs://your-staging-bucket
   ```

3. **Check IAM permissions**: Service account needs:
   - `aiplatform.reasoningEngines.create`
   - `storage.buckets.get`
   - `secretmanager.versions.access`

### Agent Not Responding

1. **Check agent status** in Cloud Console
2. **Review logs** for errors
3. **Verify Secret Manager** secrets exist and are accessible

### OAuth Not Working

1. **Verify OAuth client** is configured correctly
2. **Check redirect URIs** match your setup
3. **Ensure scopes** in `auth_config.py` match OAuth client

## Cost Considerations

Agent Engine pricing:
- **Prediction requests**: Charged per request
- **Model usage**: Charged per token (Gemini pricing)
- **Storage**: GCS bucket storage costs

See: [Vertex AI Pricing](https://cloud.google.com/vertex-ai/pricing)

## Next Steps

- [ ] Configure OAuth client credentials
- [ ] Deploy to Agent Engine
- [ ] Test RAG tools (no auth required)
- [ ] Test Workspace tools (OAuth required)
- [ ] Set up monitoring and alerts
- [ ] Configure production secrets
- [ ] Implement web UI for OAuth (optional)

## References

- [ADK Deployment Guide](https://google.github.io/adk-docs/deploy/)
- [Agent Engine Overview](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview)
- [ADK Authentication](https://google.github.io/adk-docs/tools/authentication/)
