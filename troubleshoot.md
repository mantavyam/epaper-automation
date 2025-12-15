# 🔧 Troubleshooting Guide

## Common Issues & Solutions

### 1. Workflow Not Running Automatically

**Symptoms:**
- No daily runs visible in Actions tab
- Expected run time passed but nothing happened

**Solutions:**

✅ **Check if workflow is enabled:**
```bash
# Go to Actions tab → Select workflow → Enable if disabled
```

✅ **Verify cron schedule:**
```yaml
# .github/workflows/download_newspapers.yml
schedule:
  - cron: '30 0 * * *'  # Must be valid cron syntax
```

✅ **GitHub Actions delay:**
- Scheduled workflows can have up to 15-minute delays
- High traffic times may cause additional delays
- Try manual trigger to test

✅ **Repository visibility:**
- Public repos: No issues
- Private repos: Check Actions minutes quota

**Test Command:**
```bash
# Validate workflow syntax locally
cat .github/workflows/download_newspapers.yml | python3 -c "import yaml, sys; yaml.safe_load(sys.stdin)"
```

---

### 2. Downloads Failing

**Symptoms:**
- Workflow runs but PDFs not downloaded
- Error in logs: "Failed to download"

**Solutions:**

✅ **Check IndiaGS website availability:**
```bash
# Test if site is accessible
curl -I https://www.indiags.com/epaper-pdf-download
```

✅ **Verify URL patterns:**
The script constructs URLs like:
```
https://www.indiags.com/newspaper/pdf.php?file=uploads%2FTH-+Delhi+14-12.pdf
```

If pattern changes, update in `newspaper_downloader.py`:
```python
def construct_pdf_urls(self, newspaper_code, date_str):
    # Update this method with new patterns
```

✅ **Check date format:**
```python
# Current format: DD-MM (e.g., 14-12)
# If site changes to MM-DD, update:
def get_current_date_str(self):
    return datetime.now().strftime("%m-%d")  # Change format
```

✅ **Increase timeout:**
```python
# In newspaper_downloader.py
response = self.session.get(url, timeout=120)  # Increase from 60
```

**Debug Command:**
```bash
# Run locally to see detailed errors
python newspaper_downloader.py
```

---

### 3. Discord Notifications Not Working

**Symptoms:**
- PDFs download successfully but no Discord message
- Error: "Discord notification failed"

**Solutions:**

✅ **Verify webhook URL:**
```bash
# Test webhook manually
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"content":"🧪 Test message from E-Paper Bot"}' \
  YOUR_WEBHOOK_URL
```

✅ **Check secret configuration:**
1. Go to: Settings → Secrets and variables → Actions
2. Verify: `DISCORD_WEBHOOK_URL` exists
3. Update if needed (re-add the secret)

✅ **Webhook permissions:**
- Ensure bot has permission to post in channel
- Check Discord server settings
- Verify webhook hasn't been deleted

✅ **Rate limiting:**
Discord limits webhooks to:
- 30 requests per minute
- 5 requests per second

If hitting limits:
```python
# Add delay between messages
time.sleep(2)  # 2 seconds between newspapers
```

**Debug Output:**
```python
# Add to send_to_discord method
print(f"Webhook URL: {self.discord_webhook[:50]}...")
print(f"Response: {response.status_code}")
print(f"Response body: {response.text}")
```

---

### 4. GitHub Pages Not Loading

**Symptoms:**
- 404 error on GitHub Pages URL
- PDFs exist in repo but not accessible via Pages

**Solutions:**

✅ **Enable GitHub Pages:**
1. Settings → Pages
2. Source: "Deploy from a branch"
3. Branch: `gh-pages` (not `main`)
4. Folder: `/root`
5. Save changes

✅ **Wait for deployment:**
- First deployment: 2-5 minutes
- Subsequent: 1-2 minutes
- Check Actions tab for Pages deployment status

✅ **Verify gh-pages branch:**
```bash
# Check if branch exists
git branch -a

# If missing, push will create it automatically
```

