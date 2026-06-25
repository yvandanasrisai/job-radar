"""
Professional ATS scorer: mirrors how enterprise ATS systems evaluate resumes.

How it works:
  1. Parse the JD into a "Required" section and a "Preferred/Nice-to-have" section.
  2. Identify skill keywords present in each section from a 100+ skill list.
  3. Required skills count 2× toward the total; preferred count 1×.
  4. Match those skills against each of the 6 base resumes.
  5. ATS % = weighted matches / weighted total × 100
  6. Return the best-matching resume, score, what to keep, and what to add.

Skill categories covered: Core ML/DS, GenAI/LLM, MLOps, Cloud/Data, BI,
Domain knowledge, Statistics/Methods — so it works for DS, MLE, DA, DE, AI.

Resume files: C:/JobRadar/resumes/
  resume1.txt  → R1 · Data Scientist
  resume2.txt  → R2 · ML Engineer
  resume3.txt  → R3 · AI/GenAI Engineer
  resume4.txt  → R4 · Research Scientist
  resume5.txt  → R5 · Data Engineer
  resume6.txt  → R6 · Data Analyst
"""

import os
import re

RESUME_DIR = r"C:\JobRadar\resumes"

RESUME_MAP = {
    "resume1.txt": "R1 · Data Scientist",
    "resume2.txt": "R2 · ML Engineer",
    "resume3.txt": "R3 · AI/GenAI Engineer",
    "resume4.txt": "R4 · Research Scientist",
    "resume5.txt": "R5 · Data Engineer",
    "resume6.txt": "R6 · Data Analyst",
}

