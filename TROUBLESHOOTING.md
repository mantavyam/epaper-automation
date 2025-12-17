# 🔧 Troubleshooting Guide

Common issues and their solutions for the e-newspaper automation system.

---

## 🚨 GitHub Actions Errors

### Error: "Chrome not found" or "ChromeDriver not found"

**Symptoms:**
```
Error: google-chrome: command not found
Or: chromedriver: not found
```

**Solution:**
The workflow should handle this automatically. If it fails:

```yaml
# Check .github/workflows/daily-newspaper.yml
# Ensure this step exists:
- name: Install Chrome and ChromeDriver
  run: |
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    # ... rest of installation
```

**Local Testing:**
```bash
# macOS
brew install --cask google-chrome

# Ubuntu
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
```

---

### Error: "Permission denied" when committing

**Symptoms:**
```
Error: fatal: could not read Username for 'https://github.com'
Or: Permission denied (publickey)
```

**Solution:**
1. Go to **Settings** → **Actions** → **General**
2. Scroll to "Workflow permissions"
3. Select **"Read and write permissions"**
4. Check **"Allow GitHub Actions to create and approve pull requests"**
5. Click **Save**

---

### Error: "Resource not accessible by integration"

**Symptoms:**
```
Error: Resource not accessible by integration
HttpError: Resource not accessible by integration
```

**Solution:**
Same as above - enable read/write permissions for workflows.

---

### Error: "No newspapers found"

**Symptoms:**
```
WARNING: No newspaper links found
ERROR: No newspapers to process
```

**Possible Causes:**
1. Website structure changed
2. Network timeout
3. Page didn't load properly

**Solution:**
1. **Test locally first:**
   ```bash
   ./test_local.sh
   ```

2. **Check the website manually:**
   - Visit https://www.indiags.com/epaper-pdf-download
   - Verify newspapers are available
   - Check if HTML structure changed

3. **Update selectors if needed:**
   ```python
   # In scraper.py, check these selectors:
   pdf_items = self.driver.find_elements(By.CLASS_NAME, "pdf-item")
   title_elem = item.find_element(By.CLASS_NAME, "card-d-s-title")
   ```

---

## 💬 Discord Integration Issues

### Error: "Failed to post to Discord"

**Symptoms:**
```
ERROR: Error posting to Discord: 404 Client Error
Or: Invalid Webhook Token
```

**Solution:**

**Check webhook URL:**
```bash
# Test webhook manually
curl -X POST "YOUR_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"content":"Test message from automation"}'
```

**Verify GitHub Secret:**
1. Go to **Settings** → **Secrets** → **Actions**
2. Check `DISCORD_WEBHOOK_URL` exists
3. Click **Update** and re-paste the URL (ensure no extra spaces)

**Check webhook is active in Discord:**
1. Discord Server → Settings → Integrations → Webhooks
2. Verify the webhook still exists
3. If deleted, create a new one and update GitHub secret

---

### Error: Messages not appearing in Discord

**Symptoms:**
- Workflow succeeds
- No errors in logs
- But no Discord messages

**Solution:**

**Check channel permissions:**
1. Webhook must have permission to post in the channel
2. Channel must not be archived
3. Check Discord server status

**Verify webhook URL format:**
```
Correct: https://discord.com/api/webhooks/123456789/abcdef...
Wrong: https://discordapp.com/... (old format)
```

---

## 📥 Download Issues

### Error: "Failed to download PDF"

**Symptoms:**
```
ERROR: Error downloading PDF: HTTPError 404
Or: Connection timeout
```

**Solution:**

**Check if PDF exists:**
1. Run workflow manually
2. Check logs for the PDF URL
3. Copy URL and try opening in browser
4. If 404, website might have changed

**Network timeout:**
```python
# In scraper.py, increase timeout:
response = requests.get(pdf_url, timeout=120)  # Increase from 60
```

---

### Error: "PDF file is 0 bytes" or corrupted

**Symptoms:**
- PDF downloads but is empty
- PDF won't open

**Solution:**

**Check response:**
```python
# Debug in scraper.py:
response = requests.get(pdf_url, timeout=60)
print(f"Status: {response.status_code}")
print(f"Size: {len(response.content)}")
```

**Verify URL:**
- Make sure you're getting the actual PDF URL, not an intermediate page
- Check if the URL redirects

---

## 🗜️ Compression Issues

### Error: "pypdf not available"

**Symptoms:**
```
WARNING: pypdf not available, PDF compression disabled
```

**Solution:**

**Install pypdf:**
```bash
pip install pypdf
```

**Or in requirements.txt:**
```
pypdf>=3.17.0
```

**Not critical:**
- Compression is optional
- Original PDF will be saved
- Workflow continues normally

---

### Error: "Compression failed"

**Symptoms:**
```
ERROR: Error compressing PDF: ...
```

**Solution:**
- This is normal for some PDFs
- Original file is kept
- No action needed

**To disable compression:**
```python
# In scraper.py, comment out:
# file_path = self.compress_pdf(file_path)
```

---

## 🌐 Website Scraping Issues

### Error: "Element not found" or "No such element"

**Symptoms:**
```
NoSuchElementException: Message: no such element: Unable to locate element
```

**Solution:**

**Website structure changed:**
1. Visit the website manually
2. Inspect the HTML elements
3. Update selectors in `scraper.py`:

```python
# Find current class names
# Old: class="pdf-item"
# New: class="newspaper-card" (example)

# Update in scraper.py:
pdf_items = self.driver.find_elements(By.CLASS_NAME, "newspaper-card")
```

