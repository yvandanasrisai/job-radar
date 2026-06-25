"""
Called by Claude Code directly — takes a JSON file path and produces a PDF.
Usage: python make_pdf.py path/to/data.json output/filename.pdf
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pdf_writer import write_pdf

if len(sys.argv) < 3:
    sys.exit("Usage: python make_pdf.py <data.json> <output.pdf>")

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out  = write_pdf(data, sys.argv[2])
print(f"PDF saved: {out}")
