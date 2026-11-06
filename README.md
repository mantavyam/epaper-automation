# E-Paper Editorial Extractor

Pulls the Editorial page out of today's **The Hindu** and **Indian Express** e-papers, publishes it to a small static site, and posts the link to Discord — the single page as a PDF, plus (for The Hindu) each main article cropped out as its own image. Runs on a GitHub Actions cron, no server to maintain.

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## How it works

One GitHub Actions workflow, one source (indiags.com), both papers. It's a plain HTTP scraper — no Selenium, no headless browser, no Chrome install. Every page in the chain is static server-rendered HTML or a direct file link; nothing here needs JavaScript execution.

```mermaid
flowchart TD
    cron["cron: 10:00 IST\n+ retries at 10:30, 11:00"] --> run["daily-newspaper.yml"]
    manual["workflow_dispatch\n(manual run)"] --> run
    run -->|"indiags.com\n4-hop link chain"| pdfs["The Hindu +\nIndian Express PDFs"]
    pdfs --> locate["locate Editorial page\n(tier 1: text layer\ntier 2: masthead OCR)"]
    locate --> single["extract single page\nas PDF"]
    locate --> crop["crop 2 articles\n(Hindu only,\nvector rule geometry)"]
    locate -->|"tier 3:\nneither found it"| full["publish the\nfull edition"]
    single --> rel["GitHub Release\neditorial-YYYY-MM-DD\n(files + run ledger)"]
    crop --> rel
    full --> rel
    rel --> pages["pages.yml: build site\nfrom live releases,\ndeploy (workflow waits)"]
    pages --> discord["Discord: link\nto the day's page"]
```

### Source: indiags.com

`scraper.py` covers both papers by walking a four-hop link chain per paper, entirely with `requests`:

```mermaid
sequenceDiagram
    participant S as scraper
    participant Site as indiags.com

    S->>Site: GET /epaper-pdf-download
    Site-->>S: card grid (paper title -> book id)
    S->>Site: GET /epaper/books/{id}
    Site-->>S: "Download Newspaper" link
    S->>Site: GET /epaper/newsletter/{id}
    Site-->>S: "Unlock via Quiz" link
    S->>Site: GET /epaper/open/{id}
    Site-->>S: 302 -> quiz page URL#unlock=/go/{token}&exp={epoch}
    S->>Site: GET /go/{token}
    Site-->>S: PDF bytes (200, one-time use)
```

The site's UI wraps this in a quiz-unlock button, a 15-second countdown banner, and assorted popups — all client-side theater. The server embeds the one-time download token in the redirect response the moment `/epaper/open/{id}` is requested, regardless of whether a human ever clicks anything. The `/go/{token}` link is genuinely single-use: a second request against the same token returns an HTML page instead of the PDF, so it's fetched exactly once and streamed straight into the extraction step, never posted as a raw link.

**Parse the unlock fragment as a query string, not by splitting on `unlock=`.** The redirect fragment carries two keys — `unlock=<url-encoded /go/ link>&exp=<epoch>`. Taking everything after `unlock=` glues `&exp=...` onto the end of the token path, and every download 404s. `urllib.parse.parse_qs` on the fragment is what `resolve_token_url()` uses; assume the site will keep adding keys there.

**The session is IPv4-only with connect retries** (`build_session()`). indiags sits behind a Hostinger CDN publishing both A and AAAA records, and intermittently refuses connections from CI runners for a few minutes at a time. GitHub Actions runners have no IPv6 egress, so every AAAA address is a guaranteed `ENETUNREACH` — and since `urllib3`'s connect loop raises only the *last* error it saw, those IPv6 failures mask the real IPv4 error and make a plain CDN blip look like a routing bug. Pinning `allowed_gai_family` to `AF_INET` keeps the reported error honest, and the retry/backoff on the adapter keeps a transient blip from costing the whole day's run.

Editorial-page location is **tiered, and which tier runs is measured per document** rather than configured per paper (`editorial.locate_editorial_page()`):

