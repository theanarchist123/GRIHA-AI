import asyncio
from database.mongo import db
from database.models.property import Property
from services.email_service import EmailService
import re
from bson import ObjectId

email_service = EmailService()

def parse_price(price_str: str) -> float:
    match = re.search(r'([\d.]+)', str(price_str))
    if match:
        val = float(match.group(1))
        if "Cr" in str(price_str):
            val *= 100
        return val
    return 0.0

async def monitor_prices_loop():
    print("🚀 Starting Background Price Monitor Worker...")
    while True:
        try:
            alerts_collection = db["alerts"]
            
            # Fetch all active watching alerts
            cursor = alerts_collection.find({"status": "watching"})
            active_alerts = await cursor.to_list(length=None)
            
            if active_alerts:
                print(f"🔍 Checking {len(active_alerts)} active alerts...")
                
            for alert in active_alerts:
                property_id = alert["property_id"]
                user_email = alert.get("user_email")
                
                if not user_email:
                    continue
                
                try:
                    # Fetch live property data
                    live_prop = await Property.get(ObjectId(property_id))
                    if not live_prop:
                        continue
                        
                    current_live_val = parse_price(live_prop.price)
                    target_val = alert.get("target_price_float", 0)
                    
                    if current_live_val > 0 and current_live_val <= target_val:
                        print(f"🚨 DROP DETECTED for {live_prop.title}! Current: {current_live_val}, Target: {target_val}")
                        
                        # Send Email
                        property_url = f"http://localhost:3000/property/{property_id}"
                        success = email_service.send_price_drop_alert(
                            recipient_email=user_email,
                            property_title=live_prop.title,
                            original_price=alert.get("original_price_float", 0),
                            new_price=current_live_val,
                            target_price=target_val,
                            property_url=property_url
                        )
                        
                        if success:
                            # Update alert to triggered
                            await alerts_collection.update_one(
                                {"_id": alert["_id"]},
                                {"$set": {
                                    "status": "triggered",
                                    "current_price_float": current_live_val,
                                    "price": str(live_prop.price)
                                }}
                            )
                except Exception as inner_e:
                    print(f"Error checking property {property_id}: {str(inner_e)}")
                    
        except Exception as e:
            print(f"❌ Error in price monitor loop: {str(e)}")
            
        # Run every 60 seconds (1 minute) for demo purposes
        await asyncio.sleep(60)
