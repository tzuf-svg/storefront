import base64
import hashlib
import hmac
import json as json_module
import pytest
from unittest.mock import patch

from django.urls import reverse

from playground.factories import TodoFactory
from playground.models import WebhookEvent
from playground.sandbox import SandboxResult


TEST_MONDAY_SECRET = 'test-monday-secret'

_SANDBOX_CODE = (
    "if provider.completed:\n"
    "    raise Exception('already done')\n"
    "provider.completed = True\n"
    "print(json.dumps({'title': provider.title, 'completed': provider.completed}))\n"
)


def _monday_payload(item_name, event_type="change_column_value", column_value="Completed", code=_SANDBOX_CODE):
    return {
        "event": {
            "type": event_type,
            "boardId": 1,
            "pulseId": 42,
            "pulseName": item_name,
            "columnId": "status",
            "value": {"label": {"text": column_value}},
        },
        "code": code,
    }


@pytest.mark.django_db
class TestMondayWebhookE2E:

    @pytest.fixture(autouse=True)
    def set_monday_secret(self, settings):
        settings.MONDAY_SIGNING_SECRET = TEST_MONDAY_SECRET

    def _post(self, api_client, payload, secret=TEST_MONDAY_SECRET):
        body = json_module.dumps(payload).encode("utf-8")
        sig = base64.b64encode(
            hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
        ).decode("utf-8")
        return api_client.post(
            reverse("webhook-secret-receiver"),
            data=body,
            content_type="application/json",
            HTTP_AUTHORIZATION=sig,
        )

    @patch("playground.views.run_in_sandbox")
    def test_valid_webhook_marks_task_completed(self, mock_sandbox, api_client):
        task = TodoFactory(title="Fix bug", completed=False)
        mock_sandbox.return_value = SandboxResult(
            success=True,
            output=json_module.dumps({"title": "Fix bug", "completed": True}),
            error=None,
        )

        response = self._post(api_client, _monday_payload("Fix bug"))

        assert response.status_code == 201
        task.refresh_from_db()
        assert task.completed is True
        assert task.completed_at is not None
        event = WebhookEvent.objects.get(id=response.data["id"])
        assert event.status == "processed"

    @patch("playground.views.run_in_sandbox")
    def test_invalid_monday_signature_rejected(self, mock_sandbox, api_client):
        response = self._post(api_client, _monday_payload("Some task"), secret="wrong-secret")

        assert response.status_code == 403
        assert not WebhookEvent.objects.exists()
        mock_sandbox.assert_not_called()

    @patch("playground.views.run_in_sandbox")
    def test_task_not_found_returns_404(self, mock_sandbox, api_client):
        response = self._post(api_client, _monday_payload("Nonexistent Task"))

        assert response.status_code == 404
        assert "Nonexistent Task" in response.data["error"]
        assert not WebhookEvent.objects.exists()
        mock_sandbox.assert_not_called()

    @patch("playground.views.run_in_sandbox")
    def test_already_completed_task_returns_409(self, mock_sandbox, api_client):
        TodoFactory(title="Done Task", completed=True)

        response = self._post(api_client, _monday_payload("Done Task"))

        assert response.status_code == 409
        assert not WebhookEvent.objects.exists()
        mock_sandbox.assert_not_called()

    @patch("playground.views.run_in_sandbox")
    def test_sandbox_crash_marks_event_failed_and_task_unchanged(self, mock_sandbox, api_client):
        task = TodoFactory(title="Broken Task", completed=False)
        mock_sandbox.return_value = SandboxResult(
            success=False,
            output="",
            error="NameError: name 'x' is not defined",
        )

        response = self._post(api_client, _monday_payload("Broken Task"))

        assert response.status_code == 500
        assert "Sandbox execution failed" in response.data["error"]
        task.refresh_from_db()
        assert task.completed is False
        assert WebhookEvent.objects.filter(status="failed").exists()

    @patch("playground.views.run_in_sandbox")
    def test_non_completed_column_value_ignored(self, mock_sandbox, api_client):
        response = self._post(api_client, _monday_payload("Any Task", column_value="In Progress"))

        assert response.status_code == 200
        assert response.data["status"] == "ignored"
        assert not WebhookEvent.objects.exists()
        mock_sandbox.assert_not_called()

    @patch("playground.views.run_in_sandbox")
    def test_non_change_column_value_event_ignored(self, mock_sandbox, api_client):
        response = self._post(api_client, _monday_payload("Any Task", event_type="create_pulse"))

        assert response.status_code == 200
        assert response.data["status"] == "ignored"
        assert not WebhookEvent.objects.exists()
        mock_sandbox.assert_not_called()

    @patch("playground.views.run_in_sandbox")
    def test_sandbox_returns_malformed_json_marks_event_failed(self, mock_sandbox, api_client):
        TodoFactory(title="Parse Error Task", completed=False)
        mock_sandbox.return_value = SandboxResult(
            success=True,
            output="not-valid-json",
            error=None,
        )

        response = self._post(api_client, _monday_payload("Parse Error Task"))

        assert response.status_code == 500
        assert "Invalid sandbox output" in response.data["error"]
        assert WebhookEvent.objects.filter(status="failed").exists()

    def test_no_authorization_header_falls_through_to_legacy_path(self, api_client):
        response = api_client.post(
            reverse("webhook-secret-receiver"),
            data=json_module.dumps(_monday_payload("Any Task")).encode("utf-8"),
            content_type="application/json",
            # No HTTP_AUTHORIZATION header — no Monday.com path
            HTTP_X_WEBHOOK_SECRET="wrong-secret",
        )

        assert response.status_code == 403
        assert not WebhookEvent.objects.exists()
