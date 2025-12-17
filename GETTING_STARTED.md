# 🚀 Getting Started - Visual Guide

## 🎯 What You'll Achieve

By the end of this guide, you'll have:
- ✅ Automated daily newspaper downloads
- ✅ Newspapers posted to your Discord channel at 6 AM IST
- ✅ Organized PDF storage in your GitHub repository
- ✅ Zero manual intervention required

---

## 📋 Prerequisites (5 minutes)

### What You Need

```
✓ Computer with internet
✓ GitHub account (free)
✓ Discord server with admin rights
✓ Basic command line knowledge
```

### What Gets Installed

```
✓ Python 3.11+ (if testing locally)
✓ Google Chrome (if testing locally)
✓ Git (for pushing code)
```

---

## 🎬 Setup Flow (Visual)

```
┌────────────────────────────────────────────────────────────┐
│                    SETUP SEQUENCE                          │
└────────────────────────────────────────────────────────────┘

[1] Create Discord Webhook
    └─► Get webhook URL
         │
         ▼
[2] Fork/Clone Repository
    └─► Your GitHub account
         │
         ▼
[3] Configure GitHub Secret
    └─► Add DISCORD_WEBHOOK_URL
         │
         ▼
[4] Enable GitHub Actions
    └─► Allow workflows to run
         │
         ▼
[5] Test Manually
    └─► Trigger first run
         │
         ▼
[6] Verify Results
    └─► Check Discord channel
         │
         ▼
✅ DONE! Daily automation active
```

---

## 🔧 Step-by-Step Setup

### Step 1: Discord Webhook (2 minutes)

```
1. Open Discord → Your Server
2. Click ⚙️ Server Settings
3. Go to Integrations
4. Click Webhooks
5. Click "New Webhook"
6. Configure:
   • Name: E-Newspaper Bot
   • Channel: #newspapers (or your preferred channel)
7. Click "Copy Webhook URL"
8. Save it somewhere safe!

Example webhook URL:
https://discord.com/api/webhooks/123456789/abcdef...
```

**Visual:**
```
Discord Server
    └── Server Settings (⚙️)
        └── Integrations
            └── Webhooks
                └── New Webhook
                    ├── Name: E-Newspaper Bot
                    ├── Channel: #newspapers
                    └── Copy Webhook URL ✓
```

---

### Step 2: GitHub Repository (3 minutes)

**Option A: Fork (Recommended)**
```
1. Go to the original repository
2. Click "Fork" button (top right)
3. Select your account
4. Wait for fork to complete
```

**Option B: Clone & Push**
```bash
# Clone the repository
git clone https://github.com/original/epaper-automation.git
cd epaper-automation

# Create your own GitHub repository
# (via GitHub web interface)

# Update remote
git remote set-url origin https://github.com/YOUR_USERNAME/epaper-automation.git

# Push
git push -u origin main
```

**Visual:**
```
GitHub
  └── New Repository
      ├── Name: epaper-automation
      ├── Visibility: Private (recommended)
      └── Create Repository
          └── Push code
              └── ✅ Repository ready!
```

---

### Step 3: Configure GitHub Secret (2 minutes)

```
1. Go to your repository on GitHub
2. Click "Settings" tab
3. In left sidebar: Secrets and variables → Actions
4. Click "New repository secret"
5. Fill in:
   • Name: DISCORD_WEBHOOK_URL
   • Value: [paste your Discord webhook URL]
6. Click "Add secret"
```

**Visual:**
```
Your Repository
  └── Settings
      └── Secrets and variables
          └── Actions
              └── New repository secret
                  ├── Name: DISCORD_WEBHOOK_URL
                  ├── Value: https://discord.com/api/webhooks/...
                  └── Add secret ✓
```

**⚠️ Important:**
- Don't include quotes around the URL
- Make sure there are no extra spaces
- Keep this secret private!

---

### Step 4: Enable GitHub Actions (1 minute)

