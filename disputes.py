from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from mock_bank_api.models import Dispute, DisputeStatus, WebhookEvent
from mock_bank_api.auth import require_role, Role, User
from mock_bank_api.event_store import EVENT_STORE

router = APIRouter(prefix="/disputes", tags=["Dispute Management"])

# --- Schema for updating a dispute ---
class DisputeUpdate(BaseModel):
    status: DisputeStatus

# --- Seed Data ---
MOCK_DISPUTES = {
    # High Risk: Bob (High risk score), Large Amount, Fraud indicator
    "DISP-999": Dispute(
        id="DISP-999", customer_id="CUST-102", transaction_id="TXN-5543", 
        amount=499.99, reason="I do not recognize this merchant. My card was stolen.", status=DisputeStatus.OPEN
    ),
    # Low Risk: Alice (Low risk score), Tiny Amount, Common error
    "DISP-100": Dispute(
        id="DISP-100", customer_id="CUST-101", transaction_id="TXN-1122", 
        amount=12.50, reason="I was double charged for my coffee this morning.", status=DisputeStatus.OPEN
    ),
    # Medium Risk: Alice, Moderate Amount, Ambiguous reason
    "DISP-101": Dispute(
        id="DISP-101", customer_id="CUST-101", transaction_id="TXN-3344", 
        amount=150.00, reason="I ordered a jacket but it never arrived at my house.", status=DisputeStatus.OPEN
    )
}

# --- Event type mapping ---
EVENT_TYPE_MAP = {
    DisputeStatus.ESCALATED: "dispute.escalated",
    DisputeStatus.RESOLVED_REFUNDED: "dispute.refunded",
    DisputeStatus.RESOLVED_DENIED: "dispute.denied",
    DisputeStatus.INVESTIGATING: "dispute.investigating",
}


@router.get("/", response_model=list[Dispute])
async def list_disputes(
    status: Optional[DisputeStatus] = None,
    user: User = Depends(require_role(Role.TIER1_SUPPORT, Role.COMPLIANCE_MANAGER, Role.SYSTEM_ADMIN)),
):
    """List all disputes, optionally filtered by status (e.g., ?status=OPEN)."""
    disputes = list(MOCK_DISPUTES.values())
    if status:
        disputes = [d for d in disputes if d.status == status]
    return disputes

@router.get("/{dispute_id}", response_model=Dispute)
async def get_dispute(
    dispute_id: str,
    user: User = Depends(require_role(Role.TIER1_SUPPORT, Role.COMPLIANCE_MANAGER, Role.SYSTEM_ADMIN)),
):
    """Fetch details of an ongoing dispute."""
    if dispute_id not in MOCK_DISPUTES:
        raise HTTPException(status_code=404, detail="Dispute ticket not found")
    return MOCK_DISPUTES[dispute_id]

@router.patch("/{dispute_id}/status", response_model=Dispute)
async def update_dispute_status(
    dispute_id: str,
    update_data: DisputeUpdate,
    user: User = Depends(require_role(Role.COMPLIANCE_MANAGER, Role.SYSTEM_ADMIN)),
):
    """
    Update the status of a dispute (used by n8n to resolve or escalate).
    Emits a WebhookEvent on state change (event-driven architecture).
    Only COMPLIANCE_MANAGER and SYSTEM_ADMIN can mutate state.
    """
    if dispute_id not in MOCK_DISPUTES:
        raise HTTPException(status_code=404, detail="Dispute ticket not found")
    
    old_status = MOCK_DISPUTES[dispute_id].status
    MOCK_DISPUTES[dispute_id].status = update_data.status

    # Emit event on state change
    if update_data.status in EVENT_TYPE_MAP and update_data.status != old_status:
        event = WebhookEvent(
            event_type=EVENT_TYPE_MAP[update_data.status],
            dispute_id=dispute_id,
            payload={
                "old_status": old_status.value,
                "new_status": update_data.status.value,
                "changed_by": user.username,
            },
        )
        EVENT_STORE.append(event)

    return MOCK_DISPUTES[dispute_id]