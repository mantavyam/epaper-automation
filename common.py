#!/usr/bin/env python3
"""Shared helpers for the extraction script."""

import os
import re
import json
import glob
import shutil
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

logger = logging.getLogger(__name__)

HISTORY_FILE = "download_history.json"
ARTIFACTS_DIR = "artifacts"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
STALE_ARTIFACT_DAYS = 7

IST = ZoneInfo("Asia/Kolkata")


def now_ist():
    """Current wall-clock time in IST, timezone-aware.

    GitHub Actions runners default to UTC -- using this everywhere "today"
    is established (not plain datetime.now()) keeps artifact dates, history
    keys, and site post dates consistent with the IST-framed cron schedule,
    regardless of which timezone the host machine is actually in.
    """
    return datetime.now(IST)

# owner/repo -- GitHub Actions sets this automatically; falls back to the
# known repo slug for local runs.
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "mantavyam/epaper-automation")


def raw_url(repo_relative_path):
    """Build a raw.githubusercontent.com URL for a file committed to main.

    Used to link the Jekyll site to artifacts without duplicating them into
    the site source -- when the 7-day cleanup deletes the file, this link
    404s, which is what the site's expiry handling detects.
    """
    return f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/main/{repo_relative_path}"

# Paper name -> short code used in artifact filenames, e.g. TH-EDITORIAL-14-08-26.pdf
PAPER_CODES = {
    "The Hindu": "TH",
    "Indian Express": "IE",
}


def dated_filename(paper_name, doc_type, today, ext, part=None):
    """Build a filename like TH-EDITORIAL-14-08-26.pdf or TH-ART1-14-08-26.png.

    doc_type: e.g. "EDITORIAL", "ART", "FULL"
    part: appended directly after doc_type with no separator (ART + 1 -> "ART1")
    """
    code = PAPER_CODES.get(paper_name, paper_name.upper().replace(" ", ""))
    label = f"{doc_type}{part}" if part is not None else doc_type
    date_str = today.strftime("%d-%m-%y")
    return f"{code}-{label}-{date_str}.{ext}"


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Invalid history file, starting fresh")
    return {}


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def already_processed(history, date_key, month_key, paper_name):
    return (
        month_key in history
        and date_key in history[month_key]
        and paper_name in history[month_key][date_key]
    )


def record_history(history, date_key, month_key, paper_name, entry):
    history.setdefault(month_key, {}).setdefault(date_key, {})[paper_name] = entry
    save_history(history)


SKIP_STREAK_LIMIT = 3
SKIP_STREAK_WINDOW = 21


def consecutive_skips(history, paper_name, today, source,
                      window=SKIP_STREAK_WINDOW):
    """Count back-to-back 'skipped_not_published' days before today.

    A skip on its own is normal -- neither paper runs an editorial every
    single day, and the pattern is irregular (Sunday 23-08-2026 published;
    the Sundays either side of it didn't). What is *not* normal is a run of
    them: the longest genuine streak on record is one day. So a streak is
    the tell that our page locator broke rather than that the paper took a
    day off -- exactly how the preppyq paywall hid for six straight green
    runs, recording 'skipped_not_published' while downloading a Razorpay
    payment page.

    Two deliberate choices in the walk:

      - Days with no entry at all are stepped over, not treated as the end
        of the streak. The workflow doesn't run every day (dispatch-only
        gaps are all over the history), and a gap says nothing either way.
      - An entry from a *different* source ends the walk. A streak is
        evidence about one source's locator, so switching sources resets
        it -- without this, the first indiags run would inherit the dead
        preppyq source's six-day streak and cry wolf immediately.
    """
    streak = 0
    for back in range(1, window + 1):
        day = (today.date() - timedelta(days=back))
        entry = (
            history.get(day.strftime("%m-%Y"), {})
            .get(day.strftime("%Y-%m-%d"), {})
            .get(paper_name)
        )
        if entry is None:
            continue  # workflow didn't run that day -- no evidence either way
        if entry.get("source") != source:
            break  # different source: its streak isn't evidence about ours
        if entry.get("status") != "skipped_not_published":
            break
        streak += 1
    return streak


REPORT_FILE = "failure-report.md"


