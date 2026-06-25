import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"C:\JobRadar\.env")

ALERT_EMAIL_ADDRESS = os.getenv("ALERT_EMAIL_ADDRESS", "")
ALERT_EMAIL_PASSWORD = os.getenv("ALERT_EMAIL_PASSWORD", "")
MY_EMAIL = os.getenv("MY_EMAIL", "")
MY_EMAIL_PASSWORD = os.getenv("MY_EMAIL_PASSWORD", "")
SCORE_THRESHOLD = int(os.getenv("SCORE_THRESHOLD", "80"))

# ── Outreach system ────────────────────────────────────────────────────────
OUTREACH_EMAIL          = os.getenv("OUTREACH_EMAIL", "")
OUTREACH_EMAIL_PASSWORD = os.getenv("OUTREACH_EMAIL_PASSWORD", "")
APOLLO_API_KEY          = os.getenv("APOLLO_API_KEY", "")
UTD_SCHOOL_NAME         = os.getenv("UTD_SCHOOL_NAME", "The University of Texas at Dallas")
MY_NAME                 = os.getenv("MY_NAME", "Vandana Sri Sai Yedla")
MY_FIRST_NAME           = os.getenv("MY_FIRST_NAME", "Vandana")
MY_PHONE                = os.getenv("MY_PHONE", "")
MY_LINKEDIN             = os.getenv("MY_LINKEDIN", "")
OUTREACH_MAX_PER_JOB    = int(os.getenv("OUTREACH_MAX_PER_JOB", "12"))
LINKEDIN_PER_COMPANY_CAP = int(os.getenv("LINKEDIN_PER_COMPANY_CAP", "10"))

# FAANG / MAANG + big tech — cast a wider net (huge orgs).
LARGE_COMPANIES = {
    "google", "amazon", "meta", "facebook", "apple", "netflix", "microsoft",
    "coinbase", "nvidia", "salesforce", "uber", "linkedin", "tiktok",
}
LARGE_COMPANY_MAX = int(os.getenv("LARGE_COMPANY_MAX", "20"))

# ---------------------------------------------------------------------------
# TARGET TITLES
# Rule: "data scientist" as substring catches "Data Scientist I", "II",
# "Marketing Data Scientist", "Healthcare Data Scientist", etc. automatically.
# ---------------------------------------------------------------------------
TARGET_TITLES = [
    # ── Core roles (substring match covers "I / II / III / Sr." variants too)
    "data scientist",
    "machine learning engineer",
    "ml engineer",
    "ai engineer",
    "analytics engineer",
    "decision scientist",
    "applied scientist",
    "research scientist",
    "nlp engineer",
    "llm engineer",

    # ── GenAI / modern AI
    "generative ai",
    "gen ai",
    "llm",
    "prompt engineer",
    "ai researcher",

    # ── Explicit entry / associate / junior (highest priority)
    "associate data scientist",
    "associate machine learning",
    "associate ml engineer",
    "associate ai engineer",
    "associate analytics engineer",
    "associate research scientist",
    "junior data scientist",
    "junior machine learning",
    "junior ml engineer",
    "entry level data scientist",
    "entry-level data scientist",
    "data scientist i",
    "data scientist ii",

    # ── Specialty variants that are still mid/entry-friendly
    "marketing data scientist",
    "business data scientist",
    "product data scientist",
    "clinical data scientist",
    "healthcare data scientist",
    "quantitative analyst",
    "quantitative researcher",
    "data science analyst",
    "machine learning analyst",
    "ai analyst",
    "forecasting analyst",
    "predictive analytics",

    # ── Senior titles kept but will be penalised if JD requires 7+ years
    "senior data scientist",
    "senior machine learning engineer",
    "senior ml engineer",
    "senior ai engineer",
    "senior analytics engineer",
    "staff data scientist",
    "staff machine learning engineer",
    "staff ml engineer",
]

POSITIVE_KEYWORDS = [
    "python", "sql", "machine learning", "deep learning", "nlp",
    "llm", "generative ai", "genai", "rag", "mlops", "scikit",
    "tensorflow", "pytorch", "xgboost", "transformers",
    "healthcare", "pharma", "financial services",
    "credit risk", "marketing analytics", "decision science",
    "causal inference", "experimentation", "a/b test", "a/b testing",
    "tableau", "power bi", "spark", "databricks", "snowflake", "aws", "azure",
    "langchain", "hugging face", "mlflow", "sagemaker", "vertex ai",
    "bigquery", "redshift", "feature engineering", "model deployment",
]

SPONSORSHIP_POSITIVE = [
    "will sponsor", "sponsorship available", "h1b", "h-1b",
    "visa sponsorship", "open to sponsorship", "sponsorship considered",
]

SPONSORSHIP_NEGATIVE = [
    "no sponsorship", "must be authorized", "us citizen only",
    "no visa", "citizens only", "permanent resident only", "ead required",
    "will not sponsor", "cannot sponsor", "not able to sponsor",
]

LOCATION_KEYWORDS = [
    "remote", "hybrid", "texas", "dallas", "plano", "austin",
    "houston", "fort worth", "nationwide", "united states",
]

LOG_FILE  = r"C:\JobRadar\run.log"
ERROR_LOG = r"C:\JobRadar\errors.log"
DB_PATH   = r"C:\JobRadar\jobs.db"
EXCEL_PATH = r"C:\JobRadar\applications.xlsx"
