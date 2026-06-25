"""
Outreach orchestrator / CLI.

Build a review queue for a company + role:
    python outreach/outreach.py "Acme Corp" "Data Scientist"
        -> uses built-in MOCK people (offline testing)
    python outreach/outreach.py "Acme Corp" "Data Scientist" --people people.json
        -> uses real people discovered via Apollo/LinkedIn (Phase 5)

Send what you approved (after editing outreach_review.xlsx):
    python outreach/outreach.py --send "Acme Corp" "Data Scientist"

people.json schema (list of objects):
    {"full_name": "...", "title": "...", "email": "" , "linkedin_url": "",
     "is_utd_alum": false, "office_city": "", "source": "apollo"}
"""
import json
import sys
import os
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (OUTREACH_MAX_PER_JOB, LINKEDIN_PER_COMPANY_CAP,
                    LARGE_COMPANIES, LARGE_COMPANY_MAX, OUTREACH_EMAIL)
from outreach.outreach_db import (
    init_outreach_db, upsert_contact, add_draft, get_log_row,
    set_status, update_message, already_contacted,
)
from outreach.classify import classify, is_recruiter, seniority_rank
from outreach.templates import build_message
from outreach.review import write_review, read_review_actions


# ── helpers ────────────────────────────────────────────────────────────────
def _first_name(full_name: str) -> str:
    return (full_name or "").strip().split(" ")[0] if full_name else ""


def _assign_kind(p: dict) -> str:
    if is_recruiter(p.get("title", "")):
        return "recruiter"
    if int(p.get("is_utd_alum", 0)):
        return "alum"
    return "local"


def _is_large(company: str) -> bool:
    c = (company or "").lower()
    return any(big in c for big in LARGE_COMPANIES)


def _cap_for(company: str) -> int:
    return LARGE_COMPANY_MAX if _is_large(company) else OUTREACH_MAX_PER_JOB


def _prioritise(people: list[dict], cap: int) -> list[dict]:
    """Recruiters first (senior first), then high-position alumni, then locals."""
    for p in people:
        p["_kind"] = _assign_kind(p)
    order = {"recruiter": 0, "alum": 1, "local": 2}
    people.sort(key=lambda p: (order[p["_kind"]], -seniority_rank(p.get("title", ""))))
    return people[:cap]


# ── build queue ─────────────────────────────────────────────────────────────
def build_queue(company: str, role: str, people: list[dict],
                applied: bool = True, make_drafts: bool = False) -> dict:
    """Classify, dedup, generate messages. If make_drafts, create Gmail drafts
    for email contacts; LinkedIn-only people are logged as 'li_pending'."""
    init_outreach_db()
    cap = _cap_for(company)
    people = _prioritise(people, cap)

    drafts_made = li_listed = skipped = draft_fail = 0
    for p in people:
        kind = p.get("_kind") or _assign_kind(p)
        contact = {
            "full_name": p.get("full_name", ""),
            "first_name": p.get("first_name") or _first_name(p.get("full_name", "")),
            "title": p.get("title", ""),
            "company": company,
            "kind": kind,
            "email": p.get("email", "") or "",
            "linkedin_url": p.get("linkedin_url", "") or "",
            "is_utd_alum": int(p.get("is_utd_alum", 0)),
            "office_city": p.get("office_city", "") or "",
            "source": p.get("source", "mock"),
        }
        cid = upsert_contact(contact)
        contact["contact_id"] = cid

        msg = build_message(contact, company, role, applied=applied)
        channel = msg["channel"]

        if already_contacted(cid, company, role, channel):
            skipped += 1
            continue

        if make_drafts and channel == "email" and contact["email"]:
            from outreach.gmail_draft import create_draft
            ok, detail = create_draft(contact["email"], msg["subject"], msg["body"])
            if ok:
                add_draft(cid, company, role, channel, msg["subject"], msg["body"],
                          status="draft_created")
                drafts_made += 1
                print(f"  ✓ Gmail draft → {contact['full_name']} <{contact['email']}>")
            else:
                add_draft(cid, company, role, channel, msg["subject"], msg["body"],
                          status="draft")
                draft_fail += 1
                print(f"  ✗ draft FAILED for {contact['full_name']}: {detail}")
        elif channel == "linkedin":
            add_draft(cid, company, role, channel, msg["subject"], msg["body"],
                      status="li_pending")
            li_listed += 1
        else:
            add_draft(cid, company, role, channel, msg["subject"], msg["body"])

    info = write_review(company, role)
    info.update({"drafts_made": drafts_made, "li_listed": li_listed,
                 "skipped_dupes": skipped, "draft_fail": draft_fail,
                 "considered": len(people), "large": _is_large(company)})
    return info


