from fastapi import APIRouter, HTTPException
from mock_bank_api.models import Customer, KYCStatus

# Create a router instance
router = APIRouter(prefix="/kyc", tags=["KYC Validation"])

# Simulated Database of Customers
MOCK_CUSTOMERS = {
    "CUST-101": Customer(
        id="CUST-101", 
        name="Alice Smith", 
        email="alice@example.com", 
        kyc_status=KYCStatus.APPROVED, 
        risk_score=12, 
        account_age_days=1450
    ),
    "CUST-102": Customer(
        id="CUST-102", 
        name="Bob Jones", 
        email="bob@example.com", 
        kyc_status=KYCStatus.PENDING, 
        risk_score=88, 
        account_age_days=5
    ),
}

@router.get("/{customer_id}", response_model=Customer)
async def get_customer_kyc(customer_id: str):
    """Fetch KYC and risk data for a specific customer."""
    if customer_id not in MOCK_CUSTOMERS:
        raise HTTPException(status_code=404, detail="Customer not found in core system")
    return MOCK_CUSTOMERS[customer_id]