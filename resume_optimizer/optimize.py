#!/usr/bin/env python3
"""
Resume Optimizer — CLI
  python optimize.py                          # interactive paste mode
  python optimize.py --file jd.txt            # from file
  python optimize.py --jd "full JD text"      # inline string
  python optimize.py --file jd.txt --company "Amazon"
"""
import sys
import os
import argparse
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv(dotenv_path=r"C:\JobRadar\.env")

from classifier import classify_jd, RESUME_MAP, WARN_PLACEHOLDER
from rewriter import rewrite_resume
from pdf_writer import write_pdf

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def _read_jd(args) -> str:
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if args.jd:
        return args.jd
    print("Paste the full job description. Type END on its own line when done:")
    print("-" * 60)
    lines = []
    try:
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines)


def run(jd_text: str, company: str = "") -> str:
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ERROR: Add  ANTHROPIC_API_KEY=sk-ant-...  to C:\\JobRadar\\.env")

    t0 = time.time()

    print("  [1/3] Classifying JD ...", end=" ", flush=True)
    category = classify_jd(jd_text)

    if category in WARN_PLACEHOLDER:
        print(f"\n  WARNING: '{category}' resume is still a placeholder (resume5.txt).")
        print("  Falling back to data_scientist.\n")
        category = "data_scientist"

    print(f"→ {category}")

    resume_text = Path(RESUME_MAP[category]).read_text(encoding="utf-8")

    print("  [2/3] Rewriting with Sonnet ...", end=" ", flush=True)
    data = rewrite_resume(jd_text, resume_text)
    print("done")

    slug = (company or category).replace(" ", "_").lower()[:30]
    filename = f"tailored_{slug}_{int(time.time())}.pdf"
    out_path  = OUTPUT_DIR / filename

    print("  [3/3] Generating PDF ...", end=" ", flush=True)
    write_pdf(data, str(out_path))
    elapsed = round(time.time() - t0, 1)
    print("done")
    print(f"\n  Saved → {out_path}  ({elapsed}s)\n")
    return str(out_path)


def main():
    ap = argparse.ArgumentParser(description="Tailor a resume to a job description")
    ap.add_argument("--jd",      help="Job description text (inline)")
    ap.add_argument("--file",    help="Path to a .txt file containing the JD")
    ap.add_argument("--company", default="", help="Company name (used in output filename)")
    args = ap.parse_args()

    jd = _read_jd(args)
    if not jd.strip():
        sys.exit("No job description provided.")
    run(jd, args.company)


if __name__ == "__main__":
    main()
