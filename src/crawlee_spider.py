"""Auto Intelligence Center - Crawlee-based spider.

References:
- https://github.com/apify/crawlee-python
"""

import asyncio
from datetime import datetime
from crawlee.beautiful_soup_crawler import BeautifulSoupCrawler, BeautifulSoupCrawlingContext
from crawlee.playwright_crawler import PlaywrightCrawler, PlaywrightCrawlingContext
from crawlee.storages import Dataset

from config import BRAND_SOURCES


class BrandNewsSpider:
    """Crawl brand official websites for new vehicle news."""
    
    def __init__(self, brand_key: str):
        self.brand_key = brand_key
        self.config = BRAND_SOURCES.get(brand_key, {})
        self.dataset = Dataset.open(name=f"news_{brand_key}")
    
    async def crawl_with_bs4(self) -> list:
        """Use BeautifulSoup crawler for static pages."""
        results = []
        
        crawler = BeautifulSoupCrawler(
            max_requests_per_crawl=20,
            request_handler=self._handle_bs4_page,
        )
        
        await crawler.run([self.config.get('news_url')])
        
        async for item in self.dataset.iterate_items():
            results.append(item)
        
        return results
    
    async def crawl_with_playwright(self) -> list:
        """Use Playwright crawler for dynamic pages."""
        results = []
        
        crawler = PlaywrightCrawler(
            max_requests_per_crawl=20,
            request_handler=self._handle_pw_page,
        )
        
        await crawler.run([self.config.get('news_url')])
        
        async for item in self.dataset.iterate_items():
            results.append(item)
        
        return results
    
    async def _handle_bs4_page(self, context: BeautifulSoupCrawlingContext) -> None:
        """Handle a single page with BeautifulSoup."""
        soup = context.soup
        
        # Generic news extraction - adapt selectors per brand
        articles = []
        for item in soup.find_all(['article', 'div'], class_=lambda x: x and 'news' in x.lower() if x else False):
            link = item.find('a')
            title_tag = item.find(['h1', 'h2', 'h3', 'h4', 'span', 'div'], class_=lambda x: x and 'title' in x.lower() if x else False)
            date_tag = item.find(['time', 'span'], class_=lambda x: x and 'date' in x.lower() if x else False)
            
            if link:
                articles.append({
                    'brand': self.brand_key,
                    'title': title_tag.get_text(strip=True) if title_tag else link.get_text(strip=True),
                    'url': link.get('href', ''),
                    'date': date_tag.get_text(strip=True) if date_tag else datetime.now().strftime('%Y-%m-%d'),
                    'source': 'official_website',
                    'crawled_at': datetime.now().isoformat(),
                })
        
        await self.dataset.push_data({'articles': articles, 'page_url': context.request.url})
    
    async def _handle_pw_page(self, context: PlaywrightCrawlingContext) -> None:
        """Handle a single page with Playwright (for JS-rendered content)."""
        page = context.page
        
        # Wait for content to load
        await page.wait_for_load_state('networkidle')
        
        # Extract data using page.evaluate
        articles = await page.evaluate('''() => {
            const items = document.querySelectorAll('article, [class*="news"], [class*="item"]');
            return Array.from(items).slice(0, 10).map(item => {
                const link = item.querySelector('a');
                const title = item.querySelector('h1, h2, h3, [class*="title"]');
                const date = item.querySelector('time, [class*="date"]');
                return {
                    title: title ? title.innerText.trim() : (link ? link.innerText.trim() : ''),
                    url: link ? link.href : '',
                    date: date ? date.innerText.trim() : new Date().toISOString().split('T')[0],
                };
            });
        }''')
        
        for article in articles:
            article['brand'] = self.brand_key
            article['source'] = 'official_website'
            article['crawled_at'] = datetime.now().isoformat()
        
        await self.dataset.push_data({'articles': articles, 'page_url': context.request.url})


async def crawl_all_brands() -> dict:
    """Crawl all enabled brand sources."""
    all_results = {}
    
    for key, cfg in BRAND_SOURCES.items():
        if not cfg.get('enabled', False):
            continue
        
        print(f"Crawling {cfg['name']} ({key})...")
        spider = BrandNewsSpider(key)
        
        try:
            # Try static crawl first, fall back to Playwright if needed
            results = await spider.crawl_with_bs4()
            if not results or not any(r.get('articles') for r in results):
                print(f"  Static crawl empty, trying Playwright for {key}...")
                results = await spider.crawl_with_playwright()
            
            all_results[key] = results
            print(f"  Found {len(results)} page(s)")
        except Exception as e:
            print(f"  Error crawling {key}: {e}")
            all_results[key] = []
    
    return all_results


if __name__ == '__main__':
    results = asyncio.run(crawl_all_brands())
    for brand, data in results.items():
        print(f"\n{brand}: {len(data)} entries")
