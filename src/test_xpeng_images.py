"""Deep dive into Xpeng homepage image extraction."""

import requests
from bs4 import BeautifulSoup
import re

url = 'https://www.xiaopeng.com'
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
}

resp = requests.get(url, headers=headers, timeout=30)
soup = BeautifulSoup(resp.text, 'html.parser')

print("=" * 60)
print("小鹏官网所有图片URL")
print("=" * 60)

images = []
for img in soup.find_all('img'):
    src = img.get('src') or img.get('data-src') or img.get('data-original')
    if src:
        if src.startswith('//'):
            src = 'https:' + src
        elif src.startswith('/'):
            src = 'https://www.xiaopeng.com' + src
        images.append({'src': src, 'alt': img.get('alt', '')})

for i, img in enumerate(images[:20]):
    print(f"[{i+1}] {img['src']}")
    print(f"     alt: {img['alt']}")

# Also check for JSON data in script tags that might contain image URLs
print("\n" + "=" * 60)
print("Script标签中的图片数据")
print("=" * 60)

for script in soup.find_all('script'):
    text = script.string if script.string else ''
    if 'image' in text.lower() or 'jpg' in text.lower() or 'png' in text.lower():
        # Extract URLs
        urls = re.findall(r'https?://[^\s"\'<>]+\.(?:jpg|jpeg|png|webp)', text)
        if urls:
            print(f"Found {len(urls)} URLs in script")
            for u in urls[:5]:
                print(f"  {u}")
            break

# Check for car configuration JSON
print("\n" + "=" * 60)
print("页面中的车型相关文本")
print("=" * 60)

text = soup.get_text()
if 'MONA' in text:
    print("✅ 页面包含 'MONA'")
if 'L03' in text:
    print("✅ 页面包含 'L03'")
if 'M03' in text:
    print("✅ 页面包含 'M03'")
