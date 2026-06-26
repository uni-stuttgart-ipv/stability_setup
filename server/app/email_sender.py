# filepath: app/email_sender.py
import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Optional
import socket
import aiosmtplib

from jinja2 import Template

from .config import EmailConfigSettings

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailSender:
    def __init__(self, config: EmailConfigSettings):
        self.config = config

    async def send_email(
        self,
        email_to: str,
        subject: str,
        html_template: str,
        template_body: dict,
        attachment: Optional[bytes] = None,
        attachment_filename: Optional[str] = None,
        email_cc: Optional[str] = None,
    ) -> bool:
        """
        Sends an email with HTML content and an optional attachment.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        if not self.config.EMAILS_FROM_EMAIL:
            logger.error("Sender email (EMAILS_FROM_EMAIL) is not configured.")
            return False

        # 1. Render the HTML template
        template = Template(html_template)
        html_content = template.render(**template_body)

        # 2. Create the email message
        msg = MIMEMultipart()
        msg["From"] = formataddr((self.config.EMAILS_FROM_NAME, self.config.EMAILS_FROM_EMAIL))
        msg["To"] = email_to.replace(";", ",")
        if email_cc:
            msg["Cc"] = email_cc.replace(";", ",")
        msg["Subject"] = subject
        msg.attach(MIMEText(html_content, "html"))

        # 3. Add attachment if provided
        if attachment and attachment_filename:
            part = MIMEApplication(attachment, Name=attachment_filename)
            part["Content-Disposition"] = f'attachment; filename="{attachment_filename}"'
            msg.attach(part)

        # 4. Send the email
        try:
            # Using a context manager for the SMTP connection
            async with aiosmtplib.SMTP(hostname=self.config.SMTP_HOST, port=self.config.SMTP_PORT) as server:
                # await server.starttls()
                await server.login(self.config.SMTP_USER, self.config.SMTP_PASSWORD)
                await server.send_message(msg)
            logger.info(f"Email sent successfully to {email_to}")
            return True
        except (aiosmtplib.SMTPException, ConnectionRefusedError, socket.gaierror) as e:
            # The `socket.gaierror` is included to catch DNS resolution errors,
            # which can happen if the SMTP_HOST is incorrect or unreachable.
            # See Python docs for more info: https://docs.python.org/3/library/socket.html
            logger.critical(f"Failed to send email to {email_to}. Error: {e}")
            return False

