#!/usr/bin/env python3
"""
Helper script to discover Seattle Times Midi crossword API URLs.

This script attempts to find the actual AmuseLabs API endpoints used by
the Seattle Times Midi crossword page.

Requirements:
    pip install selenium requests beautifulsoup4

Usage:
    python discover_urls.py

This will:
1. Load the Seattle Times Midi page in a headless browser
2. Intercept network traffic
3. Extract the AmuseLabs API URLs
4. Display the URLs to update in seattletimesdownloader.py
"""

import re
import sys
from urllib.parse import urlparse, parse_qs

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
except ImportError:
    print("Error: selenium not installed")
    print("Install with: pip install selenium")
    print("\nAlternatively, manually inspect the page:")
    print("1. Open https://www.seattletimes.com/games-crossword-midi/")
    print("2. Open DevTools > Network tab")
    print("3. Look for requests to amuselabs.com")
    print("4. Find URLs with 'date-picker' and 'crossword'")
    sys.exit(1)


def discover_urls():
    """Use Selenium to load the page and capture network requests."""
    
    print("Starting browser (this may take a moment)...")
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    # Enable performance logging to capture network traffic
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"Error: Could not start Chrome driver: {e}")
        print("\nManual inspection required:")
        print("1. Open https://www.seattletimes.com/games-crossword-midi/ in browser")
        print("2. Open DevTools > Network tab")
        print("3. Look for requests to amuselabs.com")
        sys.exit(1)
    
    print("Loading Seattle Times Midi crossword page...")
    
    try:
        # Load the page
        driver.get("https://www.seattletimes.com/games-crossword-midi/")
        
        # Wait for the puzzle embed to load
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "puzzleme-embed")))
        
        print("Page loaded, analyzing network traffic...\n")
        
        # Get performance logs (network activity)
        logs = driver.get_log('performance')
        
        amuselabs_urls = []
        
        for entry in logs:
            try:
                import json
                log = json.loads(entry['message'])['message']
                
                if log['method'] == 'Network.requestWillBeSent':
                    url = log['params']['request']['url']
                    
                    if 'amuselabs.com' in url:
                        amuselabs_urls.append(url)
            except:
                continue
        
        # Deduplicate and filter
        amuselabs_urls = list(set(amuselabs_urls))
        
        # Find picker and crossword URLs
        picker_urls = [u for u in amuselabs_urls if 'date-picker' in u]
        crossword_urls = [u for u in amuselabs_urls if 'crossword' in u and 'id=' in u]
        
        print("=" * 70)
        print("DISCOVERED URLs:")
        print("=" * 70)
        
        if picker_urls:
            print("\nDate Picker URL(s):")
            for url in picker_urls:
                print(f"  {url}")
                parsed = urlparse(url)
                base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                print(f"\n  Use in code:")
                print(f'  self.picker_url = "{base_url}?set=seattletimes-crossword-midi"')
        
        if crossword_urls:
            print("\nCrossword URL(s):")
            for url in crossword_urls:
                print(f"  {url}")
                parsed = urlparse(url)
                query = parse_qs(parsed.query)
                if 'id' in query:
                    puzzle_id = query['id'][0]
                    print(f"\n  Puzzle ID format: {puzzle_id}")
                base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                print(f"\n  Use in code:")
                print(f'  self.url_from_id = "{base_url}?id={{puzzle_id}}&set=seattletimes-crossword-midi"')
        
        if not picker_urls and not crossword_urls:
            print("\nNo AmuseLabs API calls detected!")
            print("The puzzle may load via a different mechanism.")
            print("\nAll AmuseLabs URLs found:")
            for url in amuselabs_urls:
                print(f"  {url}")
        
        print("\n" + "=" * 70)
        print("\nNext steps:")
        print("1. Update src/xword_dl/downloader/seattletimesdownloader.py")
        print("2. Test with: xword-dl stm --latest")
        print("=" * 70)
        
    finally:
        driver.quit()


if __name__ == "__main__":
    discover_urls()
