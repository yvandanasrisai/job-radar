"""
Job Radar — main pipeline.

Two run modes:
  python main.py            → full run (all sources, every 2 h)
  python main.py --quick    → quick run (LinkedIn + Gmail only, every 15 min)

Task Scheduler should have two tasks:
  JobRadar-Quick  every 15 min  → python main.py --quick
  JobRadar-Full   every 2 h     → python main.py
"""
import re as _re
import sys
import traceback
from datetime import datetime, timezone, timedelta

from config import SCORE_THRESHOLD, LOG_FILE
from database import (
    init_db, is_seen, mark_seen, save_scored_job,
    mark_notified, get_unnotified_scored_jobs, rebuild_excel,
)
from fetchers import (
    fetch_greenhouse_jobs, fetch_lever_jobs, fetch_ashby_jobs,
    fetch_rss_jobs, fetch_gmail_jobs,
    fetch_linkedin_jobs, fetch_workday_jobs,
)
from scorer import score_job, is_usa_job, load_blocked_companies
from resume_scorer import best_resume_for_job
from notifier import send_job_alert

_48H = timedelta(hours=48)
_QUICK_MODE = "--quick" in sys.argv


def log(msg: str):
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", errors="replace").decode("ascii"))
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _is_fresh(posted_at: str | None) -> bool:
    """
    Returns True when the job is recent enough to email.
      - No date / "(scraped)" label  → True  (benefit of doubt)
      - API-provided date < 48 h     → True
      - API-provided date >= 48 h    → False
    """
    if not posted_at:
        return True
    if "(scraped)" in posted_at:
        return True

    now   = datetime.now(timezone.utc)
    clean = _re.sub(r"\s*UTC\s*$", "", posted_at.strip(), flags=_re.IGNORECASE).strip()

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(clean, fmt).replace(tzinfo=timezone.utc)
            return (now - dt) < _48H
        except ValueError:
            continue

    try:
        dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt) < _48H
    except Exception:
        pass

    return True   # unparseable → include (benefit of doubt)


def main():
    mode = "QUICK" if _QUICK_MODE else "FULL"
    log(f"=== Job Radar run START ({mode}) ===")
    init_db()
    load_blocked_companies()

    # ── Fetch ─────────────────────────────────────────────────────────────
    all_jobs: list[dict] = []

    if _QUICK_MODE:
        fetchers = [
            ("LinkedIn",    lambda: fetch_linkedin_jobs(quick=True)),
            ("Gmail",       fetch_gmail_jobs),
        ]
    else:
        fetchers = [
            ("Greenhouse",  fetch_greenhouse_jobs),
            ("Lever",       fetch_lever_jobs),
            ("Ashby",       fetch_ashby_jobs),
            ("RSS",         fetch_rss_jobs),
            ("Gmail",       fetch_gmail_jobs),
            ("LinkedIn",    lambda: fetch_linkedin_jobs(quick=False)),
            ("Workday",     fetch_workday_jobs),
        ]

    for name, fetcher in fetchers:
        try:
            jobs = fetcher()
            log(f"{name}: {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception:
            log(f"{name} FAILED: {traceback.format_exc()}")

    log(f"Total fetched: {len(all_jobs)}")

    # ── Process ────────────────────────────────────────────────────────────
    new_count = skipped_intl = skipped_old = skipped_agency = scored_count = 0

    for job in all_jobs:
        job_id = job.get("job_id", "")
        if not job_id:
            continue
        if is_seen(job_id):
            continue

        mark_seen(job_id, job.get("source", ""), job.get("title", ""),
                  job.get("company", ""), job.get("url", ""))
        new_count += 1

        if not is_usa_job(job):
            skipped_intl += 1
            continue

        posted_at = job.get("posted_at")
        if not posted_at:
            posted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d") + " (scraped)"

        if not _is_fresh(posted_at):
            skipped_old += 1
            continue

        try:
            result = score_job(job)
            score  = result["score"]

            if "staffing/recruiting" in result.get("notes", ""):
                skipped_agency += 1
                continue

            if score >= SCORE_THRESHOLD:
                desc = job.get("description") or ""
                easy = 1 if ("easy apply" in desc.lower() or "quick apply" in desc.lower()) else 0

                resume_result = best_resume_for_job(desc)
                best_resume   = resume_result.get("name", "")
                ats_score     = resume_result.get("score", 0)

                save_scored_job(
                    job_id      = job_id,
                    score       = score,
                    title       = job.get("title", ""),
                    company     = job.get("company", ""),
                    url         = job.get("url", ""),
                    location    = job.get("location", ""),
                    sponsorship = result["sponsorship"],
                    source      = job.get("source", ""),
                    posted_at   = posted_at,
                    best_resume = best_resume,
                    ats_score   = ats_score,
                    easy_apply  = easy,
                    yoe_flag    = result.get("yoe_flag", ""),
                    reposted    = int(result.get("reposted", False)),
                )
                scored_count += 1
        except Exception:
            log(f"Error processing {job_id}:\n{traceback.format_exc()}")

    log(
        f"New: {new_count} | Intl: {skipped_intl} | Old: {skipped_old} | "
        f"Agency: {skipped_agency} | Score>={SCORE_THRESHOLD}: {scored_count}"
    )

    # ── Notify ─────────────────────────────────────────────────────────────
    to_notify = get_unnotified_scored_jobs()
    if to_notify:
        try:
            send_job_alert(to_notify)
            for j in to_notify:
                mark_notified(j["job_id"])
            log(f"Alert sent for {len(to_notify)} jobs")
        except Exception:
            log(f"Notification FAILED:\n{traceback.format_exc()}")
    else:
        log("No new high-score jobs to notify")

    try:
        rebuild_excel()
    except Exception:
        log(f"Excel rebuild FAILED:\n{traceback.format_exc()}")

    log("=== Job Radar run COMPLETE ===\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        msg = f"FATAL ERROR:\n{traceback.format_exc()}"
        print(msg, file=sys.stderr)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")
        sys.exit(1)
