# 📰 E-Newspaper Auto-Downloader

Automated system to download The Hindu and Indian Express newspapers from IndiaGS and distribute via Discord.

## 🎯 Features

- ✅ **Automated Daily Downloads** - Runs at 6 AM IST via GitHub Actions
- 📦 **PDF Compression** - Reduces file sizes to save storage
- 📁 **Organized Storage** - Month-wise folders (DEC24, JAN25, etc.)
- 🗑️ **Auto Cleanup** - Deletes old folders after 7-day buffer
- 📨 **Discord Integration** - Automatic notifications with download links
- 🔄 **Duplicate Prevention** - Tracks processed newspapers in JSON history
- 🌐 **GitHub Pages Hosting** - Files accessible via public URLs
- 🔧 **Smart URL Construction** - Pattern-based approach with fallback

## 📋 Prerequisites

- GitHub account
- Discord server with webhook access
- Basic Git knowledge

## 🚀 Quick Setup

### Step 1: Fork/Create Repository

1. Create a new GitHub repository (e.g., `epaper-automation`)
2. Clone it locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/epaper-automation.git
   cd epaper-automation
   ```

### Step 2: Add Files

Copy these files to your repository:
- `newspaper_downloader.py` - Main Python script
- `.github/workflows/download_newspapers.yml` - GitHub Actions workflow
- `requirements.txt` - Python dependencies
- `download_history.json` - Create with: `echo '{"downloads":[]}' > download_history.json`

```bash
mkdir -p .github/workflows e-paper
touch download_history.json
echo '{"downloads":[]}' > download_history.json
```

### Step 3: Configure Discord Webhook

1. Go to your Discord server → Server Settings → Integrations → Webhooks
2. Click "New Webhook"
3. Name it "E-Paper Bot", select your channel, copy the webhook URL
4. In GitHub: Repository → Settings → Secrets and variables → Actions
5. Click "New repository secret"
   - Name: `DISCORD_WEBHOOK_URL`
   - Value: Your webhook URL
6. Click "Add secret"

### Step 4: Enable GitHub Pages

1. Go to repository Settings → Pages
2. Source: Deploy from a branch
3. Branch: `gh-pages` → `/root`
4. Click Save

### Step 5: Initial Commit and Push

```bash
git add .
git commit -m "Initial setup - E-Paper automation"
git push origin main
```

### Step 6: Enable Workflow

1. Go to Actions tab in your repository
2. Click "I understand my workflows, go ahead and enable them"
3. Select "Download E-Newspapers" workflow
4. Click "Run workflow" → "Run workflow" to test

## 📅 Workflow Schedule

The automation runs:
- **Daily at 6:00 AM IST** (00:30 UTC)
- Can be triggered manually from Actions tab

## 📂 Folder Structure

```
epaper-automation/
├── .github/
│   └── workflows/
│       └── download_newspapers.yml
├── e-paper/
│   ├── DEC24/
│   │   ├── TH-Delhi-14-12.pdf
│   │   └── IE-Delhi-14-12.pdf
│   ├── JAN25/
│   │   └── ...
│   └── FEB25/
│       └── ...
├── newspaper_downloader.py
├── download_history.json
├── requirements.txt
└── README.md
```

## 🔧 Configuration

### Modify Newspapers

Edit `newspaper_downloader.py`:

```python
self.newspapers = {
    "The Hindu": "TH-+Delhi",
    "Indian Express": "IE-+Delhi",
    # Add more:
    # "The Hindu International": "TH-+International",
}
```

### Change Schedule

Edit `.github/workflows/download_newspapers.yml`:

```yaml
schedule:
  # Format: minute hour day month day-of-week (UTC)
  - cron: '30 0 * * *'  # 6:00 AM IST
  # Examples:
  # - cron: '0 1 * * *'   # 6:30 AM IST
  # - cron: '0 */6 * * *' # Every 6 hours
```

### Customize Cleanup Period

Edit `newspaper_downloader.py`:

```python
def cleanup_old_folders(self):
    # Change from day 7 to day 15:
    if current_date.day > 15:  # Currently 7
        return
```

## 📊 Monitoring

### Check Workflow Status
- Go to Actions tab
- View recent runs
- Check logs for any errors

### Download History
- View `download_history.json` in repository
- Contains all processed newspapers with timestamps

### Discord Notifications
Each successful download sends an embed with:
- Newspaper name and date
- File size
- Download link (GitHub Pages)

## 🛠️ Troubleshooting

### Downloads Not Working

1. **Check workflow logs** in Actions tab
2. **Verify Discord webhook** is correct
3. **Test manually**: Actions → Download E-Newspapers → Run workflow

### PDFs Not Accessible

1. Ensure GitHub Pages is enabled (Settings → Pages)
2. Wait 2-3 minutes after first push for Pages deployment
3. Check URLs match pattern: `https://USERNAME.github.io/REPO/e-paper/DEC24/file.pdf`

### History Not Saving

```bash
# Manually reset history
echo '{"downloads":[]}' > download_history.json
git add download_history.json
git commit -m "Reset history"
git push
```

### Workflow Not Running

1. Check if workflow is enabled (Actions tab)
2. Verify cron syntax is correct
3. GitHub Actions may have delays up to 15 minutes

## 🔒 Security Notes

- Never commit webhook URLs directly in code
- Always use GitHub Secrets for sensitive data
- Repository can be private (Actions still work)
- GitHub Pages can be made private for private repos

## 📈 Usage Limits

GitHub Free Tier:
- ✅ 2000 Actions minutes/month (plenty for daily runs)
- ✅ 1GB storage (with PDF compression)
- ✅ Unlimited GitHub Pages bandwidth

## 🤝 Contributing

Feel free to:
- Report issues
- Suggest improvements
- Submit pull requests

## 📝 License

This project is for educational purposes. Respect copyright laws and terms of service of content providers.

## ⚡ Advanced Features

### URL Pattern Analysis

The script uses intelligent URL construction:
```
Pattern: /newspaper/pdf.php?file=uploads%2F{NEWSPAPER}+{DATE}.pdf
Example: /newspaper/pdf.php?file=uploads%2FTH-+Delhi+14-12.pdf
```

### Compression Stats

Typical compression results:
- Original: 25-35 MB
- Compressed: 15-25 MB
- Reduction: 30-40%

### Fallback Mechanism

If direct URL fails, the script can be enhanced with:
1. Web scraping the listing page
2. Following navigation links
3. Bypassing timer logic

## 📞 Support

For issues or questions:
1. Check existing GitHub Issues
2. Create new issue with logs
3. Tag with appropriate labels

## 🎓 For Students

This tool helps students:
- ✅ Save time on manual downloads
- ✅ Never miss daily newspapers
- ✅ Focus on preparation instead of logistics
- ✅ Share resources efficiently

**Happy Studying! 📚**

---

*Made with ❤️ for UPSC aspirants and competitive exam students*
