"""Test script: Crawl Xiaomi Auto news using Playwright."""

import asyncio
from playwright.async_api import async_playwright


async def crawl_xiaomi_news():
    """Fetch Xiaomi Auto news list."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto('https://www.xiaomiev.com/news', wait_until='networkidle')
        await asyncio.sleep(3)  # Wait for JS rendering
        
        # Extract news items
        articles = await page.evaluate('''() => {
            const items = document.querySelectorAll('a[href*="/news/"], .news-item, article');
            return Array.from(items).slice(0, 10).map(el => {
                const title = el.querySelector('h1, h2, h3, .title, [class*="title"]');
                const date = el.querySelector('time, .date, [class*="date"]');
                return {
                    title: title ? title.innerText.trim() : el.innerText.slice(0, 50),
                    url: el.href || el.querySelector('a')?.href || '',
                    date: date ? date.innerText.trim() : '',
                };
            });
        }''')
        
        await browser.close()
        return articles


if __name__ == '__main__':
    results = asyncio.run(crawl_xiaomi_news())
    print(f"Found {len(results)} articles:")
    for article in results:
        print(f"  - {article['title'][:40]} ({article['date']})")
