"""GCP Secret Manager client. Not yet wired into ConnectorConfig (see
libs/models/chat_and_connectors.py's flag) -- this module exists so that
follow-up is a matter of calling these two functions, not building the
GCP integration from scratch.
"""

from __future__ import annotations

from libs.gcp.config import GCP_PROJECT_ID


def store_secret(secret_id: str, value: str) -> str:
    """Creates (or adds a new version to) a secret. Returns the secret's
    resource name."""
    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{GCP_PROJECT_ID}"

    try:
        client.get_secret(name=f"{parent}/secrets/{secret_id}")
    except Exception:  # noqa: BLE001 -- secret doesn't exist yet
        client.create_secret(
            parent=parent,
            secret_id=secret_id,
            secret={"replication": {"automatic": {}}},
        )

    response = client.add_secret_version(
        parent=f"{parent}/secrets/{secret_id}",
        payload={"data": value.encode("utf-8")},
    )
    return response.name


def read_secret(secret_id: str, *, version: str = "latest") -> str:
    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("utf-8")
