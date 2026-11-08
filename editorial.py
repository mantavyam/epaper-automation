#!/usr/bin/env python3
"""
Editorial-page location and extraction.

Locating the editorial page is tiered, and which tier runs is *measured*
per document rather than configured per paper:

  1. "text" -- the PDF has a usable text layer, so the masthead line is
     found directly. Exact and fast (~0.4s for an 18-page edition).
  2. "ocr" -- the text layer is missing or unusable, or tier 1 found
     nothing. The top strip of each page is rendered and OCR'd. Slower
     (~20-40s with early exit) but independent of the text layer entirely.
  3. neither matched. The caller ships the full edition instead; see
     scraper.process_paper.

Tier 1 falling through to tier 2 is itself a signal worth alerting on: it
means a paper whose text layer used to work has changed, and the run is
now on the slow path.

Why tiers rather than a per-paper mode flag: The Hindu ships a clean text
layer (100% of its non-space characters extract as real text), while
Indian Express embeds every font as Identity-H with a ToUnicode CMap that
maps every glyph to U+FFFD -- so its text layer *exists* (~20k chars a
page) but decodes to control bytes, and only 19% of characters survive.
Measuring that ratio picks the right tier on its own, and keeps picking
the right one if either paper changes its production pipeline.
"""

import io
import re
import logging
from datetime import date

import pymupdf

logger = logging.getLogger(__name__)

# Rendering resolution for every OCR path. Not a tuning knob: at 150 dpi
# tesseract missed The Hindu's masthead entirely on a page where 200 dpi
# read it cleanly.
OCR_DPI = 200

# Share of page height treated as "the masthead area". Also not a knob:
# at 0.15 the Indian Express masthead fell outside the strip and the page
# was missed.
TOP_FRAC = 0.25

# Every page is searched, the first included. indiags trims the paper
# before uploading, so the editorial page can sit at index 0 or 1 -- it
# was at index 1 on 2026-11-03 and 11-05, which an old "skip the first two
# pages" guard against front-page teasers missed. The teasers ("The
# Editorial Page: Release 2017-18 consumption data...") are rejected by
# the normalised full-line match below, not by skipping pages.

# Editions indiags sometimes uploads under the main paper's card that
# carry no editorial page: The Hindu's children's supplement (2026-11-07)
# and a Sunday upload of only pages 8-14 (2026-11-01). Checked only after
# both locators fail, so a Sunday paper that does have its editorial page
# is still published.
NON_EDITORIAL_EDITIONS = [
    (re.compile(r"\bin school\b"), "The Hindu In School"),
    (re.compile(r"\bsunday\b"), "Sunday edition"),
]

_NORM_RE = re.compile(r"[^a-z0-9]+")

_MONTHS = ("january february march april may june july august september "
           "october november december").split()
_DATE_RE = re.compile(rf"({'|'.join(_MONTHS)}) (\d{{1,2}}) (\d{{4}})")


def _normalize(text):
    """Lowercase, and reduce every run of non-alphanumerics to one space.

    OCR output is dirty in ways an exact match can't survive -- The
    Hindu's masthead came back as '. Editorial =' -- while the decoys we
    must reject differ from the masthead in *words*, not punctuation. So
    normalise punctuation away and match the whole remaining line.
    """
    return _NORM_RE.sub(" ", text.lower()).strip()


def text_layer_usable(doc, threshold=0.5):
    """Does this PDF's text layer decode to real characters?

    Measured, because "has a text layer" and "has a *usable* text layer"
    are different questions -- see the module docstring. The Hindu scores
    1.00 and Indian Express 0.19, so the threshold sits in a very wide gap
    and needs no tuning.
    """
    good = total = 0
    for page in doc:
        for ch in page.get_text():
            if ch.isspace():
                continue
            total += 1
            if ch.isprintable() and ch != "�":
                good += 1
    if not total:
        return False
    return good / total >= threshold


def _ocr_strip(page, top_frac=TOP_FRAC, dpi=OCR_DPI):
    """OCR the masthead strip at the top of one page."""
    import pytesseract
    from PIL import Image

    rect = page.rect
    clip = pymupdf.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + rect.height * top_frac)
    zoom = dpi / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip)
    return pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes("png"))))


