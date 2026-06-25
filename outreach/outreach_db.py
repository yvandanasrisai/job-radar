"""
Outreach storage — adds two tables to the existing Job Radar SQLite DB (jobs.db).

  contacts      one row per person we've discovered (dedup by contact_id)
  outreach_log  one row per (person, company, role, channel) message

Dedup rules:
  - contact_id = sha1(lower(full_name) + '|' + lower(company))  → same person at
    same company is stored once.
  - outreach_log has UNIQUE(contact_id, company, role, channel) so we never
    queue/send the same person twice for the same role on the same channel.
"""
import hashlib
import sqlite3
from datetime import datetime, timezone

# Reuse the same database file the rest of Job Radar uses.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH


def _conn():
    return sqlite3.connect(DB_PATH)


def _now():
    return datetime.now(timezone.utc).isoformat()


def make_contact_id(full_name: str, company: str) -> str:
    key = f"{(full_name or '').strip().lower()}|{(company or '').strip().lower()}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def init_outreach_db():
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                contact_id   TEXT PRIMARY KEY,
                full_name    TEXT,
                first_name   TEXT,
                title        TEXT,
                company      TEXT,
                kind         TEXT,        -- 'recruiter' | 'alum' | 'local'
                email        TEXT,        -- '' if LinkedIn-only
                linkedin_url TEXT,
                is_utd_alum  INTEGER DEFAULT 0,
                office_city  TEXT,
                source       TEXT,        -- 'apollo' | 'linkedin' | 'mock'
                created_at   TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS outreach_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id  TEXT,
                company     TEXT,
                role        TEXT,
                channel     TEXT,         -- 'email' | 'linkedin'
                subject     TEXT,
                message     TEXT,
                status      TEXT,         -- 'draft'|'approved'|'sent'|'replied'|'skipped'
                created_at  TIMESTAMP,
                sent_at     TIMESTAMP,
                UNIQUE(contact_id, company, role, channel)
            )
        """)
        con.commit()


def upsert_contact(c: dict) -> str:
    """Insert/refresh a contact. Returns its contact_id."""
    cid = c.get("contact_id") or make_contact_id(c.get("full_name", ""), c.get("company", ""))
    with _conn() as con:
        con.execute(
            """INSERT INTO contacts
               (contact_id, full_name, first_name, title, company, kind, email,
                linkedin_url, is_utd_alum, office_city, source, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(contact_id) DO UPDATE SET
                 title=excluded.title, kind=excluded.kind,
                 email=CASE WHEN excluded.email != '' THEN excluded.email ELSE contacts.email END,
                 linkedin_url=CASE WHEN excluded.linkedin_url != '' THEN excluded.linkedin_url ELSE contacts.linkedin_url END,
                 is_utd_alum=excluded.is_utd_alum, office_city=excluded.office_city,
                 source=excluded.source""",
            (cid, c.get("full_name", ""), c.get("first_name", ""), c.get("title", ""),
             c.get("company", ""), c.get("kind", ""), c.get("email", ""),
             c.get("linkedin_url", ""), int(c.get("is_utd_alum", 0)),
             c.get("office_city", ""), c.get("source", ""), _now()),
        )
        con.commit()
    return cid


def already_contacted(contact_id: str, company: str, role: str, channel: str) -> bool:
    """True if we've previously queued/sent this person for this role+channel
    in any non-skipped state."""
    with _conn() as con:
        row = con.execute(
            """SELECT status FROM outreach_log
               WHERE contact_id=? AND company=? AND role=? AND channel=?""",
            (contact_id, company, role, channel),
        ).fetchone()
    return row is not None and row[0] not in ("skipped",)


def add_draft(contact_id: str, company: str, role: str, channel: str,
              subject: str, message: str, status: str = "draft") -> bool:
    """Queue a row with the given status. Returns False if a non-skipped row
    already exists (dedup). status: 'draft' | 'draft_created' | 'li_pending'."""
    if already_contacted(contact_id, company, role, channel):
        return False
    sent = _now() if status in ("draft_created", "sent") else None
    with _conn() as con:
        con.execute(
            """INSERT OR REPLACE INTO outreach_log
               (contact_id, company, role, channel, subject, message, status, created_at, sent_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (contact_id, company, role, channel, subject, message, status, _now(), sent),
        )
        con.commit()
    return True


def set_status(log_id: int, status: str):
    sent = _now() if status == "sent" else None
    with _conn() as con:
        con.execute(
            "UPDATE outreach_log SET status=?, sent_at=COALESCE(?, sent_at) WHERE id=?",
            (status, sent, log_id),
        )
        con.commit()


def get_drafts(company: str | None = None, role: str | None = None,
               status: str = "draft") -> list[dict]:
    """Join outreach_log with contacts for the review queue / sender."""
    q = """SELECT l.id, l.contact_id, l.company, l.role, l.channel, l.subject,
                  l.message, l.status, c.full_name, c.first_name, c.title,
                  c.kind, c.email, c.linkedin_url, c.is_utd_alum, c.office_city
           FROM outreach_log l JOIN contacts c ON l.contact_id = c.contact_id
           WHERE l.status = ?"""
    args: list = [status]
    if company:
        q += " AND l.company = ?"; args.append(company)
    if role:
        q += " AND l.role = ?"; args.append(role)
    q += " ORDER BY l.channel, c.kind DESC"
    with _conn() as con:
        rows = con.execute(q, args).fetchall()
    cols = ["id", "contact_id", "company", "role", "channel", "subject", "message",
            "status", "full_name", "first_name", "title", "kind", "email",
            "linkedin_url", "is_utd_alum", "office_city"]
    return [dict(zip(cols, r)) for r in rows]


def get_log_row(log_id: int) -> dict | None:
    """Fetch one outreach_log row joined with its contact (for sending)."""
    with _conn() as con:
        row = con.execute(
            """SELECT l.id, l.contact_id, l.company, l.role, l.channel, l.subject,
                      l.message, l.status, c.full_name, c.first_name, c.title,
                      c.kind, c.email, c.linkedin_url
               FROM outreach_log l JOIN contacts c ON l.contact_id = c.contact_id
               WHERE l.id=?""", (log_id,)).fetchone()
    if not row:
        return None
    cols = ["id", "contact_id", "company", "role", "channel", "subject", "message",
            "status", "full_name", "first_name", "title", "kind", "email", "linkedin_url"]
    return dict(zip(cols, row))


def update_message(log_id: int, subject: str, message: str):
    with _conn() as con:
        con.execute("UPDATE outreach_log SET subject=?, message=? WHERE id=?",
                    (subject, message, log_id))
        con.commit()


def _rows_by_status(statuses: tuple[str, ...]) -> list[dict]:
    placeholders = ",".join("?" * len(statuses))
    with _conn() as con:
        rows = con.execute(
            f"""SELECT l.id, l.contact_id, l.company, l.role, l.channel, l.subject,
                       l.message, l.status, l.sent_at, c.full_name, c.first_name,
                       c.title, c.kind, c.email, c.linkedin_url, c.is_utd_alum
                FROM outreach_log l JOIN contacts c ON l.contact_id = c.contact_id
                WHERE l.status IN ({placeholders})
                ORDER BY l.company, l.channel, c.kind DESC""",
            statuses,
        ).fetchall()
    cols = ["id", "contact_id", "company", "role", "channel", "subject", "message",
            "status", "sent_at", "full_name", "first_name", "title", "kind",
            "email", "linkedin_url", "is_utd_alum"]
    return [dict(zip(cols, r)) for r in rows]


def get_pending() -> list[dict]:
    """Rows awaiting your action: plain drafts + LinkedIn-to-send."""
    return _rows_by_status(("draft", "li_pending"))


def get_all_sent() -> list[dict]:
    """History: Gmail drafts created, sent, skipped, approved."""
    return _rows_by_status(("draft_created", "sent", "skipped", "approved"))


def linkedin_sent_for_company(company: str) -> int:
    """Count LinkedIn messages sent (approved or sent status) for this company."""
    with _conn() as con:
        row = con.execute(
            """SELECT COUNT(*) FROM outreach_log
               WHERE channel='linkedin' AND status IN ('sent','approved')
                 AND company=?""",
            (company,),
        ).fetchone()
    return row[0] if row else 0


if __name__ == "__main__":
    init_outreach_db()
    print("Outreach tables ready in", DB_PATH)
