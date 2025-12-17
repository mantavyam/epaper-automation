# 🗺️ System Architecture Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GITHUB ACTIONS                            │
│                     (Ubuntu Runner)                              │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Cron Trigger: Daily 6:00 AM IST (00:30 UTC)          │    │
│  └────────────────────────────────────────────────────────┘    │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  1. Setup Environment                                  │    │
│  │     • Install Python 3.11                             │    │
│  │     • Install Chrome & ChromeDriver                   │    │
│  │     • Install dependencies (requirements.txt)         │    │
│  └────────────────────────────────────────────────────────┘    │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  2. Run scraper.py                                     │    │
│  │     • Load history from JSON                          │    │
│  │     • Initialize Selenium WebDriver                   │    │
│  │     • Execute automation workflow                     │    │
│  └────────────────────────────────────────────────────────┘    │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  3. Commit & Push Changes                              │    │
│  │     • Add new PDFs to repository                      │    │
│  │     • Update download_history.json                    │    │
│  │     • Push to main branch                             │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Scraper Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                      SCRAPER.PY WORKFLOW                         │
└─────────────────────────────────────────────────────────────────┘

START
  │
  ├─► Load download_history.json
  │   └─► Check if today already processed
  │
  ├─► Initialize Chrome WebDriver (headless)
  │
  ├─► Navigate to IndiaGS Homepage
  │   URL: https://www.indiags.com/epaper-pdf-download
  │
  ├─► Parse Homepage HTML
  │   └─► Find newspapers:
  │       ├─► The Hindu
  │       └─► Indian Express
  │
  ├─► For Each Newspaper:
  │   │
  │   ├─► STEP 1: Click "Read" Link
  │   │   └─► Navigate to: newspaper/ad.php?file=...
  │   │
  │   ├─► STEP 2: Find "Read Newspaper" Button
  │   │   └─► Extract onclick URL
  │   │   └─► Navigate to: newsletter.php?file=...
  │   │
  │   ├─► STEP 3: Wait for Download Timer
  │   │   ├─► JavaScript timer: 15 seconds
  │   │   └─► Extract PDF URL from script
  │   │
  │   ├─► STEP 4: Download PDF
  │   │   ├─► URL: /newspaper/pdf.php?file=...
  │   │   ├─► Method: HTTP GET request
  │   │   └─► Save to: e-paper/MMMYY/XX_YYYY-MM-DD.pdf
  │   │
  │   ├─► STEP 5: Compress PDF (Optional)
  │   │   ├─► Use pypdf library
  │   │   ├─► If compression helps: replace original
  │   │   └─► If not: keep original
  │   │
  │   ├─► STEP 6: Post to Discord
  │   │   ├─► Create rich embed
  │   │   ├─► Include file info & download link
  │   │   └─► POST to webhook URL
  │   │
  │   └─► STEP 7: Update History
  │       ├─► Add entry to download_history.json
  │       └─► Include: file_path, pdf_url, timestamp
  │
  ├─► Cleanup Old Folders
  │   └─► If today is 8th of month:
  │       └─► Delete previous month folder
  │
  └─► Close WebDriver
  
END
```

## Data Flow Diagram

```
┌──────────────┐
│  IndiaGS     │
│  Website     │◄─────────┐
└──────────────┘          │
       │                  │ Selenium
       │ HTML Pages       │ Automation
       ▼                  │
┌──────────────┐          │
│  Scraper     │──────────┘
│  (Python)    │
└──────────────┘
       │
       ├─► Extract PDF URLs
       │
       ├─► Download PDFs ──────► requests.get()
       │                              │
       │                              ▼
       │                    ┌──────────────────┐
       │                    │   PDF Files      │
       │                    └──────────────────┘
       │                              │
       │                              ▼
       │                    ┌──────────────────┐
       ├───────────────────►│  PDF Compression │
       │                    │    (pypdf)       │
       │                    └──────────────────┘
       │                              │
       │                              ▼
       │                    ┌──────────────────┐
       ├───────────────────►│  File Storage    │
       │                    │  e-paper/MMMYY/  │
       │                    └──────────────────┘
       │
       ├─► Update History
       │         │
       │         ▼
       │   ┌──────────────────────┐
       │   │ download_history.json │
       │   └──────────────────────┘
       │
       └─► Post to Discord
                 │
                 ▼
         ┌──────────────┐
         │   Discord    │
         │   Webhook    │
         └──────────────┘
                 │
                 ▼
         ┌──────────────┐
         │   Discord    │
         │   Channel    │
         │   (Students) │
         └──────────────┘
