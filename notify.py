#!/usr/bin/env python3
"""
Posts the day's Discord notification -- a link, not attachments.

Split out of scraper.py because of ordering. The link points at the
GitHub Pages post, which does not exist until the site has been committed,
built and deployed; posting it from the extraction step would hand readers
a URL that 404s for a minute or two. So scraper.py writes notify.json,
the workflow commits, dispatches pages.yml and waits for the deploy to
conclude, and only then does this run.

Idempotent by construction: scraper.py writes the manifest only when it
actually published something, and a re-run for a date already in the
history short-circuits before publishing. A re-run therefore leaves no
manifest and this script posts nothing.
"""

import os
import sys
import json
import logging

import common

NOTIFY_FILE = "notify.json"

common.configure_logging()
logger = logging.getLogger(__name__)

# What the reader gets when the editorial page could not be located. Worth
# saying in the message rather than letting them click through and wonder
# why today's post looks different.
_FULL_EDITION_NOTE = " (full edition -- editorial page could not be located)"


def main():
    if not os.path.exists(NOTIFY_FILE):
        logger.info("No %s -- nothing was published this run, so nothing to post", NOTIFY_FILE)
        return

    with open(NOTIFY_FILE) as f:
        manifest = json.load(f)

    papers = manifest.get("papers", [])
    if not papers:
        logger.info("Manifest lists no papers -- nothing to post")
        return

    lines = []
    for paper in papers:
        note = _FULL_EDITION_NOTE if paper.get("located_via") == "full" else ""
        lines.append(f"• **{paper['name']}**{note}")

    date_display = manifest["date_display"]
    url = manifest["url"]

    posted = common.post_discord(
        content=f"**Editorials** — {date_display}",
        embed_title=f"Editorials — {date_display}",
        embed_description="\n".join(lines) + f"\n\n[Read on the site]({url})",
        embed_url=url,
    )
    if not posted:
        logger.error("Discord notification failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
