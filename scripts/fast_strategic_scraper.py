#!/usr/bin/env python3
"""
Fast Strategic Dynatrace Documentation Scraper
==============================================

This approach focuses on getting a good taxonomy structure FAST by:
1. Targeting known main sections first
2. Using breadth-first approach (wide coverage, limited depth)
3. Smart stopping when we have good coverage
4. Parallel processing where possible
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
import json
import time
import logging
from typing import Dict, List, Set
from dataclasses import dataclass, asdict
from collections import deque
import argparse
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class FastPage:
    """Lightweight page representation"""
    url: str
    title: str
    description: str
    section: str
    subsection: str
    depth: int

class FastStrategicScraper:
    """Fast scraper focusing on strategic coverage over completeness"""
    
    # Known main sections from our test
    KNOWN_SECTIONS = [
        'observe',
        'analyze-explore-automate', 
        'manage',
        'ingest-from',
        'secure',
        'whats-new',
        'deliver'
    ]
    
    def __init__(self, base_url: str = "https://docs.dynatrace.com/docs", max_depth: int = 15):
        self.base_url = base_url
        self.max_depth = max_depth
        self.pages: Dict[str, FastPage] = {}
        self.visited: Set[str] = set()
        self.driver = None
        
    def setup_driver(self):
        """Setup optimized Chrome driver"""
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-images")  # Faster loading
        chrome_options.add_argument("--disable-javascript")  # Try without JS first
        chrome_options.add_argument("--window-size=1024,768")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(5)
        self.driver.set_page_load_timeout(15)
        logger.info("Optimized Chrome driver initialized")
    
    def cleanup_driver(self):
        """Clean up driver"""
        if self.driver:
            self.driver.quit()
    
    def extract_fast_page_info(self, url: str, depth: int) -> FastPage:
        """Fast extraction of essential page info"""
        try:
            self.driver.get(url)
            time.sleep(1)  # Minimal wait
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Quick title extraction
            title_tag = soup.find('title')
            title = title_tag.get_text().strip() if title_tag else "Untitled"
            title = title.replace(' — Dynatrace Docs', '').replace(' - Dynatrace Docs', '')
            
            # Quick description from meta or first paragraph
            description = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                description = meta_desc.get('content', '').strip()
            else:
                # Try first paragraph
                p_tag = soup.find('p')
                if p_tag:
                    description = p_tag.get_text().strip()[:200]
            
            # Determine section/subsection from URL
            path_parts = url.replace(self.base_url, '').strip('/').split('/')
            section = path_parts[0] if path_parts and path_parts[0] else 'root'
            subsection = path_parts[1] if len(path_parts) > 1 and path_parts[1] else ''
            
            return FastPage(
                url=url,
                title=title,
                description=description or "No description available",
                section=section,
                subsection=subsection,
                depth=depth
            )
            
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            # Return minimal page info
            path_parts = url.replace(self.base_url, '').strip('/').split('/')
            section = path_parts[0] if path_parts and path_parts[0] else 'root'
            return FastPage(
                url=url,
                title="Error Loading Page",
                description="Failed to load page content",
                section=section,
                subsection=path_parts[1] if len(path_parts) > 1 else '',
                depth=depth
            )
    
    def get_section_links(self, section: str) -> List[str]:
        """Get links for a specific section"""
        section_url = f"{self.base_url}/{section}"
        links = []
        
        try:
            self.driver.get(section_url)
            time.sleep(2)
            
            # Look for navigation links in this section
            nav_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href^="/docs"]')
            
            for link in nav_links:
                href = link.get_attribute('href')
                if href and section in href:
                    links.append(href)
            
            logger.info(f"Found {len(links)} links in section: {section}")
            
        except Exception as e:
            logger.error(f"Error getting links for section {section}: {e}")
        
        return list(set(links))  # Remove duplicates
    
    def strategic_crawl(self) -> Dict[str, FastPage]:
        """Strategic crawl focusing on main sections"""
        logger.info("Starting strategic crawl...")
        self.setup_driver()
        
        try:
            # 1. Get main page
            logger.info("Processing main page...")
            main_page = self.extract_fast_page_info(self.base_url, 0)
            self.pages[self.base_url] = main_page
            self.visited.add(self.base_url)
            
            # 2. Process each known section
            for section in self.KNOWN_SECTIONS:
                logger.info(f"Processing section: {section}")
                
                # Get section main page
                section_url = f"{self.base_url}/{section}"
                if section_url not in self.visited:
                    try:
                        section_page = self.extract_fast_page_info(section_url, 1)
                        self.pages[section_url] = section_page
                        self.visited.add(section_url)
                    except Exception as e:
                        logger.error(f"Failed to process section {section}: {e}")
                        continue
                
                # Get some subsection links (limited depth for speed)
                section_links = self.get_section_links(section)
                
                # Process up to 10 subsection pages per section (for speed)
                for i, link in enumerate(section_links[:10]):
                    if link not in self.visited:
                        try:
                            page = self.extract_fast_page_info(link, 2)
                            self.pages[link] = page
                            self.visited.add(link)
                            
                            # Brief pause to avoid overwhelming server
                            time.sleep(0.5)
                            
                        except Exception as e:
                            logger.error(f"Failed to process {link}: {e}")
                
                logger.info(f"Completed section {section}: {len([p for p in self.pages.values() if p.section == section])} pages")
            
            logger.info(f"Strategic crawl completed: {len(self.pages)} total pages")
            return self.pages
            
        finally:
            self.cleanup_driver()
    
    def generate_taxonomy(self) -> Dict:
        """Generate taxonomy from crawled pages"""
        taxonomy = {
            "metadata": {
                "base_url": self.base_url,
                "total_pages": len(self.pages),
                "crawl_type": "strategic_fast",
                "max_depth": self.max_depth,
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
                    "depth": page.depth
                })
            else:
                sections[section]["pages"].append({
                    "url": page.url,
                    "title": page.title,
                    "description": page.description,
                    "depth": page.depth
                })
        
        taxonomy["structure"] = sections
        return taxonomy
    
    def save_results(self, filename: str = "dynatrace_fast_taxonomy.json"):
        """Save fast taxonomy results"""
        taxonomy = self.generate_taxonomy()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(taxonomy, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Fast taxonomy saved to {filename}")
        return filename

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Fast strategic Dynatrace docs scraper')
    parser.add_argument('--base-url', default='https://docs.dynatrace.com/docs')
    parser.add_argument('--max-depth', type=int, default=15)
    parser.add_argument('--output', default='dynatrace_fast_taxonomy.json')
    
    args = parser.parse_args()
    
    scraper = FastStrategicScraper(
        base_url=args.base_url,
        max_depth=args.max_depth
    )
    
    try:
        start_time = time.time()
        pages = scraper.strategic_crawl()
        filename = scraper.save_results(args.output)
        elapsed = time.time() - start_time
        
        print(f"\n🚀 FAST STRATEGIC CRAWL COMPLETED!")
        print(f"⏱️  Time taken: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"📄 Pages discovered: {len(pages)}")
        print(f"💾 Saved to: {filename}")
        
        # Show sections
        taxonomy = scraper.generate_taxonomy()
        print(f"\n📊 Sections discovered:")
        for section_name in sorted(taxonomy["structure"].keys()):
            section = taxonomy["structure"][section_name]
            total_pages = len(section.get("pages", []))
            subsections = len(section.get("subsections", {}))
            for sub in section.get("subsections", {}).values():
                total_pages += len(sub.get("pages", []))
            print(f"  - {section_name}: {total_pages} pages, {subsections} subsections")
        
        print(f"\n💡 This gives you a good foundation taxonomy structure!")
        print(f"💡 Use this for your interactive webpage, then expand specific sections if needed.")
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fast crawl failed: {e}")

if __name__ == "__main__":
    main()