```
1. Go to "Actions" tab in your repository
2. If you see a message about workflows:
   Click "I understand my workflows, go ahead and enable them"
3. You should see "Daily E-Newspaper Automation" workflow
```

**Visual:**
```
Repository
  └── Actions Tab
      ├── Enable workflows (if needed)
      └── See workflow: "Daily E-Newspaper Automation"
          ├── Scheduled: Daily at 6:00 AM IST
          └── Status: Ready to run
```

---

### Step 5: Test Run (5 minutes)

**Manual Trigger:**
```
1. Go to Actions tab
2. Click "Daily E-Newspaper Automation" in left sidebar
3. Click "Run workflow" button (right side)
4. Keep "Branch: main" selected
5. Click green "Run workflow" button
6. Wait 30 seconds, refresh page
7. Click on the running workflow to see logs
```

**Visual:**
```
Actions Tab
  └── Daily E-Newspaper Automation
      └── Run workflow ▼
          ├── Branch: main
          └── Run workflow (button)
              └── Watch logs...
                  ├── Setup Environment ✓
                  ├── Download Newspapers ✓
                  ├── Post to Discord ✓
                  └── Commit Changes ✓
```

**Expected Log Output:**
```
✓ Checkout repository
✓ Set up Python 3.11
✓ Install dependencies
✓ Install Chrome and ChromeDriver
✓ Run newspaper automation
  ├─► Processing The Hindu...
  ├─► Downloaded: e-paper/DEC25/TH_2025-12-17.pdf
  ├─► Posted to Discord: The Hindu
  ├─► Processing Indian Express...
  ├─► Downloaded: e-paper/DEC25/IE_2025-12-17.pdf
  └─► Posted to Discord: Indian Express
✓ Commit and push changes
```

---

### Step 6: Verify Results (2 minutes)

**Check Discord:**
```
1. Open your Discord server
2. Go to the channel you configured
3. You should see 2 messages:
   📰 The Hindu - [Today's Date]
   📰 The Indian Express - [Today's Date]
```

**Check GitHub:**
```
1. Go to your repository
2. Browse to: e-paper/DEC25/ (or current month)
3. You should see:
   • TH_2025-12-17.pdf
   • IE_2025-12-17.pdf
4. Check download_history.json
   • Should have today's entry
```

**Visual Discord Message:**
```
┌───────────────────────────────────────┐
│ 📰 The Hindu - 17 December 2025      │
├───────────────────────────────────────┤
│ ✅ Downloaded successfully            │
│ 📁 Size: 12.34 MB                     │
│                                       │
│ File Location                         │
│ e-paper/DEC25/TH_2025-12-17.pdf      │
│                                       │
│ 📥 Direct Link                        │
│ [Download URL]                        │
└───────────────────────────────────────┘
```

---

## ✅ Success Criteria

After completing all steps, verify:

- [ ] Discord webhook URL is configured
- [ ] GitHub repository exists with all code
- [ ] GitHub secret is set (DISCORD_WEBHOOK_URL)
- [ ] GitHub Actions is enabled
- [ ] First manual run completed successfully
- [ ] Both newspapers appear in Discord
- [ ] PDFs saved in e-paper/MMMYY/ folder
- [ ] download_history.json created
- [ ] No errors in Actions logs

**If all checked: 🎉 You're done! Newspapers will auto-download daily at 6 AM IST**

---

## 🔄 Daily Operation

Once set up, here's what happens automatically:

```
Every Day at 6:00 AM IST:

1. GitHub Actions wakes up
   └─► Runs the automation workflow

2. Script navigates to IndiaGS
   └─► Finds The Hindu & Indian Express

3. Downloads both newspapers
   └─► Saves to e-paper/DEC25/

4. Compresses PDFs (optional)
   └─► Saves storage space

5. Posts to Discord
   └─► Students get notified

6. Updates repository
   └─► Commits new files

7. You do nothing! 😊
   └─► Just check Discord for newspapers
```

