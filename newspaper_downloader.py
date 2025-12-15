#!/usr/bin/env python3
"""
Advanced E-Newspaper Downloader with Web Scraping Fallback
Includes retry logic, pattern-based URLs, and web scraping capabilities
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
import time
from urllib.parse import quote, urljoin
import PyPDF2
import shutil
from bs4 import BeautifulSoup
import re

class AdvancedNewspaperDownloader:
    def __init__(self):
        self.base_url = "https://www.indiags.com"
        self.newspapers = {
            "The Hindu": {
                "code": "TH-+Delhi",
                "display_name": "The Hindu"
            },
            "Indian Express": {
                "code": "IE-+Delhi", 
                "display_name": "Indian Express"
            }
        }
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.history_file = "download_history.json"
        self.base_folder = "e-paper"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
    def get_current_date_str(self):
        """Returns date in DD-MM format"""
        return datetime.now().strftime("%d-%m")
    
    def get_month_folder(self):
        """Returns folder name in MMMYY format (e.g., DEC24)"""
        return datetime.now().strftime("%b%y").upper()
    
    def load_history(self):
        """Load download history from JSON file"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"downloads": []}
    
    def save_history(self, history):
        """Save download history to JSON file"""
        with open(self.history_file, 'w') as f:
            json.dump(history, indent=2, fp=f)
    
    def check_if_already_downloaded(self, newspaper, date_str):
        """Check if newspaper for this date was already processed"""
        history = self.load_history()
        for entry in history["downloads"]:
            if entry["newspaper"] == newspaper and entry["date"] == date_str:
                return True
        return False
    
    def construct_pdf_urls(self, newspaper_code, date_str):
        """Construct multiple potential PDF URLs using observed patterns"""
        filename = f"{newspaper_code}+{date_str}.pdf"
        encoded_filename = quote(filename, safe='')
        
        # Try multiple URL patterns based on analysis
        urls = [
            # Direct PDF endpoint (most reliable)
            f"{self.base_url}/newspaper/pdf.php?file=uploads%2F{encoded_filename}",
            
            # Alternative patterns
            f"{self.base_url}/newspaper/uploads/{filename}",
            f"{self.base_url}/uploads/{filename}",
        ]
        
        return urls
    
    def scrape_newspaper_link(self, newspaper_name):
        """Fallback: Scrape the main page to find newspaper link"""
        try:
            print(f"🔍 Scraping main page for {newspaper_name}...")
            
            response = self.session.get(f"{self.base_url}/epaper-pdf-download", timeout=30)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the newspaper card
            for card in soup.find_all('div', class_='pdf-item'):
                title_div = card.find('div', class_='card-d-s-title')
                if title_div and newspaper_name.lower() in title_div.text.lower():
                    # Find the Read button
                    read_btn = card.find('a', class_='btn-read')
                    if read_btn and read_btn.get('href'):
                        return urljoin(self.base_url, read_btn['href'])
            
            return None
            
        except Exception as e:
            print(f"✗ Scraping error: {e}")
            return None
    
    def extract_pdf_from_intermediate_page(self, url):
        """Navigate through intermediate pages to get final PDF URL"""
        try:
            print(f"📄 Navigating intermediate page...")
            
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for newsletter.php link
            newsletter_btn = soup.find('button', onclick=re.compile(r'newsletter\.php'))
            if newsletter_btn:
                onclick = newsletter_btn.get('onclick', '')
                match = re.search(r'newsletter\.php\?file=([^\'\"]+)', onclick)
                if match:
                    newsletter_url = f"{self.base_url}/newspaper/newsletter.php?file={match.group(1)}"
                    
                    # Get the newsletter page
                    response = self.session.get(newsletter_url, timeout=30)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Find download button
                        download_btn = soup.find('button', id='downloadBtn')
                        if download_btn:
                            # Extract the PDF URL from the onclick or parent form
                            # Based on the HTML, it redirects to pdf.php
                            file_param = match.group(1)
                            return f"{self.base_url}/newspaper/pdf.php?file={file_param}"
            
            return None
            
        except Exception as e:
            print(f"✗ Navigation error: {e}")
            return None
    
    def is_valid_pdf(self, file_path):
        """Verify if downloaded file is a valid PDF"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(1024)
                return header.startswith(b'%PDF')
        except:
            return False
    
    def download_pdf(self, url, output_path, max_retries=3):
        """Download PDF with retry logic and validation"""
        for attempt in range(max_retries):
            try:
                print(f"⬇️  Downloading (attempt {attempt + 1}/{max_retries})...")
                
                response = self.session.get(url, timeout=60, stream=True)
                
                if response.status_code == 200:
                    # Save to file
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    # Validate PDF
                    if self.is_valid_pdf(output_path):
                        file_size = os.path.getsize(output_path) / 1024 / 1024
                        print(f"✅ Downloaded {file_size:.2f}MB")
                        return True
                    else:
                        print(f"❌ Invalid PDF received")
                        if os.path.exists(output_path):
                            os.remove(output_path)
                else:
                    print(f"❌ HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
            
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"⏳ Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
        return False
    
    def compress_pdf(self, input_path, output_path):
        """Compress PDF to save storage space"""
        try:
            print(f"🗜️  Compressing PDF...")
            
            reader = PyPDF2.PdfReader(input_path)
            writer = PyPDF2.PdfWriter()
            
            for page in reader.pages:
                page.compress_content_streams()
                writer.add_page(page)
            
            with open(output_path, 'wb') as f:
                writer.write(f)
            
            original_size = os.path.getsize(input_path) / 1024 / 1024
            compressed_size = os.path.getsize(output_path) / 1024 / 1024
            reduction = ((original_size - compressed_size) / original_size) * 100
            
            print(f"✅ {original_size:.2f}MB → {compressed_size:.2f}MB ({reduction:.1f}% reduction)")
            return True
            
        except Exception as e:
            print(f"⚠️  Compression failed: {e}")
            # Copy original if compression fails
            if input_path != output_path:
                shutil.copy(input_path, output_path)
            return False
    
    def send_to_discord(self, newspaper, date_str, file_path, github_url=None):
        """Send notification to Discord with download link"""
        if not self.discord_webhook:
            print("⚠️  Discord webhook not configured")
            return False
        
        try:
            file_size = os.path.getsize(file_path) / 1024 / 1024
            
            embed = {
                "title": f"📰 {newspaper}",
                "description": f"**{datetime.now().strftime('%A, %B %d, %Y')}**\n\nToday's edition is ready!",
                "color": 5814783,  # Blue-purple
                "fields": [
                    {
                        "name": "📅 Date",
                        "value": date_str.replace('-', '/'),
                        "inline": True
                    },
                    {
                        "name": "📦 Size",
                        "value": f"{file_size:.2f} MB",
                        "inline": True
                    }
                ],
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "E-Paper Automation • IndiaGS"
                }
            }
            
            if github_url:
                embed["fields"].append({
                    "name": "⬇️ Download Link",
                    "value": f"[Click here to download PDF]({github_url})",
                    "inline": False
                })
            
            payload = {
                "username": "📰 E-Paper Bot",
                "embeds": [embed]
            }
            
            response = self.session.post(self.discord_webhook, json=payload, timeout=10)
            
            if response.status_code in [200, 204]:
                print(f"✅ Discord notification sent")
                return True
            else:
                print(f"❌ Discord failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Discord error: {e}")
            return False
    
    def cleanup_old_folders(self):
        """Delete folders older than current month with 7-day buffer"""
        try:
            current_date = datetime.now()
            
            # Only cleanup after 7th day of month
            if current_date.day <= 7:
                print(f"🧹 Cleanup scheduled for day 8+ (today is day {current_date.day})")
                return
            
            # Calculate cutoff (previous month)
            cutoff_date = current_date.replace(day=1) - timedelta(days=1)
            cutoff_folder = cutoff_date.strftime("%b%y").upper()
            
            base_path = Path(self.base_folder)
            if not base_path.exists():
                return
            
            deleted = 0
            for folder in base_path.iterdir():
                if folder.is_dir() and folder.name < cutoff_folder:
                    try:
                        shutil.rmtree(folder)
                        print(f"🗑️  Deleted: {folder.name}")
                        deleted += 1
                    except Exception as e:
                        print(f"❌ Failed to delete {folder.name}: {e}")
            
            if deleted == 0:
                print(f"✅ No old folders to cleanup")
            else:
                print(f"✅ Cleaned up {deleted} old folder(s)")
                        
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
    
    def generate_github_url(self, file_path):
        """Generate GitHub Pages URL for the file"""
        repo = os.getenv("GITHUB_REPOSITORY", "username/repo")
        owner = repo.split('/')[0]
        repo_name = repo.split('/')[1]
        return f"https://{owner}.github.io/{repo_name}/{file_path.replace(os.sep, '/')}"
    
    def process_newspaper(self, newspaper, config):
        """Main processing logic for a single newspaper"""
        date_str = self.get_current_date_str()
        month_folder = self.get_month_folder()
        
        print(f"\n{'='*70}")
        print(f"📰 {newspaper}")
        print(f"{'='*70}")
        
        # Check if already processed
        if self.check_if_already_downloaded(newspaper, date_str):
            print(f"⏭️  Already processed for {date_str}")
            return False
        
        # Create folder structure
        folder_path = Path(self.base_folder) / month_folder
        folder_path.mkdir(parents=True, exist_ok=True)
        
        newspaper_code = config["code"]
        temp_file = folder_path / f"temp_{newspaper_code.replace('+', '-')}-{date_str}.pdf"
        final_file = folder_path / f"{newspaper_code.replace('+', '-')}-{date_str}.pdf"
        
        # Method 1: Try direct URLs first (faster)
        print(f"🎯 Method 1: Direct URL construction")
        urls = self.construct_pdf_urls(newspaper_code, date_str)
        
        success = False
        for i, url in enumerate(urls, 1):
            print(f"  Attempt {i}/{len(urls)}: {url}")
            if self.download_pdf(url, temp_file):
                success = True
                break
            time.sleep(2)
        
        # Method 2: Fallback to web scraping
        if not success:
            print(f"\n🔄 Method 2: Web scraping fallback")
            
            # Scrape main page
            ad_page_url = self.scrape_newspaper_link(config["display_name"])
            
            if ad_page_url:
                print(f"  Found ad page: {ad_page_url}")
                
                # Navigate through intermediate pages
                pdf_url = self.extract_pdf_from_intermediate_page(ad_page_url)
                
                if pdf_url:
                    print(f"  Final PDF URL: {pdf_url}")
                    success = self.download_pdf(pdf_url, temp_file)
        
        if not success:
            print(f"❌ Failed to download {newspaper}")
            return False
        
        # Compress PDF
        self.compress_pdf(temp_file, final_file)
        
        # Clean up temp file
        if temp_file.exists() and temp_file != final_file:
            temp_file.unlink()
        
        # Generate GitHub Pages URL
        github_url = self.generate_github_url(str(final_file))
        
        # Send to Discord
        self.send_to_discord(newspaper, date_str, final_file, github_url)
        
        # Update history
        history = self.load_history()
        history["downloads"].append({
            "newspaper": newspaper,
            "date": date_str,
            "timestamp": datetime.now().isoformat(),
            "file_path": str(final_file),
            "github_url": github_url,
            "file_size_mb": round(os.path.getsize(final_file) / 1024 / 1024, 2)
        })
        self.save_history(history)
        
        print(f"✅ Successfully processed {newspaper}\n")
        return True
    
    def run(self):
        """Main execution method"""
        print(f"\n{'#'*70}")
        print(f"#  📰 E-NEWSPAPER AUTO-DOWNLOADER")
        print(f"#  🕐 {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}")
        print(f"{'#'*70}\n")
        
        success_count = 0
        failed = []
        
        for newspaper, config in self.newspapers.items():
            try:
                if self.process_newspaper(newspaper, config):
                    success_count += 1
                else:
                    failed.append(newspaper)
                time.sleep(3)  # Pause between newspapers
            except Exception as e:
                print(f"❌ Critical error processing {newspaper}: {e}")
                failed.append(newspaper)
        
        # Cleanup old folders
        print(f"\n{'='*70}")
        self.cleanup_old_folders()
        
        # Summary
        print(f"\n{'='*70}")
        print(f"📊 SUMMARY")
        print(f"{'='*70}")
        print(f"✅ Successful: {success_count}/{len(self.newspapers)}")
        if failed:
            print(f"❌ Failed: {', '.join(failed)}")
        print(f"🕐 Completed: {datetime.now().strftime('%I:%M %p')}")
        print(f"{'='*70}\n")
        
        return success_count > 0

if __name__ == "__main__":
    downloader = AdvancedNewspaperDownloader()
    success = downloader.run()
    exit(0 if success else 1)
