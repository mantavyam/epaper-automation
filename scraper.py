#!/usr/bin/env python3
"""
E-Newspaper Editorial Extractor (indiags.com)

Walks indiags' 4-hop link chain per paper -- homepage -> book page ->
newsletter page -> quiz-unlock redirect -- to reach a one-time-use direct
PDF link, then extracts just the Editorial page and posts it to Discord.

The Hindu's PDF carries vector rule geometry, so its two main articles are
cropped out as images. Indian Express is single-page-PDF-only: its PDF is a
flattened raster page with no vector drawings and no reliably-detectable
printed rule lines at any pixel threshold tested, so rule-based article
cropping isn't viable there.

Every step is a plain HTTP GET + HTML parse -- no browser automation. The
"quiz"/15s-timer/popups on this site are pure client-side UI theater: the
server embeds the one-time download token in the redirect response
regardless of whether a human ever interacts with the page.
"""

import os
import sys
import re
import socket
import logging
import urllib.parse


import requests
import urllib3.util.connection
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import fitz  # PyMuPDF
from bs4 import BeautifulSoup

import common
import editorial
import site_publish

BASE_URL = "https://www.indiags.com/epaper-pdf-download"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# paper title on site -> (display name, editorial locate mode)
PAPERS = {
    "The Hindu": ("The Hindu", "text"),
    "Indian Express": ("Indian Express", "ocr"),
}
PAPER_CODES = {"The Hindu": "TH", "Indian Express": "IE"}
SOURCE = "indiags"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def build_session():
    """Session hardened against indiags' intermittent connect failures.

    indiags sits behind a Hostinger CDN that publishes both A and AAAA
    records and occasionally refuses connections from CI runners for a few
    minutes at a time (observed: a run failing every address with
    ETIMEDOUT/ENETUNREACH, then the identical chain succeeding half an hour
    later). Two mitigations:

      - IPv4 only. GitHub Actions runners have no IPv6 egress, so every
        AAAA address is a guaranteed ENETUNREACH that only serves to mask
        the real IPv4 error in urllib3's "raise the last error" loop.
        Note this patch is process-wide, not per-session -- urllib3 reads
        allowed_gai_family as a module global on every connect, so it also
        applies to the Discord upload. That's intended (nothing here wants
        IPv6) but it is a side effect beyond this session object.
      - Retry connects with backoff, so a brief CDN blip costs seconds
        instead of the whole day's run.
    """
    urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET

    session = requests.Session()
    session.headers.update(HEADERS)
    retry = Retry(
        total=5,
        connect=5,
        read=3,
        backoff_factor=3,  # 0s, 6s, 12s, 24s, 48s
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


NEWSLETTER_RE = re.compile(r"/epaper/newsletter/(\d+)")
OPEN_RE = re.compile(r"/epaper/open/(\d+)")
GO_RE = re.compile(r"https?://[^\s\"'<>\\]+/go/[A-Za-z0-9_-]{16,}")


class HopError(RuntimeError):
    """A link in the chain couldn't be resolved; dumps the page that failed.

    The offending HTML is written to the working directory so the
    workflow's `*.html` upload-artifact step captures it -- otherwise a
    break is just a stack trace with no way to see what the page looked
    like at the time.
    """

    def __init__(self, what, url, html):
        path = f"hop-{what}.html"
        try:
            with open(path, "w") as f:
                f.write(html)
            saved = f", response saved to {path}"
        except OSError:
            saved = ""
        super().__init__(f"Could not resolve {what} on {url}{saved}")


def _resolve_link(soup, base_url, url_re, book_id, selector=None, label=None, what="link"):
    """Find the next hop, preferring the most change-resistant locator.

    Locators ranked by what it costs the site's author to change them:

      1. URL path shape (/epaper/newsletter/123) -- they can't change it
         without breaking their own routing, so this is the real contract.
      2. CSS class -- a theme tweak renames it.
      3. Button label -- a copy edit kills it.

    The original code used only 2 and 3, which is why a cosmetic change
    would take the whole run down. Shape first, the other two as fallbacks.

    Returns (url, how). `how` is recorded in history as an early warning:
    if it starts reading "selector:..." or "label:...", the URL shape moved
    and the chain is running on borrowed time -- visible before it breaks.
    """
    candidates = []
    for a in soup.find_all("a", href=True):
        url = urllib.parse.urljoin(base_url, a["href"])
        m = url_re.search(url)
        if m:
            candidates.append((url, m.group(1)))

    for url, found_id in candidates:
        if found_id == book_id:
            return url, "url-shape"
    if len(candidates) == 1:
        # Right shape, unexpected id. Still better evidence than a class
        # name, but worth flagging -- it means the page isn't laid out the
        # way we think it is.
        return candidates[0][0], "url-shape:id-mismatch"

    if selector:
        el = soup.select_one(selector)
        if el and el.get("href"):
            return urllib.parse.urljoin(base_url, el["href"]), f"selector:{selector}"

    if label:
        for a in soup.find_all("a", href=True):
            if label in a.get_text(strip=True).lower():
                return urllib.parse.urljoin(base_url, a["href"]), f"label:{label}"

    raise HopError(what, base_url, str(soup))


def resolve_token_url(session, book_id):
    """Walk the 4-hop chain for one book id, return (url, how) for the PDF."""
    hows = []
    books_url = f"{BASE_URL.rsplit('/', 1)[0]}/epaper/books/{book_id}"
    r1 = session.get(books_url, timeout=30)
    r1.raise_for_status()
    newsletter_url, how = _resolve_link(
        BeautifulSoup(r1.text, "html.parser"), books_url, NEWSLETTER_RE, book_id,
        selector="a.ep-cta-btn", label="download newspaper", what="newsletter-link",
    )
    hows.append(how)

    r2 = session.get(newsletter_url, timeout=30)
    r2.raise_for_status()
    open_url, how = _resolve_link(
        BeautifulSoup(r2.text, "html.parser"), newsletter_url, OPEN_RE, book_id,
        selector="a.ep-cta-btn", label="unlock via quiz", what="open-link",
    )
    hows.append(how)

    r3 = session.get(open_url, timeout=30, allow_redirects=True)
    r3.raise_for_status()
    token_url, how = _extract_go_url(r3)
    hows.append(how)
    return token_url, "|".join(hows)


def _extract_go_url(response):
    """Pull the one-time /go/ link out of the unlock redirect.

    Checked in three places, because the site has already moved this once.
    It used to be the whole fragment after "unlock="; then `&exp=<epoch>`
    was appended, and splitting on "unlock=" glued that onto the token path
    and 404'd every download. So: parse the fragment as a query string
    (handles any further keys they add), then the query string proper (the
    obvious place for it to move next), then fall back to scanning the
    response body for anything shaped like a /go/ link.
    """
    parts = urllib.parse.urlparse(response.url)
    for source, raw in (("fragment", parts.fragment), ("query", parts.query)):
        value = urllib.parse.parse_qs(raw).get("unlock", [None])[0]
        if value and GO_RE.fullmatch(value):
            return value, f"unlock-{source}"

    m = GO_RE.search(response.text)
    if m:
        return m.group(0), "go-url-in-body"

    raise HopError("go-url", response.url, response.text)


BOOKS_RE = re.compile(r"/epaper/books/(\d+)")


def find_book_ids(session):
    """Map paper title -> book id from the homepage.

    Driven off the /epaper/books/{id} link shape rather than the card
    markup (.ep-card / .ttl / a.ep-read), so a theme change that renames
    those classes doesn't take the run down. The paper is identified by
    looking at the text around each link -- matched case- and
    whitespace-insensitively on a substring, so "The Hindu ePaper" or
    "The Hindu (Delhi)" still resolves to The Hindu.
    """
    r = session.get(BASE_URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    ids = {}
    for a in soup.find_all("a", href=True):
        m = BOOKS_RE.search(a["href"])
        if not m:
            continue
        title = _owning_paper(a)
        if title and title not in ids:
            ids[title] = m.group(1)

    if not ids:
        raise HopError("book-ids", BASE_URL, str(soup))
    return ids


def _owning_paper(link):
    """Which paper does this book link belong to?

    The link text itself is just "Read", so the title has to come from an
    ancestor -- but the ancestors run from too narrow to too wide: the
    immediate wrapper is a bare <div class="foot"> holding only "Read",
    while two levels up the grid contains *both* papers and would happily
    mis-assign one to the other.

    So walk outward and stop at the first ancestor mentioning exactly one
    known paper. Too-narrow levels mention none and are skipped; too-wide
    levels mention several and are rejected rather than guessed at.
    """
    node = link
    for _ in range(6):
        node = node.parent
        if node is None:
            return None
        text = " ".join(node.get_text(" ", strip=True).lower().split())
        hits = [t for t in PAPERS if t.lower() in text]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            return None  # ambiguous: this level spans multiple papers
    return None


def process_paper(session, site_title, display_name, mode, book_id, history, today):
    date_key = today.strftime("%Y-%m-%d")
    month_key = today.strftime("%m-%Y")

    if common.already_processed(history, date_key, month_key, display_name):
        logger.info("%s already processed today", display_name)
        return True

    token_url, how = resolve_token_url(session, book_id)
    if "selector:" in how or "label:" in how:
        # Still working, but on a weaker locator than it should be. Worth
        # hearing about now, while there's time to fix it calmly, rather
        # than when the fallback goes too and the run starts failing.
        common.report_problem(
            f"{display_name}: chain fell back to a weaker locator",
            f"Resolved via `{how}` instead of the URL path shape. The site's "
            f"link structure moved, so the run still worked but is now relying "
            f"on a CSS class or button label -- either of which a cosmetic "
            f"change will break. Update the URL patterns in scraper.py.",
            level="warning",
        )
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
            {
                "status": "skipped_not_published",
                "source": SOURCE,
                "timestamp": common.now_ist().isoformat(),
            },
        )
        doc.close()

        # A skip is normal; a run of them means the locator broke, not that
        # the paper took the week off. See common.consecutive_skips().
        streak = common.consecutive_skips(history, display_name, today, SOURCE) + 1
        if streak >= common.SKIP_STREAK_LIMIT:
            msg = (
                f"{display_name} has recorded {streak} consecutive days with no "
                f"editorial page found. The longest genuine gap on record is one "
                f"day, so this is far more likely a broken page locator than a "
                f"real run of unpublished editorials. Check whether the masthead "
                f"wording changed."
            )
            logger.error(msg)
            common.report_problem(f"{display_name}: {streak}-day skip streak", msg)
            return False
        return True

    single_pdf_path = os.path.join(
        artifact_dir, common.dated_filename(display_name, "EDITORIAL", today, "pdf")
    )
    editorial.extract_single_page_pdf(doc, page_idx, single_pdf_path)

    article_paths = []
    if PAPER_CODES[display_name] == "TH":
        for i, png_bytes in enumerate(editorial.extract_hindu_articles(doc, page_idx), start=1):
            p = os.path.join(
                artifact_dir, common.dated_filename(display_name, "ART", today, "png", part=i)
            )
            with open(p, "wb") as f:
                f.write(png_bytes)
            article_paths.append(p)

    doc.close()
    os.remove(raw_pdf_path)

    date_str = today.strftime("%d %B %Y")
    files = [(os.path.basename(p), p) for p in article_paths]
    files.append((os.path.basename(single_pdf_path), single_pdf_path))
    posted = common.post_discord(
        content=f"**{display_name} Editorial** -- {date_str}",
        embed_title=f"{display_name} Editorial - {date_str}",
        embed_color=0x3498DB,
        file_paths=files,
        date_str=date_str,
    )

    site_publish.publish_post(
        display_name, PAPER_CODES[display_name], today,
        editorial_pdf_path=single_pdf_path,
        article_image_paths=article_paths or None,
    )

    common.record_history(
        history, date_key, month_key, display_name,
        {
            "status": "posted" if posted else "post_failed",
            "source": SOURCE,
            "resolved_via": how,
            "editorial_page_index": page_idx,
            "artifact_dir": artifact_dir,
            "timestamp": common.now_ist().isoformat(),
        },
    )
    return posted


def main():
    logger.info("=== Editorial Extraction Started ===")
    today = common.now_ist()
    history = common.load_history()
    session = build_session()

    try:
        book_ids = find_book_ids(session)
    except Exception as e:
        logger.error("Could not read the indiags homepage: %s", e)
        common.report_problem("Editorial extraction failed", f"Homepage unreadable: {e}")
        sys.exit(1)

    overall_ok = True
    failures = []
    for site_title, (display_name, mode) in PAPERS.items():
        book_id = book_ids.get(site_title)
        if not book_id:
            logger.error("%s not found on indiags homepage today", site_title)
            failures.append(f"{display_name}: no book link on the homepage")
            overall_ok = False
            continue
        try:
            ok = process_paper(session, site_title, display_name, mode, book_id, history, today)
            overall_ok = overall_ok and ok
        except Exception as e:
            logger.error("Error processing %s: %s", display_name, e)
            failures.append(f"{display_name}: {e}")
            overall_ok = False

    # Streak trips alert on their own (with a more specific message), so
    # only raise the generic one for exceptions caught here.
    if failures:
        common.report_problem(
            "Editorial extraction failed", "\n".join(f"- {f}" for f in failures)
        )

    common.cleanup_stale_artifacts()
    common.cleanup_stale_posts()
    logger.info("=== Editorial Extraction %s ===", "Completed" if overall_ok else "Completed with errors")
    if not overall_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
