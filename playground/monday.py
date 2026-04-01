import hmac
import hashlib
import base64
import logging
from dataclasses import dataclass
from django.conf import settings

logger = logging.getLogger(__name__)

RELEVANT_EVENT_TYPE = "change_column_value"
COMPLETED_VALUE = "Completed"


@dataclass
class MondayEvent:
    event_type: str
    board_id: int
    item_id: int
    item_name: str
    column_id: str
    column_value: str
    code: str


def validate_monday_signature(request) -> bool:
    auth_header = request.headers.get("Authorization", "")
    signing_secret = settings.MONDAY_SIGNING_SECRET.encode("utf-8")
    expected = base64.b64encode(
        hmac.new(signing_secret, request.body, hashlib.sha256).digest()
    ).decode("utf-8")
    return hmac.compare_digest(auth_header, expected)


def normalize_monday_event(payload: dict) -> MondayEvent | None:
    event = payload.get("event", {})
    event_type = event.get("type")

    if event_type != RELEVANT_EVENT_TYPE:
        logger.info("Ignoring Monday.com event type: %s", event_type)
        return None

    column_value = event.get("value", {}).get("label", {}).get("text", "")

    if column_value != COMPLETED_VALUE:
        logger.info("Ignoring column value: %r", column_value)
        return None

    return MondayEvent(
        event_type=event_type,
        board_id=event.get("boardId"),
        item_id=event.get("pulseId"),
        item_name=event.get("pulseName", ""),
        column_id=event.get("columnId"),
        column_value=column_value,
        code=payload.get("code", ""),
    )