# ---------------------------------------------------------------------------
# Skills dictionary — grouped by category.
# Each tuple is (keyword_to_match, display_name).
# We match using `keyword in text` (substring), so shorter terms must be
# specific enough to avoid false positives.
# ---------------------------------------------------------------------------
_SKILLS: list[tuple[str, str]] = [
    # ── Core Programming ────────────────────────────────────────────────────
    ("python",          "Python"),
    ("sql",             "SQL"),
    ("scala",           "Scala"),
    ("java ",           "Java"),
    ("r programming",   "R"),
    ("julia",           "Julia"),
    ("bash",            "Bash/Shell"),

    # ── ML / Statistics ─────────────────────────────────────────────────────
    ("machine learning","Machine Learning"),
    ("deep learning",   "Deep Learning"),
    ("scikit-learn",    "Scikit-learn"),
    ("scikit",          "Scikit-learn"),
    ("xgboost",         "XGBoost"),
    ("lightgbm",        "LightGBM"),
    ("catboost",        "CatBoost"),
    ("pytorch",         "PyTorch"),
    ("tensorflow",      "TensorFlow"),
    ("keras",           "Keras"),
    ("jax",             "JAX"),
    ("statistics",      "Statistics"),
    ("statistical modeling", "Statistical Modeling"),
    ("regression",      "Regression"),
    ("classification",  "Classification"),
    ("clustering",      "Clustering"),
    ("time series",     "Time Series"),
    ("forecasting",     "Forecasting"),
    ("bayesian",        "Bayesian"),
    ("a/b testing",     "A/B Testing"),
    ("a/b test",        "A/B Testing"),
    ("hypothesis testing","Hypothesis Testing"),
    ("causal inference","Causal Inference"),
    ("experimentation", "Experimentation"),
    ("feature engineering","Feature Engineering"),
    ("model deployment","Model Deployment"),
    ("optimization",    "Optimization"),
    ("shap",            "SHAP/Explainability"),
    ("explainability",  "Explainability"),
    ("propensity",      "Propensity Modeling"),
    ("segmentation",    "Segmentation"),

    # ── NLP ─────────────────────────────────────────────────────────────────
    ("nlp",             "NLP"),
    ("natural language","NLP"),
    ("text mining",     "Text Mining"),
    ("sentiment",       "Sentiment Analysis"),
    ("named entity",    "NER"),
    ("transformers",    "Transformers"),
    ("bert",            "BERT"),
    ("spacy",           "spaCy"),

    # ── GenAI / LLM ─────────────────────────────────────────────────────────
    ("llm",             "LLM"),
    ("large language model","LLM"),
    ("generative ai",   "Generative AI"),
    ("genai",           "GenAI"),
    ("rag",             "RAG"),
    ("langchain",       "LangChain"),
    ("langgraph",       "LangGraph"),
    ("hugging face",    "Hugging Face"),
    ("gpt",             "GPT"),
    ("gemini",          "Gemini"),
    ("llama",           "LLaMA"),
    ("mistral",         "Mistral"),
    ("prompt engineering","Prompt Engineering"),
    ("embeddings",      "Embeddings"),
    ("vector search",   "Vector Search"),
    ("semantic search", "Semantic Search"),
    ("faiss",           "FAISS"),
    ("chromadb",        "ChromaDB"),
    ("pinecone",        "Pinecone"),
    ("weaviate",        "Weaviate"),
    ("multi-agent",     "Multi-agent"),
    ("agentic",         "Agentic AI"),
    ("fine-tuning",     "Fine-tuning"),
    ("fine tuning",     "Fine-tuning"),

    # ── MLOps / Engineering ─────────────────────────────────────────────────
    ("mlops",           "MLOps"),
    ("mlflow",          "MLflow"),
    ("airflow",         "Apache Airflow"),
    ("kubeflow",        "Kubeflow"),
    ("prefect",         "Prefect"),
    ("docker",          "Docker"),
    ("kubernetes",      "Kubernetes"),
    ("k8s",             "Kubernetes"),
    ("ci/cd",           "CI/CD"),
    ("fastapi",         "FastAPI"),
    ("flask",           "Flask"),
    ("streamlit",       "Streamlit"),
    ("rest api",        "REST API"),
    ("sagemaker",       "AWS SageMaker"),
    ("vertex ai",       "Vertex AI"),
    ("azure ml",        "Azure ML"),
    ("bentoml",         "BentoML"),

    # ── Cloud / Big Data ────────────────────────────────────────────────────
    ("aws",             "AWS"),
    ("gcp",             "GCP"),
    ("azure",           "Azure"),
    ("spark",           "Apache Spark"),
    ("pyspark",         "PySpark"),
    ("kafka",           "Kafka"),
    ("databricks",      "Databricks"),
    ("snowflake",       "Snowflake"),
    ("bigquery",        "BigQuery"),
    ("redshift",        "Redshift"),
    ("dbt",             "dbt"),
    ("etl",             "ETL"),
    ("data pipeline",   "Data Pipelines"),
    ("data warehouse",  "Data Warehouse"),
    ("s3",              "AWS S3"),
    ("hadoop",          "Hadoop"),
    ("hive",            "Hive"),

    # ── BI / Visualization ───────────────────────────────────────────────────
    ("tableau",         "Tableau"),
    ("power bi",        "Power BI"),
    ("looker",          "Looker"),
    ("quicksight",      "QuickSight"),
    ("matplotlib",      "Matplotlib"),
    ("seaborn",         "Seaborn"),
    ("plotly",          "Plotly"),

    # ── Domain Knowledge ─────────────────────────────────────────────────────
    ("healthcare",      "Healthcare"),
    ("clinical",        "Clinical"),
    ("pharma",          "Pharma"),
    ("biotech",         "Biotech"),
    ("fintech",         "Fintech"),
    ("credit risk",     "Credit Risk"),
    ("fraud detection", "Fraud Detection"),
    ("marketing analytics","Marketing Analytics"),
    ("recommendation",  "Recommendation Systems"),
    ("computer vision", "Computer Vision"),
    ("decision science","Decision Science"),
]

# Markers that indicate a "Required" section in the JD
_REQ_MARKERS = re.compile(
    r"(?:^|\n)\s*(?:"
    r"required|requirements?|must\s+have|must-have|"
    r"essential|minimum\s+qualifications?|basic\s+qualifications?|"
    r"what\s+you(?:'ll|'d|\s+will)\s+need|you\s+(?:must|need|have)"
    r")",
    re.IGNORECASE | re.MULTILINE,
)

# Markers that indicate a "Preferred/Nice-to-have" section
_PREF_MARKERS = re.compile(
    r"(?:^|\n)\s*(?:"
    r"preferred|nice\s+to\s+have|nice-to-have|bonus|plus|"
    r"desired|ideal|would\s+be\s+(?:a\s+)?(?:great\s+)?(?:plus|bonus)|"
    r"additional|extra\s+credit|not\s+required\s+but"
    r")",
    re.IGNORECASE | re.MULTILINE,
)


