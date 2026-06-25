import os
import sys
import anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"C:\JobRadar\.env")

RESUME_MAP = {
    "data_scientist":            r"C:\JobRadar\resumes\resume1.txt",
    "ml_engineer":               r"C:\JobRadar\resumes\resume2.txt",
    "ai_engineer":               r"C:\JobRadar\resumes\resume3.txt",
    "applied_scientist":         r"C:\JobRadar\resumes\resume4.txt",
    "data_engineer":             r"C:\JobRadar\resumes\resume5.txt",
    "data_analyst":              r"C:\JobRadar\resumes\resume6.txt",
    "healthcare_data_scientist": r"C:\JobRadar\resumes\resume7.txt",
}

WARN_PLACEHOLDER: set = set()  # all resumes now filled in

_PROMPT = """Classify this job description into exactly one category. Reply with ONLY the category name, nothing else.

Categories:
- healthcare_data_scientist : data science role at a healthcare/pharma/insurance/clinical company (Humana, UHC, CVS, Optum, Cigna, etc.)
- applied_scientist         : titled "Applied Scientist" or "Research Scientist", or heavy research/experimentation focus
- ai_engineer               : GenAI, LLM, RAG, NLP engineering, AI platform, model API development
- ml_engineer               : MLOps, model deployment, serving infrastructure, feature stores, production ML pipelines
- data_engineer             : ETL, data pipelines, data platform, warehouse, Spark, Databricks, dbt primary focus
- data_analyst              : BI, reporting, dashboards, SQL analytics, Tableau/Power BI as primary responsibility
- data_scientist            : all other data science / predictive modeling / machine learning roles

JD (first 2000 chars):
{jd}"""


def classify_jd(jd_text: str) -> str:
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ERROR: ANTHROPIC_API_KEY not set in C:\\JobRadar\\.env")

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=20,
        messages=[{"role": "user", "content": _PROMPT.format(jd=jd_text[:2000])}],
    )
    category = response.content[0].text.strip().lower()
    return category if category in RESUME_MAP else "data_scientist"
