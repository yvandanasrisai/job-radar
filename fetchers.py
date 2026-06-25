import hashlib
import imaplib
import email as email_lib
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

import httpx

from config import ALERT_EMAIL_ADDRESS, ALERT_EMAIL_PASSWORD, ERROR_LOG


def _log_error(source: str, err):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {source}: {err}\n")


def _get(url: str, timeout: int = 15, headers: dict | None = None) -> httpx.Response | None:
    try:
        h = {"User-Agent": "Mozilla/5.0 JobRadar/1.0"}
        if headers:
            h.update(headers)
        r = httpx.get(url, timeout=timeout, follow_redirects=True, headers=h)
        r.raise_for_status()
        return r
    except Exception as e:
        _log_error("_get", f"{url} -> {e}")
        return None


def _post(url: str, payload: dict, timeout: int = 15) -> httpx.Response | None:
    try:
        r = httpx.post(
            url, json=payload, timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 JobRadar/1.0",
                "Content-Type": "application/json",
            }
        )
        r.raise_for_status()
        return r
    except Exception as e:
        _log_error("_post", f"{url} -> {e}")
        return None


def _hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:16]


def _parse_lever_ts(ms: int | None) -> str | None:
    """Convert Lever's Unix-ms timestamp to ISO date string."""
    if not ms:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return None


def _parse_rss_date(date_str: str | None) -> str | None:
    """Parse RSS pubDate into a readable string."""
    if not date_str:
        return None
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
    ):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            continue
    return date_str[:16] if date_str else None


# ---------------------------------------------------------------------------
# 1. Greenhouse
# ---------------------------------------------------------------------------
GREENHOUSE_COMPANIES = [
    "airbnb", "twilio", "dropbox", "gitlab", "cloudflare",
    "datadog", "databricks", "fivetran", "mixpanel", "brex", "carta", "gusto",
    "hashicorp", "segment", "plaid", "rippling",
    "palantir", "sas",
    "genentech", "biogen", "illumina", "veeva",
    "hologic", "iqvia", "labcorp", "questdiagnostics",
    "nerdwallet", "chime", "betterment", "robinhoodmarkets", "coinbase",
    "deloitte", "accenture",
]


def fetch_greenhouse_jobs() -> list[dict]:
    results = []
    for company in GREENHOUSE_COMPANIES:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"
        resp = _get(url)
        if resp is None:
            continue
        try:
            data = resp.json()
            for job in data.get("jobs", []):
                loc = job.get("location") or {}
                # Greenhouse returns updated_at in ISO format
                posted_at = job.get("updated_at") or job.get("created_at")
                if posted_at:
                    try:
                        dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
                        posted_at = dt.strftime("%Y-%m-%d %H:%M UTC")
                    except Exception:
                        posted_at = posted_at[:16]
                results.append({
                    "job_id": f"gh_{company}_{job['id']}",
                    "title": job.get("title", ""),
                    "company": company.title(),
                    "url": job.get("absolute_url", ""),
                    "location": loc.get("name", "") if isinstance(loc, dict) else str(loc),
                    "description": job.get("content", ""),
                    "source": "Greenhouse",
                    "posted_at": posted_at,
                })
        except Exception as e:
            _log_error("fetch_greenhouse_jobs", f"{company}: {e}")
    return results


# ---------------------------------------------------------------------------
# 2. Lever
# ---------------------------------------------------------------------------
LEVER_COMPANIES = [
    "palantir", "shieldai", "veeva", "ro",
    "anduril", "nerdwallet", "samsara", "lattice", "faire", "affirm",
    "duolingo", "amplitude", "elastic", "benchling", "recursion",
    "ziprecruiter", "experian", "fico", "leidos", "maximus",
]


def fetch_lever_jobs() -> list[dict]:
    results = []
    for company in LEVER_COMPANIES:
        url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        resp = _get(url)
        if resp is None:
            continue
        try:
            postings = resp.json()
            if not isinstance(postings, list):
                continue
            for p in postings:
                cats = p.get("categories") or {}
                results.append({
                    "job_id": f"lv_{company}_{p['id']}",
                    "title": p.get("text", ""),
                    "company": company.title(),
                    "url": p.get("hostedUrl", ""),
                    "location": cats.get("location", ""),
                    "description": p.get("descriptionPlain", ""),
                    "source": "Lever",
                    "posted_at": _parse_lever_ts(p.get("createdAt")),
                })
        except Exception as e:
            _log_error("fetch_lever_jobs", f"{company}: {e}")
    return results


