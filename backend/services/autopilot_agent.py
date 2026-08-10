"""
Autopilot Agent — Autonomous property hunting engine.
Periodically scrapes, matches, optionally runs legal checks,
and sends daily morning digests. This is the core intelligence
behind the "Autopilot Hunt" feature.
"""
import uuid
import traceback
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from database.models.autopilot import AutopilotHunt, AutopilotRun, AutopilotMatch
from database.models.property import Property
from database.models.search_profile import SearchProfile
from database.models.notification import Notification
from services.matching_agent import MatchingAgent
from services.legal_agent import LegalAgent
from services.email_service import EmailService
from services.activity_logger import log_activity
from config import settings


class AutopilotAgent:
    def __init__(self):
        self.matching_agent = MatchingAgent()
        self.legal_agent = LegalAgent()
        self.email_service = EmailService()

    async def run_cycle(self) -> None:
        """
        Main cycle: find all active hunts that are due for a run,
        and process each one.
        """
        now = datetime.now(timezone.utc)
        
        # Find active hunts where next_run_at is in the past (or None = never run)
        active_hunts = await AutopilotHunt.find(
            AutopilotHunt.status == "active"
        ).to_list()
        
        for hunt in active_hunts:
            # Skip if not yet due
            if hunt.next_run_at and hunt.next_run_at > now:
                continue
            
            try:
                run_result = await self._process_hunt(hunt)
                print(f"[AutopilotAgent] Hunt {hunt.id} cycle complete: "
                      f"{run_result.new_matches} new matches from "
                      f"{run_result.properties_scraped} candidates")
            except Exception as e:
                print(f"[AutopilotAgent] Error processing hunt {hunt.id}: {e}")
                traceback.print_exc()

    async def _process_hunt(self, hunt: AutopilotHunt) -> AutopilotRun:
        """
        Process a single hunt:
        1. Query properties matching the hunt's criteria
        2. Score them via MatchingAgent
        3. Optionally run legal checks on top matches
        4. Store results and update hunt metadata
        """
        run_id = str(uuid.uuid4())[:8]
        run = AutopilotRun(
            run_id=run_id,
            started_at=datetime.now(timezone.utc),
            status="running"
        )
        
        try:
            # Step 1: Find candidate properties matching hunt criteria
            candidates = await self._find_candidates(hunt)
            run.properties_scraped = len(candidates)
            
            if not candidates:
                run.status = "completed"
                run.completed_at = datetime.now(timezone.utc)
                await self._save_run(hunt, run)
                return run
            
            # Step 2: Score candidates using MatchingAgent
            # Build a temporary SearchProfile from hunt config
            profile = SearchProfile(
                clerk_id=hunt.clerk_id,
                intent="rent",
                city="",  # We already filtered by locality
                localities=hunt.locations,
                budget_min=hunt.min_budget,
                budget_max=hunt.max_budget,
                size=hunt.bhk,
                must_haves=hunt.must_have,
                deal_breakers=[],
            )
            
            matches = await self.matching_agent.run_matching(hunt.clerk_id, profile)
            
            # Step 3: Record new matches on the hunt
            existing_prop_ids = {m.property_id for m in hunt.matches}
            new_matches_count = 0
            
            for match in matches:
                prop_id = str(match.property)
                if prop_id in existing_prop_ids:
                    continue
                
                autopilot_match = AutopilotMatch(
                    property_id=prop_id,
                    match_score=match.match_score,
                    found_at=datetime.now(timezone.utc)
                )
                
                # Step 4: Auto legal check if enabled
                if hunt.auto_legal_check and match.match_score >= 75:
                    try:
                        prop = await Property.get(match.property)
                        if prop:
                            report = await self.legal_agent.analyze_property(prop, hunt.clerk_id)
                            autopilot_match.legal_checked = True
                            autopilot_match.legal_status = report.overall_risk if report else "unknown"
                            run.legal_checks_run += 1
                    except Exception as e:
                        print(f"[AutopilotAgent] Legal check failed for {prop_id}: {e}")
                
                hunt.matches.append(autopilot_match)
                new_matches_count += 1
            
            run.new_matches = new_matches_count
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            
            # Update hunt metadata
            hunt.total_properties_found += new_matches_count
            hunt.total_runs += 1
            hunt.last_run_at = datetime.now(timezone.utc)
            hunt.next_run_at = datetime.now(timezone.utc) + timedelta(hours=hunt.interval_hours)
            
            # Keep only latest 50 matches to prevent unbounded growth
            if len(hunt.matches) > 50:
                hunt.matches = sorted(hunt.matches, key=lambda m: m.match_score, reverse=True)[:50]
            
            await self._save_run(hunt, run)
            
            # Log activity and notify
            if new_matches_count > 0:
                await log_activity(
                    user_id=hunt.clerk_id,
                    activity_type="autopilot",
                    text=f"Autopilot found {new_matches_count} new match{'es' if new_matches_count > 1 else ''}",
                    action_label="View",
                    action_href="/autopilot",
                )
                
                notif = Notification(
                    clerk_id=hunt.clerk_id,
                    type="match_found",
                    title="Autopilot Match Found ✨",
                    message=f"Found {new_matches_count} new matching propert{'ies' if new_matches_count > 1 else 'y'} for your hunt.",
                    priority="normal",
                    action_url="/autopilot"
                )
                await notif.insert()
            
            return run
            
        except Exception as e:
            run.status = "error"
            run.error = str(e)[:500]
            run.completed_at = datetime.now(timezone.utc)
            
            # Still schedule next run even on error
            hunt.next_run_at = datetime.now(timezone.utc) + timedelta(hours=hunt.interval_hours)
            await self._save_run(hunt, run)
            raise

    async def _find_candidates(self, hunt: AutopilotHunt) -> List[Property]:
        """Find properties matching the hunt's hard criteria."""
        conditions = [
            {"is_fake": {"$ne": True}},
            {"price": {"$gte": hunt.min_budget, "$lte": hunt.max_budget}},
        ]
        
        # BHK filter
        if hunt.bhk:
            bhk_num = hunt.bhk.split()[0]
            conditions.append({"bhk": {"$regex": bhk_num, "$options": "i"}})
        
        # Location filter — match any of the hunt's target locations
        if hunt.locations:
            or_clauses = []
            for loc in hunt.locations:
                or_clauses.append({"locality": {"$regex": loc, "$options": "i"}})
                or_clauses.append({"city": {"$regex": loc, "$options": "i"}})
            conditions.append({"$or": or_clauses})
        
        # Furnishing filter
        if hunt.preferred_furnishing:
            conditions.append({"furnished_status": {"$regex": hunt.preferred_furnishing, "$options": "i"}})
        
        query = {"$and": conditions}
        return await Property.find(query).sort("-created_at").limit(30).to_list()

    async def _save_run(self, hunt: AutopilotHunt, run: AutopilotRun) -> None:
        """Append run to hunt's history and save."""
        # Keep only latest 20 runs
        hunt.runs.append(run)
        if len(hunt.runs) > 20:
            hunt.runs = hunt.runs[-20:]
        await hunt.save()

    async def send_morning_digest(self) -> None:
        """
        Send a daily morning digest email to all active hunts
        that have a digest_email configured.
        """
        active_hunts = await AutopilotHunt.find(
            AutopilotHunt.status == "active"
        ).to_list()
        
        for hunt in active_hunts:
            if not hunt.digest_email:
                continue
            
            try:
                # Get matches from the last 24 hours
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                recent_matches = [
                    m for m in hunt.matches 
                    if m.found_at and m.found_at > cutoff
                ]
                
                if not recent_matches:
                    continue
                
                # Build digest content
                match_rows = ""
                for m in sorted(recent_matches, key=lambda x: x.match_score, reverse=True)[:10]:
                    prop = await Property.get(m.property_id)
                    if not prop:
                        continue
                    legal_badge = ""
                    if m.legal_checked:
                        color = "#27AE60" if m.legal_status == "low" else "#C9922A" if m.legal_status == "medium" else "#E74C3C"
                        legal_badge = f'<span style="color:{color};font-weight:bold;">Legal: {m.legal_status}</span>'
                    
                    frontend_url = settings.frontend_url or "http://localhost:3000"
                    match_rows += f"""
                    <tr>
                        <td style="padding:12px;border-bottom:1px solid #E5E0D8;">
                            <strong>{prop.title or prop.bhk}</strong><br>
                            <span style="color:#8C8577;font-size:0.9em;">{prop.locality}, {prop.city}</span>
                        </td>
                        <td style="padding:12px;border-bottom:1px solid #E5E0D8;text-align:right;">
                            ₹{int(prop.price):,}/mo<br>
                            <span style="color:#2D5016;font-weight:bold;">{int(m.match_score)}% match</span><br>
                            {legal_badge}
                        </td>
                    </tr>
                    """
                
                if not match_rows:
                    continue
                
                # Build and send email
                self._send_digest_email(
                    recipient=hunt.digest_email,
                    match_count=len(recent_matches),
                    match_rows_html=match_rows,
                    locations=", ".join(hunt.locations[:3]),
                    bhk=hunt.bhk,
                )
                
                print(f"[AutopilotAgent] Morning digest sent to {hunt.digest_email}")
                
            except Exception as e:
                print(f"[AutopilotAgent] Digest failed for {hunt.digest_email}: {e}")
                traceback.print_exc()

    def _send_digest_email(self, recipient: str, match_count: int, match_rows_html: str, locations: str, bhk: str) -> None:
        """Send the formatted morning digest email."""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🏠 Griha AI Morning Digest: {match_count} new match{'es' if match_count > 1 else ''}"
        msg["From"] = f"Griha AI <{self.email_service.sender_email}>"
        msg["To"] = recipient
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #1C1C1C; background-color: #FAF8F3; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #FFFFFF; border: 1px solid #E5E0D8; border-radius: 10px; overflow: hidden;">
              <div style="background-color: #2D5016; padding: 20px; text-align: center;">
                <h1 style="color: #FFFFFF; margin: 0;">Good Morning! ☀️</h1>
                <p style="color: #E5E0D8; margin: 5px 0 0;">Your Griha AI Autopilot Report</p>
              </div>
              <div style="padding: 30px;">
                <h2 style="color: #2D5016; margin-top: 0;">
                  {match_count} new match{'es' if match_count > 1 else ''} for {bhk} in {locations}
                </h2>
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                  {match_rows_html}
                </table>
                <p style="text-align: center; margin-top: 30px;">
                  <a href="{settings.frontend_url or 'http://localhost:3000'}/autopilot" 
                     style="background-color: #2D5016; color: #FFFFFF; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    View All Matches
                  </a>
                </p>
              </div>
            </div>
          </body>
        </html>
        """
        
        part = MIMEText(html, "html")
        msg.attach(part)
        
        try:
            server = smtplib.SMTP(self.email_service.smtp_server, self.email_service.smtp_port)
            server.starttls()
            server.login(self.email_service.sender_email, self.email_service.sender_password)
            server.sendmail(self.email_service.sender_email, recipient, msg.as_string())
            server.quit()
        except Exception as e:
            print(f"[AutopilotAgent] Email send error: {e}")