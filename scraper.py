#!/usr/bin/env python3
"""
E-Newspaper Automation Script for IndiaGS
Downloads The Hindu and The Indian Express newspapers daily
Posts to Discord and maintains organized storage
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin, quote
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Optional PDF compression
try:
    from pypdf import PdfReader, PdfWriter
    COMPRESSION_AVAILABLE = True
except ImportError:
    COMPRESSION_AVAILABLE = False
    logging.warning("pypdf not available, PDF compression disabled")

# Configuration
BASE_URL = "https://www.indiags.com/epaper-pdf-download"
HISTORY_FILE = "download_history.json"
BASE_FOLDER = "e-paper"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# Newspapers to track
NEWSPAPERS = {
    "The Hindu": "TH",
    "Indian Express": "IE"
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewspaperDownloader:
    """Handles the newspaper download automation"""
    
    def __init__(self):
        self.history = self.load_history()
        self.today = datetime.now()
        self.month_folder = self.today.strftime("%b%y").upper()  # e.g., DEC25
        self.driver = None
        
    def setup_driver(self):
        """Initialize headless Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Use webdriver-manager to automatically handle ChromeDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("Chrome driver initialized")
        
    def close_driver(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            logger.info("Chrome driver closed")
    
    def load_history(self):
        """Load download history from JSON file"""
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Invalid history file, creating new one")
                return {}
        return {}
    
    def save_history(self):
        """Save download history to JSON file"""
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.history, f, indent=2)
        logger.info("History saved")
    
    def create_month_folder(self):
        """Create folder for current month"""
        folder_path = Path(BASE_FOLDER) / self.month_folder
        folder_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Month folder created/verified: {folder_path}")
        return folder_path
    
    def cleanup_old_folders(self):
        """Delete old month folders after 7 days into new month"""
        if self.today.day >= 8:
            # Calculate previous month
            first_of_this_month = self.today.replace(day=1)
            last_month = first_of_this_month - timedelta(days=1)
            old_folder_name = last_month.strftime("%b%y").upper()
            old_folder_path = Path(BASE_FOLDER) / old_folder_name
            
            if old_folder_path.exists():
                try:
                    import shutil
                    shutil.rmtree(old_folder_path)
                    logger.info(f"Deleted old folder: {old_folder_path}")
                except Exception as e:
                    logger.error(f"Failed to delete old folder: {e}")
    
    def get_newspaper_links(self):
        """Scrape the main page to get newspaper links"""
        logger.info(f"Accessing main page: {BASE_URL}")
        self.driver.get(BASE_URL)
        
        # Wait for page to load
        time.sleep(3)
        
        newspaper_links = {}
        
        try:
            # Find all newspaper items
            pdf_items = self.driver.find_elements(By.CLASS_NAME, "pdf-item")
            
            for item in pdf_items:
                try:
                    # Get newspaper title
                    title_elem = item.find_element(By.CLASS_NAME, "card-d-s-title")
                    title = title_elem.text.strip()
                    
                    # Check if it's one of our target newspapers
                    for newspaper_name in NEWSPAPERS.keys():
                        if newspaper_name in title:
                            # Get the Read link
                            read_link = item.find_element(By.CLASS_NAME, "btn-read")
                            href = read_link.get_attribute("href")
                            newspaper_links[newspaper_name] = urljoin(BASE_URL, href)
                            logger.info(f"Found {newspaper_name}: {href}")
                            break
                            
                except NoSuchElementException:
                    continue
            
        except Exception as e:
            logger.error(f"Error getting newspaper links: {e}")
        
        return newspaper_links
    
    def navigate_to_download_page(self, initial_url):
        """Navigate through intermediate page to download page"""
        logger.info(f"Navigating to: {initial_url}")
        self.driver.get(initial_url)
        
        # Wait for intermediate page to load
        time.sleep(2)
        
        try:
            # Find and click "Read Newspaper" button
            read_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "read-button"))
            )
            
            # Get the onclick attribute which contains the URL
            onclick = read_button.get_attribute("onclick")
            
            # Extract URL from onclick (format: window.open('url', '_blank'))
            import re
            match = re.search(r"window\.open\('([^']+)'", onclick)
            if match:
                newsletter_url = match.group(1)
                # Convert relative URL to absolute
                full_url = urljoin(initial_url, newsletter_url)
                logger.info(f"Found newsletter URL: {full_url}")
                
                # Navigate to newsletter page
                self.driver.get(full_url)
                return True
            
        except Exception as e:
            logger.error(f"Error navigating to download page: {e}")
            return False
        
        return False
    
    def wait_for_download_button(self):
        """Wait for the download timer and get the PDF URL"""
        logger.info("Waiting for download button...")
        
        try:
            # Wait for download button to be present
            download_btn = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "downloadBtn"))
            )
            
            # Wait for timer to complete (15 seconds + buffer)
            time.sleep(16)
            
            # Get the onclick or check for window.location.href in script
            # The button triggers: window.location.href = "/newspaper/pdf.php?file=..."
            
            # Execute JavaScript to get the PDF URL
            pdf_url = self.driver.execute_script("""
                var btn = document.getElementById('downloadBtn');
                if (btn) {
                    // Simulate click and capture the URL
                    var scripts = document.getElementsByTagName('script');
                    for (var i = 0; i < scripts.length; i++) {
                        var scriptText = scripts[i].innerHTML;
                        var match = scriptText.match(/window\\.location\\.href\\s*=\\s*["']([^"']+)["']/);
                        if (match) {
                            return match[1];
                        }
                    }
                }
                return null;
            """)
            
            if pdf_url:
                # Convert relative URL to absolute
                full_pdf_url = urljoin(self.driver.current_url, pdf_url)
                logger.info(f"Found PDF URL: {full_pdf_url}")
                return full_pdf_url
            
        except TimeoutException:
            logger.error("Timeout waiting for download button")
        except Exception as e:
            logger.error(f"Error getting download button: {e}")
        
        return None
    
    def download_pdf(self, pdf_url, newspaper_name):
        """Download the PDF file"""
        try:
            response = requests.get(pdf_url, timeout=60)
            response.raise_for_status()
            
            # Generate filename
            date_str = self.today.strftime("%Y-%m-%d")
            prefix = NEWSPAPERS[newspaper_name]
            filename = f"{prefix}_{date_str}.pdf"
            
            folder_path = self.create_month_folder()
            file_path = folder_path / filename
            
            # Save PDF
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded: {file_path} ({len(response.content)} bytes)")
            return file_path
            
        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            return None
    
    def compress_pdf(self, file_path):
        """Compress PDF to save storage space"""
        if not COMPRESSION_AVAILABLE:
            logger.info("PDF compression not available, skipping")
            return file_path
        
        try:
            original_size = os.path.getsize(file_path)
            
            # Read PDF
            reader = PdfReader(file_path)
            writer = PdfWriter()
            
            # Copy all pages
            for page in reader.pages:
                writer.add_page(page)
            
            # Compress
            for page in writer.pages:
                page.compress_content_streams()
            
            # Write compressed version
            compressed_path = file_path.with_name(f"{file_path.stem}_compressed.pdf")
            with open(compressed_path, 'wb') as f:
                writer.write(f)
            
            compressed_size = os.path.getsize(compressed_path)
            
            # If compression saved space, replace original
            if compressed_size < original_size:
                os.remove(file_path)
                os.rename(compressed_path, file_path)
                savings = (1 - compressed_size/original_size) * 100
                logger.info(f"Compressed PDF: {savings:.1f}% smaller")
            else:
                # Compression didn't help, remove compressed version
                os.remove(compressed_path)
                logger.info("Compression didn't reduce size, keeping original")
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error compressing PDF: {e}")
            # Return original file path on error
            return file_path
    
    def post_to_discord(self, newspaper_name, file_path=None, pdf_url=None):
        """Post newspaper to Discord via webhook"""
        if not DISCORD_WEBHOOK_URL:
            logger.warning("Discord webhook URL not configured")
            return False
        
        try:
            date_str = self.today.strftime("%d %B %Y")
            
            # Prepare embed
            embed = {
                "title": f"📰 {newspaper_name} - {date_str}",
                "color": 0x3498db if "Hindu" in newspaper_name else 0xe74c3c,
                "timestamp": self.today.isoformat(),
                "footer": {
                    "text": "E-Newspaper Automation"
                }
            }
            
            # Add file info or URL
            if file_path and file_path.exists():
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                embed["description"] = f"✅ Downloaded successfully\n📁 Size: {file_size:.2f} MB"
                embed["fields"] = [
                    {
                        "name": "File Location",
                        "value": f"`{file_path}`",
                        "inline": False
                    }
                ]
            
            if pdf_url:
                embed["fields"] = embed.get("fields", [])
                embed["fields"].append({
                    "name": "📥 Direct Link",
                    "value": pdf_url,
                    "inline": False
                })
            
            payload = {
                "embeds": [embed]
            }
            
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Posted to Discord: {newspaper_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error posting to Discord: {e}")
            return False
    
    def process_newspaper(self, newspaper_name, initial_url):
        """Process a single newspaper download"""
        date_key = self.today.strftime("%Y-%m-%d")
        
        # Check if already processed today
        if date_key in self.history:
            if newspaper_name in self.history[date_key]:
                logger.info(f"{newspaper_name} already processed today")
                return
        
        logger.info(f"Processing {newspaper_name}...")
        
        # Navigate through pages
        if not self.navigate_to_download_page(initial_url):
            logger.error(f"Failed to navigate for {newspaper_name}")
            # Store URL as fallback
            self.store_fallback_link(newspaper_name, initial_url)
            return
        
        # Get PDF URL
        pdf_url = self.wait_for_download_button()
        if not pdf_url:
            logger.error(f"Failed to get PDF URL for {newspaper_name}")
            self.store_fallback_link(newspaper_name, initial_url)
            return
        
        # Download PDF
        file_path = self.download_pdf(pdf_url, newspaper_name)
        if not file_path:
            logger.error(f"Failed to download PDF for {newspaper_name}")
            self.store_fallback_link(newspaper_name, pdf_url)
            return
        
        # Compress PDF
        file_path = self.compress_pdf(file_path)
        
        # Post to Discord
        self.post_to_discord(newspaper_name, file_path, pdf_url)
        
        # Update history
        if date_key not in self.history:
            self.history[date_key] = {}
        
        self.history[date_key][newspaper_name] = {
            "file_path": str(file_path),
            "pdf_url": pdf_url,
            "timestamp": datetime.now().isoformat()
        }
        
        self.save_history()
        logger.info(f"✅ Successfully processed {newspaper_name}")
    
    def store_fallback_link(self, newspaper_name, url):
        """Store link as fallback when download fails"""
        date_key = self.today.strftime("%Y-%m-%d")
        
        if date_key not in self.history:
            self.history[date_key] = {}
        
        self.history[date_key][newspaper_name] = {
            "fallback_url": url,
            "timestamp": datetime.now().isoformat(),
            "status": "fallback"
        }
        
        self.save_history()
        
        # Post fallback link to Discord
        self.post_to_discord(newspaper_name, pdf_url=url)
        
        logger.info(f"Stored fallback link for {newspaper_name}")
    
    def run(self):
        """Main execution flow"""
        logger.info("=== E-Newspaper Automation Started ===")
        
        try:
            # Setup
            self.setup_driver()
            
            # Get newspaper links from main page
            newspaper_links = self.get_newspaper_links()
            
            if not newspaper_links:
                logger.error("No newspaper links found")
                return
            
            # Process each newspaper
            for newspaper_name, url in newspaper_links.items():
                try:
                    self.process_newspaper(newspaper_name, url)
                except Exception as e:
                    logger.error(f"Error processing {newspaper_name}: {e}")
                    continue
            
            # Cleanup old folders
            self.cleanup_old_folders()
            
            logger.info("=== E-Newspaper Automation Completed ===")
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise
        
        finally:
            self.close_driver()


def main():
    """Entry point"""
    downloader = NewspaperDownloader()
    downloader.run()


if __name__ == "__main__":
    main()
