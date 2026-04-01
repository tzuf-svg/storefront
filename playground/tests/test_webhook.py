import pytest
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.urls import reverse

from playground.factories import WebhookEventFactory
from playground.models import WebhookEvent
from playground.tasks import process_webhook_event


@pytest.mark.django_db
class TestWebhook:

    @patch('playground.views.process_webhook_event')
    def test_valid_secret_creates_event(self, mock_task, api_client):
        mock_task.delay = MagicMock()
        payload = {'event': 'task.created', 'data': {'id': 1}}
        response = api_client.post(
            reverse('webhook-secret-receiver'),
            payload,
            format='json',
            HTTP_X_WEBHOOK_SECRET=settings.WEBHOOK_SECRET,
        )
        assert response.status_code == 201
        assert WebhookEvent.objects.filter(payload=payload).exists()

    @patch('playground.views.process_webhook_event')
    def test_invalid_secret_rejected(self, mock_task, api_client):
        mock_task.delay = MagicMock()
        response = api_client.post(
            reverse('webhook-secret-receiver'),
            {'event': 'task.created'},
            format='json',
            HTTP_X_WEBHOOK_SECRET='wrong-secret',
        )
        assert response.status_code == 403

    @patch('playground.tasks.process_webhook_event.delay')
    def test_celery_task_queued(self, mock_delay, api_client):
        payload = {'event': 'ping'}
        response = api_client.post(
            reverse('webhook-secret-receiver'),
            payload,
            format='json',
            HTTP_X_WEBHOOK_SECRET=settings.WEBHOOK_SECRET,
        )
        assert response.status_code == 201
        mock_delay.assert_called_once_with(response.data['id'])


@pytest.mark.django_db
class TestCeleryTask:

    def test_process_webhook_event_success(self):
        event = WebhookEventFactory()
        process_webhook_event(event.id)
        event.refresh_from_db()
        assert event.status == 'processed'

    def test_process_webhook_event_not_found(self):
        process_webhook_event(99999)
        assert not WebhookEvent.objects.filter(pk=99999).exists()

    def test_process_webhook_event_simulate_failure(self):
        event = WebhookEventFactory()
        with pytest.raises(Exception):
            process_webhook_event(event.id, simulate_failure=True)
        event.refresh_from_db()
        assert event.status == 'failed'