# ---------------------------------------------------------------------------
# 3. Ashby
# ---------------------------------------------------------------------------
ASHBY_COMPANIES = [
    "OpenAI", "Anthropic", "Cohere", "Scale-AI", "Databricks",
    "HuggingFace", "Mistral", "TogetherAI", "Modal", "Perplexity",
    "Character", "Airbyte", "Hightouch", "Nerdwallet", "Compound",
]


def fetch_ashby_jobs() -> list[dict]:
    results = []
    for company in ASHBY_COMPANIES:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
        resp = _get(url)
        if resp is None:
            continue
        try:
            jobs = resp.json().get("jobs") or []
            for job in jobs:
                loc = job.get("location") or job.get("locationName") or ""
                if job.get("isRemote"):
                    loc = f"Remote — {loc}".strip(" —")
                # Ashby provides publishedAt in ISO format
                posted_raw = job.get("publishedAt") or job.get("updatedAt")
                posted_at = None
                if posted_raw:
                    try:
                        dt = datetime.fromisoformat(posted_raw.replace("Z", "+00:00"))
                        posted_at = dt.strftime("%Y-%m-%d %H:%M UTC")
                    except Exception:
                        posted_at = posted_raw[:16]
                results.append({
                    "job_id": f"ashby_{company}_{job['id']}",
                    "title": job.get("title", ""),
                    "company": company,
                    "url": job.get("applyUrl") or f"https://jobs.ashbyhq.com/{company}/{job['id']}",
                    "location": loc,
                    "description": job.get("descriptionHtml") or job.get("description") or job.get("title", ""),
                    "source": "Ashby",
                    "posted_at": posted_at,
                })
        except Exception as e:
            _log_error("fetch_ashby_jobs", f"{company}: {e}")
    return results


# ---------------------------------------------------------------------------
# 4. RSS
# ---------------------------------------------------------------------------
RSS_FEEDS = [
    ("https://remoteok.com/remote-data-scientist-jobs.json",        "RemoteOK"),
    ("https://weworkremotely.com/categories/remote-data-science-jobs.rss",      "WeWorkRemotely"),
    ("https://weworkremotely.com/categories/remote-machine-learning-jobs.rss",  "WeWorkRemotely"),
    ("https://jobicy.com/?feed=job_feed&job_categories=data-science&job_types=full-time",   "Jobicy"),
    ("https://jobicy.com/?feed=job_feed&job_categories=machine-learning&job_types=full-time", "Jobicy"),
    ("https://remoteleaf.com/feed/", "RemoteLeaf"),
]


def fetch_rss_jobs() -> list[dict]:
    results = []
    for feed_url, feed_name in RSS_FEEDS:
        resp = _get(feed_url)
        if resp is None:
            continue
        ct = resp.headers.get("content-type", "")
        try:
            if "json" in ct or feed_url.endswith(".json"):
                items = resp.json()
                if isinstance(items, list):
                    for job in items:
                        if not isinstance(job, dict):
                            continue
                        link = job.get("url") or job.get("apply_url") or ""
                        if not link:
                            continue
                        # RemoteOK "date" is a Unix timestamp
                        posted_at = None
                        if job.get("date"):
                            try:
                                posted_at = datetime.fromtimestamp(
                                    int(job["date"]), tz=timezone.utc
                                ).strftime("%Y-%m-%d")
                            except Exception:
                                pass
                        results.append({
                            "job_id": f"rss_{_hash(link)}",
                            "title": job.get("position") or job.get("title") or "",
                            "company": job.get("company") or "",
                            "url": link,
                            "location": "Remote",
                            "description": job.get("description") or str(job.get("tags") or ""),
                            "source": feed_name,
                            "posted_at": posted_at,
                        })
            else:
                root = ET.fromstring(resp.text)
                channel = root.find("channel") or root
                for item in channel.findall("item"):
                    title_el  = item.find("title")
                    link_el   = item.find("link")
                    desc_el   = item.find("description")
                    date_el   = item.find("pubDate")
                    title = title_el.text if title_el is not None else ""
                    link  = link_el.text  if link_el  is not None else ""
                    desc  = desc_el.text  if desc_el  is not None else ""
                    pub   = date_el.text  if date_el  is not None else None
                    if not link:
                        continue
                    results.append({
                        "job_id": f"rss_{_hash(link)}",
                        "title": title,
                        "company": "",
                        "url": link,
                        "location": "",
                        "description": desc,
                        "source": feed_name,
                        "posted_at": _parse_rss_date(pub),
                    })
        except Exception as e:
            _log_error("fetch_rss_jobs", f"{feed_url}: {e}")
    return results