---

## 🛠️ Local Testing (Optional)

If you want to test locally before GitHub Actions:

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/epaper-automation.git
cd epaper-automation

# 2. Create .env file
cp .env.example .env
nano .env  # Add your Discord webhook URL

# 3. Run test script
./test_local.sh
```

**What happens:**
```
🔧 E-Newspaper Automation - Local Test
======================================
✅ Python found: Python 3.11.x
📦 Creating virtual environment...
🔌 Activating virtual environment...
📚 Installing dependencies...
✅ Discord webhook configured
✅ Chrome found
🚀 Running newspaper automation...
======================================
✅ Automation completed successfully!
```

---

## 📊 Monitoring

### Check Workflow Status

```
Repository → Actions Tab
  └─► See all runs
      ├─► ✅ Green checkmark = Success
      ├─► ❌ Red X = Failed (check logs)
      └─► 🟡 Yellow dot = In progress
```

### View Downloaded Files

```
Repository → Code Tab → e-paper/
  └─► DEC25/
      ├─► TH_2025-12-17.pdf
      ├─► IE_2025-12-17.pdf
      └─► (more files...)
```

### Check History

```
Repository → download_history.json
  └─► View all processed dates
      └─► File paths and URLs
```

---

## 🚨 Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| No Discord messages | Check webhook URL in GitHub Secrets |
| Workflow fails | Click workflow → View logs → Find error |
| PDFs not downloading | Website might have changed structure |
| "Permission denied" | Settings → Actions → Enable read/write |
| Duplicate downloads | History file prevents this automatically |

**For detailed troubleshooting, see [SETUP_GUIDE.md](SETUP_GUIDE.md#troubleshooting)**

---

## 🎓 Understanding the Components

### What Each File Does

```
scraper.py
  └─► Main automation script
      • Navigates website
      • Downloads PDFs
      • Posts to Discord

requirements.txt
  └─► Python dependencies
      • selenium, requests, pypdf

.github/workflows/daily-newspaper.yml
  └─► GitHub Actions configuration
      • When to run
      • What to do

download_history.json (auto-generated)
  └─► Tracks processed newspapers
      • Prevents duplicates

e-paper/ (auto-generated)
  └─► PDF storage
      • Organized by month
```

---

## 🎯 Next Steps

Now that you're set up:

1. **Wait for Tomorrow**
   - Automation runs at 6 AM IST
   - Check Discord for newspapers

2. **Share with Students**
   - Tell them about the Discord channel
   - They get daily newspapers automatically

3. **Monitor Weekly**
   - Check Actions tab for any failures
   - Verify newspapers are being posted

4. **Read Documentation**
   - [SETUP_GUIDE.md](SETUP_GUIDE.md) for advanced config
   - [ARCHITECTURE.md](ARCHITECTURE.md) to understand design
   - [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for full overview

---

## 💡 Tips

### Storage Management
- PDFs are auto-cleaned monthly
- Old month deleted on 8th of each month
- Monitor storage: `python maintenance.py storage`

### Customization
- Change schedule: Edit `.github/workflows/daily-newspaper.yml`
- Add more newspapers: Edit `NEWSPAPERS` dict in `scraper.py`
- Disable PDF storage: Comment out download in script

### Maintenance Commands
```bash
python maintenance.py history     # View recent downloads
python maintenance.py storage     # Check storage usage
python maintenance.py verify      # Verify setup
python maintenance.py export      # Export all links
```

---

## 🎉 Congratulations!

You've successfully set up automated e-newspaper delivery!

Students can now focus on studying instead of hunting for newspapers daily.

**Happy Reading! 📚**

---

## 📞 Need Help?

- 📖 Read [SETUP_GUIDE.md](SETUP_GUIDE.md)
- 📖 Check [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)
- 🐛 Open an issue on GitHub
- 💬 Ask in discussions

---

**Made with ❤️ for students by students**
