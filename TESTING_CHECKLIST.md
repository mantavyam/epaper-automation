# ✅ Testing Checklist

Use this checklist to verify your e-newspaper automation is working correctly.

## 📋 Pre-Deployment Checklist

### Local Environment
- [ ] Python 3.11+ installed
- [ ] Google Chrome installed
- [ ] Git installed and configured
- [ ] Virtual environment created
- [ ] All dependencies installed (`pip install -r requirements.txt`)

### Configuration
- [ ] `.env` file created from `.env.example`
- [ ] Discord webhook URL added to `.env`
- [ ] Webhook URL tested (sends test message successfully)
- [ ] `.gitignore` updated to exclude `.env`

### Code Review
- [ ] `scraper.py` has correct base URL
- [ ] Newspaper names match website exactly
- [ ] Folder naming convention is correct (MMMYY format)
- [ ] Cleanup logic is set for 8th of month

---

## 🧪 Local Testing

### Basic Functionality
- [ ] Run `./test_local.sh` successfully
- [ ] Script completes without errors
- [ ] PDFs downloaded to `e-paper/MMMYY/` folder
- [ ] Both newspapers present (TH and IE)
- [ ] `download_history.json` created with today's entry

### File Verification
- [ ] PDFs are valid (can be opened)
- [ ] File sizes are reasonable (not 0 bytes)
- [ ] Filenames follow format: `TH_YYYY-MM-DD.pdf`
- [ ] Compression attempted (check console logs)

### Discord Integration
- [ ] Both newspapers posted to Discord channel
- [ ] Discord embeds show correct information
- [ ] PDF URLs are clickable
- [ ] File size information is displayed

---

## 🐙 GitHub Setup

### Repository
- [ ] Repository created on GitHub
- [ ] Code pushed to `main` branch
- [ ] All files present (check on GitHub)
- [ ] `.env` NOT pushed (check it's gitignored)

### Secrets Configuration
- [ ] `DISCORD_WEBHOOK_URL` secret added
- [ ] Secret value is correct (no extra spaces)
- [ ] Secret is accessible to workflows

### GitHub Actions
- [ ] Workflows enabled in Actions tab
- [ ] `daily-newspaper.yml` visible
- [ ] Workflow permissions set to "Read and write"

---

## ☁️ GitHub Actions Testing

### First Manual Run
- [ ] Trigger workflow manually
- [ ] Workflow starts successfully
- [ ] All steps complete without errors
- [ ] Check detailed logs for warnings

### Workflow Steps
- [ ] ✅ Checkout repository
- [ ] ✅ Set up Python 3.11
- [ ] ✅ Install dependencies
- [ ] ✅ Install Chrome and ChromeDriver
- [ ] ✅ Run newspaper automation
- [ ] ✅ Commit and push changes
- [ ] ✅ No errors in logs

### Post-Run Verification
- [ ] New commit appears in repository
- [ ] Commit message is correct
- [ ] PDFs added to `e-paper/` folder
- [ ] `download_history.json` updated
- [ ] Discord received both newspapers

---

## 📊 Monitoring (Day 1-7)

### Daily Checks
- [ ] Day 1: Workflow runs automatically at 6 AM IST
- [ ] Day 2: New PDFs added (no duplicates)
- [ ] Day 3: History file grows correctly
- [ ] Day 4: No errors in Actions logs
- [ ] Day 5: Discord posts are consistent
- [ ] Day 6: Storage usage is acceptable
- [ ] Day 7: Week's worth of newspapers collected

### Edge Cases
- [ ] What if website is down? (Check logs)
- [ ] What if Discord webhook fails? (PDFs still saved?)
- [ ] What if PDF is unavailable? (Fallback link stored?)
- [ ] What if workflow times out? (Check timeout settings)

---

## 🧹 Cleanup Testing (Month 2, Day 8+)

### Old Folder Deletion
- [ ] Wait until 8th of next month
- [ ] Verify previous month folder is deleted
- [ ] Current month folder still exists
- [ ] History file still intact

---

## 🔧 Advanced Testing

### Compression Testing
- [ ] PDF compression reduces file size
- [ ] Original PDF saved if compression fails
- [ ] Compressed PDFs are valid

### History Tracking
- [ ] Duplicate dates are not re-downloaded
- [ ] History survives across workflow runs
- [ ] Manual history reset works

### Error Recovery
- [ ] Script continues if one newspaper fails
- [ ] Fallback links stored correctly
- [ ] Discord still receives partial updates

---

## 📈 Performance Metrics

### Timing
- [ ] Workflow completes in < 10 minutes
- [ ] Chrome loads pages within timeout
- [ ] PDF downloads complete successfully

### Storage
- [ ] Repository size < 100MB after 1 month
- [ ] Repository size < 500MB (GitHub limit)
- [ ] Consider Git LFS if approaching limit

---

## 🚨 Troubleshooting Verified

### Common Issues Tested
- [ ] Chrome not found → Fixed
- [ ] ChromeDriver mismatch → Fixed
- [ ] Discord webhook invalid → Error message clear
- [ ] Website structure changed → Graceful failure
- [ ] Network timeout → Retry or fallback

---

## ✅ Final Sign-Off

- [ ] All local tests passed
- [ ] GitHub Actions running daily
- [ ] Discord integration working
- [ ] Storage management verified
- [ ] Error handling tested
- [ ] Documentation reviewed
- [ ] Repository is organized

---

## 📝 Notes

### Issues Encountered:
```
[Write any issues you encountered and how you resolved them]
```

### Observations:
```
[Any notable observations about performance, timing, etc.]
```

### Future Improvements:
```
[Ideas for enhancing the automation]
```

---

**Date Completed:** _______________

**Signed Off By:** _______________

---

## 🎉 Congratulations!

If all items are checked, your e-newspaper automation is production-ready!

Students can now enjoy automated daily newspapers in their Discord channel. 📚