# ── send approved ───────────────────────────────────────────────────────────
def send_approved(company: str, role: str) -> dict:
    from outreach.email_sender import send_email

    actions = read_review_actions()
    sent = skipped = held = li_approved = failed = 0
    linkedin_todo: list[dict] = []

    for a in actions:
        row = get_log_row(a["log_id"])
        if not row:
            continue
        action = a["action"]
        # Persist any edits the user made in the xlsx.
        if a["subject"] != row["subject"] or a["message"] != row["message"]:
            update_message(a["log_id"], a["subject"], a["message"])
            row["subject"], row["message"] = a["subject"], a["message"]

        if action == "skip":
            set_status(a["log_id"], "skipped"); skipped += 1
            continue
        if action != "send":
            held += 1
            continue

        if row["channel"] == "email":
            ok, detail = send_email(row["email"], row["subject"], row["message"])
            if ok:
                set_status(a["log_id"], "sent"); sent += 1
            else:
                failed += 1
                print(f"  ✗ email to {row['email']} FAILED: {detail}")
        else:  # linkedin -> semi-auto, mark approved for the Chrome step
            set_status(a["log_id"], "approved"); li_approved += 1
            linkedin_todo.append(row)

    # Refresh the review files so sent/skipped rows drop off the draft queue.
    write_review(company, role)

    if linkedin_todo:
        print(f"\n{len(linkedin_todo)} LinkedIn message(s) approved for {company} "
              f"(cap: up to {LINKEDIN_PER_COMPANY_CAP}/company). "
              f"Drive these via Claude-in-Chrome:")
        for r in linkedin_todo:
            print(f"  • {r['full_name']} ({r['title']}) — {r['linkedin_url'] or 'no URL'}")
            print(f"      {r['message']}")

    return {"sent": sent, "skipped": skipped, "held": held,
            "linkedin_approved": li_approved, "failed": failed}


# ── mock discovery (Phase 4 offline testing) ────────────────────────────────
def discover_mock(company: str, role: str) -> list[dict]:
    return [
        {"full_name": "Jordan Mills", "title": "Senior Technical Recruiter",
         "email": "jordan.mills@example.com", "source": "mock"},
        {"full_name": "Alyssa Chen", "title": "Talent Acquisition Partner",
         "email": "", "linkedin_url": "https://linkedin.com/in/alyssachen", "source": "mock"},
        {"full_name": "Priya Nair", "title": "Data Scientist", "is_utd_alum": 1,
         "email": "", "linkedin_url": "https://linkedin.com/in/priyanair", "source": "mock"},
        {"full_name": "Marcus Lee", "title": "Machine Learning Engineer",
         "office_city": "Dallas, TX", "email": "", "is_utd_alum": 0,
         "linkedin_url": "https://linkedin.com/in/marcuslee", "source": "mock"},
    ]


# ── CLI ──────────────────────────────────────────────────────────────────────
def _load_people(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv: list[str]):
    if not argv:
        print(__doc__); return

    send_mode    = "--send" in argv
    drafts_mode  = "--drafts" in argv
    networking   = "--networking" in argv
    argv = [a for a in argv if a not in ("--send", "--drafts", "--networking")]

    people_path = None
    if "--people" in argv:
        i = argv.index("--people")
        people_path = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]

    if len(argv) < 2:
        print('Usage: outreach.py "Company" "Role" [--people file.json] '
              '[--drafts] [--networking] [--send]')
        return
    company, role = argv[0], argv[1]

    if send_mode:
        res = send_approved(company, role)
        print(f"\nSENT {res['sent']} email(s) | LinkedIn approved {res['linkedin_approved']} "
              f"| skipped {res['skipped']} | held {res['held']} | failed {res['failed']}")
        return

    people = _load_people(people_path) if people_path else discover_mock(company, role)
    applied = not networking
    info = build_queue(company, role, people, applied=applied, make_drafts=drafts_mode)

    tag = "LARGE company (wider net)" if info["large"] else "standard"
    mode = "NETWORKING (no 'I applied')" if networking else "applied"
    print(f"\n[{company} — {role}]  {tag} · {mode}")
    if drafts_mode:
        print(f"  Gmail drafts created: {info['drafts_made']}  "
              f"(failed: {info['draft_fail']})")
    print(f"  LinkedIn-only listed in tracker: {info['li_listed']}")
    print(f"  Duplicates skipped: {info['skipped_dupes']}  ·  considered: {info['considered']}")
    print(f"\n  Email drafts → review in Gmail Drafts ({OUTREACH_EMAIL}).")
    print(f"  Tracker: {info['xlsx']}")


if __name__ == "__main__":
    main(sys.argv[1:])
