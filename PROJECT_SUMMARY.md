# 📰 E-Newspaper Automation - Project Summary

## 🎯 Project Overview

**Purpose**: Automate daily download of "The Hindu" and "The Indian Express" newspapers from IndiaGS website and distribute them via Discord to students preparing for competitive exams.

**Technology Stack**: Python, Selenium, GitHub Actions, Discord Webhooks

**Automation Schedule**: Daily at 6:00 AM IST (00:30 UTC)

---

## 📂 Project Structure

```
epaper-automation/
│
├── 📄 scraper.py                    # Main automation script (450+ lines)
├── 📄 requirements.txt              # Python dependencies
├── 📄 maintenance.py                # Utility script for maintenance tasks
├── 📄 test_local.sh                 # Local testing script
│
├── 📁 .github/workflows/
│   └── daily-newspaper.yml          # GitHub Actions workflow
│
├── 📁 docs/
│   └── index.html                   # Optional GitHub Pages dashboard
│
├── 📁 e-newspaper/                  # Sample HTML files for reference
│   ├── indiags-home.html
│   ├── intermediate-page.html
│   └── download-file-page.html
│
├── 📁 e-paper/                      # Auto-generated PDF storage
│   ├── DEC25/                       # Monthly folders (MMMYY format)
│   │   ├── TH_2025-12-17.pdf
│   │   └── IE_2025-12-17.pdf
│   └── JAN26/
│       └── ...
│
├── 📄 download_history.json         # Auto-generated download tracking
│
├── 📄 .env.example                  # Environment variable template
├── 📄 .gitignore                    # Git ignore rules
│
├── 📄 README.md                     # Main documentation
├── 📄 QUICKSTART.md                 # Quick reference guide
├── 📄 SETUP_GUIDE.md                # Detailed setup instructions
├── 📄 TESTING_CHECKLIST.md          # Testing checklist
└── 📄 LICENSE                       # Project license
```

---

## 🚀 Core Features

### ✅ Implemented Features

1. **Automated Scraping**
   - Navigates IndiaGS website
   - Locates target newspapers
   - Handles intermediate ad pages
   - Waits for download timers

2. **Download Management**
   - Downloads PDF files via HTTP requests
   - Optional PDF compression (pypdf)
   - Fallback to link storage on failure
   - Organized folder structure (MMMYY)

3. **History Tracking**
   - JSON-based download history
   - Prevents duplicate downloads
   - Tracks file paths and URLs
   - Maintains metadata

4. **Discord Integration**
   - Rich embed messages
   - File size information
   - Direct download links
   - Newspaper categorization

5. **Storage Management**
   - Monthly folder organization
   - Auto-cleanup on 8th of next month
   - Storage monitoring utilities

6. **Error Handling**
   - Graceful failure recovery
   - Fallback link storage
   - Detailed error logging
   - Continues on single failure

7. **GitHub Actions**
   - Automated daily runs
   - Chrome/ChromeDriver setup
   - Git commit automation
   - Artifact uploads on failure

---

## 🔧 Key Components

### scraper.py

**Main Class**: `NewspaperDownloader`

**Key Methods**:
- `get_newspaper_links()` - Scrape main page
- `navigate_to_download_page()` - Handle intermediate pages
- `wait_for_download_button()` - Extract PDF URL
- `download_pdf()` - Download PDF file
- `compress_pdf()` - Optional compression
- `post_to_discord()` - Discord webhook
- `cleanup_old_folders()` - Storage management

**Configuration**:
```python
BASE_URL = "https://www.indiags.com/epaper-pdf-download"
NEWSPAPERS = {
    "The Hindu": "TH",
    "Indian Express": "IE"
}
```

### GitHub Actions Workflow

**Triggers**:
- Schedule: `cron: '30 0 * * *'` (6:00 AM IST)
- Manual: `workflow_dispatch`

**Steps**:
1. Checkout repository
2. Setup Python 3.11
3. Install dependencies
4. Install Chrome/ChromeDriver
5. Run scraper
6. Commit changes
7. Push to repository

**Required Secret**:
- `DISCORD_WEBHOOK_URL`

### Maintenance Utilities

**Commands**:
```bash
python maintenance.py history --days 7    # View history
python maintenance.py storage             # Check storage
python maintenance.py cleanup --days 30   # Cleanup old files
python maintenance.py verify              # Verify setup
python maintenance.py export              # Export links
```

---

## 📊 Data Flow

```
1. GitHub Actions (cron trigger)
   ↓
2. Run scraper.py
   ↓
3. Scrape IndiaGS homepage
   ↓
4. For each newspaper (The Hindu, Indian Express):
   a. Click "Read" link
   b. Navigate intermediate page
   c. Click "Read Newspaper" button
   d. Wait for download timer (15s)
   e. Extract PDF URL from JavaScript
   f. Download PDF via requests
   g. Compress PDF (if possible)
   h. Save to e-paper/MMMYY/
   i. Post to Discord
   j. Update history
   ↓
5. Cleanup old folders (if 8th of month)
   ↓
6. Commit and push changes
   ↓
7. Discord notification sent
```

---

## 🎨 Discord Message Format

