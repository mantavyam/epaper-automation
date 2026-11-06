#!/usr/bin/env python3
"""Shared helpers for the extraction script."""

import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import releases

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

# Local staging folder for the day's extracted files. Never committed:
# everything published goes to that day's GitHub Release (releases.py).
OUTPUT_DIR = "out"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

IST = ZoneInfo("Asia/Kolkata")


def now_ist():
    """Current wall-clock time in IST, timezone-aware.

    GitHub Actions runners default to UTC -- using this everywhere "today"
    is established (not plain datetime.now()) keeps artifact dates, history
    keys, and site post dates consistent with the IST-framed cron schedule,
    regardless of which timezone the host machine is actually in.
    """
    return datetime.now(IST)

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
    """The run record, rebuilt from the live releases' ledgers.

    Same shape the old download_history.json had -- MM-YYYY -> YYYY-MM-DD
    -> paper -> entry -- so already_processed() and
    consecutive_full_editions() read it unchanged. It only reaches back as
    far as the releases do (the 7-day window), which is all either needs.
    """
    history = {}
    for r in releases.list_releases():
        day = r["date"]
        history.setdefault(day.strftime("%m-%Y"), {})[day.strftime("%Y-%m-%d")] = r["ledger"]
    return history


def already_processed(history, date_key, month_key, paper_name):
    return (
        month_key in history
        and date_key in history[month_key]
        and paper_name in history[month_key][date_key]
    )


def record_history(history, date_key, month_key, paper_name, entry, paths):
    """Publish this paper's files to the day's release and record it there."""
    day = history.setdefault(month_key, {}).setdefault(date_key, {})
    day[paper_name] = entry
    releases.publish(datetime.strptime(date_key, "%Y-%m-%d").date(), paths, day)


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
    path = os.path.join(OUTPUT_DIR, date_str)
    os.makedirs(path, exist_ok=True)
    return path


def post_discord(content):
    """Post a plain-text message to the Discord webhook.

    Deliberately just `content` -- no embed object, no attachments. Files
    used to be uploaded straight to the webhook; they aren't any more,
    because the site hosts every artifact behind a PDF.js viewer and a link
    carries strictly more than an upload did. The embed that briefly
    replaced them was no better: Discord renders a link preview from the
    page's own metadata anyway, so building one by hand only added a
    coloured sidebar and a duplicate title.

    Note the linked post disappears with its release after the 7-day
    window, so older Discord links will 404. That is accepted -- this is
    a rolling week of history, not an archive.
    """
    if not DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook URL not configured")
        return False

    # Imported here so the site build (site_publish.py, which runs in
    # pages.yml without installing requirements) can import this module.
    import requests

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL, json={"content": content}, timeout=30
        )
        response.raise_for_status()
        logger.info("Posted to Discord")
        return True
    except Exception as e:
        logger.error("Error posting to Discord: %s", e)
        return False
