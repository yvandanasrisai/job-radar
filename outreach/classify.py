"""
Classify a person by job title into an outreach bucket.

  'recruiter' → someone who screens/hires → formal cold email about the role
  'employee'  → works there, not a recruiter → potential referral source

Whether an employee is treated as 'alum' or 'local' is decided by the
discovery layer (is_utd_alum flag / office city), not here.
"""

_RECRUITER_TERMS = [
    "recruiter", "recruiting", "recruitment", "talent acquisition",
    "talent partner", "talent sourcer", "sourcer", "ta partner",
    "people operations", "people ops", "hr business partner", "hrbp",
    "university recruiter", "technical recruiter", "tech recruiter",
    "staffing", "head of talent", "talent lead",
]

# Seniority hint — used only to prioritise (senior recruiters first).
_SENIOR_TERMS = [
    "senior", "sr.", "sr ", "lead", "principal", "head", "director",
    "manager", "vp", "vice president", "chief",
]


def is_recruiter(title: str) -> bool:
    t = (title or "").lower()
    return any(term in t for term in _RECRUITER_TERMS)


def classify(title: str) -> str:
    """Return 'recruiter' or 'employee'."""
    return "recruiter" if is_recruiter(title) else "employee"


def seniority_rank(title: str) -> int:
    """Higher = more senior. Used to sort recruiters so we spend Apollo email
    credits on senior people first."""
    t = (title or "").lower()
    rank = 0
    for i, term in enumerate(_SENIOR_TERMS):
        if term in t:
            rank = max(rank, len(_SENIOR_TERMS) - i)
    return rank


if __name__ == "__main__":
    samples = [
        "Senior Technical Recruiter", "Talent Acquisition Partner",
        "Data Scientist", "Engineering Manager", "University Recruiter",
        "Head of Talent", "Software Engineer", "Sourcer",
    ]
    for s in samples:
        print(f"{s:35} -> {classify(s):10} (seniority {seniority_rank(s)})")
