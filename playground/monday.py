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


def validate_monday_signature(raw_body: bytes, auth_header: str) -> bool:
    """
    Validate Monday.com HMAC-SHA256 signature.
    Accepts raw_body separately so the caller reads request.body
    before DRF consumes it via request.data.
    """
    signing_secret = settings.MONDAY_SIGNING_SECRET.encode("utf-8")
    expected = base64.b64encode(
        hmac.new(signing_secret, raw_body, hashlib.sha256).digest()
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

    # Validate required integer/string fields before building the dataclass
    board_id = event.get("boardId")
    item_id = event.get("pulseId")
    column_id = event.get("columnId")

    if not isinstance(board_id, int) or not isinstance(item_id, int):
        logger.warning("Missing or invalid boardId/pulseId in Monday.com event")
        return None

    if not isinstance(column_id, str):
        logger.warning("Missing or invalid columnId in Monday.com event")
        return None

    return MondayEvent(
        event_type=event_type,
        board_id=board_id,
        item_id=item_id,
        item_name=event.get("pulseName", ""),
        column_id=column_id,
        column_value=column_value,
        code=payload.get("code", ""),
    )
