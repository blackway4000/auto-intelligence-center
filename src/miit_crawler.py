"""MIIT (工信部) vehicle announcement crawler.

Sources official vehicle approval data and images from MIIT announcements.
"""

import asyncio
import json
import os
from playwright.async_api import async_playwright
import requests

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'miit')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# MIIT official query system
MIIT_BASE_URL = 'https://service.miit-eidc.org.cn/miitxxgk/gonggao_xxgk/index_ggcp.html'

# Alternative: Third-party sites that aggregate MIIT data
MIIT_SOURCES = {
    'autohome_miit': 'https://chejiahao.m.autohome.com.cn/360/chejiahao/detailinfo/18389411',  # Zero run B10
    'sohu_miit': 'https://m.sohu.com/a/348009042_526255/',
}


async def crawl_miit_official():
    """Crawl MIIT official announcement system."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"Accessing MIIT official system: {MIIT_BASE_URL}")
        await page.goto(MIIT_BASE_URL, wait_until='networkidle')
        await asyncio.sleep(3)
        
        # Check page structure
        title = await page.title()
        print(f"Page title: {title}")
        
        # Look for search functionality
        search_box = await page.query_selector('input[type="text"], input[placeholder*="搜索"], input[name*="query"]')
        if search_box:
            print("Found search box, attempting to search for '零跑'")
            await search_box.fill('零跑')
            
            # Find search button
            search_btn = await page.query_selector('button[type="submit"], .search-btn, [class*="search"]')
            if search_btn:
                await search_btn.click()
                await asyncio.sleep(5)
        
        # Extract results
        results = await page.evaluate('''() => {
            const items = document.querySelectorAll('tr, .item, [class*="result"], [class*="list"]');
            return Array.from(items).slice(0, 20).map(item => {
                const links = Array.from(item.querySelectorAll('a'));
                return {
                    text: item.innerText.slice(0, 200),
                    links: links.map(a => ({text: a.innerText, href: a.href}))
                };
            });
        }''')
        
        # Save debug info
        with open(os.path.join(OUTPUT_DIR, 'miit_official_debug.json'), 'w') as f:
            json.dump({'title': title, 'results': results}, f, indent=2, ensure_ascii=False)
        
        print(f"Extracted {len(results)} items")
        for r in results[:5]:
            print(f"  {r['text'][:80]}")
        
        await browser.close()
        return results


async def crawl_autohome_miit():
    """Crawl Autohome MIIT article for specific vehicle images."""
    url = 'https://chejiahao.m.autohome.com.cn/360/chejiahao/detailinfo/18389411'
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"\nAccessing Autohome MIIT article: {url}")
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(3)
        
        title = await page.title()
        print(f"Page title: {title}")
        
        # Extract images from article
        images = await page.evaluate('''() => {
            const content = document.querySelector('.article-content, .content, article, .rich-text');
            if (!content) return [];
            
            const imgs = Array.from(content.querySelectorAll('img'));
            return imgs.map(img => ({
                src: img.src,
                alt: img.alt,
                width: img.naturalWidth,
                height: img.naturalHeight,
            })).filter(img => img.src && img.width > 300);
        }''')
        
        # Extract text content with specs
        text = await page.evaluate('''() => {
            const content = document.querySelector('.article-content, .content, article, .rich-text');
            return content ? content.innerText.slice(0, 3000) : '';
        }''')
        
        result = {
            'url': url,
            'title': title,
            'images': images,
            'text_preview': text,
        }
        
        with open(os.path.join(OUTPUT_DIR, 'autohome_miit_b10.json'), 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"Found {len(images)} images")
        for img in images:
            print(f"  {img['width']}x{img['height']} -> {img['src'][:70]}")
        
        await browser.close()
        return result


def download_miit_images(json_path: str, output_subdir: str = 'miit_images'):
    """Download MIIT images from JSON result."""
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return
    
    with open(json_path) as f:
        data = json.load(f)
    
    images = data.get('images', [])
    if not images:
        print("No images found")
        return
    
    download_dir = os.path.join(OUTPUT_DIR, output_subdir)
    os.makedirs(download_dir, exist_ok=True)
    
    print(f"\nDownloading {len(images)} MIIT images...")
    for i, img in enumerate(images):
        url = img['src']
        ext = url.split('.')[-1].split('?')[0][:4]
        if ext not in ['jpg', 'jpeg', 'png', 'webp']:
            ext = 'jpg'
        
        filename = f"miit_{i:02d}.{ext}"
        save_path = os.path.join(download_dir, filename)
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://chejiahao.m.autohome.com.cn/',
            }
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(resp.content)
            
            print(f"  [{i+1}/{len(images)}] {os.path.getsize(save_path)} bytes -> {filename}")
        except Exception as e:
            print(f"  [{i+1}/{len(images)}] Failed: {e}")


if __name__ == '__main__':
    # Crawl MIIT official system
    print("="*60)
    print("Step 1: MIIT Official System")
    print("="*60)
    asyncio.run(crawl_miit_official())
    
    # Crawl Autohome MIIT article
    print("\n" + "="*60)
    print("Step 2: Autohome MIIT Article (Zero Run B10)")
    print("="*60)
    result = asyncio.run(crawl_autohome_miit())
    
    # Download images
    if result and result.get('images'):
        download_miit_images(
            os.path.join(OUTPUT_DIR, 'autohome_miit_b10.json'),
            output_subdir='b10_miit'
        )