def _matches(line, header_re, backup_re):
    """The masthead as the whole line, or the backup marker anywhere in it."""
    norm = _normalize(line)
    return bool(header_re.fullmatch(norm) or (backup_re and backup_re.search(norm)))


def _locate_via_text(doc, header_re, top_frac, backup_re=None):
    """Find the masthead in the text layer, gated on where it sits.

    Matched on geometry (the line's y-position), not on its ordinal among
    extracted lines. Text comes out in content-stream order, not
    top-to-bottom, so a stray caption block can be emitted before the
    masthead and shift every following line down by one -- which is what
    silently broke the original locator: the header sat at the very edge
    of a fixed line-count window, and any such shift pushed it out,
    reporting "no editorial page" on days the paper had published one.
    """
    for i, page in enumerate(doc):
        cutoff = page.rect.y0 + page.rect.height * top_frac
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                if line["bbox"][1] > cutoff:
                    continue
                text = "".join(s["text"] for s in line["spans"])
                if _matches(text, header_re, backup_re):
                    return i
    return None


def _locate_via_ocr(doc, header_re, top_frac, dpi, backup_re=None):
    """Find the masthead by OCR'ing each page's top strip.

    Returns on the first hit rather than sweeping the whole edition --
    a full sweep of a 22-page paper costs ~60s against ~38s stopping at
    the editorial page.
    """
    for i, page in enumerate(doc):
        for line in _ocr_strip(page, top_frac, dpi).split("\n"):
            if _matches(line, header_re, backup_re):
                return i
    return None


def locate_editorial_page(doc, header_re, backup_re=None, top_frac=TOP_FRAC, dpi=OCR_DPI):
    """Locate the editorial page. Returns (page_index, how).

    backup_re is a second marker that only appears on the editorial page
    (Indian Express's "Wordly Wise" column), searched for anywhere in a
    line of the top strip. It covers days OCR garbles the masthead itself,
    as on 2026-11-04.

    how is one of:
      "text"         -- found in a usable text layer. The good path.
      "ocr"          -- the text layer was unusable, so OCR found it.
                        Normal and expected for Indian Express.
      "ocr-fallback" -- the text layer was usable but did NOT contain the
                        masthead, and OCR found it anyway. That combination
                        is only possible if the paper's text-layer layout
                        moved, so callers should treat it as a drift alarm
                        even though the run succeeded.
      "full"         -- neither tier found it; the caller's cue to ship the
                        whole edition rather than skip the paper.
    """
    usable = text_layer_usable(doc)
    if usable:
        index = _locate_via_text(doc, header_re, top_frac, backup_re)
        if index is not None:
            return index, "text"
        logger.warning(
            "text layer is usable but the masthead wasn't found in it "
            "-- falling back to OCR"
        )

    index = _locate_via_ocr(doc, header_re, top_frac, dpi, backup_re)
    if index is not None:
        return index, "ocr-fallback" if usable else "ocr"
    return None, "full"


def non_editorial_edition(doc, top_frac=0.1):
    """Name the edition if it's one that has no editorial page, else None.

    Reads each page's header strip -- the text layer when it decodes, OCR
    otherwise -- for the markers in NON_EDITORIAL_EDITIONS.
    """
    usable = text_layer_usable(doc)
    for page in doc:
        if usable:
            r = page.rect
            strip = page.get_text(clip=pymupdf.Rect(r.x0, r.y0, r.x1, r.y0 + r.height * top_frac))
        else:
            strip = _ocr_strip(page, top_frac)
        text = _normalize(strip)
        for pattern, label in NON_EDITORIAL_EDITIONS:
            if pattern.search(text):
                return label
    return None


