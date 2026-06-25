"""
Formal, structured outreach message templates.

Rules (per user requirements):
  - Professional cold outreach, not a casual "please look at my application".
  - A structured paragraph highlighting role-relevant work.
  - NO resume attached — end with an offer to share it on request.
  - Email and LinkedIn variants. LinkedIn connection notes are <= 300 chars.

build_message(...) returns {'subject', 'body', 'channel'} ready to queue.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MY_NAME, MY_FIRST_NAME, MY_PHONE, MY_LINKEDIN, OUTREACH_EMAIL, UTD_SCHOOL_NAME
from outreach.resume_content import (build_relevant_para, linkedin_relevant_phrase,
                                     build_brief_para)


def _signature() -> str:
    parts = [MY_NAME]
    contact = " | ".join(p for p in [OUTREACH_EMAIL, MY_PHONE, MY_LINKEDIN] if p)
    if contact:
        parts.append(contact)
    return "\n".join(parts)


# ── EMAIL: recruiter ────────────────────────────────────────────────────────
def recruiter_email(person: dict, company: str, role: str) -> dict:
    first = person.get("first_name") or "there"
    brief = build_brief_para(role)
    subject = f"Following Up on {company} - {role} - Application"
    body = f"""Hi {first},

I recently applied for the {role} role at {company} and wanted to reach out directly — it's an opportunity I'm genuinely excited about.

A little about me: I'm a data scientist (UT Dallas), and most recently I {brief}. I love turning messy data into things teams can actually use, and from the role I really think I'd be a strong fit.

If you'd be open to taking a look at my application, I'd so appreciate it. And if you're not the right person for this one, I'd be grateful for a referral — it's a tough market right now, so even a small nudge would mean a lot. Happy to share my resume whenever it's helpful.

Thank you so much!

Best,
{_signature()}"""
    return {"subject": subject, "body": body, "channel": "email"}


# ── EMAIL: alumni referral ──────────────────────────────────────────────────
def alum_referral_email(person: dict, company: str, role: str) -> dict:
    first = person.get("first_name") or "there"
    brief = build_brief_para(role)
    subject = f"Would Appreciate Your Advice on {role}"
    body = f"""Hi {first},

I came across your profile and saw we're both UT Dallas grads — always nice to meet a fellow Comet, especially one at {company}!

I recently applied for the {role} role at {company} and would really value your advice. A quick bit about me: I'm a data scientist, and most recently I {brief} — it's the kind of work I love, and I genuinely think I'd be a good fit here.

If you're open to it, I'd be grateful for a referral, or even just your read on the team. Happy to share my resume so you have everything you need. Either way, thank you — it means a lot!

Best,
{_signature()}"""
    return {"subject": subject, "body": body, "channel": "email"}


# ── EMAIL: local (non-alum) referral ────────────────────────────────────────
def local_referral_email(person: dict, company: str, role: str) -> dict:
    first = person.get("first_name") or "there"
    brief = build_brief_para(role)
    subject = f"Applied for {role} – Would Love Your Advice"
    body = f"""Hi {first},

I hope you're doing well! I recently applied for the {role} role at {company} and wanted to reach out to someone on the team.

A quick bit about me: I'm a data scientist (UT Dallas), and most recently I {brief}. From what I've seen of the role, I genuinely think I'd be a strong fit.

If you're open to it, I'd really appreciate a referral or any advice you can share about the team — it's a tough market right now. Happy to send over my resume if that's helpful. Thank you so much!

Best,
{_signature()}"""
    return {"subject": subject, "body": body, "channel": "email"}


# ── EMAIL: networking (NOT applied — Netflix/Meta/Apple etc.) ────────────────
def networking_recruiter_email(person: dict, company: str, role: str) -> dict:
    first = person.get("first_name") or "there"
    brief = build_brief_para(role)
    subject = f"Exploring {role} Opportunities at {company}"
    body = f"""Hi {first},

I'm a data scientist (UT Dallas) and a big admirer of what {company} is building — I'm actively exploring {role} opportunities there.

A little about me: most recently I {brief}, and I love turning data into things teams can actually use. From what I've seen, I think I'd be a strong fit for this kind of role.

I'd love to connect, and if something relevant opens up I'd be grateful to be considered — or for a referral if you think I'd be a fit. It's a competitive market, so any guidance means a lot. Happy to share my resume anytime.

Thank you so much!

Best,
{_signature()}"""
    return {"subject": subject, "body": body, "channel": "email"}


def networking_alum_email(person: dict, company: str, role: str) -> dict:
    first = person.get("first_name") or "there"
    brief = build_brief_para(role)
    subject = f"Would Appreciate Your Advice on {role} at {company}"
    body = f"""Hi {first},

I came across your profile and saw we're both UT Dallas grads — always great to meet a fellow Comet, especially one doing such cool work at {company}!

