import json as _json
import re
from datetime import datetime, timezone

from config import TARGET_TITLES, POSITIVE_KEYWORDS

# ---------------------------------------------------------------------------
# Dynamic company blocklist — grows automatically when LinkedIn industry
# detection flags a new staffing/IT-consulting company.
# ---------------------------------------------------------------------------
_BLOCKED_FILE  = r"C:\JobRadar\blocked_companies.json"
_blocked_cache: dict[str, str] = {}


def load_blocked_companies() -> None:
    """Call once at startup (main.py). Loads JSON file into memory cache."""
    global _blocked_cache
    try:
        with open(_BLOCKED_FILE, encoding="utf-8") as f:
            _blocked_cache = _json.load(f)
    except Exception:
        _blocked_cache = {}


def _is_blocked(company_lower: str) -> bool:
    return bool(company_lower and company_lower in _blocked_cache)


def _auto_block(company: str, reason: str) -> None:
    """Add company to in-memory cache and persist to JSON (silent on error)."""
    name = company.lower().strip()
    if not name or name in _blocked_cache:
        return
    _blocked_cache[name] = reason
    try:
        with open(_BLOCKED_FILE, "w", encoding="utf-8") as f:
            _json.dump(dict(sorted(_blocked_cache.items())), f, indent=2)
    except Exception:
        pass


# LinkedIn industry strings that conclusively identify staffing/consulting firms
_STAFFING_INDUSTRIES = frozenset({
    "staffing and recruiting",
    "it services and it consulting",
    "it staffing and it consulting",
    "human resources services",
    "outsourcing and offshoring consulting",
    "professional employer organizations",
})

# Company name keyword fallback (catches novel agencies not yet in the JSON)
_STAFFING_NAME_KW = (
    "staffing", "recruiting", " recruiter", "headhunter",
    "placement agency", "workforce solutions",
)

# Description-level signals (catches agencies with innocent-looking company names)
_STAFFING_DESC_SIGNALS = (
    "our client is looking", "on behalf of our client",
    "corp to corp", "c2c only", "w2 or c2c", "c2c or w2",
    "corp-to-corp", "bill rate",
)

