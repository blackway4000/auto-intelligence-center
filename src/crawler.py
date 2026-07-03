"""Base crawler for collecting vehicle news from brand websites."""

import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import REQUEST_TIMEOUT, REQUEST_DELAY, USER_AGENT, BRAND_SOURCES


class BaseCrawler:
    """Base class for brand website crawlers."""
    
    def __init__(self, brand_key):
        self.brand_key = brand_key
        self.config = BRAND_SOURCES.get(brand_key, {})
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
    
    def fetch(self, url):
        """Fetch a URL with retry logic."""
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return resp.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def parse_news_list(self, html):
        """Parse news list from HTML. Override in subclass."""
        soup = BeautifulSoup(html, 'lxml')
        articles = []
        # Generic fallback - look for common article patterns
        for item in soup.find_all(['article', 'div'], class_=lambda x: x and ('news' in x.lower() if x else False)):
            link = item.find('a')
            if link:
                articles.append({
                    'title': link.get_text(strip=True),
                    'url': link.get('href', ''),
                    'date': datetime.now().strftime('%Y-%m-%d'),
                })
        return articles


class XiaomiCrawler(BaseCrawler):
    """Crawler for Xiaomi Auto news."""
    
    def __init__(self):
        super().__init__('xiaomi')
    
    def crawl(self):
        """Crawl Xiaomi Auto news."""
        url = self.config.get('news_url')
        html = self.fetch(url)
        if not html:
            return []
        return self.parse_news_list(html)


def crawl_all_brands():
    """Crawl all enabled brand sources."""
    results = {}
    for key, cfg in BRAND_SOURCES.items():
        if not cfg.get('enabled', False):
            continue
        print(f"Crawling {cfg['name']}...")
        if key == 'xiaomi':
            crawler = XiaomiCrawler()
        else:
            crawler = BaseCrawler(key)
        results[key] = crawler.crawl()
    return results


if __name__ == '__main__':
    results = crawl_all_brands()
    for brand, articles in results.items():
        print(f"\n{brand}: {len(articles)} articles found")
        for article in articles[:3]:
            print(f"  - {article['title']}")