# ---------------------------------------------------------------------------
# 5. LinkedIn (guest search API — no login required)
# We use f_TPR=r900 (last 15 min) for the quick scheduler run.
# For each matching-title job we fetch the full description from the job page
# so keyword scoring works properly. Rate-limited to avoid blocks.
# Note: LinkedIn's ToS prohibits scraping; this is best-effort.
# ---------------------------------------------------------------------------
LINKEDIN_KEYWORDS = [
    "data scientist", "machine learning engineer", "data analyst",
    "ai engineer", "data engineer", "nlp engineer", "llm engineer",
    "generative ai engineer", "applied scientist",
]
LINKEDIN_GEO_ID    = "103644278"   # United States
LINKEDIN_TIME_15M  = "r900"        # last 15 min (quick runs)
LINKEDIN_TIME_1H   = "r3600"       # last hour   (full runs)

# Title must contain at least one of these to bother fetching the full JD
_LI_RELEVANT_WORDS = {
    "data", "scientist", "ml", "ai", "machine learning", "analyst",
    "engineer", "llm", "nlp", "analytics", "learning", "research",
    "intelligence", "generative", "gen ai", "genai", "deep learning",
    "applied", "quantitative", "forecasting", "decision", "computer vision",
}

# LinkedIn company industry strings that conclusively identify staffing firms.
# Kept in sync with scorer._STAFFING_INDUSTRIES.
_STAFFING_INDUSTRIES = frozenset({
    "staffing and recruiting",
    "it services and it consulting",
    "it staffing and it consulting",
    "human resources services",
    "outsourcing and offshoring consulting",
    "professional employer organizations",
})


# Sidebar/recommendation sections list OTHER companies and their industries —
# must be cut off before scanning, or we mis-flag the hiring company.
_LI_SIDEBAR_MARKERS = (
    "people also viewed", "similar searches", "more jobs",
    "jobs you may be interested", "similar jobs", "set alert",
    "recommended for you", "people you may know",
)


def _detect_company_industry(soup) -> str:
    """Scan ONLY the top portion of the LinkedIn job page (before the
    'People also viewed' sidebar) for the hiring company's industry.
    Returns the matched staffing-industry string or ''."""
    text = soup.get_text(separator="\n", strip=True).lower()
    cut = len(text)
    for m in _LI_SIDEBAR_MARKERS:
        i = text.find(m)
        if i != -1:
            cut = min(cut, i)
    text = text[:cut]
    for ind in _STAFFING_INDUSTRIES:
        if ind in text:
            return ind
    return ""


_LI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _li_relevant_title(title: str) -> bool:
    tl = title.lower()
    return any(w in tl for w in _LI_RELEVANT_WORDS)


def _fetch_linkedin_description(job_url: str) -> tuple[str, str]:
    """
    Fetches JD and company industry from a LinkedIn job page.
    Returns (description_text, company_industry).
    company_industry is a staffing-industry string or '' if not a staffing firm.
    """
    import json as _json
    import time
    time.sleep(0.8)   # gentle rate limit
    resp = _get(job_url, timeout=20, headers=_LI_HEADERS)
    if resp is None:
        return ("", "")
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")

        desc = ""
        # Primary: JSON-LD embedded in page (most reliable)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = _json.loads(script.string or "")
                if isinstance(data, dict) and "JobPosting" in str(data.get("@type", "")):
                    desc = (data.get("description") or "")[:5000]
                    break
            except Exception:
                pass

        # Fallback: description HTML section
        if not desc:
            for cls in ("show-more-less-html__markup", "description__text",
                        "job-description__content"):
                el = soup.find(class_=lambda c: c and cls in c)
                if el:
                    desc = el.get_text(separator=" ", strip=True)[:5000]
                    break

        industry = _detect_company_industry(soup)
        return (desc, industry)
    except Exception:
        pass
    return ("", "")


