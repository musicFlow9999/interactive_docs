#!/usr/bin/env python3
"""
Quick test script to verify Selenium can detect Dynatrace documentation navigation
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin, urlparse

def test_navigation_detection():
    """Test if we can detect navigation links on the Dynatrace docs site"""
    
    print("🔧 Setting up Chrome browser...")
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        driver.set_page_load_timeout(30)
        
        print("✅ Browser initialized successfully")
        
        # Load the Dynatrace docs page
        url = "https://docs.dynatrace.com/docs"
        print(f"🌐 Loading {url}...")
        
        driver.get(url)
        
        # Wait for page to load
        print("⏳ Waiting for JavaScript to render...")
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(3)  # Additional wait for dynamic content
        
        print("✅ Page loaded successfully")
        
        # Get page source and parse
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Extract title
        title = soup.find('title')
        print(f"📄 Page title: {title.get_text() if title else 'No title'}")
        
        # Test various navigation selectors
        nav_selectors = [
            'nav a[href]',
            '.navigation a[href]',
            '.nav a[href]',
            '.sidebar a[href]',
            '.menu a[href]',
            '[role="navigation"] a[href]',
            '.docs-nav a[href]',
            '[data-testid*="nav"] a[href]',
            '[class*="nav"] a[href]',
            'a[href^="/docs"]'
        ]
        
        all_links = set()
        selector_results = {}
        
        for selector in nav_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                links = []
                for element in elements:
                    href = element.get_attribute('href')
                    if href and '/docs' in href:
                        absolute_url = urljoin(url, href)
                        parsed = urlparse(absolute_url)
                        if parsed.netloc == 'docs.dynatrace.com':
                            links.append(absolute_url)
                            all_links.add(absolute_url)
                
                selector_results[selector] = len(links)
                if links:
                    print(f"🔗 {selector}: {len(links)} links")
                    for link in links[:3]:  # Show first 3 examples
                        print(f"   → {link}")
                    if len(links) > 3:
                        print(f"   ... and {len(links) - 3} more")
                        
            except Exception as e:
                selector_results[selector] = 0
        
        print(f"\n📊 SUMMARY:")
        print(f"Total unique documentation links found: {len(all_links)}")
        print(f"Working selectors: {sum(1 for count in selector_results.values() if count > 0)}")
        
        if len(all_links) > 1:
            print("✅ SUCCESS: Navigation detection is working!")
            print("✅ The Selenium scraper should work properly")
            
            # Show some example sections detected
            sections = set()
            for link in list(all_links)[:20]:  # Check first 20 links
                path = urlparse(link).path
                parts = path.split('/')[2:]  # Remove '/docs'
                if parts:
                    sections.add(parts[0])
            
            if sections:
                print(f"🏗️  Documentation sections detected: {', '.join(sorted(sections))}")
        else:
            print("❌ PROBLEM: Very few navigation links found")
            print("❌ The site might have changed or additional selectors are needed")
        
        # Test if we can find any main content
        content_selectors = ['main', '.content', '.page-content', 'article']
        for selector in content_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"📝 Found main content area: {selector}")
                break
        
        # Check for any JavaScript errors
        logs = driver.get_log('browser')
        js_errors = [log for log in logs if log['level'] == 'SEVERE']
        if js_errors:
            print(f"⚠️  JavaScript errors detected: {len(js_errors)}")
        else:
            print("✅ No JavaScript errors detected")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print("❌ Make sure Chrome and ChromeDriver are installed")
        return False
    
    finally:
        try:
            driver.quit()
            print("🔧 Browser closed")
        except:
            pass
    
    return len(all_links) > 10  # Consider success if we find more than 10 links

def test_with_firefox():
    """Test with Firefox as backup"""
    print("\n🦊 Testing with Firefox...")
    
    try:
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
        firefox_options = FirefoxOptions()
        firefox_options.add_argument("--headless")
        
        driver = webdriver.Firefox(options=firefox_options)
        # Same test logic here...
        print("✅ Firefox test would go here")
        driver.quit()
        
    except Exception as e:
        print(f"❌ Firefox test failed: {e}")

if __name__ == "__main__":
    print("🧪 DYNATRACE DOCUMENTATION NAVIGATION TEST")
    print("=" * 50)
    
    success = test_navigation_detection()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 TEST PASSED: Ready to run full scraper!")
        print("\nNext steps:")
        print("1. Run a small test crawl:")
        print("   python selenium_dynatrace_scraper.py --max-pages 50 --max-depth 5")
        print("\n2. If that works, run the full crawl:")
        print("   python selenium_dynatrace_scraper.py --max-pages 5000 --max-depth 50")
    else:
        print("⚠️  TEST FAILED: Navigation detection needs improvement")
        print("\nTroubleshooting:")
        print("1. Make sure Chrome is installed")
        print("2. Install ChromeDriver: pip install webdriver-manager")
        print("3. Try Firefox: Add --browser firefox option")
        print("4. Check if site structure changed")