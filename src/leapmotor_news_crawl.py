"""Crawl Leapmotor news detail pages for official images."""
import asyncio
import json
from playwright.async_api import async_playwright
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'leapmotor')

async def crawl_news_detail(news_id: str):
    """Crawl a specific news page for images and content."""
    url = f'https://www.leapmotor.com/news/news-detail.html?id={news_id}'
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(3)
        
        # Extract title
        title = await page.title()
        
        # Extract images from article content
        images = await page.evaluate('''() => {
            const content = document.querySelector('.news-content, .article-content, .content, article');
            if (!content) return [];
            
            const imgs = Array.from(content.querySelectorAll('img'));
            return imgs.map(img => ({
                src: img.src,
                alt: img.alt,
                width: img.naturalWidth,
                height: img.naturalHeight,
            })).filter(img => img.src && img.src.startsWith('http') && img.width > 300);
        }''')
        
        # Extract article text
        text = await page.evaluate('''() => {
            const content = document.querySelector('.news-content, .article-content, .content, article');
            return content ? content.innerText.slice(0, 2000) : '';
        }''')
        
        result = {
            'url': url,
            'title': title,
            'images': images,
            'text_preview': text,
        }
        
        # Save
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, f'news_{news_id}.json'), 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"News: {title}")
        print(f"Images: {len(images)}")
        for img in images:
            print(f"  {img['width']}x{img['height']} -> {img['src'][:80]}")
        
        await browser.close()
        return result


if __name__ == '__main__':
    # Test with some known news IDs
    # 2583 = C16 related, 2687 = delivery news
    news_ids = ['2583', '2687', '3419', '3322']
    
    for nid in news_ids:
        print(f"\n{'='*60}")
        print(f"Crawling news {nid}...")
        asyncio.run(crawl_news_detail(nid))
