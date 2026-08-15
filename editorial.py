#!/usr/bin/env python3
"""
Editorial-page location and extraction.

Two ways to find the editorial page, depending on how usable the PDF's
text layer is:
  - "text" mode (The Hindu): the PDF has a clean text layer. The page
    header always carries a standalone line reading exactly "Editorial".
  - "ocr" mode (Indian Express): the PDF page is a flattened raster image
    with a broken/glyph-indexed text layer, so text search is unreliable.
    OCR the top strip of each page and look for "The Editorial Page".

Both return None when no page matches -- that means the paper didn't
publish an editorial today (Sunday, holiday), and callers should skip
posting for that paper rather than guessing.
"""

import io
import re
import logging

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

HINDU_HEADER = "editorial"
IE_HEADER_RE = re.compile(r"editorial\s*page", re.IGNORECASE)


def locate_editorial_page_text(doc, header=HINDU_HEADER, top_lines=8):
    """Scan each page's top text lines for an exact masthead match."""
    for i, page in enumerate(doc):
        text = page.get_text()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines[:top_lines]:
            if line.lower() == header:
                return i
    return None


def locate_editorial_page_ocr(doc, pattern=IE_HEADER_RE, top_frac=0.20, dpi=200, max_line_len=30):
    """OCR the top strip of each page, looking for a standalone masthead line.

    Scoped to the top of the page, and matched line-by-line rather than
    against the whole strip: the front page carries a teaser banner like
    "The Editorial Page: SC has nurtured environmental law..." pointing
    readers to the real page, which also matches the phrase but is a long
    sentence with a colon, not the actual masthead. The real masthead is a
    short standalone line (just "The Editorial Page", no colon/summary),
    so a max-length gate cleanly tells them apart.
    """
    import pytesseract
    from PIL import Image

    for i, page in enumerate(doc):
        rect = page.rect
        clip = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + rect.height * top_frac)
        zoom = dpi / 72
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img)
        for line in text.split("\n"):
            line = line.strip()
            if pattern.search(line) and len(line) <= max_line_len:
                return i
    return None


def extract_single_page_pdf(doc, page_index, out_path):
    """Save one page of `doc` as its own compact PDF."""
    single = fitz.open()
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


def extract_hindu_articles(doc, page_index, dpi=200):
    """Crop the two main editorial articles as high-res PNG bytes.

    Uses vector rule geometry (the PDF's own drawn lines), not pixel
    heuristics: a full-height vertical rule marks off the sidebar column
    (short filler pieces, excluded); horizontal rules within the content
    column bound each article. The Hindu always runs exactly two main
    articles on this page, followed by a Letters-to-the-Editor block that
    is dropped unconditionally.

    Returns a list of PNG bytes -- always empty, never raises, if the page
    doesn't carry usable vector rule geometry (a raster/flattened page like
    Indian Express's, or any PDF that just doesn't match this rule layout).
    Article images are a nice-to-have on top of the single-page PDF, which
    is the deliverable that must always go through regardless -- so any
    failure here degrades silently rather than aborting the caller's run.
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
            clip = fitz.Rect(content_x0, y0, page.rect.width, y1)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
            images.append(pix.tobytes("png"))

        return images
    except Exception as e:
        logger.warning("Article extraction failed unexpectedly (%s) -- skipping, single-page PDF unaffected", e)
        return []
