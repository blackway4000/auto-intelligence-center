"""Debug script: Inspect Xiaomi Auto news page structure."""

import asyncio
from playwright.async_api import async_playwright


async def debug_xiaomi_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto('https://www.xiaomiev.com/news', wait_until='networkidle')
        await asyncio.sleep(5)
        
        # Get page title
        title = await page.title()
        print(f"Page title: {title}")
        
        # Get all text content
        text = await page.evaluate('() => document.body.innerText')
        print(f"\nPage text (first 1000 chars):\n{text[:1000]}")
        
        # Try different selectors
        selectors = [
            'a', 'article', '[class*="news"]', '[class*="item"]',
            'h1', 'h2', 'h3', '.title', '[class*="title"]',
            'li', '.list-item'
        ]
        
        print("\n--- Selector counts ---")
        for sel in selectors:
            count = await page.evaluate(f'() => document.querySelectorAll("{sel}").length')
            print(f"  {sel}: {count}")
        
        # Get all links
        links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a')).slice(0, 20).map(a => ({
                text: a.innerText.slice(0, 50),
                href: a.href
            }));
        }''')
        
        print("\n--- First 20 links ---")
        for link in links:
            print(f"  {link['text'][:40]} -> {link['href'][:60]}")
        
        await browser.close()


if __name__ == '__main__':
    asyncio.run(debug_xiaomi_page())
