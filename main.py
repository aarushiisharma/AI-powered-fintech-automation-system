from fastapi import FastAPI
from mock_bank_api.routers import kyc, disputes, audit, token_usage, pii, integrations

app = FastAPI(
    title="Mock Core Banking API",
    description="Simulated banking endpoints for n8n orchestration and LLM reasoning.",
    version="2.0.0"
)

# Wire up the routers
app.include_router(pii.router)
app.include_router(kyc.router)
app.include_router(disputes.router)
app.include_router(audit.router)
app.include_router(token_usage.router)
app.include_router(integrations.router)

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "operational", "service": "core-banking-api", "version": "2.0.0"}