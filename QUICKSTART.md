# 🚀 Quick Start - E-Newspaper Automation

## One-Time Setup (5 minutes)

### 1. Get Discord Webhook
```
Discord Server → Settings → Integrations → Webhooks → New Webhook → Copy URL
```

### 2. Configure GitHub Secret
```
GitHub Repo → Settings → Secrets → Actions → New secret
Name: DISCORD_WEBHOOK_URL
Value: [paste webhook URL]
```

### 3. Enable Actions
```
GitHub Repo → Actions → Enable workflows
```

✅ **Done! Newspapers will auto-download daily at 6 AM IST**

---

## Test Locally (Optional)

```bash
# Quick test
./test_local.sh

# Or manual:
cp .env.example .env          # Edit and add webhook URL
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export DISCORD_WEBHOOK_URL="your_url"
python scraper.py
```

---

## Common Tasks

### Run manually on GitHub
```
Actions → Daily E-Newspaper Automation → Run workflow
```

### Check logs
```
Actions → Click latest run → View logs
```

### View downloaded PDFs
```
Browse: e-paper/DEC25/ (or current month)
```

### Reset history
```bash
rm download_history.json
git add . && git commit -m "Reset" && git push
```

---

## File Structure

```
📁 epaper-automation/
├── 📄 scraper.py              ← Main script
├── 📄 requirements.txt        ← Dependencies
├── 📄 download_history.json   ← Auto-generated history
├── 📁 .github/workflows/      ← GitHub Actions config
└── 📁 e-paper/               ← Downloaded PDFs
    └── 📁 DEC25/             ← Current month
        ├── TH_2025-12-17.pdf
        └── IE_2025-12-17.pdf
```

---

## Key Features

✅ Auto-runs daily at 6 AM IST  
✅ Posts to Discord automatically  
✅ Compresses PDFs to save space  
✅ Auto-deletes old months  
✅ Tracks history (no duplicates)  
✅ Falls back to links if download fails  

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No Discord posts | Check webhook URL in GitHub Secrets |
| PDFs not downloading | Test locally: `./test_local.sh` |
| Workflow fails | Check Actions logs for errors |
| Storage full | Enable Git LFS or disable PDF storage |

---

## Need Help?

📖 Read [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions  
📖 Read [README.md](README.md) for full documentation  

---

**⭐ Star the repo if it helps you!**
