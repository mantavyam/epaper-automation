# 🚀 Quick Start Guide - E-Paper Automation

## Prerequisites
- GitHub account
- Discord server with admin access
- 10 minutes of your time

## 📦 One-Time Setup (5 steps)

### Step 1: Create Repository (2 min)

```bash
# Create a new directory
mkdir epaper-automation
cd epaper-automation

# Download setup script and make it executable
curl -O https://raw.githubusercontent.com/YOUR_REPO/setup.sh
chmod +x setup.sh
```

### Step 2: Add All Files (2 min)

Create these files in your repository:

1. **newspaper_downloader.py** - Main Python script
2. **.github/workflows/download_newspapers.yml** - GitHub Actions workflow
3. **requirements.txt** - Dependencies
4. **index.html** - GitHub Pages interface
5. **config.json** - Configuration

Or run the setup script:
```bash
./setup.sh
```

### Step 3: Initialize Git (1 min)

```bash
# Initialize repository
git init

# Add all files
git add .

# Create first commit
git commit -m "🎉 Initial setup - E-Paper automation"

# Create repository on GitHub (do this in browser first)
# Then connect local repo to GitHub:
git remote add origin https://github.com/YOUR_USERNAME/epaper-automation.git
git branch -M main
git push -u origin main
```

### Step 4: Configure Discord (2 min)

**Get Discord Webhook:**
1. Open Discord → Your Server
2. Server Settings → Integrations → Webhooks
3. Click "New Webhook"
4. Name: "E-Paper Bot"
5. Select channel (e.g., #newspapers)
6. Click "Copy Webhook URL"

**Add to GitHub:**
1. Go to your repository on GitHub
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `DISCORD_WEBHOOK_URL`
5. Value: Paste your webhook URL
6. Click "Add secret"

### Step 5: Enable GitHub Features (3 min)

**Enable GitHub Actions:**
1. Go to Actions tab
2. Click "I understand my workflows, go ahead and enable them"

**Enable GitHub Pages:**
1. Settings → Pages
2. Source: "Deploy from a branch"
3. Branch: Select "gh-pages" → "/root"
4. Click Save

## 🎯 Test Your Setup

### Manual Test Run

1. Go to **Actions** tab
2. Select "Download E-Newspapers"
3. Click "Run workflow" dropdown
4. Click green "Run workflow" button
5. Wait 2-3 minutes
6. Check the run logs

### Verify Success

✅ Check Discord - You should see newspaper notifications
✅ Check repository - `e-paper/` folder created with PDFs
✅ Check GitHub Pages - Visit `https://YOUR_USERNAME.github.io/epaper-automation`

## 📅 Daily Schedule

After setup, newspapers download automatically:
- **Time:** 6:00 AM IST (00:30 UTC)
- **Frequency:** Daily
- **Notifications:** Sent to Discord
- **Accessible:** Via GitHub Pages

## 🔧 Customization

### Change Schedule

Edit `.github/workflows/download_newspapers.yml`:

```yaml
schedule:
  - cron: '30 0 * * *'  # Current: 6:00 AM IST
  # - cron: '0 1 * * *'  # Change to: 6:30 AM IST
  # - cron: '0 */6 * * *' # Every 6 hours
```

### Add More Newspapers

Edit `config.json`:

```json
{
  "newspapers": {
    "The Hindu": {
      "code": "TH-+Delhi",
      "display_name": "The Hindu",
      "enabled": true
    },
    "Indian Express": {
      "code": "IE-+Delhi",
      "display_name": "Indian Express",
      "enabled": true
    },
    "The Hindu International": {
      "code": "TH-+International",
      "display_name": "The Hindu International",
      "enabled": true
    }
  }
}
```

### Adjust Cleanup Period

Edit `config.json`:

```json
{
  "settings": {
    "cleanup_buffer_days": 7  // Change to 14, 30, etc.
  }
}
```

## 📊 Monitoring

### Check Workflow Runs
- **Actions Tab** → View all runs and logs
- **Email Notifications** → GitHub sends on failure

### View Download History
- `download_history.json` in repository
- Shows all processed newspapers with timestamps

### Discord Notifications
Each download sends:
- 📰 Newspaper name
- 📅 Date
- 📦 File size
- ⬇️ Download link

## 🐛 Troubleshooting

### Workflow Not Running

```bash
# Check workflow file syntax
cat .github/workflows/download_newspapers.yml

# Verify it's committed
git log --oneline --all --graph
```

### PDFs Not Downloading

1. Check Actions logs for errors
2. Verify IndiaGS website is accessible
3. Test manually: Actions → Run workflow

### Discord Not Working

1. Verify webhook URL is correct
2. Check Discord channel permissions
3. Test webhook:
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"content":"Test message"}' \
  YOUR_WEBHOOK_URL
```

### GitHub Pages Not Showing

1. Wait 2-3 minutes after first push
2. Check Settings → Pages is enabled
3. Verify gh-pages branch exists
4. Clear browser cache

## 📱 Access Your Newspapers

### GitHub Pages Interface
```
https://YOUR_USERNAME.github.io/epaper-automation
```

### Direct PDF Links
```
https://YOUR_USERNAME.github.io/epaper-automation/e-paper/DEC24/TH-Delhi-14-12.pdf
```

### Discord Channel
Check your configured channel for daily notifications

## 🎓 For Students

### Best Practices

1. **Read Daily** - Check Discord each morning
2. **Download Archive** - Keep local copies for offline reading
3. **Share Responsibly** - Respect copyright and terms of service
4. **Stay Updated** - Monitor workflow for any issues

### Study Tips

- ✅ Set aside 30-45 minutes daily
- ✅ Focus on editorial and opinion pieces
- ✅ Note important current affairs
- ✅ Practice English comprehension
- ✅ Maintain a vocabulary journal

## 🆘 Get Help

### Common Issues

| Issue | Solution |
|-------|----------|
| Workflow failed | Check Actions logs |
| No Discord message | Verify webhook secret |
| PDF won't open | Re-download from GitHub Pages |
| Old folders not deleted | Wait until 8th of month |

### Resources

- **GitHub Actions Docs:** https://docs.github.com/actions
- **Python Requests:** https://requests.readthedocs.io
- **PyPDF2 Docs:** https://pypdf2.readthedocs.io

### Community

- Open GitHub Issues for bugs
- Star the repository if helpful
- Share improvements via Pull Requests

## ✨ Advanced Features

### Webhook Integration with Other Services

The system can be extended to:
- Send to Telegram
- Post to Slack
- Email notifications
- RSS feed generation

### Backup Solutions

Consider backing up PDFs to:
- Google Drive (via API)
- Dropbox (via webhook)
- Personal server (via rsync)

### Analytics

Track download patterns:
- Which newspapers most popular
- Peak download times
- Storage usage trends

## 🎉 Success!

You're now running a fully automated newspaper download system!

**What happens next:**
1. Every day at 6 AM IST, the workflow runs
2. Newspapers are downloaded and compressed
3. Discord receives notifications with links
4. PDFs are accessible via GitHub Pages
5. Old files automatically cleaned up

**Enjoy your automation! 📰✨**

---

*Questions? Open an issue on GitHub!*
