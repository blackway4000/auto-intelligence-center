"""Crawl Leapmotor official website for vehicle images and info."""
import asyncio
import json
from playwright.async_api import async_playwright
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'leapmotor')

async def crawl_leapmotor():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Main page
        await page.goto('https://www.leapmotor.com', wait_until='networkidle')
        await asyncio.sleep(3)
        
        # Extract all image URLs
        images = await page.evaluate('''() => {
            const imgs = Array.from(document.querySelectorAll('img'));
            return imgs.map(img => ({
                src: img.src,
                alt: img.alt,
                width: img.naturalWidth,
                height: img.naturalHeight,
            })).filter(img => img.src && img.src.startsWith('http'));
        }''')
        
        # Save image list
        with open(os.path.join(OUTPUT_DIR, 'images.json'), 'w') as f:
            json.dump(images, f, indent=2, ensure_ascii=False)
        
        print(f"Found {len(images)} images on main page")
        for img in images[:20]:
            print(f"  {img['alt'][:40]:40s} -> {img['src'][:80]}")
        
        # Also check product/vehicle pages if links exist
        links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a[href*="car"], a[href*="product"], a[href*="vehicle"], a[href*="model"]'))
                .map(a => ({text: a.innerText.trim(), href: a.href}))
                .filter(a => a.href.startsWith('http'));
        }''')
        
        print(f"\nFound {len(links)} potential vehicle pages")
        for link in links[:10]:
            print(f"  {link['text'][:30]:30s} -> {link['href']}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(crawl_leapmotor())