1. **text** — the PDF's text layer decodes, so the masthead line is read straight out of it. Exact and fast (~0.4s for an 18-page edition). The match is gated on *where the line sits on the page*, not on its ordinal among extracted lines: text comes out in content-stream order, not top-to-bottom, so a stray caption block emitted first shifts every following line down by one. That is exactly what silently broke the original locator, which used a fixed `lines[:8]` window with the masthead sitting at index 7.
2. **ocr** — the text layer is missing or unusable, or tier 1 found nothing. The top 25% of each page is rendered at 200 DPI and read with `pytesseract`, stopping at the first hit (~20–40s). Neither number is a tuning knob: at 150 DPI tesseract missed The Hindu's masthead on a page 200 DPI read cleanly, and at a 15% strip the Indian Express masthead fell outside the crop entirely.
3. **full** — neither tier found it. The whole edition is published instead of skipping the paper; the PDF is in hand either way, and a reader would rather have the full paper than nothing.

`text_layer_usable()` is what picks the tier: the share of non-space extracted characters that decode to real text. The Hindu scores **1.00**; Indian Express scores **0.19** — it embeds every font as `Identity-H` with a `ToUnicode` CMap mapping every glyph to `U+FFFD`, so its text layer *exists* (~20k characters a page) but decodes to control bytes. The threshold sits in a very wide gap and needs no tuning. Measuring beats a hardcoded per-paper flag: it keeps picking the right tier if either paper changes its production pipeline.

Masthead patterns are matched against a **normalised** line — lowercased, every run of non-alphanumerics collapsed to one space — and must match it *in full*. Both parts earn their place. Normalisation, because OCR output is dirty in ways exact matching can't survive (The Hindu's masthead came back as `. Editorial =`). Full-line matching, because the decoys differ from the masthead in *words*, not punctuation: on 2026-09-18 the Indian Express edition carried `the editorial page release 2017 18 consumption data put all doubt to rest` (a front-page teaser), `naging editor and director of re` (masthead bleed) and `editorials and opinions` (a section strap), all rejected, with the real `the editorial page` found on page 14. Note the teaser was on **page 5** — skipping the first two pages is a cheap extra guard, not a sufficient one.

The Hindu's PDF carries vector rule geometry, so its two main articles are cropped from the page. `PyMuPDF`'s `get_drawings()` returns the exact rules the page was laid out with:

- a full-height vertical rule marks off the left sidebar (short filler pieces) — excluded
- horizontal rules within the remaining content column bound each article, in order
- The Hindu always runs exactly two main articles on this page, followed by Letters to the Editor, which is dropped unconditionally

Each article is rendered to a high-resolution PNG from its exact rule-bounded region. Indian Express stays page-PDF-only: `get_drawings()` returns nothing at all on its editorial page. The rules and photos a reader sees there live in a full-page background raster, with the text drawn as vector glyphs on top — so there is no rule geometry to crop against, and none is detectable at the pixel level either (tested down to per-row dark-run analysis at 200 DPI).

### Guardrails

Both real breakages so far were *silent* — a green workflow producing nothing. preppyq's paywall hid for six consecutive runs, and the `&exp=` change 404'd every download while the run still reported success. So the guards are aimed less at any particular future change than at the failure *mode*: looking fine while doing nothing.

**Link resolution is ranked by how stable the locator is** (`_resolve_link()`). The URL path shape (`/epaper/newsletter/{id}`) comes first — the author can't change it without breaking their own routing — with the CSS class and then the button label as fallbacks. The original code used only the last two, which is why a theme tweak or a copy edit would have taken the whole run down. Verified against mutated copies of the live homepage: stripping *every* `class` attribute, renaming all three card classes, and rewording the paper titles to "The Hindu ePaper" / "Indian Express (Delhi)" all still resolve correctly.

Which locator actually fired is recorded in the day's release ledger as `resolved_via`, and anything other than `url-shape` logs a warning. That's the early-warning signal: the fallbacks firing means the shape moved and the chain is running on borrowed time, visible *before* it breaks.

**The one-time `/go/` token is looked for in three places** (`_extract_go_url()`) — fragment as a query string, then the query string proper, then anything `/go/`-shaped in the response body. The site has already moved this once; parsing the fragment with `parse_qs` means further added keys are a non-event.

