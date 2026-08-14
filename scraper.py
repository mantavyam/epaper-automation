#!/usr/bin/env python3
"""
Primary E-Newspaper Editorial Extractor (preppyq.in)

Fetches today's The Hindu (International edition) PDF from preppyq.in,
locates the Editorial page, crops the two main articles as PNGs, and
posts them plus the single editorial-page PDF to Discord.

No browser automation: the source is a static WordPress page, fetched
and parsed with requests/BeautifulSoup.

Falls back to daily-newspaper-fallback.yml (dispatched by the workflow)
if this fails or the source table doesn't have today's link yet.
"""

import os
import sys
import logging
from datetime import datetime

import requests
import fitz  # PyMuPDF
from bs4 import BeautifulSoup

import common
import editorial

BASE_URL = "https://preppyq.in/the-hindu-newspaper/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
PAPER_NAME = "The Hindu"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def find_today_editions(today):
    """Parse preppyq's table for today's Hindu edition links.

    Returns a dict like {"International": url, "Delhi": url} -- whichever
    editions are present for today's date. Missing editions are simply
    absent from the dict.
    """
    r = requests.get(BASE_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    tables = soup.find_all("table")
    if not tables:
        raise RuntimeError("No tables found on preppyq page")

    date_tag = today.strftime("%d-%m-%Y")
    editions = {}
    for tr in tables[0].find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) != 2:
            continue
        label = tds[0].get_text(strip=True)
        if date_tag not in label:
            continue
        a = tds[1].find("a")
        if not a or not a.get("href"):
            continue
        for edition in ("International", "Delhi"):
            if edition in label:
                editions[edition] = a["href"]

    return editions


def process():
    today = datetime.now()
    date_key = today.strftime("%Y-%m-%d")
    month_key = today.strftime("%m-%Y")

    history = common.load_history()
    if common.already_processed(history, date_key, month_key, PAPER_NAME):
        logger.info("%s already processed today", PAPER_NAME)
        return True

    editions = find_today_editions(today)
    if not editions:
        logger.error("Today's link not found on preppyq -- source may be stale")
        return False

    # Prefer International (fewer ads) for extraction; fall back to whatever
    # edition is present. Both edition links (if available) are still
    # delivered as-is -- they're persistent, static-hosted URLs.
    extract_edition = "International" if "International" in editions else next(iter(editions))
    pdf_url = editions[extract_edition]

    logger.info("Downloading %s edition: %s", extract_edition, pdf_url)
    r = requests.get(pdf_url, headers=HEADERS, timeout=60)
    r.raise_for_status()

    artifact_dir = common.artifact_dir_for(date_key)
    raw_pdf_path = os.path.join(
        artifact_dir, common.dated_filename(PAPER_NAME, "FULL", today, "pdf")
    )
    with open(raw_pdf_path, "wb") as f:
        f.write(r.content)

    doc = fitz.open(raw_pdf_path)
    page_idx = editorial.locate_editorial_page_text(doc)

    if page_idx is None:
        logger.info("No Editorial page found today -- likely Sunday/holiday, skipping")
        os.remove(raw_pdf_path)
        common.record_history(
            history, date_key, month_key, PAPER_NAME,
            {"status": "skipped_not_published", "timestamp": datetime.now().isoformat()},
        )
        return True

    single_pdf_path = os.path.join(
        artifact_dir, common.dated_filename(PAPER_NAME, "EDITORIAL", today, "pdf")
    )
    editorial.extract_single_page_pdf(doc, page_idx, single_pdf_path)

    article_pngs = editorial.extract_hindu_articles(doc, page_idx)
    article_paths = []
    if not article_pngs:
        full_png = editorial.render_full_page_png(doc, page_idx)
        full_png_path = os.path.join(
            artifact_dir, common.dated_filename(PAPER_NAME, "FULLPAGE", today, "png")
        )
        with open(full_png_path, "wb") as f:
            f.write(full_png)
        article_paths.append(full_png_path)
    else:
        for i, png_bytes in enumerate(article_pngs, start=1):
            p = os.path.join(
                artifact_dir, common.dated_filename(PAPER_NAME, "ART", today, "png", part=i)
            )
            with open(p, "wb") as f:
                f.write(png_bytes)
            article_paths.append(p)

    doc.close()
    os.remove(raw_pdf_path)

    date_str = today.strftime("%d %B %Y")
    files = [(os.path.basename(p), p) for p in article_paths]
    files.append((os.path.basename(single_pdf_path), single_pdf_path))

    edition_lines = "\n".join(
        f"{edition}: {url}" for edition, url in editions.items()
    )
    content = (
        f"**{PAPER_NAME} Editorial** -- {date_str}\n"
        f"(extracted from {extract_edition} edition)\n\n"
        f"Full e-paper PDFs:\n{edition_lines}"
    )

    posted = common.post_discord(
        content=content,
        embed_title=f"{PAPER_NAME} Editorial - {date_str}",
        embed_color=0x3498DB,
        file_paths=files,
        date_str=date_str,
    )

    common.record_history(
        history, date_key, month_key, PAPER_NAME,
        {
            "status": "posted" if posted else "post_failed",
            "edition_urls": editions,
            "extracted_from": extract_edition,
            "editorial_page_index": page_idx,
            "artifact_dir": artifact_dir,
            "timestamp": datetime.now().isoformat(),
        },
    )

    common.cleanup_stale_artifacts()
    return posted


def main():
    logger.info("=== Primary Editorial Extraction Started ===")
    ok = process()
    logger.info("=== Primary Editorial Extraction %s ===", "Completed" if ok else "Failed")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
