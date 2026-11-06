#!/usr/bin/env python3
"""GitHub Releases as the store for each day's files and its run record.

One release per date, tagged editorial-YYYY-MM-DD. Its assets are that
day's extracted files (TH-EDITORIAL-..., TH-ART1-..., IE-EDITORIAL-...);
its description carries the run record -- what download_history.json used
to hold -- as JSON inside a hidden <!-- ledger ... --> comment.

Nothing binary is committed to git, and the bot commits nothing at all:
release assets don't count toward repo size, and deleting a release
(prune) frees its files outright instead of leaving blobs in history.

The site can't read release assets from the browser -- they send no
Access-Control-Allow-Origin and are served as attachments -- so pages.yml
downloads the live window at build time and serves it same-origin (see
site_publish.py).

Everything goes through the `gh` CLI (preinstalled on Actions runners,
authenticated via GH_TOKEN; locally, via `gh auth login`), which keeps
this module stdlib-only.
"""

import os
import re
import json
import logging
import subprocess
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

REPO = os.getenv("GITHUB_REPOSITORY", "mantavyam/epaper-automation")
# Overridable so a test run can publish under a throwaway prefix and
# delete it afterwards without touching the live releases.
TAG_PREFIX = os.getenv("RELEASE_TAG_PREFIX", "editorial-")
RETENTION_DAYS = 7

_LEDGER_RE = re.compile(r"<!-- ledger\n(.*?)\n-->", re.DOTALL)


def _gh(*args, stdin=None):
    return subprocess.run(
        ["gh", *args], input=stdin, capture_output=True, text=True, check=True
    ).stdout


def tag_for(day):
    return f"{TAG_PREFIX}{day:%Y-%m-%d}"


def _day_of(tag):
    if not tag.startswith(TAG_PREFIX):
        return None
    try:
        return datetime.strptime(tag[len(TAG_PREFIX):], "%Y-%m-%d").date()
    except ValueError:
        return None


def list_releases():
    """This pipeline's releases, newest first.

    Each: {"tag", "date", "ledger": {paper: entry}, "assets": {name: size}}.
    Releases under other tags are ignored, so the repo can carry unrelated
    releases without them being read or pruned.
    """
    out = _gh("api", "--paginate", f"repos/{REPO}/releases?per_page=100", "--jq", ".[]")
    releases = []
    for line in out.splitlines():
        r = json.loads(line)
        day = _day_of(r["tag_name"])
        if day is None:
            continue
        m = _LEDGER_RE.search(r.get("body") or "")
        releases.append({
            "tag": r["tag_name"],
            "date": day,
            "ledger": json.loads(m.group(1)) if m else {},
            "assets": {a["name"]: a["size"] for a in r["assets"]},
        })
    releases.sort(key=lambda r: r["date"], reverse=True)
    return releases


def _body(ledger):
    """Readable summary on top, machine-readable ledger hidden below."""
    lines = []
    for paper, entry in ledger.items():
        what = "full edition" if entry.get("status") == "published_full_edition" else "editorial page"
        lines.append(f"- **{paper}**: {what} (`{entry.get('located_via')}`)")
    return "\n".join(lines) + f"\n\n<!-- ledger\n{json.dumps(ledger, indent=2)}\n-->\n"


def publish(day, paths, ledger):
    """Attach `paths` to the day's release (creating it) and store `ledger`.

    Upload first, ledger second: a run that dies between the two leaves
    files with no ledger entry, so the next retry redoes the paper (and
    --clobber overwrites the files) rather than believing it's done.
    """
    tag = tag_for(day)
    exists = subprocess.run(
        ["gh", "release", "view", tag, "-R", REPO], capture_output=True
    ).returncode == 0
    if exists:
        if paths:
            _gh("release", "upload", tag, *paths, "--clobber", "-R", REPO)
        _gh("release", "edit", tag, "--notes-file", "-", "-R", REPO, stdin=_body(ledger))
    else:
        _gh(
            "release", "create", tag, *paths, "-R", REPO,
            "--title", f"Editorials · {day:%d %b %Y}",
            "--notes-file", "-", "--latest=false",
            stdin=_body(ledger),
        )
    logger.info("Release %s: %d file(s) published", tag, len(paths))


def prune(releases=None, days=RETENTION_DAYS, today=None):
    """Delete releases (and their tags) older than the rolling window.

    Returns the number deleted. Deleting the release is what expires its
    files -- there is no other copy to clean up.
    """
    releases = list_releases() if releases is None else releases
    cutoff = (today or date.today()) - timedelta(days=days)
    deleted = 0
    for r in releases:
        if r["date"] < cutoff:
            _gh("release", "delete", r["tag"], "--cleanup-tag", "--yes", "-R", REPO)
            logger.info("Deleted expired release %s", r["tag"])
            deleted += 1
    return deleted


def download(tag, dest):
    """Fetch every asset of one release into `dest`."""
    os.makedirs(dest, exist_ok=True)
    _gh("release", "download", tag, "-D", dest, "--clobber", "-R", REPO)
