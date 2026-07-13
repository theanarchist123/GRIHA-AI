import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings

class EmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = settings.email_sender_email or "nikhilrkadam2005@gmail.com"
        self.sender_password = settings.email_sender_password or ""

    def send_price_drop_alert(self, recipient_email: str, property_title: str, original_price: float, new_price: float, target_price: float, property_url: str):
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"🚨 Price Drop Alert: {property_title}"
            msg["From"] = f"Griha AI <{self.sender_email}>"
            msg["To"] = recipient_email

            # Formatting prices safely
            orig_str = f"₹{original_price:.2f} L" if original_price < 100 else f"₹{original_price:.2f} Cr"
            new_str = f"₹{new_price:.2f} L" if new_price < 100 else f"₹{new_price:.2f} Cr"
            target_str = f"₹{target_price:.2f} L" if target_price < 100 else f"₹{target_price:.2f} Cr"

            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #1C1C1C; background-color: #FAF8F3; padding: 20px;">
                <div style="max-w: 600px; margin: 0 auto; background-color: #FFFFFF; border: 1px solid #E5E0D8; border-radius: 10px; overflow: hidden;">
                  <div style="background-color: #C9922A; padding: 20px; text-align: center;">
                    <h1 style="color: #FFFFFF; margin: 0;">Griha AI Alert</h1>
                  </div>
                  <div style="padding: 30px;">
                    <h2 style="color: #2D5016;">Great news! Price Dropped!</h2>
                    <p>The price for <strong>{property_title}</strong> has dropped below your target.</p>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 20px; margin-bottom: 20px;">
                      <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #E5E0D8;"><strong>Original Price:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #E5E0D8; text-align: right;">{orig_str}</td>
                      </tr>
                      <tr>
                        <td style="padding: 10px; border-bottom: 1px solid #E5E0D8;"><strong>Your Target:</strong></td>
                        <td style="padding: 10px; border-bottom: 1px solid #E5E0D8; text-align: right; color: #C9922A;">{target_str}</td>
                      </tr>
                      <tr>
                        <td style="padding: 10px;"><strong>New Price:</strong></td>
                        <td style="padding: 10px; text-align: right; color: #27AE60; font-weight: bold; font-size: 1.2em;">{new_str}</td>
                      </tr>
                    </table>
                    <p style="text-align: center; margin-top: 30px;">
                      <a href="{property_url}" style="background-color: #2D5016; color: #FFFFFF; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">View Property</a>
                    </p>
                  </div>
                </div>
              </body>
            </html>
            """
            
            part = MIMEText(html, "html")
            msg.attach(part)

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, recipient_email, msg.as_string())
            server.quit()
            
            print(f"✅ Alert email sent to {recipient_email} for {property_title}")
            return True
        except Exception as e:
            print(f"❌ Failed to send email alert: {str(e)}")
            return False