**Increase wait time:**
```python
# In scraper.py:
time.sleep(5)  # Increase from 3
```

---

### Error: "Timeout waiting for download button"

**Symptoms:**
```
TimeoutException: Message: timeout
```

**Solution:**

**Increase timeout:**
```python
# In scraper.py:
download_btn = WebDriverWait(self.driver, 30).until(  # Increase from 20
    EC.presence_of_element_located((By.ID, "downloadBtn"))
)
```

**Check if button exists:**
- Visit page manually
- Verify button has id="downloadBtn"
- Check if JavaScript is blocking

---

## 📁 File System Issues

### Error: "Permission denied" when creating folders

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: 'e-paper/DEC25'
```

**Solution:**

**Local:**
```bash
# Check directory permissions
ls -la

# Fix permissions
chmod 755 e-paper/
```

**GitHub Actions:**
- Usually not an issue
- Workspace is writable by default

---

### Error: "Disk space full"

**Symptoms:**
```
OSError: [Errno 28] No space left on device
```

**Solution:**

**Check repository size:**
```bash
python maintenance.py storage
```

**Free up space:**
```bash
# Delete old files
python maintenance.py cleanup --days 30

# Or manually:
rm -rf e-paper/NOV25/
```

**Long-term solution:**
1. Enable Git LFS for large files
2. Or disable PDF storage, only store links

---

## 📊 History File Issues

### Error: "Invalid history file" or JSON decode error

**Symptoms:**
```
JSONDecodeError: Expecting value: line 1 column 1
```

**Solution:**

**Reset history:**
```bash
# Backup first
cp download_history.json download_history.json.backup

# Delete corrupted file
rm download_history.json

# Script will create new one on next run
```

---

### Issue: "Downloading same newspaper multiple times"

**Symptoms:**
- Same date appears multiple times in history
- PDFs are re-downloaded

**Solution:**

**Check history format:**
```json
{
  "2025-12-17": {
    "The Hindu": {
      "file_path": "e-paper/DEC25/TH_2025-12-17.pdf",
      "pdf_url": "https://...",
      "timestamp": "2025-12-17T06:00:00"
    }
  }
}
```

**Ensure date format is correct:**
```python
# In scraper.py:
date_key = self.today.strftime("%Y-%m-%d")  # Must be YYYY-MM-DD
```

---

## 🔍 Debugging Tips

### Enable verbose logging

```python
# In scraper.py, add at the top:
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

### Take screenshots on error

```python
# In scraper.py, add error handling:
try:
    # Your code
except Exception as e:
    self.driver.save_screenshot('error_screenshot.png')
    logger.error(f"Error: {e}")
```

### Print page source

```python
# Debug HTML:
print(self.driver.page_source)
```

### Check element exists before clicking

```python
# Use WebDriverWait:
element = WebDriverWait(self.driver, 10).until(
    EC.presence_of_element_located((By.ID, "myButton"))
)
element.click()
```

---

## 🧪 Testing Checklist

When troubleshooting, verify:

- [ ] Python 3.11+ installed
- [ ] Chrome browser installed
- [ ] All dependencies in requirements.txt installed
- [ ] Discord webhook URL is valid
- [ ] GitHub secret is configured correctly
- [ ] Workflow has read/write permissions
- [ ] Website is accessible
- [ ] Website structure hasn't changed
- [ ] Internet connection is stable
- [ ] No rate limiting from website

---

## 🆘 Common Error Messages Reference

| Error | Meaning | Quick Fix |
|-------|---------|-----------|
| `ModuleNotFoundError: No module named 'selenium'` | Dependencies not installed | `pip install -r requirements.txt` |
| `WebDriverException: chrome not reachable` | Chrome not found | Install Chrome browser |
| `TimeoutException` | Element took too long to load | Increase timeout value |
| `NoSuchElementException` | Element not found on page | Update selector or check website |
| `HTTPError: 404` | URL not found | Check if URL is still valid |
| `JSONDecodeError` | Invalid JSON in history | Reset history file |
| `PermissionError` | Can't write to file/folder | Check permissions |
| `ConnectionError` | Network issue | Check internet connection |

---

## 📞 Getting Help

If you've tried everything and still have issues:

1. **Check GitHub Actions logs:**
   - Actions tab → Click failed run → View detailed logs

2. **Test locally:**
   ```bash
   ./test_local.sh
   ```

3. **Check if website changed:**
   - Visit https://www.indiags.com/epaper-pdf-download
   - Compare with sample HTML files in e-newspaper/

4. **Verify configuration:**
   ```bash
   python maintenance.py verify
   ```

5. **Open an issue:**
   - Include error logs
   - Include workflow run URL
   - Describe what you've tried

---

## 🔄 Recovery Procedures

### Complete Reset

If everything is broken:

```bash
# 1. Backup history (if needed)
cp download_history.json backup.json

# 2. Delete generated files
rm -rf e-paper/
rm download_history.json

# 3. Re-run test
./test_local.sh

# 4. If works locally, commit and push
git add .
git commit -m "Reset automation"
git push

# 5. Trigger GitHub Actions manually
```

### Website Structure Changed

```bash
# 1. Download sample pages
wget https://www.indiags.com/epaper-pdf-download -O new-homepage.html

# 2. Compare with e-newspaper/indiags-home.html
diff e-newspaper/indiags-home.html new-homepage.html

# 3. Update scraper.py selectors based on differences

# 4. Test locally before pushing
./test_local.sh
```

---

**Remember: Most issues are configuration problems, not code bugs!**

**Check the basics first: webhook URL, permissions, and dependencies.**
