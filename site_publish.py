#!/usr/bin/env python3
"""
Publishes a Jekyll post for the app/ site whenever a scraper successfully
extracts an editorial page.

Posts link to artifacts via raw.githubusercontent.com rather than copying
files into the site source -- see common.raw_url(). Both the artifacts and
the post itself are pruned on the same 7-day window (common.STALE_ARTIFACT_DAYS,
common.cleanup_stale_posts()) -- this is a rolling week of history, not a
long-term archive. The site's client-side expiry handling
(app/_includes/expiry-check.html) is a safety net for the brief window
within a single cleanup cycle where a post can outlive its artifact.
"""

import os

import common

POSTS_DIR = os.path.join("app", "_posts")


def _slugify(paper_name):
    return paper_name.lower().replace(" ", "-")


def publish_post(paper_name, paper_code, today, editorial_pdf_path,
                  article_image_paths=None, edition_urls=None, source_label="primary"):
    """Write a Jekyll post for today's editorial extraction.

    editorial_pdf_path / article_image_paths: repo-relative paths (e.g.
    "artifacts/2026-08-14/TH-EDITORIAL-14-08-26.pdf") as already used for
    the Discord attachments -- reused here to build raw.githubusercontent
    links.
    edition_urls: optional {edition_name: external_url} for source PDFs
    that are hosted elsewhere and never expire (e.g. preppyq.in) -- listed
    as plain links, no expiry check needed.
    """
    os.makedirs(POSTS_DIR, exist_ok=True)

    date_str = today.strftime("%Y-%m-%d")
    slug = f"{date_str}-{_slugify(paper_name)}-editorial"
    post_path = os.path.join(POSTS_DIR, f"{slug}.md")

    display_date = today.strftime("%d %b %Y")
    editorial_url = common.raw_url(editorial_pdf_path)

    lines = [
        "---",
        "layout: category-post",
        f'title: "{paper_name} Editorial — {display_date}"',
        # +05:30 (IST) explicitly -- without an offset Jekyll compares this
        # naive timestamp against the build machine's own clock (UTC in CI),
        # and silently skips the post as "future dated".
        f"date: {today.strftime('%Y-%m-%d %H:%M:%S')} +05:30",
        "categories: epaper",
        f"paper: {paper_code}",
        f"source: {source_label}",
        "---",
        "",
    ]

    if edition_urls:
        lines.append("**Full e-paper editions:**")
        lines.append("")
        for edition, url in edition_urls.items():
            lines.append(f"- [{edition}]({url})")
        lines.append("")

    lines.append("**Editorial page (PDF):**")
    lines.append("")
    lines.append(
        f'<a href="{editorial_url}" data-check-expiry target="_blank" rel="noopener">'
        f"Download {paper_name} Editorial — {display_date}</a>"
    )
    lines.append("")

    if article_image_paths:
        lines.append("**Articles:**")
        lines.append("")
        for i, img_path in enumerate(article_image_paths, start=1):
            img_url = common.raw_url(img_path)
            lines.append(
                f'<img class="artifact-image" src="{img_url}" '
                f'alt="{paper_name} editorial article {i} — {display_date}" '
                f'loading="lazy" onerror="handleArtifactError(this)">'
            )
            lines.append("")

    with open(post_path, "w") as f:
        f.write("\n".join(lines))

    return post_path
