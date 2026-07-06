from fastapi import APIRouter

router = APIRouter(prefix="/api/broker-calls", tags=["BrokerCalls"])

@router.get("/")
async def get_calls():
    return {"status": "success", "data": []}