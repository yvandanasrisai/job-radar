"""
Send a single cold-outreach email via Gmail SMTP (vandanasrisaiyedla@gmail.com).

Deliberately PLAIN TEXT and NO ATTACHMENT — cold emails with attachments and
heavy HTML are far more likely to hit spam. Mirrors the SMTP pattern in
notifier.py (STARTTLS, app password with spaces stripped).
"""
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from datetime import datetime, timezone

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OUTREACH_EMAIL, OUTREACH_EMAIL_PASSWORD, MY_NAME, ERROR_LOG


def send_email(to_addr: str, subject: str, body: str) -> tuple[bool, str]:
    """Returns (ok, detail). Never raises — logs failures like notifier.py."""
    if not OUTREACH_EMAIL or not OUTREACH_EMAIL_PASSWORD:
        return False, "OUTREACH_EMAIL / OUTREACH_EMAIL_PASSWORD not set in .env"
    if not to_addr:
        return False, "no recipient address"

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"]    = formataddr((MY_NAME, OUTREACH_EMAIL))
    msg["To"]      = to_addr
    msg["Reply-To"] = OUTREACH_EMAIL

    pw = OUTREACH_EMAIL_PASSWORD.replace(" ", "")
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(OUTREACH_EMAIL, pw)
            server.sendmail(OUTREACH_EMAIL, [to_addr], msg.as_string())
        return True, "sent"
    except Exception as e:
        try:
            with open(ERROR_LOG, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now(timezone.utc).isoformat()}] outreach SMTP failed -> {to_addr}: {e}\n")
        except Exception:
            pass
        return False, str(e)


if __name__ == "__main__":
    # Smoke test handled by _test_outreach_smtp.py
    print("email_sender ready. From:", OUTREACH_EMAIL or "(not configured)")
