#!/usr/bin/env python3
"""Shared helpers for the primary and fallback extraction scripts."""

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
