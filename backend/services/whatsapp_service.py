from twilio.rest import Client
from config import settings
import logging

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        if settings.twilio_account_sid and settings.twilio_auth_token:
            self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            self.from_number = settings.twilio_whatsapp_from or "whatsapp:+14155238886"
            self.enabled = True
        else:
            self.enabled = False

    def send_price_drop_alert(self, to_number: str, property_title: str, original_price: float, new_price: float, property_url: str):
        if not self.enabled:
            logger.warning("Twilio not configured. Skipping WhatsApp alert.")
            return

        body = (f"🚨 *Price Drop Alert* - {property_title}\n\n"
                f"Original: ₹{original_price:.2f}L → New: ₹{new_price:.2f}L\n"
                f"View: {property_url}")
        
        # Ensure to_number has country code
        if not to_number.startswith("+"):
            to_number = "+91" + to_number

        try:
            self.client.messages.create(
                body=body,
                from_=self.from_number,
                to=f"whatsapp:{to_number}"
            )
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
