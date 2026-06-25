<div align="center">

# 🎯 Job Radar

### Automated Intelligence for Data Science & ML Job Hunting

*Stop refreshing. Start getting notified.*

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?style=flat-square&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Sources](https://img.shields.io/badge/Job%20Sources-7%20Active-00a651?style=flat-square)](#data-sources)
[![Companies](https://img.shields.io/badge/Employers%20Monitored-100%2B-ff8c00?style=flat-square)](#data-sources)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

</div>

---

## The Problem

The window between a job posting going live and the first wave of applications is **under 2 hours** for competitive DS/ML roles. By the time you see it on LinkedIn the next morning, there are already 300+ applicants. Manual job hunting is an asymmetric game — and you're losing it.

## The Solution

Job Radar runs **silently in the background**, monitoring 100+ employers across 7 data sources every 15 minutes. Every new posting is scored against your exact target profile — title match, visa sponsorship, recency, skill overlap, company prestige — and only the top matches hit your inbox, with a colour-coded HTML card showing exactly why the job is worth your time.

> **You stop searching. Job Radar searches for you.**

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FETCH  (every 15 min / 2 h)                │
│                                                                     │
│  LinkedIn ─────────────────────────────────────┐                   │
│  Greenhouse (30 companies) ────────────────────┤                   │
│  Lever      (20 companies) ────────────────────┤                   │
│  Ashby      (15 AI firms)  ────────────────────┤──► DEDUP          │
│  Workday    (10 employers) ────────────────────┤   (MD5 hash)      │
│  RSS Feeds  (6 boards)     ────────────────────┤                   │
│  Gmail IMAP (LI + Indeed)  ────────────────────┘                   │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │ new jobs only
                                    ▼
┌───────────────────────────────────────────────────────────────────┐
│                         SCORE  (100-point engine)                  │
│                                                                   │
│  ✦ Title match      (0–25)    ✦ Recency           (0–25)         │
│  ✦ Skill keywords   (0–20)    ✦ Visa sponsorship  (0–20 / SKIP)  │
│  ✦ Company prestige (5–10)    ✦ Seniority penalty (–15 if Sr/Lead)│
│                                                                   │
│  → Staffing agencies: BLOCKED     → No-sponsorship: HARD SKIP    │
│  → Security clearance: BLOCKED    → Title typos/fakes: BLOCKED   │
└───────────────────────────────────┬───────────────────────────────┘
                                    │ score ≥ threshold
                                    ▼
┌───────────────────────────────────────────────────────────────────┐
│                         NOTIFY  (Gmail HTML Alert)                 │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  82  │  👑 Ramp  ·  Data Scientist  ·  Remote, US        │    │
│  │ score│  🟢 Sponsors visa  LinkedIn  ✅ Entry  📅 Jun 25  │    │
│  │      │  Best Resume: R1-DataScientist  ATS: 78% ████░    │    │
│  │      │                              [ Apply → ]          │    │
│  └──────────────────────────────────────────────────────────┘    │
└───────────────────────────────────┬───────────────────────────────┘
                                    │
                                    ▼
                      SQLite DB  ──►  Excel Tracker
```

---

## Features

| Feature | Description | Status |
|---|---|:---:|
| **Multi-source aggregation** | 7 concurrent sources, 100+ employers, 48-hour freshness window | ✅ |
| **100-point scoring engine** | Title + Recency + Skills + Sponsorship + Company quality | ✅ |
| **Sponsorship hard-filter** | Any "no sponsorship / citizens only" phrasing → SKIP, never emailed | ✅ |
| **Agency auto-blocklist** | 105+ staffing firms detected via LinkedIn industry tags, name patterns, JD signals | ✅ |
| **ATS resume matching** | 6 tailored resumes × every JD → best resume + % skills matched | ✅ |
| **Crown for top companies** | 👑 badge on Stripe, Google, Ramp, Anthropic, Databricks etc. | ✅ |
| **Reposted job detection** | 🔄 badge + capped recency score so re-posts don't steal priority | ✅ |
| **Cold outreach engine** | Discovers recruiters via Apollo + UTD alumni via LinkedIn → Gmail drafts | ✅ |
| **Excel application tracker** | Every scored job → `applications.xlsx` with score, ATS %, sponsorship, status | ✅ |
| **Automated scheduling** | Windows Task Scheduler: 15-min quick runs + 2-hour full runs | ✅ |
| **Security clearance filter** | Top-secret / SCI clearance roles silently excluded | ✅ |
| **Seniority penalty** | Senior / Staff / Director titles scored –15 (tuned for early-career search) | ✅ |

---

## Data Sources

| # | Source | Type | Coverage | Refresh |
|---|--------|------|----------|---------|
| **1** | **LinkedIn** | Guest API + scrape | All public DS/ML postings, US-only | Every 15 min |
| **2** | **Greenhouse** | REST API | 30 companies — Airbnb, Twilio, Dropbox, Figma, Databricks… | Every 2 hours |
| **3** | **Lever** | REST API | 20 companies — Palantir, Veeva, Shield AI, Carta… | Every 2 hours |
| **4** | **Ashby** | REST API | 15 AI-native firms — OpenAI, Anthropic, Cohere, Scale AI, HuggingFace… | Every 2 hours |
| **5** | **Workday** | POST API | 10 large employers — Humana, Progressive, Schwab, Target, GE, Nike… | Every 2 hours |
| **6** | **RSS Feeds** | XML/JSON | RemoteOK, WeWorkRemotely, Jobicy, RemoteLeaf | Every 2 hours |
| **7** | **Gmail IMAP** | IMAP search | LinkedIn Job Alerts + Indeed Digest (7-day look-back) | Every 15 min |

---

## Scoring Algorithm

Every job that passes the hard filters receives a score from 0 to 100. Only jobs at or above `SCORE_THRESHOLD` (default: 55) trigger an email alert.

```
┌─────────────────────────────────────────────────────────┐
│                  100-POINT BREAKDOWN                    │
├──────────────────────┬────────────────────────────────┤
│  Title relevance     │  25 pts  (exact match)          │
│                      │  15 pts  (partial match)         │
│                      │ –15 pts  penalty (Senior/Lead)   │
│                      │  +3 pts  bonus (Entry/Associate) │
├──────────────────────┼────────────────────────────────┤
│  Recency             │  25 pts  < 1 hour old           │
│                      │  18 pts  1–2 hours              │
│                      │  12 pts  2–6 hours              │
│                      │   8 pts  6–24 hours             │
│                      │   4 pts  24–48 hours            │
│                      │  ≤ 6 pts  reposted job (capped) │
├──────────────────────┼────────────────────────────────┤
│  Skill keywords      │  20 pts  10+ keywords matched   │
│                      │  15 pts  7–9 keywords           │
│                      │  10 pts  4–6 keywords           │
│                      │   5 pts  1–3 keywords           │
├──────────────────────┼────────────────────────────────┤
│  Visa sponsorship    │  20 pts  "will sponsor / H-1B"  │
│                      │  10 pts  unclear / not stated   │
│                      │   0 pts  HARD SKIP              │
├──────────────────────┼────────────────────────────────┤
│  Company quality     │  10 pts  FAANG / Tier-1 startup │
│                      │   5 pts  all other companies    │
└──────────────────────┴────────────────────────────────┘

HARD SKIPS (score = 0, never emailed):
  • No/unclear visa sponsorship         • "US citizens only" any phrasing
  • Security clearance required         • 5+ years experience required
  • Staffing / consulting agency        • Fake / misspelled job title
  • Company in dynamic blocklist (105+) • Non-US location
```

**Score colours in email alert:**  🟢 ≥ 90 · 🟠 80–89 · ⬜ 55–79

---

## ATS Resume Matching

For every job that passes scoring, the system simulates what an Applicant Tracking System sees when it parses your resume against the JD.

```
6 tailored resume variants  ×  any job description
            ↓
   Parse JD for "Required" vs "Preferred" skill sections
            ↓
   Required skills × 2 weight  |  Preferred skills × 1 weight
            ↓
   Score each resume: matched_skills / total_weighted_skills
            ↓
   Return: best resume name + ATS % + "keep these" + "add these"
```

**Skill domains covered (100+ keywords):**  
Python · SQL · Scala · TensorFlow · PyTorch · Scikit-learn · XGBoost · Transformers · LangChain · HuggingFace · RAG · Fine-tuning · MLOps · MLflow · Airflow · Spark · Databricks · Snowflake · BigQuery · Redshift · AWS · Azure · GCP · Tableau · Power BI · A/B Testing · Causal Inference · Feature Engineering · Model Deployment · Healthcare · Finance

---

## Cold Outreach System

> Full documentation: [`outreach/README_OUTREACH.md`](outreach/README_OUTREACH.md)

For high-scoring roles, Job Radar can build a personalised outreach queue targeting:
- **Recruiters** at the hiring company (discovered via Apollo.io, ranked by seniority)
- **Alumni connections** — UTD / your university alumni working at the company
- **Local employees** — Dallas-area employees for in-person networking

Every contact is deduplicated across roles and companies so you never message the same person twice. Messages are generated as **Gmail drafts** — you review and send manually. No resume attached (better deliverability); the email offers to share one on request.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.12 · full type hints | Core pipeline |
| **HTTP Client** | [httpx](https://www.python-httpx.org/) | API calls, LinkedIn scrape |
| **HTML Parser** | [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) | LinkedIn job cards, Workday |
| **Database** | SQLite via `sqlite3` | seen_jobs, scored_jobs, contacts |
| **Email — send** | `smtplib` + Gmail SMTP | HTML job alert delivery |
| **Email — fetch** | `imaplib` + Gmail IMAP | LinkedIn / Indeed alert ingestion |
| **Spreadsheet** | [openpyxl](https://openpyxl.readthedocs.io/) | `applications.xlsx` export |
| **AI — resumes** | [Anthropic Claude API](https://docs.anthropic.com/) | Resume rewriting & tailoring |
| **PDF output** | [ReportLab](https://www.reportlab.com/) | Tailored resume PDFs |
| **Web UI** | [Flask](https://flask.palletsprojects.com/) | Resume optimizer interface |
| **Scheduler** | Windows Task Scheduler | 15-min / 2-hour automated runs |
| **Env config** | [python-dotenv](https://pypi.org/project/python-dotenv/) | Credentials isolation |

---

## Project Structure

```
JobRadar/
│
├── main.py                  # Pipeline orchestrator (fetch → score → notify)
├── fetchers.py              # All 7 source integrations (~760 lines)
├── scorer.py                # 100-point scoring engine + blocklist logic
├── database.py              # SQLite schema, UPSERT helpers, Excel sync
├── notifier.py              # HTML email card builder + Gmail SMTP sender
├── resume_scorer.py         # ATS simulation — picks best resume per JD
├── config.py                # TARGET_TITLES, POSITIVE_KEYWORDS, paths, env vars
│
├── outreach/                # Cold outreach subsystem
│   ├── outreach.py          # Orchestrator: discover → queue → draft
│   ├── apollo_api.py        # Apollo.io recruiter discovery
│   ├── classify.py          # Title → recruiter / employee classification
│   ├── templates.py         # Email + LinkedIn message templates
│   ├── email_sender.py      # SMTP sender for outreach emails
│   ├── gmail_draft.py       # Pre-fill Gmail drafts for manual review
│   ├── review.py            # Export outreach_review.xlsx + HTML queue
│   └── README_OUTREACH.md   # Full outreach system documentation
│
├── resume_optimizer/        # AI-powered resume tailoring (optional)
│   ├── optimize.py          # CLI entry point
│   ├── classifier.py        # JD role-type classification
│   ├── rewriter.py          # Claude API resume rewrite
│   └── pdf_writer.py        # ReportLab PDF output
│
├── blocked_companies.json   # Dynamic blocklist — 105+ staffing firms
├── requirements.txt         # Python dependencies
├── .env.example             # Credential template (copy → .env, fill in)
│
├── run_quick.bat            # Task Scheduler trigger: LinkedIn + Gmail (15 min)
├── run_full.bat             # Task Scheduler trigger: all 7 sources (2 hour)
└── make_drafts.bat          # Generate Gmail outreach drafts
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Windows 10/11 (Task Scheduler integration)
- A Gmail account with **App Passwords** enabled

### 1. Clone & Install

```bash
git clone https://github.com/yvandanasrisai/job-radar.git
cd job-radar
pip install -r requirements.txt
```

### 2. Configure Credentials

```bash
copy .env.example .env
# Open .env and fill in your Gmail credentials, score threshold, and profile info
```

> **Gmail App Password:** Google Account → Security → 2-Step Verification → App Passwords → Select "Mail" → Generate

### 3. Run Manually

```bash
# Quick run: LinkedIn + Gmail only (~2 min)
python main.py --quick

# Full run: all 7 sources (~8 min)
python main.py
```

### 4. Add Your Resumes

Place plain-text resume files in the `resumes/` folder:
```
resumes/
├── resume1.txt    # Data Scientist focus
├── resume2.txt    # ML Engineer focus
├── resume3.txt    # AI / GenAI focus
└── ...
```

### 5. Schedule Automation

Once the manual run works, set up Windows Task Scheduler:

```
Quick run  — every 15 minutes  → run_quick.bat
Full run   — every 2 hours     → run_full.bat
```

See the [Scheduler Setup](#automated-scheduling) section below for exact steps.

---

## Automated Scheduling

Job Radar is designed to run unattended via Windows Task Scheduler.

| Task Name | Script | Interval | Sources |
|---|---|---|---|
| `JobRadar-Quick` | `run_quick.bat` | Every 15 min | LinkedIn + Gmail |
| `JobRadar-Full` | `run_full.bat` | Every 2 hours | All 7 sources |

**Setup steps (PowerShell, run as Administrator):**

```powershell
# Quick run — every 15 minutes
$action = New-ScheduledTaskAction -Execute "C:\JobRadar\run_quick.bat"
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 15) -Once -At (Get-Date)
Register-ScheduledTask -TaskName "JobRadar-Quick" -Action $action -Trigger $trigger -RunLevel Highest

# Full run — every 2 hours
$action2 = New-ScheduledTaskAction -Execute "C:\JobRadar\run_full.bat"
$trigger2 = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Hours 2) -Once -At (Get-Date)
Register-ScheduledTask -TaskName "JobRadar-Full" -Action $action2 -Trigger $trigger2 -RunLevel Highest
```

---

## Email Alert Preview

Each job alert email contains **HTML job cards** with:

```
┌──────────────────────────────────────────────────────────────────┐
│  [ 82 ]  Data Scientist                                🔄 Reposted│
│  score   👑 Stripe  ·  Remote, US  ⭐ Texas                       │
├──────────────────────────────────────────────────────────────────┤
│  🟢 Sponsors visa   LinkedIn   ✅ Entry/Assoc   📅 Jun 25 · 2:23 PM│
├──────────────────────────────────────────────────────────────────┤
│  Best Resume: R1-DataScientist   ATS Match: ████░  78%           │
│                                                  [ Apply → ]     │
└──────────────────────────────────────────────────────────────────┘
```

**Score colours:** 🟢 ≥ 90 (green)  ·  🟠 80–89 (orange)  ·  ⬜ 55–79 (grey)  
**Badges shown:** sponsorship status · source platform · Easy Apply / Entry-level flags · Texas proximity · reposted indicator · 👑 for FAANG / tier-1 startups

---

## Environment Variables

| Variable | Required | Description |
|---|:---:|---|
| `ALERT_EMAIL_ADDRESS` | ✅ | Gmail that sends the alert |
| `ALERT_EMAIL_PASSWORD` | ✅ | 16-char Gmail App Password |
| `MY_EMAIL` | ✅ | Your email that receives alerts |
| `SCORE_THRESHOLD` | ✅ | Min score to trigger email (default: `55`) |
| `OUTREACH_EMAIL` | ⬜ | Separate Gmail for cold outreach |
| `OUTREACH_EMAIL_PASSWORD` | ⬜ | App Password for outreach Gmail |
| `APOLLO_API_KEY` | ⬜ | Apollo.io key for recruiter discovery |
| `MY_NAME` | ⬜ | Full name for outreach email signatures |
| `MY_LINKEDIN` | ⬜ | LinkedIn URL for signatures |
| `UTD_SCHOOL_NAME` | ⬜ | University for alumni outreach targeting |

---

## Company Blocklist Logic

Job Radar maintains `blocked_companies.json` — a dynamic blocklist that starts pre-seeded with known staffing firms and **grows automatically** as new ones are detected.

```
Detection methods (applied in order):
  1. LinkedIn industry tag  →  "Staffing and Recruiting" / "IT Services and IT Consulting"
  2. Company name keywords  →  "staffing", "recruiter", "placement agency", "headhunter"
  3. JD description signals →  "our client is looking", "corp-to-corp", "c2c only", "bill rate"

On detection: company is auto-added to blocked_companies.json
On next run: blocked company is silently skipped before scoring
```

Currently blocks **105+ companies** including:
Adecco, Apex Systems, Collabera, Cognizant, Insight Global, Kforce, ManpowerGroup, Mastech, Randstad, Tata Consultancy, TekSystems, and dozens of auto-detected agencies.

---

## Limitations & Notes

- **LinkedIn scraping:** Uses the guest (non-authenticated) API. Rate-limited intentionally — one request every ~0.8 seconds. No login credentials used or stored.
- **Windows-only:** Batch scripts and Task Scheduler are Windows-specific. Core Python pipeline is cross-platform.
- **Gmail App Passwords:** Requires 2FA enabled on the Gmail account. Standard OAuth not used (simpler setup for local automation).
- **Apollo free tier:** 50 credits/month on free plan. Outreach system degrades gracefully when the quota is exhausted.
- **Resume optimizer:** Requires an Anthropic API key and is run on-demand — it is not part of the scheduled pipeline.

---

## Why I Built This

I was applying to Data Science roles during an active job search and kept seeing the same pattern: strong-match jobs posted at 9 AM, 300 applicants by noon, closed in 48 hours. The first-mover advantage in job applications is real — being in the first 50 applicants at a company that uses ATS screening is materially different from being applicant #400.

I built Job Radar to solve this with engineering. It monitors the firehose, filters aggressively, scores rigorously, and only interrupts me for jobs that actually match. The outreach system adds a parallel track: rather than waiting in the ATS queue, it surfaces warm connections at the company to reach out to directly.

This is a fully production system — it has been running 24/7, processing 500–2,000 job postings per run, and sending daily alerts.

---

## Contributing

This project was built for personal use but is open-sourced in case others find it useful. If you adapt it for your own job search:

1. Update `TARGET_TITLES` and `POSITIVE_KEYWORDS` in `config.py` to match your role targets
2. Update `SCORE_THRESHOLD` in `.env` based on alert volume you want
3. Replace the `Greenhouse` / `Lever` / `Ashby` company lists in `fetchers.py` with companies relevant to your industry
4. Add your own resume files to `resumes/`

Pull requests welcome for new job source integrations, improved scoring logic, or platform portability (macOS / Linux scheduling).

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with Python · Powered by curiosity · Refined by necessity**

*Vandana Sri Sai Yedla — [LinkedIn](https://linkedin.com/in/vandana-yedla) · [GitHub](https://github.com/yvandanasrisai)*

</div>
