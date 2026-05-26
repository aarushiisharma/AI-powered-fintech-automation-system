from fastapi import APIRouter
from pydantic import BaseModel
from mock_bank_api.pii_scrubber import scrub

router = APIRouter(prefix="/pii", tags=["PII Scrubber"])


class ScrubRequest(BaseModel):
    text: str


@router.post("/scrub")
async def scrub_text(request: ScrubRequest):
    """
    Scrub PII from text. Use this EXPLICITLY in n8n between
    Fetch Dispute and LLM steps — only on fields that need it.
    
    n8n flow: Fetch Dispute → POST /pii/scrub (reason field) → LLM
    """
    masked_text, entities = scrub(request.text)
    return {
        "original_text": request.text,
        "scrubbed_text": masked_text,
        "entities_detected": entities,
        "pii_found": len(entities) > 0,
    }
