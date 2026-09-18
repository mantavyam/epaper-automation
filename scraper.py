#!/usr/bin/env python3
"""
E-Newspaper Editorial Extractor (indiags.com)

Walks indiags' 4-hop link chain per paper -- homepage -> book page ->
newsletter page -> quiz-unlock redirect -- to reach a one-time-use direct
PDF link, then extracts just the Editorial page and publishes it.

The Hindu's PDF carries vector rule geometry, so its two main articles are
cropped out as images. Indian Express is page-PDF-only: its editorial page
draws no vector rules at all (the rules a reader sees live in a full-page
background raster), so rule-based article cropping isn't viable there.

Locating the editorial page is tiered and self-detecting -- see
editorial.locate_editorial_page. If both tiers miss, the whole edition is
published rather than skipping the paper for the day: the PDF is in hand
either way, and a reader would rather have the full paper than nothing.

Nothing is posted to Discord from here. This script writes the site post
and a notify.json manifest; notify.py posts the link once GitHub Pages has
actually deployed it.

Every step is a plain HTTP GET + HTML parse -- no browser automation. The
"quiz"/15s-timer/popups on this site are pure client-side UI theater: the
server embeds the one-time download token in the redirect response
regardless of whether a human ever interacts with the page.
"""

import os
import sys
import re
import json
import socket
import logging
import urllib.parse
from datetime import timedelta


import requests
import urllib3.util.connection
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pymupdf
from bs4 import BeautifulSoup

import common
import editorial
import site_publish

BASE_URL = "https://www.indiags.com/epaper-pdf-download"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# paper title on site -> (display name, masthead pattern)
#
# The pattern is matched against a *normalised* line (lowercased, every run
# of non-alphanumerics collapsed to one space) and must match the line in
# full. That full-line requirement is what rejects the front-page teasers
# both papers run -- "the editorial page release 2017 18 consumption data
# ..." and "editorials and opinions" both contain the phrase but are not
# the masthead.
#
# There is deliberately no "which locator to use" column any more: the
# tier is measured per document from the PDF itself.
PAPERS = {
    "The Hindu": ("The Hindu", re.compile(r"editorial")),
    "Indian Express": ("Indian Express", re.compile(r"(the )?editorial page")),
}
PAPER_CODES = {"The Hindu": "TH", "Indian Express": "IE"}
SOURCE = "indiags"

# Manifest handed to notify.py. Written only when something was actually
# published this run, which is what makes re-runs idempotent: a re-run
# short-circuits on already_processed, writes no manifest, and notify.py
# then has nothing to post.
NOTIFY_FILE = "notify.json"

# Sanity gates on the downloaded file, before it is treated as a paper.
# These exist because the failure that hid longest in this system was a
# *successful* download of the wrong thing -- the previous source served a
# Razorpay payment page for six green runs while the history recorded
# "skipped_not_published" each day.
MIN_PDF_BYTES = 1_000_000
MIN_PAGES = 8

common.configure_logging()
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
        applies to every other outbound request in the process. That's
        intended (nothing here wants IPv6) but it is a side effect
        beyond this session object.
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


def _validate_download(content, content_type, display_name):
    """Reject anything that isn't plausibly a full newspaper PDF."""
    if "pdf" not in content_type:
        raise RuntimeError(
            f"{display_name}: token url returned {content_type or 'no content-type'}, not a PDF"
        )
    if not content.startswith(b"%PDF"):
        raise RuntimeError(f"{display_name}: response body is not a PDF (bad magic bytes)")
    if len(content) < MIN_PDF_BYTES:
        raise RuntimeError(
            f"{display_name}: PDF is only {len(content) / 1e6:.2f} MB, "
            f"below the {MIN_PDF_BYTES / 1e6:.2f} MB floor for a full edition"
        )


def _check_freshness(doc, page_idx, display_name, today):
    """Warn if the edition's printed date isn't today's (or yesterday's).

    Best-effort and non-fatal. An unreadable dateline is not evidence that
    the edition is stale, and refusing to publish on that basis would turn
    a cosmetic change into an outage. A *readable* dateline that disagrees,
    though, means we fetched the wrong day's paper -- worth saying loudly
    while still shipping what we have.
    """
    printed = editorial.edition_date(doc, page_idx)
    if printed is None:
        logger.warning("%s: could not read an edition date to verify freshness", display_name)
        return
    if printed not in (today.date(), today.date() - timedelta(days=1)):
        common.report_problem(
            f"{display_name}: edition date looks stale",
            f"The PDF is dated {printed:%d %B %Y} but today is "
            f"{today:%d %B %Y}. The source may be serving a cached or "
            f"wrong-day edition. Published anyway.",
            level="warning",
        )


