from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime

# --- Enums for strict status tracking ---
class KYCStatus(str, Enum):
    APPROVED = "APPROVED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    FLAGGED = "FLAGGED"

class DisputeStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED_REFUNDED = "RESOLVED_REFUNDED"
    RESOLVED_DENIED = "RESOLVED_DENIED"
    ESCALATED = "ESCALATED" # This is our Human-in-the-Loop trigger

# --- Core Data Models ---
class Customer(BaseModel):
    id: str = Field(..., description="Unique customer ID")
    name: str
    email: str
    kyc_status: KYCStatus
    risk_score: int = Field(..., ge=0, le=100, description="Risk score from 0-100")
    account_age_days: int

class Dispute(BaseModel):
    id: str
    customer_id: str
    transaction_id: str
    amount: float
    reason: str = Field(..., description="Customer's stated reason for the dispute")
    status: DisputeStatus = DisputeStatus.OPEN
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AuditLog(BaseModel):
    id: Optional[str] = None 
    action: str = Field(..., description="What the system did (e.g., 'FROZE_ACCOUNT')")
    agent: str = "n8n-LLM-Orchestrator"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: str = Field(..., description="Why the system made this decision")
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="AI confidence in this decision (0.0 to 1.0)"
    )
    approved_by: Optional[str] = Field(None, description="Username of the approver (from RBAC)")

class TokenUsage(BaseModel):
    id: Optional[str] = None
    workflow_run_id: str = Field(..., description="n8n execution/run ID")
    dispute_id: Optional[str] = Field(None, description="Associated dispute ID if applicable")
    model: str = "llama-3.1-8b-instant"
    prompt_tokens: int = Field(..., ge=0)
    completion_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    estimated_cost_usd: float = Field(0.0, ge=0.0, description="Auto-calculated if not provided")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# --- Integration Layer Models ---
class WebhookEvent(BaseModel):
    id: Optional[str] = None
    event_type: str = Field(..., description="e.g., 'dispute.escalated', 'dispute.refunded'")
    dispute_id: str
    payload: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class RefundRequest(BaseModel):
    dispute_id: str
    amount: float = Field(..., gt=0)
    reason: str
    approved_by: str = Field(..., description="Username from RBAC who approved")
    idempotency_key: str = Field(..., description="Prevents duplicate refunds")

class IntegrationResponse(BaseModel):
    status: str = Field(..., description="'success' or 'failed'")
    error_message: Optional[str] = None