# ---------------------------------------------------------------------------
# Security clearance filter
# ---------------------------------------------------------------------------
_CLEARANCE_RE = re.compile(
    r'\b(?:'
    r'security\s+clearance|clearance\s+required|clearance\s+is\s+required'
    r'|secret\s+clearance|top\s+secret|ts\s*/\s*sci|ts/sci'
    r'|dod\s+clearance|dod\s+secret|government\s+clearance'
    r'|active\s+clearance|active\s+secret|clearance\s+eligible'
    r'|must\s+hold\s+(?:a\s+)?clearance|requires\s+clearance'
    r'|q\s+clearance|sci\s+access|polygraph'
    r'|public\s+trust\s+clearance|security\s+investigation'
    r')\b',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# YOE filter — skip jobs requiring 5+ years
# ---------------------------------------------------------------------------
_YOE_SKIP_RE = re.compile(
    r'\b(?:'
    r'(?:[5-9]|[1-9]\d)\s*\+\s*(?:years?|yrs?)'
    r'|(?:[5-9]|[1-9]\d)\s+or\s+more\s+(?:years?|yrs?)'
    r'|(?:minimum|at\s+least|min\.?)\s+(?:of\s+)?(?:[5-9]|[1-9]\d)\s+(?:years?|yrs?)'
    r')'
    r'(?:\s+(?:of\s+)?(?:total\s+|professional\s+|relevant\s+|work\s+|'
    r'industry\s+|hands[- ]on\s+)?(?:experience|exp(?:erience)?))?'
    r'\b',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Sponsorship — regex replaces the simple list-based check for better recall
# ---------------------------------------------------------------------------
_SPONS_NO_RE = re.compile(
    r'(?:'
    r'no\s+(?:visa\s+)?sponsorship'
    r'|no\s+(?:immigration|visa)\s+(?:assistance|support)'
    r'|sponsorship\s+(?:is\s+)?(?:not\s+available|unavailable|not\s+offered)'
    r'|visa\s+(?:assistance|sponsorship)\s+(?:will\s+not\s+be\s+provided|is\s+not\s+(?:available|provided))'
    # "does not offer support or sponsorship" / "will not provide sponsorship"
    r'|(?:do(?:es)?\s+not|will\s+not|won.?t|cannot|can.?t|are\s+not\s+able\s+to|unable\s+to)'
    r'\s+(?:offer|provide|support|sponsor)(?:\s+(?:support\s+or\s+)?(?:visa\s+|immigration\s+)?sponsorship)?'
    r'|not\s+able\s+to\s+(?:sponsor|support\s+visa|provide\s+(?:visa|sponsorship))'
    r'|no\s+sponsorship\s+(?:at\s+this\s+time|now\s+or\s+in\s+the\s+future|for\s+this)'
    # work-authorization / right-to-work requirements
    r'|must\s+be\s+(?:authorized|legally\s+authorized|eligible)\s+to\s+work'
    r'|must\s+(?:already\s+)?(?:have|possess)\s+(?:the\s+)?(?:legal\s+)?right\s+to\s+work'
    r'|(?:the\s+)?right\s+to\s+work\s+in\s+the\s+(?:united\s+states|u\.?\s*s)'
    r'|must\s+have\s+(?:existing\s+)?(?:work\s+)?(?:authorization|employment\s+eligibility)'
    r'|without\s+(?:the\s+need\s+for\s+)?(?:visa\s+|immigration\s+)?sponsorship'
    r'|not\s+(?:considering|eligible\s+for)\s+(?:candidates\s+(?:who\s+)?)?(?:require|need|requesting)\s+(?:visa|h-?1b|sponsorship)'
    # citizenship requirements
    r'|must\s+be\s+(?:a\s+|an\s+)?u\.?\s*s\.?\s*\.?\s*citizen'
    r'|u\.?\s*s\.?\s+citizenship\s+(?:is\s+)?required'
    r'|citizenship\s+(?:is\s+)?required'
    r'|ead\s+(?:card\s+)?(?:required|only)'
    r'|us\s+citi(?:zen(?:ship)?|zens?)\s+(?:or\s+(?:green\s+card|permanent\s+resident)\s+)?(?:only|required)'
    r'|green\s+card\s+(?:holders?\s+)?(?:only|required)'
    r'|permanent\s+resident\s+(?:only|required)'
    # "only US/USA citizens" — "only" appears BEFORE the citizenship term
    r'|only\s+(?:usa?|u\.?\s*s\.?)\s+citizens?'
    r'|open\s+(?:only\s+)?to\s+(?:usa?|u\.?\s*s\.?)\s+citizens?'
    r')',
    re.IGNORECASE,
)

_SPONS_YES_RE = re.compile(
    r'\b(?:'
    r'will\s+sponsor'
    r'|sponsorship\s+(?:is\s+)?(?:available|provided|offered|considered)'
    r'|visa\s+sponsorship\s+(?:is\s+)?(?:available|provided|offered)'
    r'|open\s+to\s+sponsorship'
    r'|we\s+(?:do\s+)?sponsor'
    r'|sponsoring\s+(?:h-?1b|visa)'
    r'|can\s+sponsor'
    r'|provide\s+(?:visa|immigration)\s+sponsorship'
    r'|h-?1b\s+(?:visa\s+)?(?:sponsorship|sponsor)'
    r'|eligible\s+for\s+(?:visa|h-?1b)\s+sponsorship'
    r')\b',
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Title / keyword helpers
# ---------------------------------------------------------------------------
_PARTIAL_TITLE_WORDS = {
    "data", "scientist", "machine", "learning", "ai", "analytics",
    "engineer", "nlp", "generative", "llm", "research", "applied",
    "decision", "associate", "quantitative", "forecasting", "predictive",
    "gen ai", "genai", "intelligence", "computer vision", "cv engineer",
    "statistician", "modeler", "modeling", "inference",
}

_ENTRY_SIGNALS = {
    "associate", "junior", "jr.", "entry", "entry-level",
    " i ", " ii ", "new grad", "early career", "mid-level", "mid level",
}

# Seniority signals — these should NOT add weight (user is early-career)
_SENIOR_SIGNALS = {
    "senior", "sr.", "sr ", "staff", "principal", "lead ", " lead",
    "director", "vp ", "vice president", "head of", "manager", "mgr",
}

# Fake/bot-posted titles with obvious misspellings or truncated words
_TITLE_TYPO_RE = re.compile(
    r'\bdata\s+analys\b',  # "Data Analys" — missing "t" (fake/truncated posting)
    re.IGNORECASE,
)

# Recognized quality employers — small bonus (10 vs 5)
_TOP_COMPANIES = {
    "google", "meta", "facebook", "amazon", "apple", "microsoft", "netflix",
    "openai", "anthropic", "nvidia", "stripe", "databricks", "airbnb", "uber",
    "lyft", "linkedin", "salesforce", "adobe", "intuit", "coinbase", "robinhood",
    "pinterest", "snowflake", "palantir", "tesla", "spacex", "doordash",
    "instacart", "plaid", "ramp", "brex", "figma", "notion", "datadog",
    "cloudflare", "twilio", "dropbox", "gitlab", "perplexity", "cohere",
    "scale ai", "hugging face", "jpmorgan", "goldman", "capital one",
    "american express", "visa", "mastercard", "walmart", "target", "disney",
    "spotify", "reddit", "block", "square", "affirm", "chime", "nerdwallet",
    "unitedhealth", "cvs", "humana", "progressive", "geico", "verily",
    "genentech", "moderna", "pfizer", "johnson & johnson",
}

# ---------------------------------------------------------------------------
# Recency scoring — fresher postings get higher priority (user requirement)
# ---------------------------------------------------------------------------
_AGO_RE = re.compile(r'(\d+)\s*(minute|min|hour|hr|day|week|month)', re.IGNORECASE)


def _hours_ago_from_text(text: str | None) -> float | None:
    """Parse LinkedIn relative time text like '23 minutes ago' -> hours."""
    if not text:
        return None
    m = _AGO_RE.search(text)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    if "min" in unit:
        return n / 60.0
    if unit.startswith("h"):
        return float(n)
    if "day" in unit:
        return n * 24.0
    if "week" in unit:
        return n * 168.0
    if "month" in unit:
        return n * 720.0
    return None


def _hours_from_posted_at(s: str | None) -> float | None:
    """Parse an absolute posted_at timestamp string -> hours ago."""
    if not s:
        return None
    clean = re.sub(r'\s*UTC\s*$', '', s.strip(), flags=re.IGNORECASE)
    clean = clean.replace("(scraped)", "").strip()
    now = datetime.now(timezone.utc)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(clean, fmt).replace(tzinfo=timezone.utc)
            return (now - dt).total_seconds() / 3600.0
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).total_seconds() / 3600.0
    except Exception:
        return None


def _recency_score(job: dict) -> tuple[int, float | None, bool]:
    """Returns (score_0_25, hours_ago_or_None, reposted_bool)."""
    hours = _hours_ago_from_text(job.get("posted_ago"))
    if hours is None:
        hours = _hours_from_posted_at(job.get("posted_at"))
    reposted = bool(job.get("reposted"))

    if hours is None:
        base = 12            # unknown date — middling, benefit of doubt
    elif hours < 1:
        base = 25            # < 1 hour — top priority
    elif hours < 2:
        base = 18            # ~1-2 hours
    elif hours < 6:
        base = 12
    elif hours < 24:
        base = 8
    elif hours < 48:
        base = 4
    else:
        base = 2

    if reposted:
        base = min(base, 6)  # reposted jobs are always low priority
    return base, hours, reposted

# ---------------------------------------------------------------------------
# USA detection helpers (used by is_usa_job)
# ---------------------------------------------------------------------------
_NON_US_MARKERS = {
    "india", "bangalore", "mumbai", "hyderabad", "pune", "delhi", "chennai",
    "uk", "united kingdom", "england", "london",
    "germany", "berlin", "munich",
    "france", "paris",
    "spain", "madrid", "barcelona",
    "ireland", "dublin",
    "australia", "melbourne", "sydney",
    "brazil", "sao paulo",
    "canada", "toronto", "vancouver", "montreal",
    "mexico", "mexico city",
    "japan", "tokyo",
    "china", "beijing", "shanghai", "shenzhen",
    "singapore",
    "netherlands", "amsterdam",
    "poland", "warsaw",
    "sweden", "stockholm",
    "denmark", "copenhagen",
    "finland", "helsinki",
    "norway", "oslo",
    "switzerland", "zurich",
    "italy", "rome", "milan",
    "portugal", "lisbon",
    "luxembourg",
    "belgium", "brussels",
    "austria", "vienna",
    "israel", "tel aviv",
    "turkey", "istanbul",
    "south africa", "johannesburg",
    "new zealand", "auckland",
    "argentina", "buenos aires",
    "colombia", "bogota",
    "south korea", "seoul",
    "taiwan", "taipei",
    "hong kong",
    "indonesia", "jakarta",
    "malaysia", "kuala lumpur",
    "philippines", "manila",
    "thailand", "bangkok",
    "vietnam", "hanoi",
    "pakistan", "karachi",
    "dubai", "uae", "abu dhabi",
    "egypt", "cairo",
    "nigeria", "lagos",
    "kenya", "nairobi",
}

_US_MARKERS = {
    "united states", " usa", "u.s.", "us only", "remote - us", "remote-us",
    "remote us", "remote, us", "nationwide", "north america",
    "texas", "dallas", "plano", "austin", "houston", "fort worth",
    "new york", "california", "san francisco", "los angeles", "seattle",
    "chicago", "boston", "atlanta", "denver", "washington, d.c", "washington dc",
    "virginia", "maryland", "florida", "miami", "phoenix", "arizona",
    "illinois", "georgia", "ohio", "pennsylvania", "north carolina",
    "massachusetts", "colorado", "minnesota", "michigan", "oregon",
    " ny", " ca", " tx", " wa", " il", " ga", " fl", " co", " ma",
}


def is_usa_job(job: dict) -> bool:
    """Return True if the job is in the USA or genuinely remote (no country lock)."""
    location    = (job.get("location") or "").lower().strip()
    desc_peek   = (job.get("description") or "")[:300].lower()

    if location and any(m in location for m in _NON_US_MARKERS):
        return False
    if any(m in location for m in _US_MARKERS):
        return True
    if any(m in desc_peek for m in _US_MARKERS):
        return True
    if not location or location in {"remote", "hybrid", "remote, worldwide", "anywhere"}:
        return True
    return True


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------
def score_job(job: dict) -> dict:
    title       = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    company     = (job.get("company") or "").lower()

    _SKIP = lambda notes, yoe="": {
        "score": 0, "sponsorship": "No sponsorship", "sponsorship_label": "No sponsorship",
        "matched_keywords": [], "notes": notes, "yoe_flag": yoe, "reposted": False,
    }

    # ── Dynamic blocklist ────────────────────────────────────────────────────
    if _is_blocked(company):
        return _SKIP("Skipped — blocked company")

    # ── LinkedIn industry auto-block ─────────────────────────────────────────
    industry = (job.get("company_industry") or "").lower()
    if industry in _STAFFING_INDUSTRIES:
        _auto_block(job.get("company", ""), f"Auto: {industry}")
        return _SKIP(f"Skipped — {industry}")

    # ── Company name keyword fallback (catches novel staffing firms) ─────────
    if any(k in company for k in _STAFFING_NAME_KW):
        _auto_block(job.get("company", ""), "name-keyword match")
        return _SKIP("Skipped — staffing/recruiting agency name")

    # ── Description-level agency signals ────────────────────────────────────
    desc_peek = description[:600]
    if any(s in desc_peek for s in _STAFFING_DESC_SIGNALS):
        return _SKIP("Skipped — staffing agency JD signals (c2c/our client)")

    # ── Clearance gate ───────────────────────────────────────────────────────
    if _CLEARANCE_RE.search(description) or _CLEARANCE_RE.search(title):
        return _SKIP("Skipped — security clearance required")

    # ── YOE gate ────────────────────────────────────────────────────────────
    if _YOE_SKIP_RE.search(description):
        return _SKIP("Skipped — JD requires 5+ years experience", yoe="5+skip")

    # ── Title typo / fake posting gate ─────────────────────────────────────
    if _TITLE_TYPO_RE.search(title):
        return _SKIP("Skipped — suspicious title (typo/fake)")

    # ── Sponsorship gate — NO sponsorship = skip (user requires sponsorship) ─
    if _SPONS_NO_RE.search(description):
        return _SKIP("Skipped — no visa sponsorship / citizen-only")
    if _SPONS_YES_RE.search(description):
        sponsorship_score, sponsorship_label = 20, "Sponsors visa"
    else:
        sponsorship_score, sponsorship_label = 10, "Sponsorship unclear"

    # ── Title relevance (25) — seniority does NOT add weight ────────────────
    is_entry  = any(e in f" {title} " for e in _ENTRY_SIGNALS)
    is_senior = any(s in f" {title} " for s in _SENIOR_SIGNALS)
    if any(t in title for t in TARGET_TITLES):
        title_score = 25
    elif any(w in title for w in _PARTIAL_TITLE_WORDS):
        title_score = 15
    else:
        title_score = 0
    if is_senior:
        title_score = max(0, title_score - 15)   # senior/lead/manager penalized
    elif is_entry:
        title_score = min(25, title_score + 3)    # small entry-level boost

    # ── Recency (25) — fresher = higher priority ────────────────────────────
    recency_score, hours_ago, reposted = _recency_score(job)

    # ── Skill keywords (20) ─────────────────────────────────────────────────
    matched_keywords = [kw for kw in POSITIVE_KEYWORDS if kw in description]
    kw_count = len(matched_keywords)
    if kw_count >= 10:
        kw_score = 20
    elif kw_count >= 7:
        kw_score = 15
    elif kw_count >= 4:
        kw_score = 10
    elif kw_count >= 1:
        kw_score = 5
    else:
        kw_score = 0

    # ── Company quality (10) ────────────────────────────────────────────────
    company_score = 10 if any(c in company for c in _TOP_COMPANIES) else 5

    total = title_score + recency_score + kw_score + sponsorship_score + company_score
    total = max(0, min(100, total))

    hrs = f"{hours_ago:.1f}h" if hours_ago is not None else "?"
    notes = (
        f"Title:{title_score} | Recency:{recency_score}({hrs}"
        f"{' REPOSTED' if reposted else ''}) | Skills:{kw_score}({kw_count}) | "
        f"Spons:{sponsorship_score}({sponsorship_label}) | Company:{company_score}"
        + (" [Entry]" if is_entry else "")
        + (" [Senior-penalized]" if is_senior else "")
    )

    return {
        "score":            total,
        "sponsorship":      sponsorship_label,
        "matched_keywords": matched_keywords,
        "notes":            notes,
        "yoe_flag":         "entry" if is_entry else ("senior" if is_senior else ""),
        "reposted":         reposted,
    }