def _split_jd_sections(jd: str) -> tuple[str, str]:
    """
    Split JD into (required_text, preferred_text).
    Falls back to treating the whole JD as "required" if no sections found.
    """
    jd_lower = jd.lower()

    req_m   = _REQ_MARKERS.search(jd_lower)
    pref_m  = _PREF_MARKERS.search(jd_lower)

    if req_m and pref_m:
        req_start  = req_m.start()
        pref_start = pref_m.start()
        if req_start < pref_start:
            return jd_lower[req_start:pref_start], jd_lower[pref_start:]
        else:
            # Preferred section appears first (unusual but handle it)
            return jd_lower[req_start:], jd_lower[pref_start:req_start]
    elif req_m:
        return jd_lower[req_m.start():], ""
    elif pref_m:
        return jd_lower, jd_lower[pref_m.start():]  # whole JD + preferred section
    else:
        return jd_lower, ""  # treat everything as required


def _load_resumes() -> dict[str, str]:
    """Returns {display_name: lowercased_text}. Skips placeholder/empty files."""
    loaded: dict[str, str] = {}
    for filename, display_name in RESUME_MAP.items():
        path = os.path.join(RESUME_DIR, filename)
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read().strip()
            if content and not content.upper().startswith("PASTE"):
                loaded[display_name] = content.lower()
        except Exception:
            pass
    return loaded


def best_resume_for_job(job_description: str) -> dict:
    """
    Professional ATS match: required skills count 2×, preferred 1×.

    Returns:
      name        — best matching resume display name
      score       — 0-100 weighted ATS %
      req_score   — % of REQUIRED skills found
      pref_score  — % of PREFERRED skills found
      matched     — top 8 matched skills
      missing     — top 6 missing REQUIRED skills (highest priority to add)
    """
    resumes = _load_resumes()
    if not resumes:
        return {
            "name": "Add resumes to C:\\JobRadar\\resumes\\",
            "score": 0, "req_score": 0, "pref_score": 0,
            "matched": [], "missing": [],
        }

    required_text, preferred_text = _split_jd_sections(job_description)

    def _unique_skills(text: str, exclude_labels: set[str] | None = None) -> list[tuple[str, str]]:
        """Return (keyword, label) pairs found in text, deduped by label."""
        seen_labels: set[str] = set(exclude_labels or [])
        result: list[tuple[str, str]] = []
        for kw, label in _SKILLS:
            if kw in text and label not in seen_labels:
                seen_labels.add(label)
                result.append((kw, label))
        return result

    # Skills found in required / preferred sections
    req_skills  = _unique_skills(required_text)
    req_labels  = {lbl for _, lbl in req_skills}
    pref_skills = _unique_skills(preferred_text, exclude_labels=req_labels)

    if not req_skills and not pref_skills:
        # Fallback: whole JD (no sections detected)
        jd_lower   = job_description.lower()
        req_skills  = _unique_skills(jd_lower)
        pref_skills = []

    if not req_skills and not pref_skills:
        return {"name": "—", "score": 0, "req_score": 0, "pref_score": 0,
                "matched": [], "missing": []}

    # Weight: required = 2, preferred = 1
    total_weight = len(req_skills) * 2 + len(pref_skills) * 1
    if total_weight == 0:
        return {"name": "—", "score": 0, "req_score": 0, "pref_score": 0,
                "matched": [], "missing": []}

    best: dict = {"name": "", "score": -1, "req_score": 0, "pref_score": 0,
                  "matched": [], "missing": []}

    for display_name, resume_text in resumes.items():
        matched_req  = [(kw, lbl) for kw, lbl in req_skills  if kw in resume_text]
        matched_pref = [(kw, lbl) for kw, lbl in pref_skills if kw in resume_text]
        missing_req  = [(kw, lbl) for kw, lbl in req_skills  if kw not in resume_text]

        weighted_match = len(matched_req) * 2 + len(matched_pref) * 1
        score = int(weighted_match / total_weight * 100)

        req_score  = int(len(matched_req)  / max(len(req_skills),  1) * 100)
        pref_score = int(len(matched_pref) / max(len(pref_skills), 1) * 100)

        if score > best["score"]:
            all_matched = [lbl for _, lbl in matched_req] + [lbl for _, lbl in matched_pref]
            best = {
                "name":       display_name,
                "score":      score,
                "req_score":  req_score,
                "pref_score": pref_score,
                "matched":    all_matched[:8],
                "missing":    [lbl for _, lbl in missing_req][:6],
            }

    return best
