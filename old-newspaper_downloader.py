#!/usr/bin/env python3
"""
E-Newspaper Downloader and Discord Distributor
Automates downloading newspapers from IndiaGS and posts to Discord
"""

import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
import time
from urllib.parse import quote
import PyPDF2
import shutil

class NewspaperDownloader:
    def __init__(self):
        self.base_url = "https://www.indiags.com"
        self.newspapers = {
            "The Hindu": "TH-+Delhi",
            "Indian Express": "IE-+Delhi"
        }
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.history_file = "download_history.json"
        self.base_folder = "e-paper"
        
    def get_current_date_str(self):
        """Returns date in DD-MM format"""
        return datetime.now().strftime("%d-%m")
    
    def get_month_folder(self):
        """Returns folder name in MMMYY format (e.g., DEC24)"""
        return datetime.now().strftime("%b%y").upper()
    
    def load_history(self):
        """Load download history from JSON file"""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                return json.load(f)
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
    
    def construct_pdf_url(self, newspaper_code, date_str):
        """Construct direct PDF URL using observed pattern"""
        filename = f"{newspaper_code}+{date_str}.pdf"
        # Try direct PDF endpoint first
        return f"{self.base_url}/newspaper/pdf.php?file=uploads%2F{quote(filename, safe='')}"
    
    def download_pdf(self, url, output_path, max_retries=3):
        """Download PDF with retry logic"""
        for attempt in range(max_retries):
            try:
                print(f"Attempting download (attempt {attempt + 1}/{max_retries})...")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(url, headers=headers, timeout=30, stream=True)
                
                if response.status_code == 200:
                    # Check if content is actually a PDF
                    content_type = response.headers.get('content-type', '')
                    if 'pdf' in content_type.lower() or response.content.startswith(b'%PDF'):
                        with open(output_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        print(f"✓ Downloaded successfully to {output_path}")
                        return True
                    else:
                        print(f"✗ Response is not a PDF (Content-Type: {content_type})")
                else:
                    print(f"✗ HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"✗ Download error: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(5)
        
        return False
    
    def compress_pdf(self, input_path, output_path):
        """Compress PDF to save storage space"""
        try:
            print(f"Compressing PDF...")
            reader = PyPDF2.PdfReader(input_path)
            writer = PyPDF2.PdfWriter()
            
            for page in reader.pages:
                page.compress_content_streams()
                writer.add_page(page)
            
            with open(output_path, 'wb') as f:
                writer.write(f)
            
            original_size = os.path.getsize(input_path)
            compressed_size = os.path.getsize(output_path)
            reduction = ((original_size - compressed_size) / original_size) * 100
            
            print(f"✓ Compressed: {original_size/1024/1024:.2f}MB → {compressed_size/1024/1024:.2f}MB ({reduction:.1f}% reduction)")
            return True
            
        except Exception as e:
            print(f"✗ Compression failed: {e}")
            # If compression fails, just copy the original
            shutil.copy(input_path, output_path)
            return False
    
    def send_to_discord(self, newspaper, date_str, file_path, github_url=None):
        """Send notification to Discord with download link"""
        if not self.discord_webhook:
            print("⚠ Discord webhook not configured")
            return False
        
        try:
            file_size = os.path.getsize(file_path) / 1024 / 1024  # Size in MB
            
            # Create embed message
            embed = {
                "title": f"📰 {newspaper} - {date_str}",
                "description": f"Today's edition is now available!",
                "color": 3447003,  # Blue color
                "fields": [
                    {"name": "Date", "value": date_str, "inline": True},
                    {"name": "Size", "value": f"{file_size:.2f} MB", "inline": True}
                ],
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "IndiaGS E-Paper Automation"}
            }
            
            if github_url:
                embed["fields"].append({
                    "name": "📥 Download",
                    "value": f"[Click here to download]({github_url})",
                    "inline": False
                })
            
            payload = {
                "username": "E-Paper Bot",
                "embeds": [embed]
            }
            
            response = requests.post(self.discord_webhook, json=payload)
            
            if response.status_code in [200, 204]:
                print(f"✓ Discord notification sent for {newspaper}")
                return True
            else:
                print(f"✗ Discord notification failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Discord error: {e}")
            return False
    
    def cleanup_old_folders(self):
        """Delete folders older than current month with 7-day buffer"""
        try:
            current_date = datetime.now()
            # Calculate cutoff date (7 days into previous month)
            if current_date.day > 7:
                return  # Only cleanup after 7th day of month
            
            cutoff_date = current_date.replace(day=1) - timedelta(days=8)
            cutoff_folder = cutoff_date.strftime("%b%y").upper()
            
            base_path = Path(self.base_folder)
            if not base_path.exists():
                return
            
            for folder in base_path.iterdir():
                if folder.is_dir() and folder.name != cutoff_folder and folder.name < cutoff_folder:
                    try:
                        shutil.rmtree(folder)
                        print(f"✓ Deleted old folder: {folder.name}")
                    except Exception as e:
                        print(f"✗ Failed to delete {folder.name}: {e}")
                        
        except Exception as e:
            print(f"✗ Cleanup error: {e}")
    
    def generate_github_url(self, file_path):
        """Generate GitHub Pages URL for the file"""
        repo_name = os.getenv("GITHUB_REPOSITORY", "username/repo")
        # Format: https://username.github.io/repo/e-paper/DEC24/TH-Delhi-14-12.pdf
        return f"https://{repo_name.split('/')[0]}.github.io/{repo_name.split('/')[1]}/{file_path}"
    
    def process_newspaper(self, newspaper, newspaper_code):
        """Main processing logic for a single newspaper"""
        date_str = self.get_current_date_str()
        month_folder = self.get_month_folder()
        
        print(f"\n{'='*60}")
        print(f"Processing: {newspaper} ({date_str})")
        print(f"{'='*60}")
        
        # Check if already processed
        if self.check_if_already_downloaded(newspaper, date_str):
            print(f"⚠ Already processed {newspaper} for {date_str}")
            return False
        
        # Create folder structure
        folder_path = Path(self.base_folder) / month_folder
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # Construct URLs and filenames
        pdf_url = self.construct_pdf_url(newspaper_code, date_str)
        temp_file = folder_path / f"temp_{newspaper_code.replace('+', '-')}-{date_str}.pdf"
        final_file = folder_path / f"{newspaper_code.replace('+', '-')}-{date_str}.pdf"
        
        print(f"URL: {pdf_url}")
        
        # Download PDF
        if not self.download_pdf(pdf_url, temp_file):
            print(f"✗ Failed to download {newspaper}")
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
            "github_url": github_url
        })
        self.save_history(history)
        
        print(f"✓ Successfully processed {newspaper}")
        return True
    
    def run(self):
        """Main execution method"""
        print(f"\n{'#'*60}")
        print(f"# E-Newspaper Downloader")
        print(f"# Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*60}\n")
        
        success_count = 0
        
        for newspaper, code in self.newspapers.items():
            try:
                if self.process_newspaper(newspaper, code):
                    success_count += 1
                time.sleep(2)  # Brief pause between newspapers
            except Exception as e:
                print(f"✗ Error processing {newspaper}: {e}")
        
        # Cleanup old folders
        self.cleanup_old_folders()
        
        print(f"\n{'='*60}")
        print(f"Summary: {success_count}/{len(self.newspapers)} newspapers processed")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        return success_count > 0

if __name__ == "__main__":
    downloader = NewspaperDownloader()
    success = downloader.run()
    exit(0 if success else 1)
