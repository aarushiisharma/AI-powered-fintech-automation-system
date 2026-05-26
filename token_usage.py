from fastapi import APIRouter, Depends
from mock_bank_api.models import TokenUsage
from mock_bank_api.auth import require_role, Role, User
import uuid

router = APIRouter(prefix="/audit/token-usage", tags=["Token Usage & Cost Tracking"])

# Simulated Database for Token Usage Logs
TOKEN_USAGE_LEDGER = []

# Groq pricing (USD per token) for llama-3.1-8b-instant
GROQ_PRICING = {
    "llama-3.1-8b-instant": {
        "prompt": 0.05 / 1_000_000,      # $0.05 per 1M input tokens
        "completion": 0.08 / 1_000_000,   # $0.08 per 1M output tokens
    }
}


def _calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Auto-calculate estimated cost based on Groq's published rates."""
    pricing = GROQ_PRICING.get(model)
    if not pricing:
        return 0.0
    return (prompt_tokens * pricing["prompt"]) + (completion_tokens * pricing["completion"])


@router.post("/")
async def log_token_usage(
    usage: TokenUsage,
    user: User = Depends(require_role(Role.COMPLIANCE_MANAGER, Role.SYSTEM_ADMIN)),
):
    """Log token usage from an n8n workflow run. Requires COMPLIANCE_MANAGER or SYSTEM_ADMIN."""
    usage.id = str(uuid.uuid4())

    # Auto-calculate cost if not provided (i.e., left at default 0.0)
    if usage.estimated_cost_usd == 0.0:
        usage.estimated_cost_usd = _calculate_cost(
            usage.model, usage.prompt_tokens, usage.completion_tokens
        )

    TOKEN_USAGE_LEDGER.append(usage)
    return {
        "status": "success",
        "log_id": usage.id,
        "estimated_cost_usd": usage.estimated_cost_usd,
    }


@router.get("/")
async def get_token_usage(
    user: User = Depends(require_role(Role.COMPLIANCE_MANAGER, Role.SYSTEM_ADMIN)),
):
    """Retrieve all token usage records. Requires COMPLIANCE_MANAGER or SYSTEM_ADMIN."""
    return TOKEN_USAGE_LEDGER


@router.get("/summary")
async def get_token_usage_summary(
    user: User = Depends(require_role(Role.COMPLIANCE_MANAGER, Role.SYSTEM_ADMIN)),
):
    """Aggregate stats: total tokens, total cost, averages per run."""
    if not TOKEN_USAGE_LEDGER:
        return {
            "total_runs": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_tokens_per_run": 0.0,
            "avg_cost_per_run": 0.0,
        }

    total_runs = len(TOKEN_USAGE_LEDGER)
    total_tokens = sum(u.total_tokens for u in TOKEN_USAGE_LEDGER)
    total_cost = sum(u.estimated_cost_usd for u in TOKEN_USAGE_LEDGER)

    return {
        "total_runs": total_runs,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 10),
        "avg_tokens_per_run": round(total_tokens / total_runs, 2),
        "avg_cost_per_run": round(total_cost / total_runs, 10),
    }