**Nothing is ever silently skipped.** The old behaviour recorded `skipped_not_published` whenever the locator found nothing, which is indistinguishable from the paper genuinely not running an editorial — and that ambiguity is what hid the last breakage for six days. Now the tiers themselves carry the diagnosis, recorded in the ledger as `located_via`:

| `located_via` | meaning | alert |
|---|---|---|
| `text` | found in a usable text layer | — |
| `ocr` | text layer unusable, OCR found it | — (normal for Indian Express) |
| `ocr-fallback` | text layer *was* usable but didn't contain the masthead; OCR covered | **warning, day 1** |
| `full` | neither tier found it; whole edition published | **warning, day 1** |

`ocr-fallback` is the valuable one: that combination is only possible if the paper's text-layer layout moved, so the drift alarm fires on the first day it happens rather than after a streak of quiet skips — while the run still succeeds on the slow path.

**A run of full-edition fallbacks fails the run** (`common.consecutive_full_editions()`). One is survivable; three consecutive days means both tiers are dead. Two details matter — days with no entry are stepped over (the workflow doesn't run every day, and a gap is not evidence), and an entry from a different `source` ends the walk, so switching sources doesn't inherit the previous one's streak.

**The download is sanity-checked before it's treated as a paper** (`_validate_download()`): `Content-Type`, `%PDF` magic bytes, a 1 MB floor and a 4-page floor (indiags now serves curated ~6-page "UPSC" cuts, not whole editions). A paper whose homepage card links to `/epaper-subscription?paper=` is paywalled server-side that day — logged as a notice and skipped, not raised as a failure. To unlock those, the run first logs in (`login()`) with `INDIAGS_EMAIL` / `INDIAGS_PASSWORD` when set; a failed login is reported as a warning and the run continues anonymously. The longest-hiding failure in this system was a *successful* download of the wrong thing — see below. The edition's printed dateline is also parsed and compared against today's date, warning (but still publishing) on a mismatch, which catches a source serving a cached or wrong-day edition.

**A tier-3 PDF is kept, not deleted.** The full edition is attached to the day's release, so the exact file that defeated both locators is available for diagnosis. The previous code deleted the download on the skip path, which is precisely why the last breakage couldn't be reproduced after the fact.

**The schedule fires three times, not once** — 10:00 IST with retries at 10:30 and 11:00. indiags sits behind a Hostinger CDN that intermittently refuses connections from GitHub runners for stretches at a time; on 2026-09-18 two of three dispatches died with `ConnectTimeoutError` on every address while the same URL served in 0.33s from elsewhere, and a single daily shot loses the whole day to that. The retries are free when the first run worked: `already_processed()` short-circuits every paper (it reads today's release), and both the site rebuild and the Discord post are gated on `steps.extract.outputs.site_changed` — true only if a paper was published or an expired release deleted — so a no-op run doesn't dispatch a Pages deploy or send a second message.

**Problems are reported, not delivered, by the scraper** (`common.report_problem()`). Nothing diagnostic goes to Discord — that webhook points at a public community server, so it stays single-purpose: posting editorials. Instead each problem is written to three places that need no secret at all — a GitHub Actions annotation (called out inline on the run page), `$GITHUB_STEP_SUMMARY` (so the run page explains itself), and `failure-report.md`.

The workflow turns that file into **a GitHub Issue**, which is what actually reaches an inbox: GitHub mails the full issue body from `notifications@github.com`, alongside the automated run-failure mail — whose own template can't carry custom text, which is why the issue exists at all. One open issue at a time, matched on exact title, so a break persisting for days adds comments rather than mailing a new issue every run; a later clean run comments "Recovered" and closes it. The issue step runs on success too, because the early-warning report fires while everything still works.

`HopError` also writes the offending page to `hop-{what}.html`, collected by the workflow's `upload-artifact` step — previously that step was dead, since nothing ever wrote a `*.html` file. None of these diagnostics are committed (they're in `.gitignore`).

**This needs Issues enabled on the repo.** The step runs with `issues: write` on the default `GITHUB_TOKEN`; if Issues are turned off, `gh issue list` fails and the step goes red.

### Why preppyq.in was dropped

The original primary source was `preppyq.in`, a static WordPress page listing direct PDF links for The Hindu. It went behind a paywall: the table's links now point at `rzp.io` Razorpay payment pages instead of PDFs. That failed *silently* — the scraper downloaded the payment page's HTML, found no `Editorial` text in it, and recorded the day as `skipped_not_published`, so the workflow kept reporting success while producing nothing. Removed entirely rather than kept as a fallback; a source that fails by looking like a quiet no-op is worse than no source.

## The site

Each date gets one Jekyll post, however many papers ran, on a small static site (`app/`, a customized [jekyll-swiss](https://github.com/broccolini/swiss) theme). The site *is* the delivery mechanism — Discord gets a link to it, not attachments. Posts are **generated at build time from the releases**, not committed.

```mermaid
flowchart LR
    extract["extraction succeeds\n(scraper.py)"] --> rel["releases.publish()\nuploads files to the day's\nrelease, stores its ledger"]
    rel --> dispatch["gh workflow run pages.yml\n(a release doesn't trigger\nany workflow by itself)"]
    dispatch --> build["pages.yml: site_publish.py\ndownloads each live release into\napp/files/, writes app/_posts/,\nthen Jekyll builds & deploys\n(daily workflow waits)"]
    build --> site["GitHub Pages site\n/epaper/DD-MM-YYYY/, one page\nper date, all papers"]
    site --> notify["notify.py posts the\nlink to Discord"]
```

**Why files are copied into the site rather than linked to the release.** Release assets send no `Access-Control-Allow-Origin` header and are served as `application/octet-stream` attachments (re-checked 2026-11-06, both the `github.com/.../releases/download/...` URL and the `release-assets.githubusercontent.com` redirect target). The PDF.js viewer fetches the PDF bytes itself, so a release URL would be CORS-blocked and the preview would silently break. `site_publish.py` instead runs `gh release download` for each release in the window during the Pages build, so every PDF and image is served from the site's own origin. The files live in the deployed Pages artifact, never in git.

**One post per date, not per paper.** `app/_posts/YYYY-MM-DD-editorials.md` is written from the release's ledger, one section per paper in a fixed order (`PAPER_ORDER`), so it doesn't matter which paper ran first or how many retries it took. URL is `/epaper/DD-MM-YYYY/` (`permalink: /epaper/:day-:month-:year/` in `_config.yml`), title "Editorials of DD/MM/YYYY". Content per paper: H1 paper name, H2 sections (Editorial/Articles as applicable), a download-button table (`app/_includes/download-button.html`, using `app/assets/download.svg`) for every downloadable file, and an inline PDF preview.

**PDF preview is a self-hosted PDF.js** (`app/assets/pdfjs/`, vendored once from [mozilla/pdf.js](https://github.com/mozilla/pdf.js) releases, trimmed of source maps/sample files/most locales down to English + Hindi). The iframe points at our own `web/viewer.html?file=<same-origin path>`, and PDF.js renders the bytes to canvas. It's kept in the repo rather than fetched at build time: it's a one-time ~2.7 MB that never grows, and fetching it on every deploy would add a network dependency whose failure skips the day's Discord post.

The vendored `viewer.mjs` carries one hand-patch — our origin (`https://mantavyam.github.io`, plus `http://localhost:4000`) added to `HOSTED_VIEWER_ORIGINS`, from when files were cross-origin on `raw.githubusercontent.com`. With same-origin files it's no longer needed, but harmless; search `viewer.mjs` for `HOSTED_VIEWER_ORIGINS` if PDF.js is ever re-vendored.

**Expiry.** The scraper deletes releases older than 7 days (`releases.prune()`), and the next build simply doesn't see them. The client-side handling in `app/_includes/expiry-check.html` is a safety net for a page cached from before that rebuild: images swap to a placeholder via `onerror`, and each download-button link runs a `fetch(..., {method: "HEAD"})` on page load and replaces itself with "This PDF has expired" if the request fails.

Site is deployed by `.github/workflows/pages.yml` (Python step for `site_publish.py`, then Jekyll via `ruby/setup-ruby` + `actions/deploy-pages`, `jekyll-sass-converter` pinned to the pure-Ruby v2 line rather than the default `sass-embedded` for one less native-binary dependency in CI) on every push touching the site or its builder, manually via `workflow_dispatch`, or explicitly dispatched by the daily workflow. The deploy job only runs from `main`, so `gh workflow run pages.yml --ref <branch>` builds a branch for inspection without replacing the live site. Browsing by date needs no custom code — `site.posts` is Jekyll's native reverse-chronological list; `/epaper/` (`app/epaper.html`) filters it to the `epaper` category. All timestamps go through `common.now_ist()` and `_config.yml`'s `timezone: Asia/Kolkata`, not the build host's own clock (GitHub Actions runners default to UTC) — Jekyll normalizes every post date to the *build machine's* local timezone before deriving permalink components, so without pinning this explicitly, a post published in the early IST morning can silently land on the wrong calendar day.

### Discord gets a link, not files

`notify.py` posts one message per day — the date, which papers ran, and a link to `/epaper/DD-MM-YYYY/`. Plain text: no attachments, and no hand-built embed either (Discord renders a link preview from the page's own metadata, so constructing one only added a coloured sidebar and a duplicate title):

```
Editorials - 18 September 2026
The Hindu
Indian Express

https://mantavyam.github.io/epaper-automation/epaper/18-09-2026/
``` The site already hosts every artifact behind a PDF.js viewer, so a link carries strictly more than an upload did (both papers in one message, article crops inline, working previews) while keeping the message small.

This is why it is a *separate script from a later workflow step*. The link points at a page that doesn't exist until the site has been rebuilt from the releases and deployed; posting it from the extraction step would hand readers a URL that 404s for a minute or two. So `scraper.py` writes `notify.json`, the workflow dispatches `pages.yml` and **waits for that deploy to conclude**, and only then runs `notify.py`. If the deploy fails or never starts, the step is skipped rather than posting a dead link.

Re-runs can't double-post, and it needs no extra state to manage that: `scraper.py` writes the manifest only when it actually published something, and a re-run for a date whose release already lists the paper short-circuits on `already_processed()` before publishing. A re-run therefore leaves no manifest and `notify.py` no-ops.

Posts disappear with their release after the 7-day window, so Discord links older than a week will 404. That's accepted — this is a rolling week of history, not an archive.

### Files and run records live in GitHub Releases

The repo holds code only; the bot never commits. Each date is one release, tagged `editorial-YYYY-MM-DD` (`releases.py`, via the `gh` CLI):

- **Assets** are the day's extracted files. Retries and the second paper add to the same release (`gh release upload --clobber`).
- **The description** holds the run record that used to be `download_history.json` — status, source, `resolved_via`, `located_via` per paper — as JSON in a hidden `<!-- ledger ... -->` comment, under a short readable summary. `common.load_history()` rebuilds the familiar `MM-YYYY -> YYYY-MM-DD -> paper` dict from the live releases, so `already_processed()` and `consecutive_full_editions()` read it unchanged; it reaches back 7 days, which covers the 3-day streak check.
- **Retention**: `releases.prune()` deletes releases (and their tags) older than 7 days on every run. Deleting a release frees its files outright.

History of this decision: files were first committed to `main` (~1.7 MB/day, permanent in history), then to a force-pushed single-commit `artifacts` branch served from `raw.githubusercontent.com` — bounded, but it relied on GitHub garbage-collecting each day's orphaned blobs and every run fetched the ~20 MB window. Releases cost nothing in repo size; the only obstacle was the CORS problem above, which the build-time copy removes.

## Repo layout

```
epaper-automation/
├── scraper.py                              # indiags.com: both papers
├── editorial.py                            # page location + extraction
├── common.py                               # ledger (from releases), reports, Discord posting
├── releases.py                             # GitHub Releases: publish, list, prune, download
├── site_publish.py                         # pages.yml build step: releases -> app/_posts + app/files
├── notify.py                               # posts the day's site link to Discord
├── (release editorial-YYYY-MM-DD)          # NOT in git; deleted after 7 days
│   ├── TH-EDITORIAL-DD-MM-YY.pdf           # single-page editorial PDF
│   ├── TH-ART1-DD-MM-YY.png                # article crop 1 (Hindu only)
│   ├── TH-ART2-DD-MM-YY.png                # article crop 2 (Hindu only)
│   ├── IE-EDITORIAL-DD-MM-YY.pdf
│   └── TH-FULL-DD-MM-YY.pdf                # whole edition, only on a tier-3 fallback
├── app/                                     # Jekyll site (jekyll-swiss theme)
│   ├── _posts/, files/                      # generated at build time from releases (gitignored)
│   ├── epaper.html                          # /epaper/ -- browsable archive
│   ├── _includes/download-button.html      # reusable download link + expiry check hook
│   ├── _includes/expiry-check.html         # client-side expired-artifact handling
│   └── assets/pdfjs/                        # vendored PDF.js (self-hosted inline viewer)
├── requirements.txt
└── .github/workflows/
    ├── daily-newspaper.yml                 # cron + manual dispatch
    └── pages.yml                           # builds + deploys app/ to GitHub Pages
```

## Setup

1. **Discord webhook** — Server Settings → Integrations → Webhooks → create one, copy the URL.
2. **Repo secrets** — Settings → Secrets and variables → Actions → add `DISCORD_WEBHOOK_URL`, plus `INDIAGS_EMAIL` and `INDIAGS_PASSWORD` (an indiags account, used to unlock subscription-locked papers; optional).
3. Enable Actions on the repo. The workflow runs on its own cron; no further setup needed.
4. **GitHub Pages** — Settings → Pages → set Source to "GitHub Actions" (one-time; `pages.yml` handles builds after that).

For local runs, copy `.env.example` to `.env` and export it; publishing needs an authenticated `gh` (`gh auth login`). Set `RELEASE_TAG_PREFIX` to publish under a throwaway prefix instead of the live `editorial-` releases:

```bash
pip install -r requirements.txt
set -a; . ./.env; set +a
RELEASE_TAG_PREFIX=test-editorial- python scraper.py       # publishes test-editorial-YYYY-MM-DD
RELEASE_TAG_PREFIX=test-editorial- python site_publish.py  # builds app/_posts + app/files from them
```

`pytesseract` needs the `tesseract-ocr` binary on PATH (`brew install tesseract` / `apt-get install tesseract-ocr`). Indian Express always needs it; The Hindu only reaches it if its text layer stops working.

## Running manually

The workflow can be triggered off-schedule from the **Actions** tab (`Run workflow`) or via `gh`:

```bash
gh workflow run daily-newspaper.yml
gh workflow run pages.yml
```

`pages.yml` also runs automatically on every push that touches `app/**` (which every extraction run does, via the new post file), so a manual run of it is rarely needed.

## Run record and file lifecycle

Each day's release ledger records, per paper, whether it was `published` or `published_full_edition`, the source, which locator resolved the chain (`resolved_via`) and which tier found the editorial page (`located_via` — see the guardrails table above). The scraper reads the live releases before doing any work, so re-running the workflow the same day is a no-op for papers already posted.

Files are named `{PAPER_CODE}-{DOC_TYPE}[N]-DD-MM-YY.{ext}` (`TH` for The Hindu, `IE` for Indian Express; `EDITORIAL` for the single-page PDF, `ART1`/`ART2` for The Hindu's article crops, `FULL` for a whole edition after a tier-3 fallback), so the paper, content and date are readable from the filename alone. They're staged in `out/YYYY-MM-DD/` (gitignored) and published to the day's release. Every run deletes releases older than **7 days**, and the site — rebuilt from whatever releases remain — stays a rolling week rather than accumulating.

## Dependencies

`requests`, `urllib3`, `beautifulsoup4`, `pymupdf`, `pytesseract`, `Pillow` — all pure-Python/HTTP, no browser runtime.

PyMuPDF is imported as `import pymupdf`, not the legacy `import fitz` alias — deprecated since 1.24.0, and the source of the `fitz API is deprecated` warning that used to head every run log. Log timestamps go through `common.configure_logging()` so they read in IST like the rest of the system, instead of the runner's UTC clock.

## License

See [LICENSE](LICENSE).
