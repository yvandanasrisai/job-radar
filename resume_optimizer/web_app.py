"""
Resume Optimizer Web UI — phone-friendly
  python resume_optimizer/web_app.py
Then on your phone browser: http://<laptop-ip>:5050
(laptop and phone must be on the same WiFi)
"""
import os
import sys
import time
import socket
from pathlib import Path
from flask import Flask, request, send_file, render_template_string

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv(dotenv_path=r"C:\JobRadar\.env")

from classifier import classify_jd, RESUME_MAP, WARN_PLACEHOLDER
from rewriter import rewrite_resume
from pdf_writer import write_pdf

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<meta charset="UTF-8">
<title>Resume Optimizer</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;padding:14px;min-height:100vh}
.card{background:#fff;border-radius:12px;padding:18px;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.1)}
h1{font-size:20px;color:#1a1a2e;margin-bottom:3px}
.sub{font-size:12px;color:#888;margin-bottom:14px}
label{display:block;font-size:12px;font-weight:700;color:#555;margin-bottom:5px;text-transform:uppercase;letter-spacing:.4px}
input[type=text]{width:100%;padding:10px 12px;border:1.5px solid #ddd;border-radius:8px;font-size:15px;margin-bottom:12px;outline:none}
input[type=text]:focus{border-color:#2d4a8a}
textarea{width:100%;height:250px;padding:10px 12px;border:1.5px solid #ddd;border-radius:8px;font-size:14px;line-height:1.5;resize:vertical;outline:none;font-family:inherit}
textarea:focus{border-color:#2d4a8a}
.btn{display:block;width:100%;padding:14px;background:#2d4a8a;color:#fff;border:none;border-radius:8px;font-size:16px;font-weight:700;cursor:pointer;margin-top:12px;text-align:center;text-decoration:none}
.btn:active{background:#1e3a7a}
.btn.green{background:#27ae60}
.btn.green:active{background:#219a52}
.result{border-left:4px solid #27ae60}
.error-card{border-left:4px solid #e74c3c}
.badge{display:inline-block;background:#e8f0fe;color:#2d4a8a;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:700;margin-bottom:8px;text-transform:uppercase;letter-spacing:.5px}
p{font-size:14px;color:#444;line-height:1.5;margin-bottom:6px}
.timer{font-size:12px;color:#888}
</style>
</head>
<body>

{% if result %}
<div class="card result">
  <div class="badge">{{ result.category }}</div>
  <p>Resume optimized successfully</p>
  <p class="timer">Generated in {{ result.elapsed }}s</p>
  <a class="btn green" href="/download/{{ result.filename }}">Download PDF Resume</a>
</div>
{% endif %}

{% if error %}
<div class="card error-card">
  <p><b>Error:</b> {{ error }}</p>
</div>
{% endif %}

<div class="card">
  <h1>Resume Optimizer</h1>
  <p class="sub">Paste any job description → get a tailored PDF in ~15s</p>
  <form method="POST">
    <label>Company Name (optional)</label>
    <input type="text" name="company" placeholder="e.g. Amazon, Humana, Google" value="{{ company or '' }}">
    <label>Job Description</label>
    <textarea name="jd" placeholder="Paste the full job description here...">{{ jd or '' }}</textarea>
    <button class="btn" type="submit">Optimize Resume</button>
  </form>
</div>

</body>
</html>"""


@app.route("/", methods=["GET", "POST"])
def index():
    result = error = jd = company = None

    if request.method == "POST":
        jd      = request.form.get("jd", "").strip()
        company = request.form.get("company", "").strip()

        if not jd:
            error = "Please paste a job description."
        elif not os.getenv("ANTHROPIC_API_KEY"):
            error = "ANTHROPIC_API_KEY not set in C:\\JobRadar\\.env — add it and restart."
        else:
            try:
                t0       = time.time()
                category = classify_jd(jd)
                if category in WARN_PLACEHOLDER:
                    category = "data_scientist"

                resume_text = Path(RESUME_MAP[category]).read_text(encoding="utf-8")
                data        = rewrite_resume(jd, resume_text)

                slug     = (company or category).replace(" ", "_").lower()[:30]
                filename = f"tailored_{slug}_{int(time.time())}.pdf"
                write_pdf(data, str(OUTPUT_DIR / filename))

                result = {
                    "category": category,
                    "elapsed":  round(time.time() - t0, 1),
                    "filename": filename,
                }
                jd = company = ""
            except Exception as exc:
                error = str(exc)

    return render_template_string(_HTML, result=result, error=error, jd=jd, company=company)


@app.route("/download/<filename>")
def download(filename):
    path = OUTPUT_DIR / filename
    if not path.exists():
        return "File not found", 404
    return send_file(str(path), as_attachment=True, download_name=filename)


def _local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


if __name__ == "__main__":
    ip = _local_ip()
    print("\n  Resume Optimizer — Web UI")
    print(f"  Laptop : http://localhost:5050")
    print(f"  Phone  : http://{ip}:5050   (same WiFi required)\n")
    app.run(host="0.0.0.0", port=5050, debug=False)
