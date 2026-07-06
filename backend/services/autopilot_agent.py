from datetime import datetime, timedelta, timezone
from typing import List
from database.models.autopilot import AutopilotHunt, AutopilotRun

class AutopilotAgent:
    def __init__(self):
        pass

    async def run_cycle(self) -> None:
        print("[AutopilotAgent] Running background cycle...")

    async def _process_hunt(self, hunt: AutopilotHunt) -> AutopilotRun:
        pass

    async def send_morning_digest(self) -> None:
        print("[AutopilotAgent] Sending morning digest...")