"""
OPTIONAL Apollo REST fast-path for people discovery.

Only used if APOLLO_API_KEY is set in .env. On the free tier the People SEARCH
endpoint usually works but EMAIL reveal is gated/credit-limited — so emails that
come back may be locked placeholders. Treat this as a way to pre-populate the
candidate LIST; reveal real emails in the Apollo web UI (browser-driven).

Returns people in the people.json schema used by outreach.py.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import APOLLO_API_KEY

API_URL = "https://api.apollo.io/api/v1/mixed_people/search"

RECRUITER_TITLES = [
    "recruiter", "technical recruiter", "senior recruiter",
    "talent acquisition", "talent acquisition partner", "recruiting manager",
    "university recruiter", "sourcer", "head of talent",
]


def _locked(email: str | None) -> bool:
    return (not email) or ("not_unlocked" in email) or ("domain.com" in (email or ""))


def search_recruiters(company: str, max_people: int = 8) -> list[dict]:
    """USA recruiters at `company`. Requires APOLLO_API_KEY. Never raises."""
    if not APOLLO_API_KEY:
        return []
    try:
        import requests
    except ImportError:
        print("apollo_api: `requests` not installed (pip install requests)")
        return []

    payload = {
        "q_organization_name": company,
        "person_titles": RECRUITER_TITLES,
        "person_locations": ["United States"],
        "page": 1,
        "per_page": max_people,
    }
    headers = {"Content-Type": "application/json",
               "Cache-Control": "no-cache",
               "x-api-key": APOLLO_API_KEY}
    try:
        r = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"apollo_api: search failed ({e})")
        return []

    out = []
    for p in data.get("people", []):
        email = p.get("email")
        out.append({
            "full_name": p.get("name", ""),
            "first_name": p.get("first_name", ""),
            "title": p.get("title", ""),
            "email": "" if _locked(email) else email,
            "linkedin_url": p.get("linkedin_url", "") or "",
            "is_utd_alum": 0,
            "office_city": (p.get("city") or ""),
            "source": "apollo",
        })
    return out


if __name__ == "__main__":
    import json
    company = sys.argv[1] if len(sys.argv) > 1 else "Stripe"
    people = search_recruiters(company)
    print(f"{len(people)} recruiters found at {company} (key set: {bool(APOLLO_API_KEY)})")
    print(json.dumps(people, indent=2))
