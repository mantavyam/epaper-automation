#!/usr/bin/env python3
"""
Fallback E-Newspaper Editorial Extractor (indiags.com)

Used only when the primary (preppyq.in) source fails. Walks indiags'
4-hop link chain per paper -- homepage -> book page -> newsletter page ->
quiz-unlock redirect -- to reach a one-time-use direct PDF link, then
extracts just the Editorial page and posts it to Discord.

No article-image cropping here (that stays on the more reliable primary
path); this just posts the single editorial-page PDF per paper.

Every step is a plain HTTP GET + HTML parse -- no browser automation.
The "quiz"/15s-timer/popups on this site are pure client-side UI theater:
the server embeds the one-time download token in the redirect response
regardless of whether a human ever interacts with the page.
"""

import os
import sys
import re
import logging
import urllib.parse
from datetime import datetime

import requests
import fitz  # PyMuPDF
from bs4 import BeautifulSoup

import common
import editorial

BASE_URL = "https://www.indiags.com/epaper-pdf-download"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# paper title on site -> (display name, editorial locate mode)
PAPERS = {
    "The Hindu": ("The Hindu", "text"),
    "Indian Express": ("Indian Express", "ocr"),
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def resolve_token_url(session, book_id):
    """Walk the 4-hop chain for one book id, return the one-time PDF url."""
    r1 = session.get(f"{BASE_URL.rsplit('/', 1)[0]}/epaper/books/{book_id}", timeout=30)
    r1.raise_for_status()
    soup1 = BeautifulSoup(r1.text, "html.parser")
    cta = soup1.select_one("a.ep-cta-btn")
    if not cta:
        raise RuntimeError(f"No 'Download Newspaper' link on books/{book_id}")
    newsletter_url = cta["href"]

    r2 = session.get(newsletter_url, timeout=30)
    r2.raise_for_status()
    soup2 = BeautifulSoup(r2.text, "html.parser")
    unlock_a = None
    for a in soup2.select("a"):
        if "unlock via quiz" in a.get_text(strip=True).lower():
            unlock_a = a
            break
    if not unlock_a:
        raise RuntimeError(f"No 'Unlock via Quiz' link on {newsletter_url}")
    open_url = unlock_a["href"]

    r3 = session.get(open_url, timeout=30, allow_redirects=True)
    r3.raise_for_status()
    frag = urllib.parse.urlparse(r3.url).fragment
    if not frag.startswith("unlock="):
        raise RuntimeError(f"No unlock fragment on redirect from {open_url}")
    return urllib.parse.unquote(frag.split("unlock=", 1)[1])


def find_book_ids(session):
    """Map paper title -> book id from the homepage cards."""
    r = session.get(BASE_URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    ids = {}
    for card in soup.select(".ep-card"):
        ttl = card.select_one(".ttl")
        a = card.select_one("a.ep-read")
        if not ttl or not a:
            continue
        title = ttl.get_text(strip=True)
        m = re.search(r"/epaper/books/(\d+)", a.get("href", ""))
        if title in PAPERS and m:
            ids[title] = m.group(1)
    return ids


def process_paper(session, site_title, display_name, mode, book_id, history, today):
    date_key = today.strftime("%Y-%m-%d")
    month_key = today.strftime("%m-%Y")

    if common.already_processed(history, date_key, month_key, display_name):
        logger.info("%s already processed today", display_name)
        return True

    token_url = resolve_token_url(session, book_id)
    logger.info("Downloading %s via %s", display_name, token_url)
    r = session.get(token_url, timeout=60)
    r.raise_for_status()
    if "pdf" not in r.headers.get("Content-Type", ""):
        raise RuntimeError(f"Token url did not return a PDF for {display_name}")

    artifact_dir = common.artifact_dir_for(date_key)
    raw_pdf_path = os.path.join(
        artifact_dir, common.dated_filename(display_name, "FULL", today, "pdf")
    )
    with open(raw_pdf_path, "wb") as f:
        f.write(r.content)

    doc = fitz.open(raw_pdf_path)
    if mode == "text":
        page_idx = editorial.locate_editorial_page_text(doc)
    else:
        page_idx = editorial.locate_editorial_page_ocr(doc)

    if page_idx is None:
        logger.info("%s: no editorial page found today, skipping", display_name)
        os.remove(raw_pdf_path)
        common.record_history(
            history, date_key, month_key, display_name,
            {"status": "skipped_not_published", "timestamp": datetime.now().isoformat()},
        )
        doc.close()
        return True

    single_pdf_path = os.path.join(
        artifact_dir, common.dated_filename(display_name, "EDITORIAL", today, "pdf")
    )
    editorial.extract_single_page_pdf(doc, page_idx, single_pdf_path)
    doc.close()
    os.remove(raw_pdf_path)

    date_str = today.strftime("%d %B %Y")
    posted = common.post_discord(
        content=f"**{display_name} Editorial** -- {date_str} (via fallback source)",
        embed_title=f"{display_name} Editorial - {date_str}",
        embed_color=0xE74C3C,
        file_paths=[(os.path.basename(single_pdf_path), single_pdf_path)],
        date_str=date_str,
    )

    common.record_history(
        history, date_key, month_key, display_name,
        {
            "status": "posted" if posted else "post_failed",
            "source": "indiags_fallback",
            "editorial_page_index": page_idx,
            "artifact_dir": artifact_dir,
            "timestamp": datetime.now().isoformat(),
        },
    )
    return posted


def main():
    logger.info("=== Fallback Editorial Extraction Started ===")
    today = datetime.now()
    history = common.load_history()
    session = requests.Session()
    session.headers.update(HEADERS)

    book_ids = find_book_ids(session)
    if not book_ids:
        logger.error("No paper cards found on indiags homepage")
        sys.exit(1)

    overall_ok = True
    for site_title, (display_name, mode) in PAPERS.items():
        book_id = book_ids.get(site_title)
        if not book_id:
            logger.error("%s not found on indiags homepage today", site_title)
            overall_ok = False
            continue
        try:
            ok = process_paper(session, site_title, display_name, mode, book_id, history, today)
            overall_ok = overall_ok and ok
        except Exception as e:
            logger.error("Error processing %s: %s", display_name, e)
            overall_ok = False

    common.cleanup_stale_artifacts()
    logger.info("=== Fallback Editorial Extraction %s ===", "Completed" if overall_ok else "Completed with errors")
    if not overall_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