```

## Folder Structure Tree

```
epaper-automation/
│
├── 📄 Core Scripts
│   ├── scraper.py              ← Main automation
│   ├── maintenance.py          ← Utility commands
│   └── test_local.sh           ← Local testing
│
├── 📁 Configuration
│   ├── .env.example            ← Template
│   ├── requirements.txt        ← Dependencies
│   └── .gitignore              ← Git rules
│
├── 📁 GitHub Actions
│   └── .github/workflows/
│       └── daily-newspaper.yml ← Workflow definition
│
├── 📁 Documentation
│   ├── README.md               ← Main docs
│   ├── QUICKSTART.md           ← Quick guide
│   ├── SETUP_GUIDE.md          ← Detailed setup
│   ├── TESTING_CHECKLIST.md   ← Testing guide
│   ├── PROJECT_SUMMARY.md      ← Overview
│   └── ARCHITECTURE.md         ← This file
│
├── 📁 Web Dashboard (Optional)
│   └── docs/
│       └── index.html          ← GitHub Pages
│
├── 📁 Sample Files (Reference)
│   └── e-newspaper/
│       ├── indiags-home.html
│       ├── intermediate-page.html
│       └── download-file-page.html
│
├── 📁 Data (Auto-generated)
│   ├── download_history.json   ← Download tracking
│   └── e-paper/                ← PDF storage
│       ├── DEC25/
│       │   ├── TH_2025-12-17.pdf
│       │   └── IE_2025-12-17.pdf
│       └── JAN26/
│           └── ...
│
└── 📄 LICENSE
```

## Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│   ┌──────────────┐         ┌──────────────┐                │
│   │   GitHub     │         │   Discord    │                │
│   │   Actions    │         │   Webhook    │                │
│   └──────────────┘         └──────────────┘                │
│          │                         ▲                         │
│          │ Triggers                │ Posts                   │
│          ▼                         │                         │
│   ┌──────────────────────────────────────┐                 │
│   │         scraper.py                    │                 │
│   │  ┌────────────────────────────────┐  │                 │
│   │  │  NewspaperDownloader Class     │  │                 │
│   │  │                                │  │                 │
│   │  │  • setup_driver()              │  │                 │
│   │  │  • get_newspaper_links()       │  │                 │
│   │  │  • navigate_to_download_page() │  │                 │
│   │  │  • download_pdf()              │  │                 │
│   │  │  • compress_pdf()              │  │                 │
│   │  │  • post_to_discord()           │  │                 │
│   │  │  • cleanup_old_folders()       │  │                 │
│   │  └────────────────────────────────┘  │                 │
│   └──────────────────────────────────────┘                 │
│          │              │              │                     │
│          │              │              │                     │
│          ▼              ▼              ▼                     │
│   ┌───────────┐  ┌───────────┐  ┌──────────────┐          │
│   │ Selenium  │  │  Requests │  │   pypdf      │          │
│   │ WebDriver │  │  Library  │  │  (optional)  │          │
│   └───────────┘  └───────────┘  └──────────────┘          │
│          │              │              │                     │
│          ▼              ▼              ▼                     │
│   ┌─────────────────────────────────────────┐              │
│   │         File System / Git Repo          │              │
│   │                                         │              │
│   │  • download_history.json                │              │
│   │  • e-paper/MMMYY/*.pdf                  │              │
│   └─────────────────────────────────────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    ERROR HANDLING                            │
└─────────────────────────────────────────────────────────────┘

Scraping Error
  │
  ├─► Website Down?
  │   ├─► Log error
  │   ├─► Store fallback link
  │   └─► Continue to next newspaper
  │
  ├─► Element Not Found?
  │   ├─► Log warning
  │   ├─► Take screenshot (if possible)
  │   └─► Store page URL as fallback
  │
  └─► Timeout?
      ├─► Retry once
      └─► If fails: skip & continue

Download Error
  │
  ├─► Network Error?
  │   ├─► Retry download
  │   └─► If fails: store URL
  │
  └─► File Write Error?
      ├─► Check permissions
      └─► Log error & continue

Compression Error
  │
  ├─► pypdf Not Installed?
  │   └─► Skip compression, use original
  │
  └─► Compression Failed?
      └─► Keep original PDF

Discord Error
  │
  ├─► Webhook Invalid?
  │   └─► Log error, continue
  │
  └─► Network Error?
      └─► Retry once, then continue

Git Commit Error
  │
  └─► Nothing to Commit?
      └─► Normal, skip commit

All Errors:
  ├─► Logged to console
  ├─► Workflow continues
  └─► Artifacts uploaded if critical
```

