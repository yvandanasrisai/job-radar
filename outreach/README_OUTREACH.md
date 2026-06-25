# Job Radar — Outreach & Referral System

Turn "I applied to **X company** for **Y role**" into a small, targeted set of
personalized messages to the right **recruiters** (cold email) and **UTD
alumni / Dallas-local employees** (referral asks) — with a **review step** before
anything sends.

## What's built

```
outreach/
  outreach_db.py     contacts + outreach_log tables in jobs.db, dedup, status
  classify.py        title -> recruiter | employee, seniority ranking
  resume_content.py  picks best resume txt + extracts role-relevant highlights
  templates.py       formal email + LinkedIn messages (no attachment)
  email_sender.py    Gmail SMTP send (plain text, no attachment)
  review.py          writes outreach_review.xlsx (editable) + outreach_queue.html
  outreach.py        orchestrator / CLI
  apollo_api.py      OPTIONAL Apollo REST fast-path (needs APOLLO_API_KEY)
  _test_outreach_smtp.py   one-shot SMTP self-test
```

Sends from **vandanasrisaiyedla@gmail.com** (app password in `C:\JobRadar\.env`).

## Messaging rules
- Formal, structured cold outreach (not "please look at my application").
- A paragraph of **role-relevant, quantified work** pulled from your resumes.
- **No resume attached** (deliverability) — every message offers to share it on request.
- **One channel per person**: email if we have a verified address, else LinkedIn.

---

## Daily usage

### 1. Discover people (interactive, in a Claude session with Chrome)
Tell Claude: **"Outreach for {Company}, role {Role}."** Claude will, in your
logged-in Chrome (Claude-in-Chrome extension):
- **Apollo** → up to ~6 USA recruiters for that role (senior first); reveal emails
  for the top few (free credits, recruiters first).
- **LinkedIn** → up to ~5 **UT Dallas alumni** at the company; if none, **Dallas-local**
  employees.
Claude saves them to `outreach/people.json`.

### 2. Build the review queue
```
python outreach/outreach.py "Company" "Role" --people outreach/people.json
```
Opens `outreach_queue.html` (preview) and writes `outreach_review.xlsx` (editable).

### 3. Review & approve
In **outreach_review.xlsx**: edit any **Subject/Message**, then set the **Action**
column to `send` or `skip` (blank = held back). Save.

### 4. Send
```
python outreach/outreach.py --send "Company" "Role"
```
- Email rows with Action=`send` → sent via Gmail.
- LinkedIn rows with Action=`send` → marked **approved** and listed; Claude then
  opens each profile in Chrome, pre-fills the note, and **you click Send**
  (capped at LINKEDIN_DAILY_CAP/day).

Re-running for the same company+role automatically **skips people already contacted**.

---

## people.json schema
```json
[
  {"full_name": "Jordan Mills", "title": "Senior Technical Recruiter",
   "email": "jordan@company.com", "linkedin_url": "",
   "is_utd_alum": false, "office_city": "", "source": "apollo"},
  {"full_name": "Priya Nair", "title": "Data Scientist",
   "email": "", "linkedin_url": "https://linkedin.com/in/priyanair",
   "is_utd_alum": true, "office_city": "Dallas, TX", "source": "linkedin"}
]
```
`kind` is derived automatically: recruiter (by title) → `recruiter`; else
`is_utd_alum` → `alum`; else → `local`.

---

## Connecting the three tools

| Tool | How it connects | Notes |
|---|---|---|
| **Gmail** (send) | `smtplib` + app password in `.env` | No setup beyond the app password. Verify with `_test_outreach_smtp.py`. |
| **Apollo** (find people/emails) | **Browser-driven** via Claude-in-Chrome (recommended). Optional REST via `APOLLO_API_KEY`. | Free tier email credits are limited → recruiters get reveal priority. |
| **LinkedIn** (alumni + DMs) | **Semi-auto** via Claude-in-Chrome; **you approve each send**. | No official API; keep volume ≲10/day to protect the account. |

**Requirement:** the **Claude-in-Chrome browser extension** must be installed and
connected, and you must be **logged into Apollo and LinkedIn** in that browser.
This is why discovery/LinkedIn sending is an interactive session, not a cron job.

---

## Apollo search recipe (what Claude runs)
- People search → **Company = {company}**, **Title** any of: Recruiter, Technical
  Recruiter, Senior Recruiter, Talent Acquisition, Recruiting Manager, University
  Recruiter, Sourcer, Head of Talent → **Location = United States**.
- Sort by seniority; "Access email" on the top 3–6 only (save credits).

## LinkedIn referral recipe (what Claude runs)
- Company page → **People** → filter **School = The University of Texas at Dallas**
  → collect up to 5 (prefer same team/role).
- If no alumni → filter **Locations = Dallas/Plano/Fort Worth** → up to 5 employees
  on or near the target team.

## Safety / notes
- App password + Apollo key live only in `.env` (never committed). Rotate the
  Gmail app password periodically.
- Emails are plain text, no attachment — best for cold-email deliverability.
- Dedup prevents contacting the same person twice for the same role+channel.
