#!/usr/bin/env python3
"""
JavaScript-Enabled Dynatrace Documentation Site Scraper
======================================================

This version uses Selenium with Chrome/Firefox to handle JavaScript-rendered content
that the original BeautifulSoup-only version couldn't access.

Features:
- Selenium WebDriver for JavaScript rendering
- Headless browser operation
- Enhanced link detection for SPA (Single Page Applications)
- Better navigation element detection
- Improved content extraction for modern docs sites
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin, urlparse, urlunparse
import logging
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, asdict
import sys
from collections import deque
import argparse
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dynatrace_selenium_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class DocumentationPage:
    """Represents a single documentation page"""
    url: str
    title: str
    description: str
    breadcrumbs: List[str]
    section: str
    subsection: str
    depth: int
    parent_url: Optional[str]
    children: List[str]
    meta_description: str
    h1_heading: str
    h2_headings: List[str]
    last_updated: Optional[str]
    nav_text: str

class DynatraceSeleniumScraper:
    """Enhanced scraper using Selenium for JavaScript-rendered content"""
    
    def __init__(self, base_url: str = "https://docs.dynatrace.com/docs", 
                 max_depth: int = 50, delay: float = 2.0, browser: str = "chrome"):
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        self.max_depth = max_depth
        self.delay = delay
        self.browser = browser.lower()
        
        # Data storage
        self.visited_urls: Set[str] = set()
        self.pages: Dict[str, DocumentationPage] = {}
        self.queue: deque = deque()
        
        # Statistics
        self.total_pages = 0
        self.failed_pages = 0
        self.max_pages = 10000
        
        # Progress saving
        self.checkpoint_interval = 50
        self.resume_file = "selenium_crawl_checkpoint.json"
        
        # Selenium driver
        self.driver = None
        
    def setup_driver(self) -> bool:
        """Initialize Selenium WebDriver"""
        try:
            if self.browser == "chrome":
                chrome_options = ChromeOptions()
                chrome_options.add_argument("--headless")  # Run in background
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
                
                self.driver = webdriver.Chrome(options=chrome_options)
                
            elif self.browser == "firefox":
                firefox_options = FirefoxOptions()
                firefox_options.add_argument("--headless")
                firefox_options.add_argument("--width=1920")
                firefox_options.add_argument("--height=1080")
                
                self.driver = webdriver.Firefox(options=firefox_options)
                
            else:
                logger.error(f"Unsupported browser: {self.browser}")
                return False
            
            # Set timeouts
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(30)
            
            logger.info(f"Selenium {self.browser} driver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Selenium driver: {e}")
            logger.info("Make sure you have Chrome/Firefox and the corresponding WebDriver installed")
            return False
    
    def cleanup_driver(self):
        """Clean up Selenium driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium driver closed")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and query params"""
        parsed = urlparse(url)
        normalized = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path.rstrip('/'),
            '', '', ''
        ))
        return normalized
    
    def is_docs_url(self, url: str) -> bool:
        """Check if URL belongs to Dynatrace docs"""
        parsed = urlparse(url)
        if parsed.netloc != self.base_domain or not parsed.path.startswith('/docs'):
            return False
        
        # Filter out unwanted patterns
        unwanted_patterns = [
            '?', '#', '/edit', '/print', '/download', 'javascript:', 'mailto:'
        ]
        
        for pattern in unwanted_patterns:
            if pattern in url:
                return False
        
        # Avoid very deep paths
        path_depth = len([p for p in parsed.path.split('/') if p])
        if path_depth > 15:
            return False
            
        return True
    
    def wait_for_page_load(self, timeout: int = 10) -> bool:
        """Wait for page to fully load including JavaScript"""
        try:
            # Wait for document.readyState to be complete
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Additional wait for dynamic content
            time.sleep(2)
            
            return True
        except TimeoutException:
            logger.warning("Page load timeout")
            return False
    
    def extract_navigation_links(self, current_url: str) -> List[str]:
        """Extract navigation links from JavaScript-rendered page"""
        links = set()
        
        try:
            # Common selectors for documentation navigation
            nav_selectors = [
                'nav a[href]',
                '.navigation a[href]',
                '.nav a[href]',
                '.sidebar a[href]',
                '.menu a[href]',
                '.nav-item a[href]',
                '.nav-link[href]',
                '[role="navigation"] a[href]',
                '.docs-nav a[href]',
                '.toc a[href]',
                '.table-of-contents a[href]',
                '.side-nav a[href]',
                '.main-nav a[href]',
                # Modern React/Vue selectors
                '[data-testid*="nav"] a[href]',
                '[data-testid*="menu"] a[href]',
                '[class*="nav"] a[href]',
                '[class*="menu"] a[href]',
                # Dynatrace specific selectors (from investigation)
                '.dock a[href]',
                '.app-header a[href]',
                '[data-testid="dock"] a[href]'
            ]
            
            for selector in nav_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        href = element.get_attribute('href')
                        if href:
                            absolute_url = urljoin(current_url, href)
                            normalized_url = self.normalize_url(absolute_url)
                            if self.is_docs_url(normalized_url):
                                links.add(normalized_url)
                except Exception as e:
                    continue
            
            # Also look for content links within main content areas
            content_selectors = [
                'main a[href^="/docs"]',
                '.content a[href^="/docs"]',
                '.page-content a[href^="/docs"]',
                'article a[href^="/docs"]',
                '.markdown a[href^="/docs"]',
                '.prose a[href^="/docs"]'
            ]
            
            for selector in content_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        href = element.get_attribute('href')
                        if href:
                            absolute_url = urljoin(current_url, href)
                            normalized_url = self.normalize_url(absolute_url)
                            if self.is_docs_url(normalized_url):
                                links.add(normalized_url)
                except Exception as e:
                    continue
            
            # Try to click navigation elements to reveal more links (for SPAs)
            try:
                nav_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                    'button[aria-expanded="false"], .nav-toggle, .menu-toggle, [role="button"]')
                
                for button in nav_buttons[:3]:  # Limit to avoid too many clicks
                    try:
                        if button.is_displayed() and button.is_enabled():
                            self.driver.execute_script("arguments[0].click();", button)
                            time.sleep(1)
                            
                            # Re-scan for new links
                            new_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href]')
                            for element in new_elements:
                                href = element.get_attribute('href')
                                if href:
                                    absolute_url = urljoin(current_url, href)
                                    normalized_url = self.normalize_url(absolute_url)
                                    if self.is_docs_url(normalized_url):
                                        links.add(normalized_url)
                    except Exception:
                        continue
            except Exception:
                pass
            
            logger.info(f"Found {len(links)} navigation links")
            return list(links)
            
        except Exception as e:
            logger.error(f"Error extracting navigation links: {e}")
            return []
    
    def extract_page_content(self, url: str, depth: int, parent_url: Optional[str] = None) -> DocumentationPage:
        """Extract comprehensive page information"""
        
        # Get page source after JavaScript rendering
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Extract basic information
        title = self.extract_title(soup)
        description = self.extract_description(soup)
        meta_description = self.extract_meta_description(soup)
        breadcrumbs = self.extract_breadcrumbs(soup)
        h1_heading = self.extract_h1(soup)
        h2_headings = self.extract_h2_headings(soup)
        nav_text = self.extract_nav_text()
        
        # Determine section and subsection
        path_parts = url.replace(self.base_url, '').strip('/').split('/')
        section = path_parts[0] if path_parts and path_parts[0] else 'root'
        subsection = path_parts[1] if len(path_parts) > 1 and path_parts[1] else ''
        
        # Extract child links
        children = self.extract_navigation_links(url)
        
        return DocumentationPage(
            url=url,
            title=title,
            description=description,
            breadcrumbs=breadcrumbs,
            section=section,
            subsection=subsection,
            depth=depth,
            parent_url=parent_url,
            children=children,
            meta_description=meta_description,
            h1_heading=h1_heading,
            h2_headings=h2_headings,
            last_updated=None,
            nav_text=nav_text
        )
    
    def extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title"""
        # Try page title first
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
            title = re.sub(r'\s*—\s*Dynatrace\s*Docs?\s*$', '', title)
            if title and title != "Dynatrace Documentation":
                return title
        
        # Try h1 tag
        h1_tag = soup.find('h1')
        if h1_tag:
            title = h1_tag.get_text().strip()
            if title:
                return title
        
        # Try various other selectors
        title_selectors = [
            '.page-title',
            '.title',
            '[data-testid="title"]',
            '.content h1',
            'main h1',
            'article h1'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text().strip()
                if title:
                    return title
        
        return "Untitled Page"
    
    def extract_description(self, soup: BeautifulSoup) -> str:
        """Extract page description"""
        selectors = [
            '.lead',
            '.description',
            '.page-description',
            '.intro',
            '.summary',
            '.content > p:first-of-type',
            'main > p:first-of-type',
            'article > p:first-of-type',
            '.markdown > p:first-of-type'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text().strip()
                if len(text) > 10:
                    return text[:500]
        
        return "No description available"
    
    def extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '').strip()
        return ""
    
    def extract_breadcrumbs(self, soup: BeautifulSoup) -> List[str]:
        """Extract breadcrumb navigation"""
        breadcrumbs = []
        
        selectors = [
            '.breadcrumb a',
            '.breadcrumbs a',
            '[data-testid="breadcrumb"] a',
            'nav[aria-label="breadcrumb"] a',
            '.page-breadcrumbs a',
            '[aria-label="Breadcrumb"] a'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                breadcrumbs = [el.get_text().strip() for el in elements]
                break
        
        return breadcrumbs
    
    def extract_h1(self, soup: BeautifulSoup) -> str:
        """Extract main H1 heading"""
        h1 = soup.find('h1')
        return h1.get_text().strip() if h1 else ""
    
    def extract_h2_headings(self, soup: BeautifulSoup) -> List[str]:
        """Extract all H2 headings"""
        h2_tags = soup.find_all('h2')
        return [h2.get_text().strip() for h2 in h2_tags]
    
    def extract_nav_text(self) -> str:
        """Extract visible navigation text from current page"""
        try:
            nav_elements = self.driver.find_elements(By.CSS_SELECTOR, 'nav, .navigation, .nav, .sidebar')
            nav_texts = []
            for element in nav_elements:
                if element.is_displayed():
                    text = element.text.strip()
                    if text:
                        nav_texts.append(text)
            return " | ".join(nav_texts)[:1000]  # Limit length
        except Exception:
            return ""
    
    def fetch_page(self, url: str) -> bool:
        """Fetch and load a page using Selenium"""
        try:
            logger.info(f"Loading page: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            if not self.wait_for_page_load():
                logger.warning(f"Page load timeout for: {url}")
                return False
            
            # Check if page loaded successfully
            current_url = self.driver.current_url
            if "error" in current_url.lower() or "404" in current_url:
                logger.warning(f"Error page detected: {current_url}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            self.failed_pages += 1
            return False
    
    def save_checkpoint(self):
        """Save crawl progress"""
        checkpoint_data = {
            'visited_urls': list(self.visited_urls),
            'queue': list(self.queue),
            'total_pages': self.total_pages,
            'failed_pages': self.failed_pages,
            'timestamp': time.time()
        }
        
        try:
            with open(self.resume_file, 'w') as f:
                json.dump(checkpoint_data, f)
            logger.info(f"Checkpoint saved at {self.total_pages} pages")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def crawl(self, resume: bool = False) -> Dict[str, DocumentationPage]:
        """Main crawling method"""
        logger.info(f"Starting Selenium crawl of {self.base_url}")
        logger.info(f"Browser: {self.browser}, Max depth: {self.max_depth}, Max pages: {self.max_pages}")
        
        # Setup Selenium driver
        if not self.setup_driver():
            logger.error("Failed to setup Selenium driver")
            return {}
        
        try:
            # Initialize queue
            if resume:
                # TODO: Implement resume functionality
                pass
            
            self.queue.append((self.base_url, 0, None))
            start_time = time.time()
            
            while self.queue and self.total_pages < self.max_pages:
                current_url, depth, parent_url = self.queue.popleft()
                
                # Skip if already visited or too deep
                if current_url in self.visited_urls or depth > self.max_depth:
                    continue
                
                self.visited_urls.add(current_url)
                
                # Fetch page
                if not self.fetch_page(current_url):
                    continue
                
                # Extract page information
                try:
                    page_info = self.extract_page_content(current_url, depth, parent_url)
                    self.pages[current_url] = page_info
                    self.total_pages += 1
                    
                    logger.info(f"[Depth {depth}] Page {self.total_pages}: {page_info.title}")
                    logger.info(f"Found {len(page_info.children)} child links")
                    
                    # Add children to queue
                    for child_url in page_info.children:
                        if child_url not in self.visited_urls:
                            self.queue.append((child_url, depth + 1, current_url))
                    
                except Exception as e:
                    logger.error(f"Error extracting content from {current_url}: {e}")
                    self.failed_pages += 1
                
                # Rate limiting
                time.sleep(self.delay)
                
                # Progress updates
                if self.total_pages % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = self.total_pages / elapsed if elapsed > 0 else 0
                    logger.info(f"Progress: {self.total_pages} pages ({rate:.1f}/min), "
                               f"{len(self.queue)} queued, {self.failed_pages} failed")
                
                # Checkpoint
                if self.total_pages % self.checkpoint_interval == 0:
                    self.save_checkpoint()
            
            logger.info(f"Crawl completed. Pages: {self.total_pages}, Failed: {self.failed_pages}")
            return self.pages
            
        finally:
            self.cleanup_driver()
    
    def generate_taxonomy(self) -> Dict:
        """Generate taxonomy from crawled pages"""
        taxonomy = {
            "metadata": {
                "base_url": self.base_url,
                "total_pages": self.total_pages,
                "failed_pages": self.failed_pages,
                "max_depth": self.max_depth,
                "browser_used": self.browser,
                "crawl_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "structure": {}
        }
        
        # Group by section
        sections = {}
        for url, page in self.pages.items():
            section = page.section
            if section not in sections:
                sections[section] = {
                    "title": section.replace('-', ' ').title(),
                    "pages": [],
                    "subsections": {}
                }
            
            if page.subsection:
                subsection = page.subsection
                if subsection not in sections[section]["subsections"]:
                    sections[section]["subsections"][subsection] = {
                        "title": subsection.replace('-', ' ').title(),
                        "pages": []
                    }
                sections[section]["subsections"][subsection]["pages"].append({
                    "url": page.url,
                    "title": page.title,
                    "description": page.description,
                    "depth": page.depth,
                    "breadcrumbs": page.breadcrumbs,
                    "h1_heading": page.h1_heading,
                    "h2_headings": page.h2_headings
                })
            else:
                sections[section]["pages"].append({
                    "url": page.url,
                    "title": page.title,
                    "description": page.description,
                    "depth": page.depth,
                    "breadcrumbs": page.breadcrumbs,
                    "h1_heading": page.h1_heading,
                    "h2_headings": page.h2_headings
                })
        
        taxonomy["structure"] = sections
        return taxonomy
    
    def save_results(self, filename: str = "dynatrace_selenium_taxonomy.json", taxonomy_only: bool = False):
        """Save results to files"""
        # Generate taxonomy
        taxonomy = self.generate_taxonomy()
        
        # Always save taxonomy-only file
        taxonomy_filename = filename.replace('.json', '_taxonomy_only.json')
        with open(taxonomy_filename, 'w', encoding='utf-8') as f:
            json.dump(taxonomy, f, indent=2, ensure_ascii=False)
        logger.info(f"Taxonomy saved to {taxonomy_filename}")
        
        # Optionally save complete results
        if not taxonomy_only:
            # Convert pages to serializable format
            pages_data = {url: asdict(page) for url, page in self.pages.items()}
            
            # Save complete results
            results = {
                "taxonomy": taxonomy,
                "all_pages": pages_data
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Complete results saved to {filename}")
        else:
            logger.info("Skipping complete results file (taxonomy-only mode)")

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Scrape Dynatrace docs with Selenium')
    parser.add_argument('--base-url', default='https://docs.dynatrace.com/docs')
    parser.add_argument('--max-depth', type=int, default=50)
    parser.add_argument('--max-pages', type=int, default=5000)
    parser.add_argument('--delay', type=float, default=2.0)
    parser.add_argument('--browser', choices=['chrome', 'firefox'], default='chrome')
    parser.add_argument('--output', default='dynatrace_selenium_taxonomy.json')
    parser.add_argument('--checkpoint-interval', type=int, default=50)
    parser.add_argument('--taxonomy-only', action='store_true',
                       help='Save only taxonomy file, skip large complete results file')
    
    args = parser.parse_args()
    
    scraper = DynatraceSeleniumScraper(
        base_url=args.base_url,
        max_depth=args.max_depth,
        delay=args.delay,
        browser=args.browser
    )
    
    scraper.max_pages = args.max_pages
    scraper.checkpoint_interval = args.checkpoint_interval
    
    try:
        pages = scraper.crawl()
        scraper.save_results(args.output, taxonomy_only=args.taxonomy_only)
        
        print(f"\nCrawl Summary:")
        print(f"Browser: {args.browser}")
        print(f"Total pages: {scraper.total_pages}")
        print(f"Failed pages: {scraper.failed_pages}")
        print(f"Max depth reached: {max([p.depth for p in pages.values()]) if pages else 0}")
        
        if args.taxonomy_only:
            taxonomy_file = args.output.replace('.json', '_taxonomy_only.json')
            print(f"Taxonomy file: {taxonomy_file}")
            print("💡 Complete results file skipped (faster processing)")
        else:
            print(f"Complete results: {args.output}")
            print(f"Taxonomy file: {args.output.replace('.json', '_taxonomy_only.json')}")
        
        if pages:
            taxonomy = scraper.generate_taxonomy()
            print(f"\nSections found ({len(taxonomy['structure'])}):")
            for section_name in sorted(taxonomy["structure"].keys()):
                section = taxonomy["structure"][section_name]
                total_pages = len(section.get("pages", []))
                subsections = len(section.get("subsections", {}))
                for sub in section.get("subsections", {}).values():
                    total_pages += len(sub.get("pages", []))
                print(f"  - {section_name}: {total_pages} pages, {subsections} subsections")
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        scraper.save_checkpoint()
        if hasattr(scraper, 'pages') and scraper.pages:
            scraper.save_results(args.output, taxonomy_only=args.taxonomy_only)
        scraper.cleanup_driver()
    except Exception as e:
        logger.error(f"Crawl failed: {e}")
        scraper.cleanup_driver()
        sys.exit(1)

if __name__ == "__main__":
    main()
