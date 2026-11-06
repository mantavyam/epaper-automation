#!/usr/bin/env python3
"""
Builds the site's date pages from the live GitHub Releases. Runs in
pages.yml before the Jekyll build, never from the scraper.

For each release in the window (releases.py), the assets are downloaded
into app/files/YYYY-MM-DD/ and one post is written to
app/_posts/YYYY-MM-DD-editorials.md, with a section per paper in a fixed
order (PAPER_ORDER). Both folders are generated output, gitignored.

Files are served from the site itself rather than linked to the release:
release assets send no Access-Control-Allow-Origin and are served as
attachments, so the PDF.js viewer (which fetches the bytes itself) could
not load them. Copied in at build time, they're same-origin.

Expiry needs no extra machinery: the scraper deletes releases older than
the 7-day window, and the next build simply doesn't see them. The site's
client-side expiry handling (app/_includes/expiry-check.html) stays as a
safety net for a page cached from before that rebuild.

Stdlib + gh only, so pages.yml doesn't have to install requirements.txt.
"""

import os
import shutil
import logging
from datetime import datetime

import common
import releases

POSTS_DIR = os.path.join("app", "_posts")
FILES_DIR = os.path.join("app", "files")
PAPER_ORDER = ["TH", "IE"]

DISCLAIMER_FOOTER = (
    "\n\n---\n\n"
    "*Shared for academic personal use, under provisions of fair dealing "
    "Operating as non-profit resource in Public Good Will."
    "(Copyright Act, 1957, §52). No rights claimed. For Takedown requests, "
    "Read More — [full disclaimer]({{ '/about/' | prepend: site.baseurl }}).*"
)

logger = logging.getLogger(__name__)


def _file_url(date_key, name):
    """Site-absolute path to a file copied into app/files/."""
    return f"{common.SITE_BASEURL}/files/{date_key}/{name}"


def _front_matter(day_dt):
    display_date = day_dt.strftime("%d/%m/%Y")
    return "\n".join([
        "---",
        "layout: category-post",
        f'title: "Editorials of {display_date}"',
        # %z requires a timezone-aware datetime -- without an explicit
        # offset Jekyll compares a naive timestamp against the build
        # machine's own clock (UTC in CI) and silently skips the post as
        # "future dated", or worse, misattributes it to the wrong day.
        f"date: {day_dt.strftime('%Y-%m-%d %H:%M:%S %z')}",
        "categories: epaper",
        "---",
    ])


def _build_section(paper_name, date_key, pdf_name, article_names, is_full_edition):
    """One paper's section. `pdf_name` is the editorial page, or -- when
    is_full_edition is set -- the whole edition, shipped because neither
    locator could find the editorial page. The whole edition is strictly
    more than nothing, so the reader still gets the day's paper; the
    banner says why it looks different."""
    pdf_url = _file_url(date_key, pdf_name)
    lines = [f"# {paper_name}", ""]
    if is_full_edition:
        lines += [
            "## Full edition",
            "",
            "> The editorial page could not be located in today's PDF, so the "
            "complete edition is published instead.",
            "",
        ]
        label, row = "Download full edition", "Complete edition"
    else:
        lines += ["## Editorial", ""]
        label, row = "Download PDF", "Full editorial page"
    lines += [
        "| Page | Download |",
        "|---|---|",
        f'| {row} | {{% include download-button.html href="{pdf_url}" '
        f'label="{label}" check_expiry=true %}} |',
        "",
        # Self-hosted PDF.js viewer on a same-origin file.
        f'<iframe class="pdf-preview" '
        f'src="{{{{ \'/assets/pdfjs/web/viewer.html\' | prepend: site.baseurl }}}}'
        f'?file={{{{ "{pdf_url}" | url_encode }}}}" '
        f'title="{paper_name} PDF"></iframe>',
    ]

    if article_names:
        lines += ["", "## Articles", ""]
        for i, name in enumerate(article_names, start=1):
            lines.append(
                f'<img class="artifact-image" src="{_file_url(date_key, name)}" '
                f'alt="{paper_name} editorial article {i}" '
                f'loading="lazy" onerror="handleArtifactError(this)">'
            )
        lines += ["", "| Article | Download |", "|---|---|"]
        for i, name in enumerate(article_names, start=1):
            lines.append(
                f'| Article {i} | {{% include download-button.html '
                f'href="{_file_url(date_key, name)}" label="Article {i}" check_expiry=true %}} |'
            )

    return "\n".join(lines)


def _sections(release):
    """Sections for every paper with a ledger entry and its files present."""
    date_key = release["date"].strftime("%Y-%m-%d")
    names = sorted(release["assets"])
    by_code = {}
    for paper_name, entry in release["ledger"].items():
        code = common.PAPER_CODES.get(paper_name)
        if code is None:
            continue
        full = entry.get("status") == "published_full_edition"
        kind = "FULL" if full else "EDITORIAL"
        pdf = next((n for n in names if n.startswith(f"{code}-{kind}-")), None)
        if pdf is None:
            logger.warning("%s: %s ledger entry but no %s file", release["tag"], paper_name, kind)
            continue
        articles = [] if full else [n for n in names if n.startswith(f"{code}-ART")]
        by_code[code] = _build_section(paper_name, date_key, pdf, articles, full)
    order = [c for c in PAPER_ORDER if c in by_code] + [c for c in by_code if c not in PAPER_ORDER]
    return [by_code[c] for c in order]


def _post_date(release):
    """The edition's date, at the earliest publish time of day (IST).

    Always the release's own date: Jekyll derives the permalink
    (/epaper/DD-MM-YYYY/) from it, and a paper scraped after midnight is
    still the previous day's edition. Only the time of day comes from the
    ledger -- the edition date is never after the scrape, so the result is
    never in the future (Jekyll silently drops future-dated posts).
    """
    stamps = [e["timestamp"] for e in release["ledger"].values() if e.get("timestamp")]
    when = (min(datetime.fromisoformat(s) for s in stamps).astimezone(common.IST).time()
            if stamps else datetime.min.time())
    return datetime.combine(release["date"], when, common.IST)


def build():
    """Regenerate app/_posts and app/files from the live releases."""
    for d in (POSTS_DIR, FILES_DIR):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)

    cutoff = common.now_ist().date().toordinal() - releases.RETENTION_DAYS
    built = 0
    for release in releases.list_releases():
        if release["date"].toordinal() < cutoff:
            continue  # expired, pending deletion by the next scraper run
        sections = _sections(release)
        if not sections:
            continue
        date_key = release["date"].strftime("%Y-%m-%d")
        releases.download(release["tag"], os.path.join(FILES_DIR, date_key))
        body = "\n\n".join(
            f'<div class="editorial-paper-section" markdown="1">\n\n{s}\n\n</div>'
            for s in sections
        )
        with open(os.path.join(POSTS_DIR, f"{date_key}-editorials.md"), "w") as f:
            f.write(_front_matter(_post_date(release)) + "\n\n" + body + DISCLAIMER_FOOTER + "\n")
        built += 1
        logger.info("Built post for %s (%d paper(s))", date_key, len(sections))
    logger.info("Built %d post(s) from releases", built)


if __name__ == "__main__":
    common.configure_logging()
    build()