def fetch_linkedin_jobs(quick: bool = False) -> list[dict]:
    """
    Always uses r3600 (last hour) to avoid missing jobs posted between scheduler
    intervals. The seen_jobs dedup in main.py prevents re-processing.
    quick param kept for API compatibility but no longer changes the time window.
    """
    from bs4 import BeautifulSoup
    from urllib.parse import quote_plus

    time_window = LINKEDIN_TIME_1H   # always last hour; dedup prevents doubles
    results:   list[dict] = []
    seen_urls: set[str]   = set()

    for keyword in LINKEDIN_KEYWORDS:
        url = (
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            f"?keywords={quote_plus(keyword)}"
            f"&geoId={LINKEDIN_GEO_ID}"
            f"&f_TPR={time_window}"
            f"&start=0&count=25"
        )
        resp = _get(url, timeout=20, headers=_LI_HEADERS)
        if resp is None:
            continue

        try:
            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.find_all("li"):
                try:
                    title_el   = card.find(class_="base-search-card__title")
                    company_el = card.find(class_="base-search-card__subtitle")
                    loc_el     = card.find(class_="job-search-card__location")
                    link_el    = card.find("a", class_=lambda c: c and "full-link" in c)
                    date_el    = card.find("time")

                    if not title_el or not link_el:
                        continue

                    job_url = (link_el.get("href") or "").split("?")[0].strip()
                    if not job_url or job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    title     = title_el.get_text(strip=True)
                    posted_at = date_el.get("datetime") if date_el else None
                    # Relative time text ("23 minutes ago") gives sub-hour recency
                    posted_ago = date_el.get_text(strip=True) if date_el else ""
                    card_txt   = card.get_text(" ", strip=True).lower()
                    reposted   = "reposted" in card_txt

                    results.append({
                        "job_id":    f"li_{_hash(job_url)}",
                        "title":     title,
                        "company":   company_el.get_text(strip=True) if company_el else "",
                        "url":       job_url,
                        "location":  loc_el.get_text(strip=True) if loc_el else "",
                        "description": "",   # filled below for relevant titles
                        "source":    "LinkedIn",
                        "posted_at": posted_at,
                        "posted_ago": posted_ago,
                        "reposted":  reposted,
                    })
                except Exception:
                    continue
        except Exception as e:
            _log_error("fetch_linkedin_jobs", f"{keyword}: {e}")

    # Fetch full descriptions + company industry for relevant titles (max 30 per run)
    fetched_desc = 0
    for job in results:
        if fetched_desc >= 30:
            break
        if _li_relevant_title(job["title"]) and not job["description"]:
            desc, industry = _fetch_linkedin_description(job["url"])
            if desc:
                job["description"] = desc
                fetched_desc += 1
            if industry:
                job["company_industry"] = industry

    return results


# ---------------------------------------------------------------------------
# 6. Workday (company-specific POST API — publicly accessible, no auth)
# Add/remove companies in the WORKDAY_COMPANIES list.
# Format: (tenant_id, wd_version, job_site_name, display_name)
# ---------------------------------------------------------------------------
WORKDAY_COMPANIES = [
    # Healthcare / Insurance
    ("humana",          "wd5", "Humana",       "Humana"),
    ("progressive",     "wd1", "Progressive",  "Progressive"),
    ("travelers",       "wd5", "External",     "Travelers"),
    ("usaa",            "wd1", "USAA",         "USAA"),
    ("cigna",           "wd5", "External",     "Cigna"),
    # Finance / Tech
    ("schwab",          "wd5", "Schwab",       "Charles Schwab"),
    ("td",              "wd5", "TD_Bank",      "TD Bank"),
    ("gartner",         "wd5", "Gartner",      "Gartner"),
    # Retail / Enterprise
    ("target",          "wd5", "Target",       "Target"),
    ("ge",              "wd5", "External",     "GE"),
]

WORKDAY_SEARCH_TERMS = [
    "data scientist", "machine learning", "data analyst", "ai engineer",
]


