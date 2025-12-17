# 📰 E-Newspaper Automation

> Automated daily download of **The Hindu** and **The Indian Express** newspapers from IndiaGS, with Discord integration for students preparing for competitive exams.

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-blue)](https://github.com/features/actions)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📚 Documentation

- � **[Getting Started](GETTING_STARTED.md)** - Visual step-by-step guide
- 📖 **[Quick Start](QUICKSTART.md)** - Get running in 5 minutes
- 📖 **[Setup Guide](SETUP_GUIDE.md)** - Detailed setup instructions  
- 🏗️ **[Architecture](ARCHITECTURE.md)** - System design & diagrams
- 📊 **[Project Summary](PROJECT_SUMMARY.md)** - Comprehensive overview
- ✅ **[Testing Checklist](TESTING_CHECKLIST.md)** - Verify your setup
- 🔧 **[Troubleshooting](TROUBLESHOOTING.md)** - Fix common issues

## 🎯 Features

- ✅ **Automated Daily Downloads**: Runs at 6:00 AM IST via GitHub Actions
- 📁 **Organized Storage**: PDFs stored in `e-paper/MMMYY/` folders (e.g., `DEC25/`)
- 🗜️ **PDF Compression**: Optional compression to save storage space
- 📊 **History Tracking**: JSON-based tracking to avoid duplicate downloads
- 🧹 **Auto Cleanup**: Deletes old month folders after 7 days into new month
- 💬 **Discord Integration**: Posts download links to Discord via webhook
- 🔄 **Fallback System**: Stores original links if download/compression fails

## 🚀 Setup

### 1. Fork/Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/epaper-automation.git
cd epaper-automation
```

### 2. Configure Discord Webhook

1. Go to your Discord server settings
2. Navigate to **Integrations** → **Webhooks**
3. Create a new webhook for your newspaper channel
4. Copy the webhook URL

### 3. Set GitHub Secrets

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Add a new repository secret:
   - **Name**: `DISCORD_WEBHOOK_URL`
   - **Value**: Your Discord webhook URL

### 4. Enable GitHub Actions

1. Go to the **Actions** tab in your repository
2. Enable workflows if prompted
3. The workflow will run automatically daily at 6:00 AM IST

## 🧪 Manual Testing

Install dependencies locally:

```bash
pip install -r requirements.txt
```

Set environment variable:

```bash
export DISCORD_WEBHOOK_URL="your_webhook_url_here"
```

Run the scraper:

```bash
python scraper.py
```

## 📂 Folder Structure

```
epaper-automation/
├── scraper.py                 # Main automation script
├── requirements.txt           # Python dependencies
├── download_history.json      # Download history (auto-generated)
├── .github/
│   └── workflows/
│       └── daily-newspaper.yml  # GitHub Actions workflow
└── e-paper/                   # Downloaded newspapers (auto-generated)
    ├── DEC25/
    │   ├── TH_2025-12-17.pdf
    │   └── IE_2025-12-17.pdf
    └── JAN26/
        └── ...
```

## 🔧 Configuration

### Change Schedule

Edit [.github/workflows/daily-newspaper.yml](.github/workflows/daily-newspaper.yml):

```yaml
schedule:
  - cron: '30 0 * * *'  # 6:00 AM IST (00:30 UTC)
```

### Add More Newspapers

Edit `NEWSPAPERS` dict in [scraper.py](scraper.py):

```python
NEWSPAPERS = {
    "The Hindu": "TH",
    "Indian Express": "IE",
    "Times of India": "TOI"  # Add more
}
```

## 📊 How It Works

1. **Scrape Main Page**: Access IndiaGS homepage and locate target newspapers
2. **Navigate Pages**: Click through intermediate ad/promo pages
3. **Wait for Timer**: Handle 15-second countdown timer on download page
4. **Extract PDF URL**: Parse JavaScript to get actual PDF download link
5. **Download PDF**: Fetch PDF file via requests
6. **Compress (Optional)**: Use pypdf to compress if available
7. **Post to Discord**: Send embed with download info
8. **Update History**: Track processed newspapers in JSON
9. **Cleanup**: Delete old folders on 8th of each month

## 🛠️ Technologies

- **Python 3.11**: Core automation
- **Selenium**: Web automation and scraping
- **Requests**: HTTP requests for downloads
- **pypdf**: PDF compression
- **GitHub Actions**: Scheduled execution
- **Discord Webhooks**: Notifications

## ⚠️ Important Notes

- PDFs are stored in the repository (ensure you have enough storage)
- GitHub free tier has 500MB storage - consider using Git LFS for larger files
- The scraper respects the website's timer requirements
- Fallback links are stored if PDF download fails

## 🐛 Troubleshooting

### No newspapers downloaded

- Check GitHub Actions logs
- Verify Discord webhook URL is correct
- Ensure the website structure hasn't changed

### Storage issues

- Enable Git LFS: `git lfs install && git lfs track "*.pdf"`
- Or modify script to only post links (not store PDFs)

### Chrome/ChromeDriver errors

- GitHub Actions handles this automatically
- For local testing, install Chrome and ChromeDriver manually

## 📜 License

See [LICENSE](LICENSE) file.

## 🤝 Contributing

Feel free to open issues or submit PRs for improvements!

---

**Made for students preparing for competitive exams** 📚