def report_problem(title, message, level="error"):
    """Record a problem for the workflow to deliver -- don't deliver it here.

    Deliberately not sent to Discord: that webhook points at a public
    community server, and chain diagnostics (internal URLs, saved HTML
    dumps, stack detail) have no business there. The webhook stays
    single-purpose -- posting editorials.

    Three sinks, none of which need a secret:
      - a GitHub Actions annotation, so the failure is called out inline
        on the run page and in the job log;
      - $GITHUB_STEP_SUMMARY, so the run page itself explains what broke;
      - REPORT_FILE, which the workflow turns into a GitHub Issue. That
        issue is what actually reaches an inbox -- GitHub mails the full
        body from notifications@github.com, alongside the automated
        run-failure mail, whose template can't be customised.

    Safe to call outside CI: the annotation is a harmless line of stdout
    and the summary sink is skipped when the env var is absent.
    """
    (logger.error if level == "error" else logger.warning)("%s -- %s", title, message)

    # Workflow commands are newline-delimited, so multi-line messages have
    # to be escaped rather than printed raw.
    escaped = (message.replace("%", "%25")
                      .replace("\r", "%0D")
                      .replace("\n", "%0A"))
    print(f"::{level} title={title}::{escaped}", flush=True)

    block = f"### {title}\n\n{message}\n\n"
    for path in (REPORT_FILE, os.getenv("GITHUB_STEP_SUMMARY", "")):
        if not path:
            continue
        try:
            with open(path, "a") as f:
                f.write(block)
        except OSError as e:
            logger.warning("Could not write problem report to %s: %s", path, e)


def artifact_dir_for(date_str):
    path = os.path.join(ARTIFACTS_DIR, date_str)
    os.makedirs(path, exist_ok=True)
    return path


def cleanup_stale_artifacts(days=STALE_ARTIFACT_DAYS):
    if not os.path.isdir(ARTIFACTS_DIR):
        return
    cutoff = now_ist().date() - timedelta(days=days)
    for name in os.listdir(ARTIFACTS_DIR):
        path = os.path.join(ARTIFACTS_DIR, name)
        if not os.path.isdir(path):
            continue
        try:
            folder_date = datetime.strptime(name, "%Y-%m-%d").date()
        except ValueError:
            continue
        if folder_date < cutoff:
            shutil.rmtree(path)
            logger.info("Removed stale artifact folder: %s", path)


POSTS_DIR = os.path.join("app", "_posts")
# Only ever matches our own generated posts (site_publish._post_path),
# e.g. 2026-08-15-editorials.md -- deliberately not "any dated .md file",
# so this never touches hand-authored site content that happens to have a
# date-prefixed filename (Jekyll's own convention for every post).
_POST_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-editorials\.md$")


def cleanup_stale_posts(days=STALE_ARTIFACT_DAYS):
    """Remove site posts whose linked artifacts have aged out.

    Posts are kept on the same 7-day window as artifacts/ -- there's no
    long-term archive, just a rolling week of history, so a post's links
    are never left dangling for long enough to need the site's expiry
    handling in the steady state (that stays as a safety net for the
    transient gap within a single cleanup cycle).
    """
    if not os.path.isdir(POSTS_DIR):
        return
    cutoff = now_ist().date() - timedelta(days=days)
    for path in glob.glob(os.path.join(POSTS_DIR, "*.md")):
        name = os.path.basename(path)
        m = _POST_DATE_RE.match(name)
        if not m:
            continue
        try:
            post_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if post_date < cutoff:
            os.remove(path)
            logger.info("Removed stale site post: %s", path)


def post_discord(content, embed_title, embed_color, file_paths, date_str):
    """Post a message with one or more file attachments to the Discord webhook.

    file_paths: list of (filename, path) tuples.
    """
    if not DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook URL not configured")
        return False

    embed = {
        "title": embed_title,
        "color": embed_color,
        "timestamp": now_ist().isoformat(),
        "footer": {"text": "E-Newspaper Editorial Extractor"},
    }
    payload = {"content": content, "embeds": [embed]}

    files = {}
    opened = []
    try:
        for idx, (filename, path) in enumerate(file_paths):
            fh = open(path, "rb")
            opened.append(fh)
            files[f"file{idx}"] = (filename, fh)

        response = requests.post(
            DISCORD_WEBHOOK_URL,
            data={"payload_json": json.dumps(payload)},
            files=files,
            timeout=30,
        )
        response.raise_for_status()
        logger.info("Posted to Discord: %s", embed_title)
        return True
    except Exception as e:
        logger.error("Error posting to Discord: %s", e)
        return False
    finally:
        for fh in opened:
            fh.close()
