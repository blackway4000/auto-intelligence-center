"""Test brand official website crawling for multiple brands.

Tests:
1. Xpeng - extract MONA L03 images from homepage
2. BYD - test crawler adaptability on another brand
"""

import requests
from bs4 import BeautifulSoup
import re
import json


def fetch_images_xpeng():
    """Fetch Xpeng homepage and extract vehicle images."""
    url = 'https://www.xiaopeng.com'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    print("=" * 60)
    print("测试1: 小鹏官网图片采集")
    print("=" * 60)
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        print(f"✅ 页面获取成功: {len(resp.text)} 字符")
        
        # Parse HTML
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find all images
        images = []
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-original')
            if src:
                # Make absolute URL
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = 'https://www.xiaopeng.com' + src
                images.append({
                    'src': src,
                    'alt': img.get('alt', ''),
                })
        
        # Also find background images in style attributes
        for tag in soup.find_all(style=True):
            style = tag['style']
            url_match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
            if url_match:
                bg_url = url_match.group(1)
                if bg_url.startswith('//'):
                    bg_url = 'https:' + bg_url
                elif bg_url.startswith('/'):
                    bg_url = 'https://www.xiaopeng.com' + bg_url
                images.append({'src': bg_url, 'alt': 'background'})
        
        print(f"📷 找到 {len(images)} 张图片")
        
        # Filter for likely vehicle images (large, high-res)
        vehicle_images = []
        for img in images:
            src = img['src']
            # Look for keywords suggesting vehicle photos
            if any(kw in src.lower() for kw in ['banner', 'car', 'vehicle', 'model', 'l03', 'mona', 'cover', 'hero']):
                vehicle_images.append(img)
        
        print(f"🚗 疑似车型图片: {len(vehicle_images)} 张")
        for i, img in enumerate(vehicle_images[:10]):
            print(f"  [{i+1}] {img['src'][:80]}... (alt: {img['alt']})")
        
        return vehicle_images
        
    except Exception as e:
        print(f"❌ 失败: {e}")
        return []


def fetch_images_byd():
    """Fetch BYD homepage and test crawler adaptability."""
    url = 'https://www.byd.com'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    print("\n" + "=" * 60)
    print("测试2: 比亚迪官网采集兼容性")
    print("=" * 60)
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        print(f"✅ 页面获取成功: {len(resp.text)} 字符")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Extract title and structure
        title = soup.title.string if soup.title else 'No title'
        print(f"📄 页面标题: {title}")
        
        # Find all images
        images = []
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-original')
            if src:
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = 'https://www.byd.com' + src
                images.append({'src': src, 'alt': img.get('alt', '')})
        
        print(f"📷 找到 {len(images)} 张图片")
        
        # Look for vehicle models mentioned
        text = soup.get_text()
        models = []
        for model in ['汉', '唐', '宋', '元', '秦', '海豹', '海豚', '海鸥', '驱逐舰', '护卫舰']:
            if model in text:
                models.append(model)
        
        print(f"🚗 页面提及车型: {', '.join(models) if models else '未检测到'}")
        
        # Show first 5 images
        for i, img in enumerate(images[:5]):
            print(f"  [{i+1}] {img['src'][:80]}...")
        
        return images
        
    except Exception as e:
        print(f"❌ 失败: {e}")
        return []


def test_xpeng_m03_detail_page():
    """Test fetching Xpeng M03 detail page for images."""
    # Try known Xpeng model page patterns
    urls_to_try = [
        'https://www.xiaopeng.com/mona/m03',
        'https://www.xiaopeng.com/car/m03',
        'https://www.xiaopeng.com/model/m03',
    ]
    
    print("\n" + "=" * 60)
    print("测试3: 小鹏MONA M03车型页探测")
    print("=" * 60)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }
    
    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            print(f"  {url} -> {resp.status_code} (final: {resp.url})")
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                images = []
                for img in soup.find_all('img'):
                    src = img.get('src') or img.get('data-src')
                    if src:
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = 'https://www.xiaopeng.com' + src
                        images.append(src)
                print(f"    ✅ 成功，找到 {len(images)} 张图片")
                for i, src in enumerate(images[:5]):
                    print(f"      [{i+1}] {src[:80]}...")
                return images
        except Exception as e:
            print(f"  {url} -> 错误: {e}")
    
    print("  ⚠️ 所有已知URL模式均失败")
    return []


if __name__ == '__main__':
    # Test 1: Xpeng homepage
    xpeng_images = fetch_images_xpeng()
    
    # Test 2: BYD homepage
    byd_images = fetch_images_byd()
    
    # Test 3: Xpeng M03 detail page
    m03_images = test_xpeng_m03_detail_page()
    
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print(f"小鹏官网图片: {len(xpeng_images)} 张")
    print(f"比亚迪官网图片: {len(byd_images)} 张")
    print(f"MONA M03车型页: {len(m03_images)} 张")
