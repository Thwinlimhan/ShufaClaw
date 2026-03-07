from fastapi import APIRouter
from crypto_agent.trading.monitoring import monitoring_service

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

@router.get("/summary")
async def get_summary():
    """Returns real-time telemetry from the V2 infrastructure."""
    return monitoring_service.get_dashboard_summary()
