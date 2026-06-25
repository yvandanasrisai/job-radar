import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone

from config import ALERT_EMAIL_ADDRESS, ALERT_EMAIL_PASSWORD, MY_EMAIL, ERROR_LOG
from scorer import _TOP_COMPANIES


def _score_color(score: int) -> str:
    if score >= 90:
        return "#00a651"
    if score >= 80:
        return "#ff8c00"
    return "#555555"


def _score_bg(score: int) -> str:
    if score >= 90:
        return "#e6f9f0"
    if score >= 80:
        return "#fff4e5"
    return "#f3f4f6"


def _spons_badge(label: str) -> str:
    colors = {
        "Sponsors visa":       ("#00a651", "#e6f9f0"),
        "Sponsorship unclear": ("#cc7a00", "#fff4e5"),
        "No sponsorship":      ("#cc0000", "#ffe5e5"),
        # Legacy labels (from older DB rows) — map to same colors
        "Likely yes": ("#00a651", "#e6f9f0"),
        "Unclear":    ("#cc7a00", "#fff4e5"),
        "No":         ("#cc0000", "#ffe5e5"),
    }
    fg, bg = colors.get(label, ("#555", "#eee"))
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 8px;'
        f'border-radius:10px;font-size:11px;font-weight:700;">{label}</span>'
    )


def _source_badge(source: str) -> str:
    colors = {
        "Greenhouse":    ("#166534", "#dcfce7"),
        "Lever":         ("#1e40af", "#dbeafe"),
        "Ashby":         ("#6b21a8", "#f3e8ff"),
        "RemoteOK":      ("#0f766e", "#ccfbf1"),
        "WeWorkRemotely":("#b45309", "#fef3c7"),
        "Jobicy":        ("#7c3aed", "#ede9fe"),
        "RemoteLeaf":    ("#0369a1", "#e0f2fe"),
        "LinkedIn":      ("#0a66c2", "#dbeafe"),
        "Indeed":        ("#2557a7", "#dbeafe"),
        "Workday":       ("#b45309", "#fef3c7"),
    }
    fg, bg = colors.get(source, ("#374151", "#f3f4f6"))
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 7px;'
        f'border-radius:10px;font-size:11px;font-weight:700;">{source}</span>'
    )


def _texas_badge(location: str) -> str:
    loc = location.lower()
    if any(c in loc for c in ["dallas", "plano", "fort worth"]):
        return ' <span style="background:#fef9c3;color:#854d0e;padding:1px 6px;border-radius:8px;font-size:11px;">⭐ DFW</span>'
    if "austin" in loc:
        return ' <span style="background:#fef9c3;color:#854d0e;padding:1px 6px;border-radius:8px;font-size:11px;">⭐ Austin</span>'
    if "houston" in loc:
        return ' <span style="background:#fef9c3;color:#854d0e;padding:1px 6px;border-radius:8px;font-size:11px;">⭐ Houston</span>'
    if "texas" in loc:
        return ' <span style="background:#fef9c3;color:#854d0e;padding:1px 6px;border-radius:8px;font-size:11px;">⭐ Texas</span>'
    return ""


def _ats_bar(ats_score: int | None) -> str:
    if not ats_score:
        return '<span style="color:#9ca3af;font-size:11px;">No JD text available</span>'
    color = "#00a651" if ats_score >= 70 else ("#ff8c00" if ats_score >= 50 else "#cc0000")
    bar_w = max(4, ats_score)
    tip = "≥70% = strong match · 50-69% = add keywords · <50% = wrong resume"
    return (
        f'<div style="display:flex;align-items:center;gap:6px;" title="{tip}">'
        f'<div style="width:80px;height:8px;background:#e5e7eb;border-radius:4px;overflow:hidden;">'
        f'<div style="width:{bar_w}%;height:100%;background:{color};border-radius:4px;"></div></div>'
        f'<span style="font-size:12px;font-weight:700;color:{color};">{ats_score}%</span>'
        f'</div>'
    )


