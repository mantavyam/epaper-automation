#!/usr/bin/env python3
"""
E-Newspaper Link Extractor Script for IndiaGS
Extracts The Hindu and The Indian Express newspaper links daily
Posts links to Discord webhook for archival and access
"""

import os
import json
import time
import re
import requests
from datetime import datetime
from urllib.parse import urljoin
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Configuration
BASE_URL = "https://www.indiags.com/epaper-pdf-download"
HISTORY_FILE = "download_history.json"
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
    """Handles the newspaper link extraction and delivery"""
    
    def __init__(self):
        self.history = self.load_history()
        self.today = datetime.now()
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
    
    def transform_ad_url_to_pdf(self, ad_url):
        """Transform ad.php URLs to pdf.php URLs"""
        pdf_url = re.sub(r'/newspaper/ad\.php', '/newspaper/pdf.php', ad_url)
        if pdf_url != ad_url:
            logger.info(f"Transformed URL: ad.php -> pdf.php")
            return pdf_url
        return ad_url
    
    def get_newspaper_links(self):
        """Scrape the main page to get newspaper links"""
        logger.info(f"Accessing main page: {BASE_URL}")
        self.driver.get(BASE_URL)
        
        # Wait for page to load
        time.sleep(3)
        
        newspaper_links = {}
        target_newspapers = set(NEWSPAPERS.keys())
        
        try:
            # Find all newspaper items
            pdf_items = self.driver.find_elements(By.CLASS_NAME, "pdf-item")
            
            for item in pdf_items:
                try:
                    # Get newspaper title
                    title_elem = item.find_element(By.CLASS_NAME, "card-d-s-title")
                    title = title_elem.text.strip()
                    
                    # Check if it's one of our target newspapers
                    if title in target_newspapers and title not in newspaper_links:
                        # Get the Read link
                        read_link = item.find_element(By.CLASS_NAME, "btn-read")
                        href = read_link.get_attribute("href")
                        newspaper_links[title] = urljoin(BASE_URL, href)
                        logger.info(f"Found {title}: {href}")
                            
                except NoSuchElementException:
                    continue
            
        except Exception as e:
            logger.error(f"Error getting newspaper links: {e}")
        
        return newspaper_links
    

    
    def post_to_discord(self, newspaper_name, pdf_url):
        """Post newspaper link to Discord via webhook"""
        if not DISCORD_WEBHOOK_URL:
            logger.warning("Discord webhook URL not configured")
            return False
        
        try:
            date_str = self.today.strftime("%d %B %Y")
            
            # Prepare embed
            embed = {
                "title": f"{newspaper_name} - {date_str}",
                "color": 0x3498db if "Hindu" in newspaper_name else 0xe74c3c,
                "timestamp": self.today.isoformat(),
                "description": "Link extracted and ready to view",
                "fields": [
                    {
                        "name": "View PDF",
                        "value": pdf_url,
                        "inline": False
                    }
                ],
                "footer": {
                    "text": "E-Newspaper Link Extractor"
                }
            }
            
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
        """Process a single newspaper link extraction"""
        date_key = self.today.strftime("%Y-%m-%d")
        month_key = self.today.strftime("%m-%Y")
        
        # Check if already processed today
        if month_key in self.history:
            if date_key in self.history[month_key]:
                if newspaper_name in self.history[month_key][date_key]:
                    logger.info(f"{newspaper_name} already processed today")
                    return
        
        logger.info(f"Processing {newspaper_name}...")
        
        # Transform ad.php URL to pdf.php
        pdf_url = self.transform_ad_url_to_pdf(initial_url)
        
        # Post to Discord
        self.post_to_discord(newspaper_name, pdf_url)
        
        # Update history with nested structure
        if month_key not in self.history:
            self.history[month_key] = {}
        if date_key not in self.history[month_key]:
            self.history[month_key][date_key] = {}
        
        self.history[month_key][date_key][newspaper_name] = {
            "pdf_url": pdf_url,
            "timestamp": datetime.now().isoformat()
        }
        
        self.save_history()
        logger.info(f"Successfully extracted and posted {newspaper_name}")
    
    def run(self):
        """Main execution flow"""
        logger.info("=== E-Newspaper Link Extraction Started ===")
        
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
            
            logger.info("=== E-Newspaper Link Extraction Completed ===")
            
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
