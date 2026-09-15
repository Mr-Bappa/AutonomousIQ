# GCP / Vertex AI integration

What's actually wired in code right now, and what's still just a plan.

## Wired in code

- **`libs/gcp/config.py`** -- reads `GCP_PROJECT_ID`, `GCP_REGION`, `GCS_BUCKET`, `VERTEX_MODEL` from env. Leave `GCP_PROJECT_ID` blank to run with zero GCP dependency.
- **`libs/gcp/storage.py`** -- Document uploads go to `gs://$GCS_BUCKET/...` if `GCS_BUCKET` is set, else fall back to local disk (`/tmp/autonomousiq-documents`). The fallback is a demo convenience, not a production storage backend.
- **`libs/gcp/secrets.py`** -- Secret Manager read/write helpers. **Not yet called from anywhere** -- `ConnectorConfig.config` still stores credentials as plain JSONB (flagged in `libs/models/chat_and_connectors.py`). Wiring ingestion connector creation to call `store_secret()` and store a reference instead of the raw value is the real follow-up.
- **`libs/llm_provider/vertex.py`** -- calls Vertex AI's Gemini via `vertexai.generative_models`, with native function-calling for the planner's tool schemas. Selected by setting `LLM_PROVIDER=vertex` (default is `naive`, a zero-dependency keyword router -- see that module's docstring).

## Install the GCP extras

```bash
pip install -e ".[gcp]" --break-system-packages
```

Installs `google-cloud-storage`, `google-cloud-secret-manager`, `google-cloud-aiplatform`.

## Auth

- **Locally:** set `GOOGLE_APPLICATION_CREDENTIALS` to a downloaded service account key JSON.
- **On Cloud Run / GKE:** leave it unset. The client libraries pick up Application Default Credentials from the attached service account automatically.

## Minimum IAM roles for that service account

- `roles/storage.objectAdmin` on the `GCS_BUCKET` (Documents)
- `roles/secretmanager.admin` on the project (or narrower, once secrets are actually being written)
- `roles/aiplatform.user` on the project (Vertex AI calls)

## "Vertex clusters" -- what this repo does and doesn't do

Vertex AI's managed prediction endpoints (what "Vertex clusters" usually
refers to -- dedicated/provisioned throughput, custom-trained model
endpoints, or a Vertex AI Workbench notebook cluster) are **not** used
here. `VertexAIProvider` calls the serverless `generate_content` API
against a published model (`gemini-1.5-flash` by default) -- no cluster
to provision, scale, or pay for idle. If a future need shows up for
fine-tuned models or dedicated throughput, that would mean:

1. Deploying a Vertex AI Endpoint (via Model Registry or Vertex AI Pipelines).
2. Pointing `VertexAIProvider` at that endpoint's resource name instead of a published model string.

Not built because nothing in the current PRD calls for a custom-trained
model -- Gemini via the standard API satisfies D-10's "single provider
implementation for Phase 0".

## Deployment target (not yet built)

STANDARDS.md/the locked build sequence has a dedicated **Infrastructure**
stage after Testing/CI/Containerization, which hasn't been reached yet.
The natural target given everything above is **Cloud Run** for `api`,
`formula-sidecar`, and `frontend` (all three are already stateless
containers per `docker-compose.yml`), with **Cloud SQL for Postgres**
replacing the local `postgres` container, and **Cloud Scheduler** invoking
`apps/worker/job_runner.py` periodically instead of the ad-hoc
`python -m` invocation. No Terraform/Cloud Build config exists yet --
this is a plan, not an implementation.
