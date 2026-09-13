"""Verifies the standard API error envelope, since approval-gate-related
error handling is treated as blocking-review-comment-worthy per STANDARDS.md.
"""

from fastapi.testclient import TestClient

from apps.api.main import app
from libs.exceptions import ApprovalRequiredError


def test_health_ok() -> None:
    client = TestClient(app)
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_approval_required_error_shape() -> None:
    """An ApprovalRequiredError must surface as a 409 with the standard
    {"error": {"code", "message", "details"}} envelope — this is the shape
    every sql_query_tool / tracker_query_tool / chart_tool failure relies on.
    """

    @app.get("/v1/_test_approval_required")
    async def _raise_approval_required() -> None:
        raise ApprovalRequiredError(
            "Query requires approval before execution",
            details={"tool": "sql_query_tool"},
        )

    client = TestClient(app)
    resp = client.get("/v1/_test_approval_required")

    assert resp.status_code == 409
    body = resp.json()
    assert body["error"]["code"] == "APPROVAL_REQUIRED"
    assert body["error"]["details"]["tool"] == "sql_query_tool"