def edition_date(doc, page_index, top_frac=TOP_FRAC, dpi=OCR_DPI):
    """The date printed on a page, or None if it isn't readable.

    Both papers print a dateline in the masthead area ("Friday, September
    18, 2026"). Read from the text layer where that decodes, and from the
    page's OCR strip otherwise. Best-effort by design: the caller warns on
    a mismatch rather than failing, since an unreadable dateline is not
    itself evidence that the edition is wrong.
    """
    page = doc[page_index]
    text = _normalize(page.get_text())
    if not _DATE_RE.search(text):
        text = _normalize(_ocr_strip(page, top_frac, dpi))

    m = _DATE_RE.search(text)
    if not m:
        return None
    try:
        return date(int(m.group(3)), _MONTHS.index(m.group(1)) + 1, int(m.group(2)))
    except ValueError:
        return None


def extract_single_page_pdf(doc, page_index, out_path):
    """Save one page of `doc` as its own compact PDF."""
    single = pymupdf.open()
    single.insert_pdf(doc, from_page=page_index, to_page=page_index)
    single.save(out_path, garbage=4, deflate=True)
    single.close()
    return out_path


def _find_sidebar_boundary(page, drawings):
    """Full-height vertical rule marking off the short-pieces sidebar column.

    Returns the x-coordinate of the boundary (content starts to its right),
    or 0.0 if no such rule is present (nothing to exclude).
    """
    tall = [
        d["rect"] for d in drawings
        if d["rect"].height > page.rect.height * 0.7 and d["rect"].width < 3
    ]
    if not tall:
        return 0.0
    # leftmost tall rule = sidebar/content divider
    tall.sort(key=lambda r: r.x0)
    return tall[0].x1


def _find_content_dividers(page, drawings, content_x0, min_width_frac=0.5):
    """Horizontal rules that start at the content column (not the full-width
    masthead rule) and span a large share of the content width -- these
    bound individual articles."""
    content_width = page.rect.width - content_x0
    lines = []
    for d in drawings:
        r = d["rect"]
        if r.height >= 3:
            continue
        if r.width < content_width * min_width_frac:
            continue
        if r.x0 < content_x0 - 5 or r.x0 > content_x0 + 60:
            continue
        lines.append(r)
    lines.sort(key=lambda r: r.y0)
    return lines


def extract_hindu_articles(doc, page_index, dpi=OCR_DPI):
    """Crop the two main editorial articles as high-res PNG bytes.

    Uses vector rule geometry (the PDF's own drawn lines), not pixel
    heuristics: a full-height vertical rule marks off the sidebar column
    (short filler pieces, excluded); horizontal rules within the content
    column bound each article. The Hindu always runs exactly two main
    articles on this page, followed by a Letters-to-the-Editor block that
    is dropped unconditionally.

    Returns a list of PNG bytes -- always empty, never raises, if the page
    doesn't carry usable vector rule geometry (Indian Express draws no
    rules at all on its editorial page, and a full-edition fallback page
    won't match this layout either). Article images are a nice-to-have on
    top of the page PDF, which is the deliverable that must always go
    through regardless -- so any failure here degrades silently rather
    than aborting the caller's run.
    """
    try:
        page = doc[page_index]
        drawings = page.get_drawings()

        sidebar_x = _find_sidebar_boundary(page, drawings)
        content_x0 = sidebar_x
        dividers = _find_content_dividers(page, drawings, content_x0)

        if len(dividers) < 2:
            logger.warning(
                "editorial rule geometry unclear (found %d content dividers, need 2) "
                "-- this PDF doesn't support article cropping, skipping",
                len(dividers),
            )
            return []

        # top of article 1 = top of the sidebar rule (roughly where the big
        # headline starts), falling back to the page's own top margin
        tall = [
            d["rect"] for d in drawings
            if d["rect"].height > page.rect.height * 0.7 and d["rect"].width < 3
        ]
        top_y = min((r.y0 for r in tall), default=page.rect.y0 + page.rect.height * 0.05)

        bounds = [top_y] + [d.y0 for d in dividers[:2]]
        zoom = dpi / 72
        images = []
        for y0, y1 in zip(bounds[:-1], bounds[1:]):
            clip = pymupdf.Rect(content_x0, y0, page.rect.width, y1)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip)
            images.append(pix.tobytes("png"))

        return images
    except Exception as e:
        logger.warning("Article extraction failed unexpectedly (%s) -- skipping, page PDF unaffected", e)
        return []
