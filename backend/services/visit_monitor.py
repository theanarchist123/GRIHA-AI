import asyncio
from datetime import datetime, timedelta, timezone
from database.mongo import db
from database.models.visit import Visit
from database.models.property import Property
from services.email_service import EmailService
from database.models.notification import Notification
from services.whatsapp_service import WhatsAppService
from config import settings
from bson import ObjectId

email_service = EmailService()
whatsapp_service = WhatsAppService()

async def monitor_visits_loop():
    print("🚀 Starting Background Visit Monitor Worker...")
    while True:
        try:
            now = datetime.now(timezone.utc)
            tomorrow = now + timedelta(days=1)
            
            # Find scheduled visits for tomorrow that haven't been reminded yet
            # We'll use a simple check: if it's within 24-25 hours of now, send reminder.
            # In a real app, we'd store a `reminder_sent` boolean on the Visit model.
            
            # Let's just find visits scheduled for tomorrow
            start_of_tomorrow = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=timezone.utc)
            end_of_tomorrow = start_of_tomorrow + timedelta(days=1)
            
            # We will rely on a new field `reminder_sent` to avoid spam.
            visits = await Visit.find({
                "status": "scheduled",
                "date": {"$gte": start_of_tomorrow, "$lt": end_of_tomorrow},
                "reminder_sent": {"$ne": True}
            }).to_list()
            
            if visits:
                print(f"📅 Found {len(visits)} visits for tomorrow. Sending reminders...")
                
            for visit in visits:
                await visit.fetch_link(Visit.property)
                prop = visit.property
                if not prop:
                    continue
                    
                property_url = f"{settings.frontend_url}/property/{prop.id}"
                
                # Send email
                try:
                    email_service.send_visit_reminder(
                        recipient_email=visit.user_email,
                        property_title=prop.title,
                        date=visit.date.strftime("%Y-%m-%d"),
                        time_slot=visit.time_slot,
                        property_url=property_url
                    )
                except Exception as e:
                    print(f"Failed to send email reminder: {e}")
                
                # In-app notification
                notif = Notification(
                    clerk_id=visit.clerk_id,
                    type="visit_reminder",
                    title="Upcoming Visit Tomorrow",
                    message=f"You have a visit scheduled for {prop.title} on {visit.date.strftime('%Y-%m-%d')} at {visit.time_slot}",
                    priority="high",
                    action_url=f"/visits"
                )
                await notif.insert()
                
                print(f"[Visit Monitor] Sent reminder for visit {visit.id}")
                
                # Update visit to mark reminder sent
                visit.reminder_sent = True
                await visit.save()
                
            # Sleep for an hour
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"❌ Error in visit monitor loop: {e}")
            await asyncio.sleep(60)
