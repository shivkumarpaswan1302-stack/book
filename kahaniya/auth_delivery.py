import base64
import logging
import os
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException, status

from .security import APP_ENV

logger = logging.getLogger(__name__)


def send_otp(phone_number: str, code: str) -> None:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    if account_sid and auth_token and from_number:
        endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        body = urlencode({"To": phone_number, "From": from_number, "Body": f"Your कHaniya sign-in code is {code}. It expires in 10 minutes."}).encode()
        credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
        request = Request(endpoint, data=body, headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"})
        with urlopen(request, timeout=10) as response:
            if response.status >= 300:
                raise HTTPException(status_code=502, detail="Could not send verification code")
        return
    if APP_ENV == "production":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Phone verification is not configured")
    logger.info("Development OTP for %s: %s", phone_number, code)


def send_password_reset(email: str, reset_url: str) -> bool:
    host = os.getenv("SMTP_HOST")
    if not host:
        if APP_ENV == "production":
            logger.error("Password reset requested but SMTP_HOST is not configured")
            return False
        logger.info("Development password reset URL for %s: %s", email, reset_url)
        return False

    message = EmailMessage()
    message["Subject"] = "Reset your कHaniya password"
    message["From"] = os.getenv("SMTP_FROM", "no-reply@kahaniya.local")
    message["To"] = email
    message.set_content(f"Use this link to reset your password. It expires in 30 minutes.\n\n{reset_url}\n")
    port = int(os.getenv("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        if os.getenv("SMTP_STARTTLS", "true").lower() == "true":
            smtp.starttls()
        username = os.getenv("SMTP_USERNAME")
        password = os.getenv("SMTP_PASSWORD")
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)
    return True