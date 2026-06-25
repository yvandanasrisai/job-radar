"""
Create a Gmail DRAFT (not a send) via IMAP APPEND to [Gmail]/Drafts.

Zero cost, no API key — uses the SAME app password the radar already uses for
IMAP (see fetchers.py). The draft lands in vandanasrisaiyedla@gmail.com Drafts;
you open Gmail, review, and hit Send yourself.

HARD RULE: plain text, NO attachment. There is no attachment parameter here, so
an attachment is impossible by construction.

Setup (one-time): IMAP must be ON for the account
  Gmail → Settings → Forwarding and POP/IMAP → Enable IMAP.
"""
import imaplib
import time
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate
from datetime import datetime, timezone

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OUTREACH_EMAIL, OUTREACH_EMAIL_PASSWORD, MY_NAME, ERROR_LOG

DRAFTS_FOLDER = "[Gmail]/Drafts"


def _log_err(msg: str):
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] gmail_draft: {msg}\n")
    except Exception:
        pass


def create_draft(to_addr: str, subject: str, body: str) -> tuple[bool, str]:
    """Append a plain-text draft to Gmail Drafts. Returns (ok, detail). Never raises."""
    if not OUTREACH_EMAIL or not OUTREACH_EMAIL_PASSWORD:
        return False, "OUTREACH_EMAIL / OUTREACH_EMAIL_PASSWORD not set in .env"
    if not to_addr:
        return False, "no recipient address"

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"]    = formataddr((MY_NAME, OUTREACH_EMAIL))
    msg["To"]      = to_addr
    msg["Date"]    = formatdate(localtime=True)

    pw = OUTREACH_EMAIL_PASSWORD.replace(" ", "")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(OUTREACH_EMAIL, pw)
        try:
            status, _ = mail.append(
                DRAFTS_FOLDER, "\\Draft",
                imaplib.Time2Internaldate(time.time()),
                msg.as_bytes(),
            )
        finally:
            try:
                mail.logout()
            except Exception:
                pass
        if status == "OK":
            return True, "draft created"
        return False, f"APPEND returned {status}"
    except imaplib.IMAP4.error as e:
        _log_err(f"IMAP auth/append failed -> {to_addr}: {e}")
        return False, f"IMAP error: {e} (is IMAP enabled for {OUTREACH_EMAIL}?)"
    except Exception as e:
        _log_err(f"failed -> {to_addr}: {e}")
        return False, str(e)


if __name__ == "__main__":
    # Self-test: drop a draft addressed to yourself.
    ok, detail = create_draft(
        OUTREACH_EMAIL,
        "[SELF-TEST] Outreach draft system",
        "This is a self-test draft.\n\nIf you can see this in your Gmail Drafts, "
        "the zero-cost draft system works.\n\nBest regards,\n" + MY_NAME,
    )
    print("OK" if ok else "FAILED", "-", detail)