def _format_date(posted_at: str | None) -> str:
    if not posted_at:
        return '<span style="color:#9ca3af;">—</span>'
    clean = posted_at.replace("(scraped)", "").replace(" UTC", "").strip()
    for fmt, has_time in [
        ("%Y-%m-%d %H:%M:%S", True),
        ("%Y-%m-%d %H:%M", True),
        ("%Y-%m-%d", False),
    ]:
        try:
            dt = datetime.strptime(clean, fmt)
            if has_time:
                t = dt.strftime("%I:%M %p")
                if t.startswith("0"):
                    t = t[1:]
                return dt.strftime("%b %d, %Y") + f" · {t}"
            return dt.strftime("%b %d, %Y")
        except Exception:
            continue
    try:
        clean10 = clean[:10]
        dt = datetime.strptime(clean10, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except Exception:
        pass
    return clean[:10] if len(clean) >= 10 else clean


def _build_card(j: dict) -> str:
    score     = j.get("score", 0)
    title     = j.get("title", "")
    company   = j.get("company", "")
    location  = j.get("location", "")
    spons     = j.get("sponsorship", "Unclear")
    source    = j.get("source", "")
    posted_at = j.get("posted_at")
    best_res  = j.get("best_resume") or ""
    ats       = j.get("ats_score") or 0
    easy      = j.get("easy_apply", 0)
    url       = j.get("url", "#")

    sc_color = _score_color(score)
    sc_bg    = _score_bg(score)
    tx_badge = _texas_badge(location)
    easy_tag = (
        '<span style="background:#dbeafe;color:#1d4ed8;padding:1px 7px;'
        'border-radius:8px;font-size:11px;font-weight:700;">⚡ Easy Apply</span> '
        if easy else ""
    )
    yoe_flag = j.get("yoe_flag", "")
    yoe_tag = ""
    if yoe_flag == "entry":
        yoe_tag = '<span style="background:#dcfce7;color:#166534;padding:1px 7px;border-radius:8px;font-size:11px;font-weight:700;">✅ Entry/Assoc</span> '

    reposted = bool(j.get("reposted", 0))
    repost_tag = (
        ' <span style="background:#fef3c7;color:#b45309;padding:1px 6px;'
        'border-radius:8px;font-size:11px;font-weight:700;">🔄 Reposted</span>'
        if reposted else ""
    )
    is_top = any(c in company.lower() for c in _TOP_COMPANIES)
    crown  = "👑 " if is_top else ""

    return f"""
<div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;
            margin-bottom:16px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06);">

  <!-- Top bar: score + title -->
  <div style="display:flex;align-items:stretch;">
    <div style="background:{sc_bg};border-right:3px solid {sc_color};
                padding:16px 14px;text-align:center;min-width:64px;flex-shrink:0;">
      <div style="font-size:26px;font-weight:800;color:{sc_color};line-height:1;">{score}</div>
      <div style="font-size:10px;color:#6b7280;margin-top:2px;">score</div>
    </div>
    <div style="padding:12px 16px;flex:1;">
      <div style="font-size:15px;font-weight:700;color:#111827;line-height:1.3;">{title}{repost_tag}</div>
      <div style="font-size:13px;color:#374151;margin-top:3px;">
        <strong>{crown}{company}</strong>
        &nbsp;·&nbsp;
        <span style="color:#6b7280;">{location}</span>{tx_badge}
      </div>
    </div>
  </div>

  <!-- Meta row -->
  <div style="background:#f9fafb;padding:8px 16px;display:flex;
              flex-wrap:wrap;gap:8px;align-items:center;border-top:1px solid #f3f4f6;">
    {_spons_badge(spons)}
    {_source_badge(source)}
    {easy_tag}{yoe_tag}
    <span style="color:#6b7280;font-size:12px;">📅 {_format_date(posted_at)}</span>
  </div>

  <!-- Resume row -->
  <div style="padding:10px 16px;border-top:1px solid #f3f4f6;
              display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
    <div>
      <span style="font-size:11px;color:#6b7280;text-transform:uppercase;
                   letter-spacing:.5px;font-weight:600;">Best Resume</span><br>
      <span style="font-size:13px;color:#111827;font-weight:600;">
        {best_res if best_res else '<span style="color:#9ca3af;">Add resumes to enable</span>'}
      </span>
    </div>
    <div>
      <span style="font-size:11px;color:#6b7280;text-transform:uppercase;
                   letter-spacing:.5px;font-weight:600;">ATS Match</span><br>
      {_ats_bar(ats)}
    </div>
    <div style="margin-left:auto;">
      <a href="{url}"
         style="background:#1d4ed8;color:#fff;padding:8px 18px;border-radius:8px;
                text-decoration:none;font-size:13px;font-weight:700;display:inline-block;">
        Apply →
      </a>
    </div>
  </div>
</div>"""


def _build_html(jobs: list[dict]) -> str:
    cards = "".join(_build_card(j) for j in jobs)
    now   = datetime.now(timezone.utc).strftime("%b %d, %Y %I:%M %p UTC")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="font-family:'Segoe UI',Arial,sans-serif;background:#f3f4f6;
             margin:0;padding:20px;">
<div style="max-width:700px;margin:0 auto;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1e3a5f,#1d4ed8);
              border-radius:14px 14px 0 0;padding:24px 28px;">
    <h1 style="color:#fff;margin:0;font-size:20px;">🎯 Job Radar — High-Match Alert</h1>
    <p style="color:#bfdbfe;margin:6px 0 0;font-size:13px;">
      <strong style="color:#fff;">{len(jobs)} new job{"s" if len(jobs)!=1 else ""}</strong>
      &nbsp;·&nbsp; USA &amp; Remote only &nbsp;·&nbsp; {now}
    </p>
  </div>

  <!-- Legend -->
  <div style="background:#fff;padding:10px 20px;border-left:1px solid #e5e7eb;
              border-right:1px solid #e5e7eb;font-size:12px;color:#6b7280;
              display:flex;gap:20px;flex-wrap:wrap;align-items:center;">
    <span><span style="color:#00a651;font-weight:700;">■</span> Score ≥ 90</span>
    <span><span style="color:#ff8c00;font-weight:700;">■</span> Score 80–89</span>
    <span>⭐ Texas priority</span>
    <span>⚡ Easy Apply</span>
    <span style="margin-left:auto;background:#f0fdf4;border:1px solid #bbf7d0;
                 padding:3px 10px;border-radius:8px;color:#166534;font-size:11px;">
      <strong>ATS %</strong> = skills from JD found in your resume.
      Target ≥70% before applying.
    </span>
  </div>

  <!-- Job Cards -->
  <div style="background:#f3f4f6;padding:16px 0;">
    {cards}
  </div>

  <!-- Cowork CTA -->
  <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;
              padding:18px 22px;margin-top:4px;">
    <h3 style="margin:0 0 8px;color:#1e40af;font-size:14px;">
      ⚡ How to apply with Cowork (Claude)
    </h3>
    <ol style="margin:0;padding-left:18px;color:#374151;font-size:13px;line-height:1.8;">
      <li>Click <strong>Apply →</strong> on the job above — note the <strong>Best Resume</strong> column</li>
      <li>Open <strong>Claude Code / Cowork</strong> in a new session</li>
      <li>Say: <em>"Optimize Resume [R1/R2/R3...] for this job: [paste URL or JD]"</em></li>
      <li>Claude will tailor keywords, generate a cover letter &amp; recruiter message</li>
      <li>Use the ATS % as your baseline — aim to get it above 75% before applying</li>
    </ol>
  </div>

  <!-- Footer -->
  <div style="text-align:center;padding:16px;color:#9ca3af;font-size:11px;">
    Job Radar · Auto-generated · vandana.jobradar@gmail.com
  </div>
</div>
</body>
</html>"""


def send_job_alert(jobs_list: list[dict]):
    if not jobs_list:
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"\U0001f3af {len(jobs_list)} High-Match Jobs — Job Radar (USA Only)"
    msg["From"]    = ALERT_EMAIL_ADDRESS
    msg["To"]      = MY_EMAIL

    html = _build_html(jobs_list)
    msg.attach(MIMEText(html, "html", "utf-8"))

    # Always save HTML locally — opens in browser even if email fails
    html_path = r"C:\JobRadar\latest_alert.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    pw = ALERT_EMAIL_PASSWORD.replace(" ", "")
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(ALERT_EMAIL_ADDRESS, pw)
            server.sendmail(ALERT_EMAIL_ADDRESS, MY_EMAIL, msg.as_string())
    except Exception as e:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] notifier SMTP failed: {e}\n")
        print(f"[notifier] Email failed ({e}). HTML saved -> {html_path}")
