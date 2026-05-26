from fastapi import APIRouter, Depends
from mock_bank_api.models import AuditLog
from mock_bank_api.auth import require_role, Role, User
import uuid

router = APIRouter(prefix="/audit", tags=["Compliance Audit Ledger"])

# Simulated Database for Logs (A simple list)
AUDIT_LEDGER = []

@router.post("/")
async def log_action(
    log: AuditLog,
    user: User = Depends(require_role(Role.SYSTEM_ADMIN)),
):
    """Log a decision made by the AI orchestration system. Requires SYSTEM_ADMIN."""
    log.id = str(uuid.uuid4())
    # Track who approved/triggered this action
    if not log.approved_by:
        log.approved_by = user.username
    AUDIT_LEDGER.append(log)
    return {"status": "success", "log_id": log.id, "approved_by": log.approved_by}

@router.get("/")
async def get_logs(
    user: User = Depends(require_role(Role.TIER1_SUPPORT, Role.COMPLIANCE_MANAGER, Role.SYSTEM_ADMIN)),
):
    """Retrieve all audit logs for compliance review. Any authenticated role can view."""
    return AUDIT_LEDGER