## Timeline Diagram (Daily Execution)

```
00:00 UTC ─────────────────────────────────────► 00:00 UTC
(5:30 AM IST)                                    (5:30 AM IST)
                                                 (Next Day)
    │
    │    00:30 UTC (6:00 AM IST)
    ├────► GitHub Actions Trigger
    │
    ├────► Setup Environment (1-2 min)
    │      • Install Python
    │      • Install Chrome
    │      • Install dependencies
    │
    ├────► Run Scraper (3-5 min)
    │      │
    │      ├─► The Hindu
    │      │   ├─► Navigate (30s)
    │      │   ├─► Wait timer (15s)
    │      │   ├─► Download (30s)
    │      │   ├─► Compress (10s)
    │      │   └─► Post Discord (5s)
    │      │
    │      └─► Indian Express
    │          ├─► Navigate (30s)
    │          ├─► Wait timer (15s)
    │          ├─► Download (30s)
    │          ├─► Compress (10s)
    │          └─► Post Discord (5s)
    │
    ├────► Commit & Push (1 min)
    │      • Git add
    │      • Git commit
    │      • Git push
    │
    └────► Complete (Total: 5-10 min)
           │
           └─► Students receive newspapers
               in Discord by 6:10 AM IST
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                           │
└─────────────────────────────────────────────────────────────┘

GitHub Repository
  │
  ├─► Environment Variables
  │   └─► DISCORD_WEBHOOK_URL (Secret)
  │       • Not in code
  │       • Not in commits
  │       • Encrypted by GitHub
  │
  ├─► .env File (Local Only)
  │   └─► .gitignore prevents commit
  │
  ├─► GitHub Actions Permissions
  │   ├─► Read repository
  │   ├─► Write to repository
  │   └─► No other access
  │
  └─► Discord Webhook
      ├─► Limited to one channel
      ├─► Can be revoked anytime
      └─► No server admin access
```

## Maintenance Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                  MAINTENANCE COMMANDS                        │
└─────────────────────────────────────────────────────────────┘

python maintenance.py history
  │
  └─► Display Recent Downloads
      • Last 7 days by default
      • Shows file paths
      • Shows URLs
      • Shows status

python maintenance.py storage
  │
  └─► Check Storage Usage
      • Size by month folder
      • Total usage
      • GitHub limit comparison
      • Usage percentage

python maintenance.py cleanup --days 30
  │
  └─► Delete Old Files
      • Files older than 30 days
      • Remove empty folders
      • Report freed space

python maintenance.py verify
  │
  └─► Verify Setup
      • Check all files exist
      • Check environment vars
      • Check configurations
      • Report status

python maintenance.py export
  │
  └─► Export All Links
      • Create text file
      • List all PDF URLs
      • Organized by date
```

---

## 🎯 Key Architectural Decisions

1. **Selenium vs. Requests**: Selenium chosen for JavaScript handling
2. **GitHub Actions vs. Cron**: GitHub Actions for zero-cost hosting
3. **JSON vs. Database**: JSON for simplicity and portability
4. **Discord vs. Email**: Discord for instant delivery and organization
5. **Repository Storage vs. Cloud**: Repository for simplicity initially

---

## 📊 Performance Considerations

- **Headless Chrome**: Reduces memory usage
- **Parallel Processing**: Not used (sequential for stability)
- **Caching**: History prevents re-downloads
- **Compression**: Optional, reduces storage by ~20-40%
- **Cleanup**: Automatic monthly deletion

---

**This architecture supports reliable, automated daily newspaper delivery to students! 📰**