✅ **Check file paths:**
URLs should be:
```
https://USERNAME.github.io/REPO/e-paper/DEC24/TH-Delhi-14-12.pdf
```

Not:
```
https://USERNAME.github.io/REPO/main/e-paper/...  # Wrong!
```

✅ **Clear cache:**
```bash
# Hard refresh in browser
# Chrome/Firefox: Ctrl+Shift+R (Cmd+Shift+R on Mac)
# Or use incognito/private mode
```

**Verify Deployment:**
```bash
# Check gh-pages branch content
git checkout gh-pages
ls -la e-paper/
git checkout main
```

---

### 5. PDF Files Corrupted

**Symptoms:**
- PDFs download but won't open
- Error: "File is damaged and could not be repaired"

**Solutions:**

✅ **Disable compression temporarily:**
```python
# In newspaper_downloader.py, comment out compression:
# self.compress_pdf(temp_file, final_file)
shutil.copy(temp_file, final_file)  # Use original
```

✅ **Check file size:**
```bash
# Very small files (<100KB) indicate failed downloads
ls -lh e-paper/DEC24/*.pdf
```

✅ **Validate PDF:**
```python
# Add validation before compression
def is_valid_pdf(self, file_path):
    try:
        with open(file_path, 'rb') as f:
            header = f.read(1024)
            return header.startswith(b'%PDF')
    except:
        return False
```

✅ **Try different compression:**
```python
# Alternative compression method
from PIL import Image
import img2pdf

# Or use external tools
os.system(f"gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -o {output} {input}")
```

**Test Locally:**
```bash
# Download and test manually
python3 -c "
from newspaper_downloader import NewspaperDownloader
dl = NewspaperDownloader()
dl.process_newspaper('The Hindu', dl.newspapers['The Hindu'])
"
```

---

### 6. Storage Quota Exceeded

**Symptoms:**
- Error: "You have exceeded your storage quota"
- Workflow fails with storage error

**Solutions:**

✅ **Check current usage:**
```bash
# View repository size
du -sh .
du -sh e-paper/
```

✅ **Reduce retention:**
```json
// config.json
{
  "settings": {
    "cleanup_buffer_days": 3  // Reduce from 7
  }
}
```

✅ **Increase compression:**
```python
# More aggressive compression
writer = PyPDF2.PdfWriter()
writer.add_metadata({'/Producer': 'PyPDF2', '/Creator': 'E-Paper Bot'})

for page in reader.pages:
    page.compress_content_streams()
    page.scale_to(0.9, 0.9)  # Scale down 10%
    writer.add_page(page)
```

✅ **Manual cleanup:**
```bash
# Delete old folders manually
git rm -rf e-paper/OCT24
git commit -m "Cleanup old newspapers"
git push
```

✅ **Use Git LFS:**
```bash
# For large PDFs
git lfs install
git lfs track "*.pdf"
git add .gitattributes
git commit -m "Enable Git LFS"
```

**GitHub Storage Limits:**
- Free: 1GB repository size
- Paid: Up to 100GB

---

### 7. History File Issues

**Symptoms:**
- Duplicate downloads
- History file corrupted
- JSON parse errors

**Solutions:**

✅ **Reset history:**
```bash
# Backup first
cp download_history.json download_history.backup.json

# Reset
echo '{"downloads":[]}' > download_history.json
git add download_history.json
git commit -m "Reset download history"
git push
```

✅ **Fix JSON syntax:**
```bash
# Validate JSON
python3 -m json.tool download_history.json

# Auto-fix common issues
python3 << 'EOF'
import json
with open('download_history.json') as f:
    data = json.load(f)
    
# Remove duplicates
seen = set()
data['downloads'] = [
    x for x in data['downloads']
    if (x['newspaper'], x['date']) not in seen
    and not seen.add((x['newspaper'], x['date']))
]

with open('download_history.json', 'w') as f:
    json.dump(data, f, indent=2)
EOF
```

