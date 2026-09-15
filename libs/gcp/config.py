"""Shared GCP configuration read from env vars. One place every GCP
client (Storage, Secret Manager, Vertex AI) reads its project/region
from, so there's a single source of truth for "which GCP project/region
is this deployment pointed at".
"""

from __future__ import annotations

import os

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
GCP_REGION = os.environ.get("GCP_REGION", "us-central1")
GCS_BUCKET = os.environ.get("GCS_BUCKET", "")
VERTEX_MODEL = os.environ.get("VERTEX_MODEL", "gemini-1.5-flash")

# Credentials: in GCP-hosted environments (Cloud Run, GKE) this is
# unset and Application Default Credentials (the attached service
# account) are used automatically. For local dev, point this at a
# downloaded service account key.
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