def _parse_workday_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    # Sometimes "Posted X Days Ago"
    if "posted" in date_str.lower():
        return None  # relative — freshness filter will include it (no date = benefit of doubt)
    # Sometimes ISO: "2024-06-15T00:00:00.000Z"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return date_str[:10] if len(date_str) >= 10 else None


def fetch_workday_jobs() -> list[dict]:
    results:   list[dict] = []
    seen_urls: set[str]   = set()

    for tenant, wd_ver, site, display in WORKDAY_COMPANIES:
        base_url  = f"https://{tenant}.{wd_ver}.myworkdayjobs.com"
        api_url   = f"{base_url}/wday/cxs/{tenant}/{site}/jobs"
        job_base  = f"{base_url}/{site}"

        for term in WORKDAY_SEARCH_TERMS:
            resp = _post(api_url, {
                "limit": 20, "offset": 0,
                "searchText": term,
                "appliedFacets": {},
            })
            if resp is None:
                continue
            try:
                data = resp.json()
                for job in data.get("jobPostings", []):
                    ext_path = job.get("externalPath", "")
                    job_url  = f"{job_base}{ext_path}" if ext_path else ""
                    if not job_url or job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    # Workday sometimes returns bulletFields with JD snippets
                    bullet = " ".join(job.get("bulletFields") or [])
                    desc   = (job.get("jobDescription") or bullet or "").strip()

                    results.append({
                        "job_id":    f"wd_{tenant}_{_hash(job_url)}",
                        "title":     job.get("title", ""),
                        "company":   display,
                        "url":       job_url,
                        "location":  job.get("locationsText", ""),
                        "description": desc,
                        "source":    "Workday",
                        "posted_at": _parse_workday_date(job.get("postedOn")),
                    })
            except Exception as e:
                _log_error("fetch_workday_jobs", f"{display}/{term}: {e}")

    return results


# ---------------------------------------------------------------------------
# 7. Gmail / IMAP
# Searches last 3 days (not just UNSEEN) so emails the user already opened
# are still processed. Seen_jobs dedup in main.py prevents re-emailing.
# ---------------------------------------------------------------------------

# LinkedIn job alert emails come from jobalerts-noreply, NOT jobs-noreply
JOB_EMAIL_SENDERS = [
    "jobalerts-noreply@linkedin.com",  # LinkedIn Job Alerts (user-created alerts)
    "jobs-noreply@linkedin.com",       # LinkedIn recommended jobs
    "jobalerts@indeed.com",            # Indeed job alerts
    "emailjobs@indeed.com",            # Indeed digest emails
]

# LinkedIn job view URL in email — includes /comm/ redirect variant
_LI_EMAIL_JOB_RE = re.compile(
    r'https?://(?:www\.)?linkedin\.com/(?:comm/)?jobs/view/(\d+)',
    re.IGNORECASE,
)
# Indeed job key extracted from viewjob or redirect URLs
_INDEED_JOB_RE = re.compile(
    r'https?://(?:www\.)?indeed\.com/(?:viewjob|rc/clk)[^"<>\s]*[?&]jk=([a-f0-9]+)',
    re.IGNORECASE,
)


def _fetch_linkedin_job_data(job_id: str) -> dict | None:
    """
    Fetches title, company, location, description, and company_industry
    for a LinkedIn job by ID. Uses JSON-LD; no login required.
    """
    import json as _json
    import time
    url = f"https://www.linkedin.com/jobs/view/{job_id}"
    time.sleep(0.8)
    resp = _get(url, timeout=20, headers=_LI_HEADERS)
    if resp is None:
        return None
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = _json.loads(script.string or "")
                if not isinstance(data, dict):
                    continue
                if "JobPosting" not in str(data.get("@type", "")):
                    continue
                loc_data = data.get("jobLocation") or {}
                if isinstance(loc_data, list):
                    loc_data = loc_data[0] if loc_data else {}
                addr  = (loc_data.get("address") or {}) if isinstance(loc_data, dict) else {}
                city  = addr.get("addressLocality", "")
                state = addr.get("addressRegion", "")
                loc   = f"{city}, {state}".strip(", ") if (city or state) else ""
                org   = data.get("hiringOrganization") or {}
                return {
                    "title":            data.get("title", ""),
                    "company":          org.get("name", "") if isinstance(org, dict) else "",
                    "location":         loc,
                    "description":      (data.get("description") or "")[:5000],
                    "posted_at":        data.get("datePosted"),
                    "company_industry": _detect_company_industry(soup),
                }
            except Exception:
                pass
    except Exception:
        pass
    return None


