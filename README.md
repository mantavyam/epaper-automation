# E-Newspaper Link Extractor

> Automated daily extraction of **The Hindu** and **The Indian Express** newspaper links from IndiaGS, with Discord webhook delivery for students preparing for competitive exams.

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-blue)](https://github.com/features/actions)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Documentation

- **[Getting Started](GETTING_STARTED.md)** - Visual step-by-step guide
-  **[Quick Start](QUICKSTART.md)** - Get running in 5 minutes
-  **[Setup Guide](SETUP_GUIDE.md)** - Detailed setup instructions  
-  **[Architecture](ARCHITECTURE.md)** - System design & diagrams
-  **[Project Summary](PROJECT_SUMMARY.md)** - Comprehensive overview
-  **[Testing Checklist](TESTING_CHECKLIST.md)** - Verify your setup
-  **[Troubleshooting](TROUBLESHOOTING.md)** - Fix common issues

## Features

- **Automated Daily Extraction**: Runs at 6:00 AM IST via GitHub Actions
- **Link Detection**: Automatically detects and transforms newspaper PDF links
- **History Tracking**: JSON-based tracking organized by month and date
- **Discord Integration**: Posts newspaper links to Discord webhook in real-time
- **Lean Workflow**: No storage overhead, fast extraction and delivery
- **Easy Extension**: Simple configuration to add more newspapers

## Setup

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

## Folder Structure

```
epaper-automation/
├── scraper.py                 # Main automation script
├── requirements.txt           # Python dependencies
├── download_history.json      # Link history (auto-generated)
├── .github/
│   └── workflows/
│       └── daily-newspaper.yml  # GitHub Actions workflow
└── README.md                  # This file
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
    "Times of India": "TOI"  # Add newspaper title and code
}
```

The newspaper title must match exactly as it appears on the website.

## How It Works

1. **Scrape Homepage**: Access IndiaGS homepage and locate target newspapers
2. **Extract Initial Links**: Get newspaper links from page (ad.php URLs)
3. **Transform URLs**: Convert ad.php endpoints to pdf.php for direct access
4. **Post to Discord**: Send newspaper link to configured webhook
5. **Track History**: Save link with timestamp in nested month-date structure
6. **Avoid Duplicates**: Check history to prevent re-posting same day

## Technologies

- **Python 3.11**: Core automation
- **Selenium**: Web scraping and link extraction
- **Requests**: HTTP requests for Discord webhooks
- **GitHub Actions**: Scheduled daily execution
- **Discord Webhooks**: Real-time link delivery

## Important Notes

- Only links are extracted and posted to Discord (no PDF files stored)
- Minimal storage footprint - only JSON history file (~10KB)
- Links may become stale over time as they are time-dependent
- History is organized by month-year for easy reference
- Runs via GitHub Actions without requiring local resources

## Troubleshooting

### No newspapers extracted

- Check GitHub Actions logs for errors
- Verify Discord webhook URL is correct and accessible
- Ensure the website structure matches expected format
- Check that newspaper titles in config match website exactly

### Discord webhook errors

- Verify webhook URL is valid and not expired
- Check Discord server permissions allow webhook posts
- Ensure DISCORD_WEBHOOK_URL secret is set in GitHub

### Chrome/ChromeDriver errors

- GitHub Actions handles ChromeDriver installation automatically
- For local testing, webdriver-manager installs ChromeDriver automatically
- Ensure no other Chrome instances are running on the system

## License

See [LICENSE](LICENSE) file.

## Contributing

Feel free to open issues or submit PRs for improvements!

---

**Made for students preparing for competitive exams** 📚
