# 📋 Complete Setup Guide - E-Newspaper Automation

## 📖 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Discord Configuration](#discord-configuration)
4. [GitHub Repository Setup](#github-repository-setup)
5. [Testing Locally](#testing-locally)
6. [Deploying to GitHub Actions](#deploying-to-github-actions)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisites

Before you begin, ensure you have:

- ✅ **Git** installed on your system
- ✅ **Python 3.11+** installed
- ✅ **Google Chrome** browser installed
- ✅ **GitHub account** (free tier works fine)
- ✅ **Discord server** with admin permissions

---

## 🚀 Initial Setup

### Step 1: Clone the Repository

```bash
# Clone your forked repository
git clone https://github.com/YOUR_USERNAME/epaper-automation.git
cd epaper-automation
```

### Step 2: Create Virtual Environment (for local testing)

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 💬 Discord Configuration

### Step 1: Create Discord Webhook

1. Open your Discord server
2. Go to **Server Settings** (click gear icon)
3. Navigate to **Integrations** → **Webhooks**
4. Click **New Webhook** or **Create Webhook**
5. Configure the webhook:
   - **Name**: `E-Newspaper Bot` (or any name you prefer)
   - **Channel**: Select the channel where newspapers will be posted
6. Click **Copy Webhook URL**
7. Save this URL - you'll need it in the next step

### Step 2: Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env file
nano .env  # or use any text editor
```

Paste your Discord webhook URL:
```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdefg...
```

---

## 🐙 GitHub Repository Setup

### Step 1: Create GitHub Repository

1. Go to [GitHub](https://github.com)
2. Click **New Repository** (+ icon in top right)
3. Configure repository:
   - **Name**: `epaper-automation`
   - **Visibility**: Private (recommended) or Public
   - **Initialize**: Don't add README, .gitignore, or license (we have them)
4. Click **Create Repository**

### Step 2: Push Code to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: E-newspaper automation setup"

# Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/epaper-automation.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 3: Configure GitHub Secrets

1. Go to your repository on GitHub
2. Click **Settings** tab
3. Navigate to **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Add the following secret:
   - **Name**: `DISCORD_WEBHOOK_URL`
   - **Value**: Your Discord webhook URL (paste it)
6. Click **Add secret**

### Step 4: Enable GitHub Actions

1. Go to **Actions** tab in your repository
2. If prompted, click **I understand my workflows, go ahead and enable them**
3. You should see the workflow "Daily E-Newspaper Automation"

---

## 🧪 Testing Locally

Before relying on GitHub Actions, test the automation locally:

### Option 1: Using Test Script (Recommended)

```bash
# Run the automated test script
./test_local.sh
```

This script will:
- Check Python installation
- Create/activate virtual environment
- Install dependencies
- Verify Discord webhook configuration
- Run the scraper
- Report results

### Option 2: Manual Testing

```bash
# Activate virtual environment
source venv/bin/activate

# Set environment variable
export DISCORD_WEBHOOK_URL="your_webhook_url"

# Run scraper
python scraper.py
```

### Verify Results

After running, check:

1. **Console Output**: Should show download progress
2. **e-paper/ Folder**: Should contain PDFs in `MMMYY/` subfolder
3. **download_history.json**: Should have today's entry
4. **Discord Channel**: Should show posted newspapers

---

## ☁️ Deploying to GitHub Actions

### Automatic Daily Runs

The workflow is configured to run automatically at **6:00 AM IST (00:30 UTC)** every day.

### Manual Trigger

You can also trigger the workflow manually:

1. Go to **Actions** tab on GitHub
2. Select **Daily E-Newspaper Automation** workflow
3. Click **Run workflow** dropdown
4. Click **Run workflow** button

### First Run

I recommend doing a manual trigger first to verify everything works:

```bash
# Push any pending changes
git add .
git commit -m "Ready for first automated run"
git push
```

Then trigger manually as described above.

---

## 📊 Monitoring & Maintenance

### Check Workflow Status

1. Go to **Actions** tab on GitHub
2. You'll see all workflow runs with status (✅ success or ❌ failed)
3. Click on any run to see detailed logs

### Discord Notifications

Each successful run will post to Discord:
- **The Hindu** newspaper with download info
- **The Indian Express** newspaper with download info

### Storage Management

The automation includes auto-cleanup:
- Old month folders are deleted on the 8th of each month
- Example: `DEC25` folder deleted on January 8, 2026

### Monitor Storage Usage

Check your repository storage:
```bash
# Get repository size
git count-objects -vH
```

GitHub free tier provides:
- **500MB** storage for private repos
- **1GB** for public repos

---

## 🔍 Troubleshooting

### Issue: "Chrome not found" error

**Local Testing:**
```bash
# macOS
brew install --cask google-chrome

# Ubuntu/Debian
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
```

**GitHub Actions:**
- This is handled automatically by the workflow
- If it fails, check the workflow logs

### Issue: No PDFs downloaded

**Check:**
1. Website structure hasn't changed
2. Discord webhook URL is correct
3. GitHub Actions has necessary permissions
4. Check workflow logs for specific errors

**Fix:**
```bash
# Test locally first
./test_local.sh

# Check logs
cat *.log  # if log files exist
```

### Issue: "Failed to post to Discord"

**Verify:**
1. Webhook URL is correct (no extra spaces)
2. Discord channel still exists
3. Webhook wasn't deleted

**Test webhook manually:**
```bash
curl -X POST "$DISCORD_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"content":"Test message"}'
```

### Issue: GitHub Actions fails with permission error

**Fix:**
1. Go to **Settings** → **Actions** → **General**
2. Scroll to **Workflow permissions**
3. Select **Read and write permissions**
4. Click **Save**

### Issue: PDFs not being committed

**Check:**
```bash
# View .gitignore
cat .gitignore

# Ensure PDFs aren't ignored
# The line "# e-paper/**/*.pdf" means PDFs ARE tracked
```

### Issue: Duplicate downloads

The script checks `download_history.json` to avoid duplicates.

**Reset history:**
```bash
# Delete history file
rm download_history.json

# Commit change
git add .
git commit -m "Reset download history"
git push
```

### Issue: Compression fails

Compression is optional. If pypdf fails:
- Original PDF is saved
- No error thrown
- Workflow continues normally

---

## 📚 Advanced Configuration

### Change Schedule Time

Edit [.github/workflows/daily-newspaper.yml](.github/workflows/daily-newspaper.yml):

```yaml
schedule:
  # Current: 6:00 AM IST (00:30 UTC)
  - cron: '30 0 * * *'
  
  # Examples:
  # 7:00 AM IST: - cron: '30 1 * * *'
  # 8:00 AM IST: - cron: '30 2 * * *'
  # 5:00 AM IST: - cron: '30 23 * * *'
```

### Add More Newspapers

Edit `NEWSPAPERS` in [scraper.py](scraper.py):

```python
NEWSPAPERS = {
    "The Hindu": "TH",
    "Indian Express": "IE",
    # Add more newspapers here
}
```

### Disable PDF Storage (Only Post Links)

Comment out PDF download in [scraper.py](scraper.py):

```python
# Instead of downloading, just post the URL
self.post_to_discord(newspaper_name, pdf_url=pdf_url)
self.store_fallback_link(newspaper_name, pdf_url)
```

### Use Git LFS for Large Files

If PDFs are too large:

```bash
# Install Git LFS
git lfs install

# Track PDF files
git lfs track "*.pdf"

# Add .gitattributes
git add .gitattributes
git commit -m "Configure Git LFS for PDFs"
git push
```

---

## 📞 Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review GitHub Actions logs
3. Test locally with `./test_local.sh`
4. Check if website structure changed
5. Open an issue on GitHub repository

---

## 📝 Daily Workflow

Once set up, the automation runs automatically:

1. ⏰ **6:00 AM IST**: GitHub Actions triggers
2. 🌐 **Scrape**: Visits IndiaGS website
3. 📥 **Download**: Fetches The Hindu and The Indian Express
4. 🗜️ **Compress**: Reduces PDF size (optional)
5. 💬 **Post**: Sends to Discord channel
6. 💾 **Save**: Commits PDFs to repository
7. 📊 **Track**: Updates download history

You just need to check Discord for the daily newspapers! 📰

---

**Happy Reading! 📚**