def fetch_gmail_jobs() -> list[dict]:
    results: list[dict] = []
    seen_ids: set[str]  = set()
    password = ALERT_EMAIL_PASSWORD.replace(" ", "")
    # Search last 7 days so that emails the user already opened are still caught
    since_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%d-%b-%Y")

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(ALERT_EMAIL_ADDRESS, password)
        mail.select("inbox")

        for sender in JOB_EMAIL_SENDERS:
            try:
                status, msg_ids = mail.search(
                    None, f'(FROM "{sender}" SINCE {since_date})'
                )
                if status != "OK":
                    continue
                ids = msg_ids[0].split()

                for mid in ids:
                    try:
                        _, data = mail.fetch(mid, "(RFC822)")
                        raw = data[0][1]
                        msg = email_lib.message_from_bytes(raw)

                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() in ("text/plain", "text/html"):
                                    try:
                                        body += part.get_payload(decode=True).decode(errors="replace")
                                    except Exception:
                                        pass
                        else:
                            try:
                                body = msg.get_payload(decode=True).decode(errors="replace")
                            except Exception:
                                pass

                        email_date = msg.get("Date")
                        posted_at  = _parse_rss_date(email_date) if email_date else None
                        is_li      = "linkedin" in sender.lower()
                        is_indeed  = "indeed"   in sender.lower()

                        if is_li:
                            # Extract LinkedIn job IDs → fetch full details from job page
                            li_ids = list(dict.fromkeys(_LI_EMAIL_JOB_RE.findall(body)))
                            for job_id_str in li_ids[:15]:
                                if job_id_str in seen_ids:
                                    continue
                                seen_ids.add(job_id_str)
                                job_url  = f"https://www.linkedin.com/jobs/view/{job_id_str}"
                                job_data = _fetch_linkedin_job_data(job_id_str)
                                if job_data:
                                    results.append({
                                        "job_id":           f"li_{_hash(job_url)}",
                                        "title":            job_data["title"],
                                        "company":          job_data["company"],
                                        "url":              job_url,
                                        "location":         job_data["location"],
                                        "description":      job_data["description"],
                                        "company_industry": job_data.get("company_industry", ""),
                                        "source":           "LinkedIn",
                                        "posted_at":        job_data.get("posted_at") or posted_at,
                                    })
                                else:
                                    # Fallback: save URL with email subject as title
                                    results.append({
                                        "job_id":      f"li_{_hash(job_url)}",
                                        "title":       msg.get("Subject", ""),
                                        "company":     "",
                                        "url":         job_url,
                                        "location":    "",
                                        "description": "",
                                        "source":      "LinkedIn",
                                        "posted_at":   posted_at,
                                    })

                        elif is_indeed:
                            # Extract Indeed job keys → canonical viewjob URLs
                            indeed_keys = list(dict.fromkeys(_INDEED_JOB_RE.findall(body)))
                            for jk in indeed_keys[:15]:
                                if jk in seen_ids:
                                    continue
                                seen_ids.add(jk)
                                job_url = f"https://www.indeed.com/viewjob?jk={jk}"
                                results.append({
                                    "job_id":      f"email_{_hash(job_url)}",
                                    "title":       msg.get("Subject", ""),
                                    "company":     "",
                                    "url":         job_url,
                                    "location":    "",
                                    "description": body[:3000],
                                    "source":      "Indeed",
                                    "posted_at":   posted_at,
                                })

                    except Exception as e:
                        _log_error("fetch_gmail_jobs.msg", f"{sender} mid={mid}: {e}")

            except Exception as e:
                _log_error("fetch_gmail_jobs.sender", f"{sender}: {e}")

        mail.logout()
    except imaplib.IMAP4.error as e:
        _log_error("fetch_gmail_jobs", f"Auth failed: {e}")
    except Exception as e:
        _log_error("fetch_gmail_jobs", str(e))

    return results
