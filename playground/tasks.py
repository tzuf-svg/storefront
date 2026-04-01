import logging
from celery import shared_task
from .models import WebhookEvent


logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_webhook_event(self, event_id, simulate_failure=False):
    event = None
    try:
        event = WebhookEvent.objects.get(id=event_id)
        logger.info(f"Processing webhook event {event_id}: {event.payload}")
        if simulate_failure:
            raise Exception("Simulated failure for testing")
        event.status = 'processed'
        event.save()
    except WebhookEvent.DoesNotExist:
        logger.error(f"Event {event_id} not found")
    except Exception as exc:
        if event:
            event.status = 'failed'
            event.save()
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
