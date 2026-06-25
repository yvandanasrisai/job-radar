import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"C:\JobRadar\.env")

_SYSTEM = """You are an elite resume optimizer. Transform the base resume into a perfect match for the job description.

MANDATORY RULES — violating any rule makes the output useless:

1. PRESERVE VERBATIM: every company name, job title, employment date, school name, degree, phone, email, LinkedIn URL — copy them character-for-character.

2. DOMAIN INJECTION — detect the hiring company's industry and inject its language into EVERY single bullet:
   • Healthcare/pharma/insurance (Humana, Optum, UHC, CVS, Cigna, Elevance) → "patient data", "clinical outcomes", "EHR/EMR", "claims", "HIPAA-compliant", "care management", "member data"
   • Research roles (Amazon Science, Meta AI, Microsoft Research, Google Brain) → "research rigor", "novel methodology", "peer-reviewed standards", "scientific experimentation", "statistically validated", "publication-quality"
   • E-commerce / marketing tech → "campaign attribution", "ROAS", "customer acquisition", "conversion funnel", "marketing mix", "lifetime value"
   • Fintech / banking → "credit risk", "fraud detection", "regulatory compliance", "AML", "financial modeling", "risk-adjusted returns"
   • Retail / supply chain → "demand forecasting", "inventory optimization", "supply chain", "logistics", "SKU-level"
   • Cloud / SaaS → mirror their exact cloud (AWS vs GCP vs Azure), use "platform reliability", "multi-tenant", "developer experience"

3. EXACT KEYWORD MATCH: copy the JD's exact tool names, buzzwords, and technical terms — never use synonyms.

4. SUMMARY — 3 focused sentences:
   • Sentence 1: years of experience + their domain + their primary keyword
   • Sentence 2: direct technical match — list 4-5 of their exact required tools
   • Sentence 3: business impact phrased in their language

5. SKILLS — reorder categories so JD's primary technologies appear first; keep all existing skills.

6. BULLET STRENGTH — every bullet = strong past-tense verb + technical specifics + quantified outcome. Minimum 4 bullets per role. Never write a weak or vague bullet.

7. PROJECTS — reframe project names and descriptions to match the JD's domain and vocabulary.

8. No invented companies, roles, or time periods.

OUTPUT: valid JSON only — no markdown fences, no explanation, no extra text — starting with {{ and ending with }}.

Schema:
{{
  "title": "exact role title from JD",
  "summary": "3-sentence tailored summary",
  "skills": [{{"category": "Category Name", "items": "skill1, skill2, skill3"}}],
  "experience": [{{"company": "exact", "title": "exact", "dates": "exact", "bullets": ["b1","b2","b3","b4"]}}],
  "projects": [{{"name": "project name", "tech": "tech stack", "bullets": ["b1"]}}],
  "leadership": ["bullet1", "bullet2"],
  "education": [{{"degree": "exact", "dates": "exact", "school": "exact"}}],
  "certifications": "cert1  |  cert2  |  cert3"
}}"""


def rewrite_resume(jd_text: str, resume_text: str) -> dict:
    client = anthropic.Anthropic()

    messages = [{
        "role": "user",
        "content": f"JOB DESCRIPTION:\n{jd_text}\n\n{'=' * 60}\n\nBASE RESUME:\n{resume_text}",
    }]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=_SYSTEM,
        messages=messages,
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # One retry: ask Claude to fix the JSON
        fix_response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=50,
            messages=[
                *messages,
                {"role": "assistant", "content": raw},
                {"role": "user", "content": "The JSON is malformed. Return ONLY the corrected JSON starting with { and ending with }."},
            ],
        )
        return json.loads(fix_response.content[0].text.strip())
