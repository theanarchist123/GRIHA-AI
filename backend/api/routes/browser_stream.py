from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio
from database.models.autopilot import AutopilotHunt
from services.property_fetcher import run_scrape_workflow
# from services.ai_client import GeminiAIClient

router = APIRouter(prefix="/ws/browser-stream", tags=["BrowserStream"])

@router.websocket("/{job_id}")
async def browser_stream_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    
    try:
        job = await AutopilotHunt.get(job_id)
        if not job:
            await websocket.send_json({"type": "error", "message": "Job not found"})
            await websocket.close()
            return

        location_str = job.locations[0] if job.locations else "Mumbai"
        await websocket.send_json({"type": "status", "message": f"Initializing Agent for {location_str}..."})
        
        class DummyWS:
            async def send_json(self, data):
                try:
                    await websocket.send_json(data)
                except:
                    pass

        dummy_ws = DummyWS()
        await run_scrape_workflow(job, dummy_ws)
        
        await websocket.send_json({"type": "status", "message": "Simulated streaming complete."})

    except WebSocketDisconnect:
        print(f"Browser stream {job_id} disconnected")
    except Exception as e:
        print(f"Browser stream error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