I'm exploring {role} opportunities at {company} and would love your perspective. A quick bit about me: I'm a data scientist, and most recently I {brief} — I think I'd be a good fit for this kind of work.

If you're open to it, I'd be grateful for any advice — and a referral, if a relevant role opens up. It's a tough market right now, so it would genuinely mean a lot. Happy to share my resume whenever helpful.

Thanks so much!

Best,
{_signature()}"""
    return {"subject": subject, "body": body, "channel": "email"}


# ── LINKEDIN: recruiter (connection note, <=300 chars) ──────────────────────
def recruiter_linkedin(person: dict, company: str, role: str) -> dict:
    first = person.get("first_name") or "there"
    phrase = linkedin_relevant_phrase(role)
    note = (f"Hi {first}, I just applied for the {role} role at {company}. "
            f"Background: {phrase}. I'd love to connect and am happy to share my "
            f"resume if helpful. Thank you! - {MY_FIRST_NAME}")
    return {"subject": "", "body": _cap300(note), "channel": "linkedin"}


# ── LINKEDIN: alumni referral (connection note, <=300 chars) ────────────────
def alum_linkedin(person: dict, company: str, role: str) -> dict:
    first = person.get("first_name") or "there"
    note = (f"Hi {first}, fellow UT Dallas grad here! I just applied for the {role} "
            f"role at {company} and would love to connect. If you're open to it, a "
            f"referral would mean a lot - happy to share my resume. Thanks! - {MY_FIRST_NAME}")
    return {"subject": "", "body": _cap300(note), "channel": "linkedin"}


# ── LINKEDIN: local employee (applied, NOT a UTD alum) ──────────────────────
def local_linkedin(person: dict, company: str, role: str) -> dict:
    first = person.get("first_name") or "there"
    note = (f"Hi {first}, I just applied for the {role} role at {company} and would love "
            f"to connect with someone on the team. If you're open to it, a referral would "
            f"mean a lot — happy to share my resume. Thank you! - {MY_FIRST_NAME}")
    return {"subject": "", "body": _cap300(note), "channel": "linkedin"}


# ── LINKEDIN: networking (NOT applied) ──────────────────────────────────────
def networking_linkedin(person: dict, company: str, role: str) -> dict:
    first = person.get("first_name") or "there"
    is_alum = person.get("kind") == "alum"
    lead = ("fellow UT Dallas grad here — I'm exploring" if is_alum
            else "I'm a UT Dallas data scientist exploring")
    note = (f"Hi {first}, {lead} {role} roles at {company} and would love to connect. "
            f"If a relevant role opens up, a referral would mean a lot — happy to share "
            f"my resume. Thank you! - {MY_FIRST_NAME}")
    return {"subject": "", "body": _cap300(note), "channel": "linkedin"}


def _cap300(text: str) -> str:
    if len(text) <= 300:
        return text
    cut = text[:297]
    return cut[:cut.rfind(" ")] + "..."


def build_message(person: dict, company: str, role: str, applied: bool = True) -> dict:
    """Route to the right template based on kind + available channel.

    person needs: kind ('recruiter'|'alum'|'local'), email, linkedin_url.
    Channel rule: email if a verified email exists, else LinkedIn.
    applied=False → networking variants that do NOT claim an application
    (used for companies you haven't applied to, e.g. Netflix/Meta/Apple).
    """
    kind = person.get("kind", "employee")
    has_email = bool(person.get("email"))

    if not applied:
        # Networking mode. Email variants only differ; LinkedIn notes already
        # read as soft connect requests, so reuse them.
        if has_email:
            return networking_alum_email(person, company, role) if kind == "alum" \
                else networking_recruiter_email(person, company, role)
        return networking_linkedin(person, company, role)

    if kind == "recruiter":
        return recruiter_email(person, company, role) if has_email \
            else recruiter_linkedin(person, company, role)
    if kind == "alum":
        return alum_referral_email(person, company, role) if has_email \
            else alum_linkedin(person, company, role)
    # local / generic employee (NOT a UTD alum — must not claim "fellow grad")
    return local_referral_email(person, company, role) if has_email \
        else local_linkedin(person, company, role)


if __name__ == "__main__":
    rec = {"first_name": "Jordan", "kind": "recruiter", "email": "jordan@acme.com"}
    alum = {"first_name": "Priya", "kind": "alum", "email": "", "linkedin_url": "x"}
    print("=== RECRUITER EMAIL ===")
    m = build_message(rec, "Acme Corp", "Data Scientist")
    print("SUBJECT:", m["subject"]); print(m["body"])
    print("\n=== ALUM LINKEDIN ===")
    m = build_message(alum, "Acme Corp", "AI Engineer")
    print(f"({len(m['body'])} chars) {m['body']}")