def process_paper(session, site_title, display_name, header_re, book_id, history, today):
    """Fetch, locate, publish one paper. Returns (ok, located_via|None)."""
    date_key = today.strftime("%Y-%m-%d")
    month_key = today.strftime("%m-%Y")

    if common.already_processed(history, date_key, month_key, display_name):
        logger.info("%s already processed today", display_name)
        return True, None

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
    _validate_download(r.content, r.headers.get("Content-Type", ""), display_name)

    artifact_dir = common.artifact_dir_for(date_key)
    full_pdf_path = os.path.join(
        artifact_dir, common.dated_filename(display_name, "FULL", today, "pdf")
    )
    with open(full_pdf_path, "wb") as f:
        f.write(r.content)

    doc = pymupdf.open(full_pdf_path)
    try:
        if len(doc) < MIN_PAGES:
            raise RuntimeError(
                f"{display_name}: PDF has only {len(doc)} pages, "
                f"below the {MIN_PAGES}-page floor for a full edition"
            )

        page_idx, located_via = editorial.locate_editorial_page(doc, header_re)
        _check_freshness(doc, page_idx if page_idx is not None else 0, display_name, today)

        if located_via == "ocr-fallback":
            # Succeeded, but only because OCR covered for a text layer that
            # should have worked. That is the drift alarm: it fires on the
            # first day the layout moves, rather than after a streak.
            common.report_problem(
                f"{display_name}: editorial page found by OCR, not the text layer",
                f"The PDF's text layer decodes fine, but the masthead wasn't "
                f"where the text locator looks -- OCR found it on page "
                f"{page_idx + 1}. The page layout has moved. The run succeeded "
                f"on the slow path; fix the text locator in editorial.py "
                f"before OCR drifts too.",
                level="warning",
            )

        if located_via == "full":
            ok = _publish_full_edition(
                display_name, full_pdf_path,
                common.artifact_branch_path(artifact_dir), history,
                date_key, month_key, today,
            )
            return ok, "full"

        page_pdf_path = os.path.join(
            artifact_dir, common.dated_filename(display_name, "EDITORIAL", today, "pdf")
        )
        editorial.extract_single_page_pdf(doc, page_idx, page_pdf_path)

        article_paths = []
        if PAPER_CODES[display_name] == "TH":
            for i, png_bytes in enumerate(editorial.extract_hindu_articles(doc, page_idx), start=1):
                p = os.path.join(
                    artifact_dir, common.dated_filename(display_name, "ART", today, "png", part=i)
                )
                with open(p, "wb") as f:
                    f.write(png_bytes)
                article_paths.append(p)
    finally:
        doc.close()

    os.remove(full_pdf_path)

    site_publish.publish_post(
        display_name, PAPER_CODES[display_name], today,
        page_pdf_path, article_image_paths=article_paths or None,
    )

    common.record_history(
        history, date_key, month_key, display_name,
        {
            "status": "published",
            "source": SOURCE,
            "resolved_via": how,
            "located_via": located_via,
            "editorial_page_index": page_idx,
            "artifact_dir": common.artifact_branch_path(artifact_dir),
            "timestamp": common.now_ist().isoformat(),
        },
    )
    return True, located_via


def _publish_full_edition(display_name, full_pdf_path, artifact_dir, history,
                          date_key, month_key, today):
    """Neither locator found the editorial page -- ship the whole paper.

    The full edition is kept rather than deleted, so the day still produces
    something readable *and* the exact PDF that defeated both locators is
    preserved for diagnosis. Previously this path deleted the download and
    recorded a skip, which is why the last breakage could not be
    reproduced after the fact.

    A run of these is a different matter: it means both tiers are dead, and
    full editions are several MB each committed into git history forever.
    So three consecutive days is treated as an outage and fails the run.
    """
    logger.warning("%s: editorial page not found -- publishing the full edition", display_name)

    site_publish.publish_post(
        display_name, PAPER_CODES[display_name], today,
        full_pdf_path, is_full_edition=True,
    )
    common.record_history(
        history, date_key, month_key, display_name,
        {
            "status": "published_full_edition",
            "source": SOURCE,
            "located_via": "full",
            "artifact_dir": artifact_dir,
            "timestamp": common.now_ist().isoformat(),
        },
    )

    streak = common.consecutive_full_editions(history, display_name, today, SOURCE) + 1
    if streak >= common.FULL_EDITION_STREAK_LIMIT:
        common.report_problem(
            f"{display_name}: {streak}-day full-edition streak",
            f"{display_name} has fallen back to publishing the full edition for "
            f"{streak} consecutive days, meaning neither the text-layer locator "
            f"nor OCR can find the editorial masthead. Both are broken, and each "
            f"day adds a multi-MB PDF to git history permanently. Check whether "
            f"the masthead wording or layout changed.",
        )
        return False

    common.report_problem(
        f"{display_name}: editorial page not found, published full edition",
        f"Neither the text-layer locator nor OCR found the masthead in today's "
        f"PDF, so the complete edition was published instead. Today's PDF is "
        f"kept at `{full_pdf_path}` for inspection.",
        level="warning",
    )
    return True


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
    published = []
    for site_title, (display_name, header_re) in PAPERS.items():
        book_id = book_ids.get(site_title)
        if not book_id:
            logger.error("%s not found on indiags homepage today", site_title)
            failures.append(f"{display_name}: no book link on the homepage")
            overall_ok = False
            continue
        try:
            ok, located_via = process_paper(
                session, site_title, display_name, header_re, book_id, history, today
            )
            overall_ok = overall_ok and ok
            if located_via:
                published.append({"name": display_name, "located_via": located_via})
        except Exception as e:
            logger.error("Error processing %s: %s", display_name, e)
            failures.append(f"{display_name}: {e}")
            overall_ok = False

    if published:
        _write_notify_manifest(published, today)

    # Streak and drift alerts raise their own, more specific reports, so
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


def _write_notify_manifest(published, today):
    """Hand notify.py what to say, once Pages has deployed the post."""
    manifest = {
        "date": today.strftime("%Y-%m-%d"),
        "date_display": today.strftime("%d %B %Y"),
        "url": common.site_post_url(today),
        "papers": published,
    }
    with open(NOTIFY_FILE, "w") as f:
        json.dump(manifest, f, indent=2)
    logger.info("Wrote %s for %d paper(s)", NOTIFY_FILE, len(published))


if __name__ == "__main__":
    main()
