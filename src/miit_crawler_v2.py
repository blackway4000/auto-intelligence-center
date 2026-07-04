"""MIIT crawler v2 - improved image extraction with lazy-load support."""

import asyncio
import json
import os
from playwright.async_api import async_playwright
import requests

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'miit')
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def crawl_with_scroll(url: str, output_name: str):
    """Crawl a page with scrolling to trigger lazy-loaded images."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"Accessing: {url}")
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(2)
        
        # Scroll down to trigger lazy loading
        for _ in range(5):
            await page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(1)
        
        title = await page.title()
        print(f"Title: {title[:60]}")
        
        # Try multiple selectors for images
        images = await page.evaluate('''() => {
            const allImgs = Array.from(document.querySelectorAll('img'));
            return allImgs.map(img => ({
                src: img.src || img.dataset.src || img.getAttribute('data-original') || img.getAttribute('data-src'),
                alt: img.alt,
                width: img.naturalWidth || parseInt(img.getAttribute('width')) || 0,
                height: img.naturalHeight || parseInt(img.getAttribute('height')) || 0,
            })).filter(img => img.src && img.src.startsWith('http') && img.width > 200);
        }''')
        
        # Also get all links that might be image galleries
        gallery_links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a[href*="image"], a[href*="pic"], a[href*="photo"]'))
                .map(a => ({text: a.innerText.trim(), href: a.href}))
                .filter(a => a.href.startsWith('http'));
        }''')
        
        result = {
            'url': url,
            'title': title,
            'images': images,
            'gallery_links': gallery_links,
        }
        
        save_path = os.path.join(OUTPUT_DIR, f'{output_name}.json')
        with open(save_path, 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"Found {len(images)} images")
        for img in images[:10]:
            print(f"  {img['width']}x{img['height']} -> {img['src'][:70]}")
        
        await browser.close()
        return result


def download_images(json_path: str, subdir: str):
    """Download images from JSON result."""
    if not os.path.exists(json_path):
        return
    
    with open(json_path) as f:
        data = json.load(f)
    
    images = data.get('images', [])
    if not images:
        print("No images to download")
        return
    
    download_dir = os.path.join(OUTPUT_DIR, subdir)
    os.makedirs(download_dir, exist_ok=True)
    
    print(f"\nDownloading {len(images)} images...")
    for i, img in enumerate(images):
        url = img['src']
        ext = url.split('.')[-1].split('?')[0][:4]
        if ext not in ['jpg', 'jpeg', 'png', 'webp']:
            ext = 'jpg'
        
        filename = f"{subdir}_{i:02d}.{ext}"
        save_path = os.path.join(download_dir, filename)
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0', 'Referer': data['url']}
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()
            with open(save_path, 'wb') as f:
                f.write(resp.content)
            print(f"  [{i+1}] {os.path.getsize(save_path)} bytes -> {filename}")
        except Exception as e:
            print(f"  [{i+1}] Failed: {e}")


if __name__ == '__main__':
    # Test multiple MIIT-related sources
    sources = [
        ('https://chejiahao.m.autohome.com.cn/360/chejiahao/detailinfo/18389411', 'autohome_b10_miit'),
        ('https://chejiahao.m.autohome.com.cn/info/15845275', 'autohome_c16_miit'),
        ('https://chejiahao.m.autohome.com.cn/info/17434138', 'autohome_c16_miit_v2'),
    ]
    
    for url, name in sources:
        print(f"\n{'='*60}")
        print(f"Crawling: {name}")
        print('='*60)
        result = asyncio.run(crawl_with_scroll(url, name))
        
        if result and result.get('images'):
            json_path = os.path.join(OUTPUT_DIR, f'{name}.json')
            download_images(json_path, name)
