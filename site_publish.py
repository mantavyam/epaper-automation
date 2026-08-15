#!/usr/bin/env python3
"""
Publishes a Jekyll post for the app/ site whenever a scraper successfully
extracts an editorial page.

One post per date, not per paper -- primary and fallback (and Hindu vs.
Indian Express) all write into the same app/_posts/YYYY-MM-DD-editorials.md,
each owning a marked-off section that gets replaced on re-run without
touching the others. Order on the page is fixed (PAPER_ORDER), independent
of which script ran first.

Posts link to artifacts via raw.githubusercontent.com rather than copying
files into the site source -- see common.raw_url(). Both the artifacts and
the post itself are pruned on the same 7-day window (common.STALE_ARTIFACT_DAYS,
common.cleanup_stale_posts()) -- this is a rolling week of history, not a
long-term archive. The site's client-side expiry handling
(app/_includes/expiry-check.html) is a safety net for the brief window
within a single cleanup cycle where a post can outlive its artifact.
"""

import os
import re

import common

POSTS_DIR = os.path.join("app", "_posts")
PAPER_ORDER = ["TH", "IE"]

DISCLAIMER_FOOTER = (
    "\n\n---\n\n"
    "*Shared for academic personal use, under provisions of fair dealing "
    "Operating as non-profit resource in Public Good Will."
    "(Copyright Act, 1957, §52). No rights claimed. For Takedown requests, "
    "Read More — [full disclaimer]({{ '/about/' | prepend: site.baseurl }}).*"
)

_SECTION_RE = re.compile(
    r'<!-- paper-section:(\w+) -->\n'
    r'<div class="editorial-paper-section" markdown="1">\n\n'
    r"(.*?)\n\n</div>\n"
    r"<!-- /paper-section:\1 -->",
    re.DOTALL,
)


def _post_path(today):
    return os.path.join(POSTS_DIR, f"{today.strftime('%Y-%m-%d')}-editorials.md")


def _front_matter(today):
    display_date = today.strftime("%d/%m/%Y")
    return "\n".join([
        "---",
        "layout: category-post",
        f'title: "Editorials of {display_date}"',
        # %z requires `today` to be timezone-aware (common.now_ist()) --
        # without an explicit offset Jekyll compares a naive timestamp
        # against the build machine's own clock (UTC in CI) and silently
        # skips the post as "future dated", or worse, misattributes it to
        # the wrong calendar day.
        f"date: {today.strftime('%Y-%m-%d %H:%M:%S %z')}",
        "categories: epaper",
        "---",
    ])


def _build_section(paper_name, paper_code, editorial_pdf_path,
                    article_image_paths=None, edition_urls=None):
    editorial_url = common.raw_url(editorial_pdf_path)
    lines = [f"# {paper_name}"]

    if edition_urls:
        lines.append("")
        lines.append("## Editions")
        lines.append("")
        lines.append("| Edition | Download |")
        lines.append("|---|---|")
        for edition, url in edition_urls.items():
            lines.append(
                f'| {edition} | '
                f'{{% include download-button.html href="{url}" label="{edition}" %}} |'
            )

    lines.append("")
    lines.append("## Editorial")
    lines.append("")
    lines.append("| Page | Download |")
    lines.append("|---|---|")
    lines.append(
        f'| Full editorial page | '
        f'{{% include download-button.html href="{editorial_url}" '
        f'label="Download PDF" check_expiry=true %}} |'
    )
    lines.append("")
    lines.append(
        # Self-hosted PDF.js viewer, not a direct iframe on the raw URL --
        # raw.githubusercontent.com serves PDFs with headers that make
        # browsers download rather than render them inline. PDF.js fetches
        # the bytes itself (raw.githubusercontent.com allows CORS) and
        # renders to canvas, sidestepping that entirely.
        f'<iframe class="pdf-preview" '
        f'src="{{{{ \'/assets/pdfjs/web/viewer.html\' | prepend: site.baseurl }}}}'
        f'?file={{{{ "{editorial_url}" | url_encode }}}}" '
        f'title="{paper_name} editorial page PDF"></iframe>'
    )

    if article_image_paths:
        lines.append("")
        lines.append("## Articles")
        lines.append("")
        for i, img_path in enumerate(article_image_paths, start=1):
            img_url = common.raw_url(img_path)
            lines.append(
                f'<img class="artifact-image" src="{img_url}" '
                f'alt="{paper_name} editorial article {i}" '
                f'loading="lazy" onerror="handleArtifactError(this)">'
            )
        lines.append("")
        lines.append("| Article | Download |")
        lines.append("|---|---|")
        for i, img_path in enumerate(article_image_paths, start=1):
            img_url = common.raw_url(img_path)
            lines.append(
                f'| Article {i} | '
                f'{{% include download-button.html href="{img_url}" '
                f'label="Article {i}" check_expiry=true %}} |'
            )

    return "\n".join(lines)


def publish_post(paper_name, paper_code, today, editorial_pdf_path,
                  article_image_paths=None, edition_urls=None):
    """Write/update today's consolidated post with this paper's section."""
    os.makedirs(POSTS_DIR, exist_ok=True)
    post_path = _post_path(today)

    sections = {}
    if os.path.exists(post_path):
        with open(post_path) as f:
            existing = f.read()
        sections = dict(_SECTION_RE.findall(existing))

    sections[paper_code] = _build_section(
        paper_name, paper_code, editorial_pdf_path,
        article_image_paths=article_image_paths, edition_urls=edition_urls,
    )

    ordered_codes = [c for c in PAPER_ORDER if c in sections] + [
        c for c in sections if c not in PAPER_ORDER
    ]
    wrapped = [
        f'<!-- paper-section:{c} -->\n<div class="editorial-paper-section" markdown="1">\n\n'
        f"{sections[c]}\n\n</div>\n<!-- /paper-section:{c} -->"
        for c in ordered_codes
    ]
    body = "\n\n".join(wrapped)

    with open(post_path, "w") as f:
        f.write(_front_matter(today) + "\n\n" + body + DISCLAIMER_FOOTER + "\n")

    return post_path
