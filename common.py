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


class _ISTFormatter(logging.Formatter):
    """Log timestamps in IST rather than the host's clock.

    Everything else in this system is IST-pinned -- history keys, artifact
    dates, post dates, all via now_ist() -- but logging still used the
    machine's local time, which is UTC on a GitHub Actions runner. That put
    a 5h30m gap between a log line and the history entry it wrote, for no
    reason other than the default.
    """

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, IST)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S,") + f"{dt.microsecond // 1000:03d}"


def configure_logging(level=logging.INFO):
    """Root logging config for the scripts: INFO to stderr, IST timestamps."""
    handler = logging.StreamHandler()
    handler.setFormatter(_ISTFormatter("%(asctime)s - %(levelname)s - %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)

HISTORY_FILE = "download_history.json"
# Subdirectory the date folders live under. The workflow blanks this, so on
# the artifacts branch the dates sit at the branch root and URLs read
# /<repo>/artifacts/2026-09-18/... rather than doubling the word.
ARTIFACTS_DIR = os.getenv("ARTIFACTS_DIR", "artifacts")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
STALE_ARTIFACT_DAYS = 7

# Artifacts live on their own branch, not on main.
#
# main's history was growing ~1.7 MB/day and would never shrink: the 7-day
# prune keeps the working tree small but every deleted byte stays in git
# history forever (measured: 20.6 MB of artifact blobs across 12 dates,
# 85% of the whole repo, with an empty artifacts/ in the working tree).
#
# So the workflow checks this branch out as a worktree, points
# ARTIFACTS_ROOT at it, and force-pushes it back as a *single* commit each
# run. The branch is a rolling mirror of the live window, its history has
# no value, and collapsing it every time bounds it permanently at ~7 days.
# main's history stops growing entirely.
#
# It stays in the same repo, served from raw.githubusercontent.com, rather
# than moving to GitHub Releases -- release assets send no
# Access-Control-Allow-Origin, so the site's PDF.js viewer (which fetches
# the bytes itself) would be CORS-blocked. raw.githubusercontent.com sends
# `*` on any branch.
ARTIFACTS_BRANCH = "artifacts"

# Filesystem root the artifact tree is written under. The workflow sets
# this to the artifacts-branch worktree; locally it defaults to the repo
# itself, so a local run behaves exactly as before.
ARTIFACTS_ROOT = os.getenv("ARTIFACTS_ROOT", ".")

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


def raw_url(local_path):
    """Build a raw.githubusercontent.com URL for an artifact.

    Takes the path the file was written to locally and resolves it against
    ARTIFACTS_ROOT, so callers don't have to know whether they're running
    inside the artifacts-branch worktree or a plain local checkout.

    Used to link the Jekyll site to artifacts without duplicating them into
    the site source -- when the 7-day cleanup deletes the file, this link
    404s, which is what the site's expiry handling detects.
    """
    rel = os.path.relpath(local_path, ARTIFACTS_ROOT)
    return f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/{ARTIFACTS_BRANCH}/{rel}"


def artifact_branch_path(local_path):
    """Where a locally-written artifact sits on the artifacts branch."""
    return os.path.relpath(local_path, ARTIFACTS_ROOT)

# Where the Jekyll site is published. Mirrors app/_config.yml's `url` +
# `baseurl` + `permalink: /epaper/:day-:month-:year/`; Discord links point
# here instead of carrying attachments.
SITE_URL = "https://mantavyam.github.io"
SITE_BASEURL = "/epaper-automation"


def site_post_url(today):
    """Public URL of the site post for a given date."""
    return f"{SITE_URL}{SITE_BASEURL}/epaper/{today.strftime('%d-%m-%Y')}/"


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


FULL_EDITION_STREAK_LIMIT = 3
FULL_EDITION_STREAK_WINDOW = 21


def consecutive_full_editions(history, paper_name, today, source,
                              window=FULL_EDITION_STREAK_WINDOW):
    """Count back-to-back days that fell through to the full-edition tier.

    Falling through once is survivable -- the paper still ships, just as
    the whole edition rather than the editorial page. A *run* of them is
    the tell that both locators are dead rather than that one day's layout
    was odd, and it is also when committed full editions start to weigh on
    the repository. Three in a row is treated as an outage.

    Two deliberate choices in the walk:

      - Days with no entry at all are stepped over, not treated as the end
        of the streak. The workflow doesn't run every day (dispatch-only
        gaps are all over the history), and a gap says nothing either way.
      - An entry from a *different* source ends the walk. A streak is
        evidence about one source's locators, so switching sources resets
        it rather than inheriting a dead source's streak and crying wolf.
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
        if entry.get("located_via") != "full":
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
    path = os.path.join(ARTIFACTS_ROOT, ARTIFACTS_DIR, date_str)
    os.makedirs(path, exist_ok=True)
    return path


def cleanup_stale_artifacts(days=STALE_ARTIFACT_DAYS):
    """Prune date folders older than the rolling window.

    Runs against ARTIFACTS_ROOT, so in CI it prunes the artifacts-branch
    worktree -- which is the only place with more than today's files in it.
    """
    base = os.path.join(ARTIFACTS_ROOT, ARTIFACTS_DIR)
    if not os.path.isdir(base):
        return
    cutoff = now_ist().date() - timedelta(days=days)
    for name in os.listdir(base):
        path = os.path.join(base, name)
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


def post_discord(content, embed_title, embed_description, embed_url,
                 embed_color=0x3498DB):
    """Post a link to the site's page for the day. No attachments.

    Files used to be uploaded straight to the webhook. They aren't any
    more: the site already hosts every artifact behind a PDF.js viewer,
    so a link carries strictly more than an attachment did (both papers
    in one message, article crops inline, working previews) and keeps the
    message small. Note the linked post is pruned on the same 7-day window
    as the artifacts -- older Discord links will 404, which is accepted.
    """
    if not DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook URL not configured")
        return False

    payload = {
        "content": content,
        "embeds": [{
            "title": embed_title,
            "description": embed_description,
            "url": embed_url,
            "color": embed_color,
            "timestamp": now_ist().isoformat(),
            "footer": {"text": "E-Newspaper Editorial Extractor"},
        }],
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=30)
        response.raise_for_status()
        logger.info("Posted to Discord: %s", embed_url)
        return True
    except Exception as e:
        logger.error("Error posting to Discord: %s", e)
        return False
