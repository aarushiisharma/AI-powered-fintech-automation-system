"""
Integration Abstraction Layer — Webhook, Refund (idempotent), and Alert endpoints.
Returns mock Stripe/Slack/Zendesk-shaped responses for seamless n8n migration.
"""

from fastapi import APIRouter, Depends
from mock_bank_api.models import (
    WebhookEvent, RefundRequest, IntegrationResponse,
)
from mock_bank_api.auth import require_role, Role, User
from mock_bank_api.event_store import EVENT_STORE
import uuid
from datetime import datetime

router = APIRouter(prefix="/integrations", tags=["Integration Layer"])

# --- In-memory stores ---
PROCESSED_REFUNDS: dict[str, dict] = {}  # idempotency_key -> response


@router.post("/webhook", response_model=IntegrationResponse)
async def receive_webhook(
    event: WebhookEvent,
    user: User = Depends(require_role(Role.SYSTEM_ADMIN)),
):
    """
    Receive and store a webhook event.
    Called by disputes router on state change (event-driven).
    """
    event.id = str(uuid.uuid4())
    EVENT_STORE.append(event)
    return IntegrationResponse(
        status="success",
        error_message=None,
    )


@router.post("/refund")
async def process_refund(
    request: RefundRequest,
    user: User = Depends(require_role(Role.COMPLIANCE_MANAGER, Role.SYSTEM_ADMIN)),
):
    """
    Process a refund with idempotency protection.
    If the same idempotency_key is sent twice, returns the cached response.
    Mock Stripe-style response shape.
    """
    # Idempotency check — prevent double refunds
    if request.idempotency_key in PROCESSED_REFUNDS:
        cached = PROCESSED_REFUNDS[request.idempotency_key]
        cached["idempotent_replay"] = True
        return cached

    # Process the refund (mock)
    refund_response = {
        "status": "success",
        "error_message": None,
        "refund_id": f"rf_{uuid.uuid4().hex[:12]}",
        "dispute_id": request.dispute_id,
        "amount": request.amount,
        "currency": "usd",
        "reason": request.reason,
        "approved_by": request.approved_by,
        "idempotency_key": request.idempotency_key,
        "idempotent_replay": False,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Store for idempotency
    PROCESSED_REFUNDS[request.idempotency_key] = refund_response

    return refund_response


@router.post("/alert")
async def send_alert(
    payload: dict,
    user: User = Depends(require_role(Role.COMPLIANCE_MANAGER, Role.SYSTEM_ADMIN)),
):
    """
    Send an alert (mock Slack-style response).
    Used for human-in-the-loop notifications on ESCALATED disputes.
    """
    alert_response = {
        "status": "success",
        "error_message": None,
        "channel": payload.get("channel", "#compliance-alerts"),
        "message": payload.get("message", "Alert triggered"),
        "alert_id": f"alert_{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.utcnow().isoformat(),
    }
    return alert_response


@router.get("/events")
async def list_events(
    user: User = Depends(require_role(Role.COMPLIANCE_MANAGER, Role.SYSTEM_ADMIN)),
):
    """List all processed webhook events."""
    return EVENT_STORE