```
┌─────────────────────────────────────────┐
│ 📰 The Hindu - 17 December 2025        │
├─────────────────────────────────────────┤
│ ✅ Downloaded successfully              │
│ 📁 Size: 12.34 MB                       │
│                                         │
│ File Location                           │
│ `e-paper/DEC25/TH_2025-12-17.pdf`     │
│                                         │
│ 📥 Direct Link                          │
│ https://www.indiags.com/newspaper/...  │
├─────────────────────────────────────────┤
│ E-Newspaper Automation • 6:00 AM IST    │
└─────────────────────────────────────────┘
```

---

## 🔐 Environment Variables

**Required**:
- `DISCORD_WEBHOOK_URL` - Discord webhook for posting newspapers

**Optional**:
- None (all configuration in code)

---

## 📈 Performance Metrics

**Expected Metrics**:
- Workflow duration: 5-10 minutes
- PDF download time: 30-60 seconds each
- Compression time: 10-30 seconds
- Total storage: ~300-500 MB/month

**Limits**:
- GitHub Actions: 2,000 minutes/month (free)
- GitHub Storage: 500 MB (private) / 1 GB (public)
- Workflow timeout: 60 minutes (configurable)

---

## 🛡️ Error Handling

**Scenarios Covered**:

1. **Website Down**
   - Logs error
   - Stores fallback link
   - Posts to Discord with warning

2. **PDF Download Fails**
   - Retries once
   - Falls back to storing URL
   - Continues with next newspaper

3. **Compression Fails**
   - Saves original PDF
   - Logs warning
   - Continues normally

4. **Discord Webhook Fails**
   - Logs error
   - PDFs still saved locally
   - History still updated

5. **Chrome/Selenium Issues**
   - Detailed error logging
   - Artifacts uploaded on failure
   - Manual intervention needed

---

## 📚 Documentation Files

| File | Purpose | Audience |
|------|---------|----------|
| README.md | Overview & features | All users |
| QUICKSTART.md | Quick setup (5 min) | New users |
| SETUP_GUIDE.md | Detailed setup | All users |
| TESTING_CHECKLIST.md | Testing guide | Developers |
| PROJECT_SUMMARY.md | This file | Developers |

---

## 🔄 Maintenance Schedule

**Daily**:
- Automated run at 6:00 AM IST
- Check Discord for posts

**Weekly**:
- Review GitHub Actions logs
- Monitor storage usage
- Verify all newspapers downloaded

**Monthly (8th day)**:
- Previous month folder auto-deleted
- Storage automatically freed

**Quarterly**:
- Review and update dependencies
- Check for website structure changes
- Optimize compression settings

---

## 🚧 Known Limitations

1. **Website Dependencies**
   - Relies on IndiaGS website structure
   - Breaks if website changes significantly
   - Requires manual update to scraper

2. **Storage Constraints**
   - GitHub has storage limits
   - May need Git LFS for long-term
   - Old files must be cleaned up

3. **Network Reliability**
   - Requires stable internet
   - No automatic retry on total failure
   - Manual re-run needed

4. **PDF Quality**
   - Compression may affect quality
   - Optional, can be disabled
   - Original saved if compression fails

---

## 🔮 Future Enhancements

**Potential Improvements**:

1. **Multiple Sources**
   - Add backup newspaper sources
   - Fallback to official websites

2. **Advanced Notifications**
   - Email notifications
   - Telegram bot integration
   - SMS alerts on failure

3. **Analytics Dashboard**
   - Track download success rate
   - Monitor storage trends
   - Visualize usage patterns

4. **Cloud Storage**
   - S3/Azure blob storage
   - Unlimited storage capacity
   - Faster access

5. **OCR & Search**
   - Extract text from PDFs
   - Searchable archive
   - Keyword notifications

6. **User Management**
   - Individual subscriptions
   - Customizable newspapers
   - Preference management

---

## 🤝 Contributing

**How to Contribute**:

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

**Areas for Contribution**:
- Add more newspapers
- Improve error handling
- Enhance Discord embeds
- Add tests
- Improve documentation

---

## 📜 License

See [LICENSE](LICENSE) file for details.

---

## 👥 Credits

**Created for**: Students preparing for competitive exams

**Technologies**:
- Python 3.11
- Selenium WebDriver
- GitHub Actions
- Discord Webhooks
- pypdf (compression)

---

## 📞 Support & Contact

**Issues**: Open an issue on GitHub
**Discussions**: Use GitHub Discussions
**Documentation**: Check SETUP_GUIDE.md

---

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Discord webhook configured
- [ ] GitHub Actions enabled
- [ ] First manual run successful
- [ ] Discord received newspapers
- [ ] History file created
- [ ] PDFs saved correctly
- [ ] Documentation reviewed
- [ ] Team notified

---

**Last Updated**: December 17, 2025
**Version**: 1.0.0
**Status**: Production Ready ✅

---

## 🎉 Success Metrics

Once deployed, you can measure success by:

1. **Reliability**: 95%+ successful daily runs
2. **Timeliness**: Newspapers available by 6:30 AM IST
3. **Completeness**: Both newspapers downloaded daily
4. **User Satisfaction**: Students actively using Discord channel
5. **Storage Efficiency**: <500MB storage used monthly

---

**Made with ❤️ for students by students**