✅ **Add backup mechanism:**
```python
# In save_history method
def save_history(self, history):
    # Backup before writing
    if os.path.exists(self.history_file):
        shutil.copy(self.history_file, f"{self.history_file}.backup")
    
    with open(self.history_file, 'w') as f:
        json.dump(history, indent=2, fp=f)
```

---

## Advanced Debugging

### Enable Verbose Logging

Add to `newspaper_downloader.py`:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Use throughout code
logger.debug(f"Attempting download from {url}")
logger.info(f"Successfully processed {newspaper}")
logger.error(f"Failed with error: {e}")
```

### Network Debugging

```python
# Add request logging
import http.client as http_client

http_client.HTTPConnection.debuglevel = 1

# Or use mitmproxy for full inspection
# pip install mitmproxy
# mitmproxy --port 8080
```

### Test Individual Components

```python
# Test PDF download
from newspaper_downloader import NewspaperDownloader
dl = NewspaperDownloader()
url = "https://www.indiags.com/newspaper/pdf.php?file=..."
dl.download_pdf(url, "test.pdf")

# Test compression
dl.compress_pdf("test.pdf", "test_compressed.pdf")

# Test Discord
dl.send_to_discord("Test", "14-12", "test.pdf", "http://example.com")
```

---

## Performance Optimization

### Speed Up Downloads

```python
# Use concurrent downloads
from concurrent.futures import ThreadPoolExecutor

def run(self):
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        for newspaper, config in self.newspapers.items():
            future = executor.submit(self.process_newspaper, newspaper, config)
            futures.append(future)
        
        for future in futures:
            future.result()
```

### Reduce Workflow Time

```yaml
# Cache Python dependencies
- name: Cache pip
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```

### Optimize PDF Compression

```python
# Fast compression (lower quality)
writer = PyPDF2.PdfWriter()
writer.add_metadata({'/Producer': 'PyPDF2'})

for page in reader.pages:
    page.compress_content_streams()  # Skip scaling
    writer.add_page(page)
```

---

## Monitoring & Alerts

### Set Up Email Notifications

```yaml
# Add to workflow
- name: Notify on Failure
  if: failure()
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 465
    username: ${{ secrets.EMAIL_USERNAME }}
    password: ${{ secrets.EMAIL_PASSWORD }}
    subject: ❌ E-Paper Download Failed
    to: your-email@example.com
    from: GitHub Actions
    body: Check ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
```

### Health Check Endpoint

```python
# Add to index.html
<script>
fetch('download_history.json')
    .then(r => r.json())
    .then(data => {
        const last = data.downloads[data.downloads.length - 1];
        const lastDate = new Date(last.timestamp);
        const hoursSince = (Date.now() - lastDate) / (1000 * 60 * 60);
        
        if (hoursSince > 30) {
            console.warn('No downloads in 30+ hours!');
            // Send alert
        }
    });
</script>
```

---

## Getting Help

### Before Opening an Issue

1. ✅ Check this troubleshooting guide
2. ✅ Review workflow logs
3. ✅ Test manually with `Run workflow`
4. ✅ Search existing issues
5. ✅ Collect error messages

### Information to Include

```markdown
**Environment:**
- OS: [e.g., Ubuntu 22.04]
- Python Version: [e.g., 3.11]
- Repository: [public/private]

**Issue:**
[Describe the problem]

**Workflow Logs:**
```
[Paste relevant log output]
```

**Steps to Reproduce:**
1. [First step]
2. [Second step]
3. [...]

**Expected vs Actual:**
- Expected: [what should happen]
- Actual: [what actually happens]
```

---

## Useful Commands

```bash
# Check workflow syntax
yamllint .github/workflows/download_newspapers.yml

# Test Python script locally
python3 -m pytest newspaper_downloader.py -v

# View git history
git log --oneline --graph --all

# Check repository size
du -sh .git

# Clean git history (dangerous!)
git filter-branch --tree-filter 'rm -rf e-paper/OLD_FOLDER' HEAD

# Force push (use with caution!)
git push --force origin main
```

---

**Still stuck? Open an issue with full details!** 🤝
