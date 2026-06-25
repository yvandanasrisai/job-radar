"""
Resume CONTENT helper (not an attachment).

Given a role title, pick the best-fit resume text file in C:\\JobRadar\\resumes\\
and extract 2-3 role-relevant, quantified highlights. These build the
`{relevant_para}` used in the cold-outreach email so the message demonstrates
fit instead of attaching a PDF (which hurts cold-email deliverability).
"""
import os
import re

RESUME_DIR = r"C:\JobRadar\resumes"

# Role keyword -> resume file. First match wins; order = priority.
ROLE_RESUME_MAP = [
    (("ai engineer", "genai", "gen ai", "generative", "llm", "nlp", "prompt"), "resume3.txt"),
    (("ml engineer", "machine learning engineer", "mlops"),                    "resume2.txt"),
    (("research scientist", "applied scientist"),                              "resume4.txt"),
    (("data engineer", "etl", "pipeline"),                                     "resume5.txt"),
    (("data analyst", "analytics analyst", "bi analyst", "business analyst"),  "resume6.txt"),
    (("data scientist", "decision scientist", "quantitative"),                 "resume1.txt"),
]
DEFAULT_RESUME = "resume1.txt"

# Themes that make a bullet "relevant" to a role family.
ROLE_THEMES = {
    "ai":        ["llm", "rag", "langchain", "genai", "generative", "nlp", "agent", "gpt", "gemini", "prompt", "vector"],
    "ml":        ["model", "ml", "xgboost", "pytorch", "scoring", "mlflow", "deploy", "pipeline", "feature"],
    "scientist": ["model", "propensity", "segmentation", "causal", "experiment", "statistical", "forecast", "shap", "predictive"],
    "engineer":  ["pipeline", "etl", "spark", "snowflake", "deploy", "api", "ci/cd", "redshift", "databricks"],
    "analyst":   ["dashboard", "power bi", "tableau", "quicksight", "sql", "insight", "report", "kpi", "analytics"],
}

_METRIC_RE = re.compile(r"(\d+%|\$\d|\d+x|\bR²|\b\d{3,}|\b\d+\.\d+)")


def pick_resume(role: str) -> str:
    r = (role or "").lower()
    for keys, fname in ROLE_RESUME_MAP:
        if any(k in r for k in keys):
            return fname
    return DEFAULT_RESUME


def _theme_keys(role: str) -> list[str]:
    r = (role or "").lower()
    keys: list[str] = []
    if any(k in r for k in ("ai", "genai", "llm", "nlp", "generative")):
        keys += ROLE_THEMES["ai"]
    if any(k in r for k in ("ml engineer", "machine learning")):
        keys += ROLE_THEMES["ml"]
    if any(k in r for k in ("scientist", "quantitative")):
        keys += ROLE_THEMES["scientist"]
    if any(k in r for k in ("engineer", "etl", "pipeline", "data engineer")):
        keys += ROLE_THEMES["engineer"]
    if any(k in r for k in ("analyst", "analytics", "bi ")):
        keys += ROLE_THEMES["analyst"]
    # Fallback: a sensible default for generic DS roles.
    return keys or ROLE_THEMES["scientist"]


def _read_bullets(fname: str) -> list[str]:
    path = os.path.join(RESUME_DIR, fname)
    if not os.path.exists(path):
        path = os.path.join(RESUME_DIR, DEFAULT_RESUME)
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    bullets = []
    for ln in lines:
        s = ln.strip().lstrip("•").lstrip("-").strip()
        if len(s) > 50 and (ln.strip().startswith("•") or ln.strip().startswith("-")):
            bullets.append(s)
    return bullets


def extract_highlights(role: str, n: int = 3) -> list[str]:
    """Top-n quantified, role-relevant bullets from the best-fit resume."""
    bullets = _read_bullets(pick_resume(role))
    keys = _theme_keys(role)

    def score(b: str) -> int:
        bl = b.lower()
        kw = sum(1 for k in keys if k in bl)
        metric = 2 if _METRIC_RE.search(b) else 0
        return kw * 2 + metric

    ranked = sorted(bullets, key=score, reverse=True)
    return ranked[:n]


def _clean(bullet: str) -> str:
    """Normalise whitespace and drop a trailing period."""
    return re.sub(r"\s+", " ", bullet).strip().rstrip(".")


def _clause(bullet: str, limit: int = 110) -> str:
    """Trim a bullet to its first clause (at a comma/semicolon) for short notes,
    keeping it readable rather than cutting mid-word."""
    b = _clean(bullet)
    if len(b) <= limit:
        return b
    # Prefer a natural break before the limit.
    window = b[:limit]
    for sep in (";", ","):
        if sep in window:
            return window[:window.rfind(sep)].strip()
    return window[:window.rfind(" ")].strip()


def build_relevant_para(role: str) -> str:
    """A tight paragraph of role-relevant work for the email body. Uses the top
    1-2 FULL quantified bullets so the metrics (the strongest part) are kept."""
    hi = extract_highlights(role, n=3)
    if not hi:
        return ("my background building and deploying production machine-learning "
                "and analytics solutions across financial services and healthcare")
    clauses = [_clean(hi[0])]
    # Add a second bullet only if the combined length stays email-friendly.
    if len(hi) > 1 and len(clauses[0]) + len(_clean(hi[1])) <= 430:
        clauses.append(_clean(hi[1]))
    return ". ".join(clauses)


def linkedin_relevant_phrase(role: str) -> str:
    """One short clause for the 300-char LinkedIn note."""
    hi = extract_highlights(role, n=1)
    return _clause(hi[0], 90) if hi else "production ML & analytics work"


def build_brief_para(role: str) -> str:
    """A short, warm, LOW-METRIC project phrase that fits 'most recently I {brief}'.
    Drops parenthetical tech-lists and trailing numbers so it reads human, not like
    a stats dump. Used in the less-formal email bodies."""
    hi = extract_highlights(role, n=3)
    if not hi:
        return "built and deployed machine-learning models to solve real business problems"
    b = _clean(hi[0])
    b = re.sub(r"\s*\([^)]*\)", "", b)        # drop "(XGBoost, K-Means, ...)"
    b = b.split(",")[0].strip()                # drop the metric tail after first comma
    return b[0].lower() + b[1:] if b else "worked on production ML systems"


if __name__ == "__main__":
    for role in ["Data Scientist", "AI Engineer", "Machine Learning Engineer",
                 "Data Analyst", "Data Engineer"]:
        print(f"\n=== {role}  ->  {pick_resume(role)}")
        print("PARA:", build_relevant_para(role))
        print("LI  :", linkedin_relevant_phrase(role))
