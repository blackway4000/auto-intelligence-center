"""Image pipeline: download, detect watermark, and clean images.

Sources priority:
1. Brand official images (no third-party watermark)
2. MIIT申报图 (public, no watermark)
3. Media images (may have watermarks - need processing)
"""

import os
import json
import requests
from PIL import Image, ImageDraw
from io import BytesIO
from typing import List, Dict, Tuple

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'leapmotor')
DOWNLOAD_DIR = os.path.join(OUTPUT_DIR, 'downloaded')
CLEAN_DIR = os.path.join(OUTPUT_DIR, 'clean')


def ensure_dirs():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(CLEAN_DIR, exist_ok=True)


def download_image(url: str, save_path: str, referer: str = None) -> bool:
    """Download image with proper headers."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        }
        if referer:
            headers['Referer'] = referer
        
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        
        with open(save_path, 'wb') as f:
            f.write(resp.content)
        
        return True
    except Exception as e:
        print(f"  Failed: {e}")
        return False


def detect_watermark_region(img: Image.Image) -> List[Tuple[int, int, int, int]]:
    """Detect likely watermark regions based on common patterns.
    
    Returns list of (left, top, right, bottom) regions that might contain watermarks.
    """
    width, height = img.size
    regions = []
    
    # Common watermark positions (as ratios of image dimensions)
    # Bottom-right corner (most common for media watermarks)
    regions.append((int(width * 0.7), int(height * 0.85), width, height))
    
    # Bottom-left corner
    regions.append((0, int(height * 0.85), int(width * 0.3), height))
    
    # Top-right corner (less common)
    regions.append((int(width * 0.8), 0, width, int(height * 0.15)))
    
    return regions


def remove_watermark_by_crop(img_path: str, output_path: str, crop_bottom: int = 40) -> str:
    """Remove watermark by cropping bottom edge (most common position).
    
    Args:
        crop_bottom: Pixels to crop from bottom
    """
    img = Image.open(img_path)
    width, height = img.size
    
    # Only crop if image is large enough
    if height > crop_bottom * 3:
        cropped = img.crop((0, 0, width, height - crop_bottom))
        cropped.save(output_path, quality=95)
        return output_path
    else:
        img.save(output_path, quality=95)
        return output_path


def remove_watermark_by_color(img_path: str, output_path: str, 
                               sample_x: int = None, sample_y: int = None,
                               threshold: int = 30) -> str:
    """Advanced: Try to detect and remove watermark by color similarity.
    
    This works for semi-transparent watermarks or single-color text.
    """
    try:
        import cv2
        import numpy as np
        
        img = cv2.imread(img_path)
        if img is None:
            return remove_watermark_by_crop(img_path, output_path)
        
        h, w = img.shape[:2]
        
        # Default sample from bottom-right corner (common watermark area)
        if sample_x is None:
            sample_x = int(w * 0.85)
        if sample_y is None:
            sample_y = int(h * 0.92)
        
        # Get background color near watermark area
        bg_color = img[sample_y, sample_x]
        
        # Create mask: pixels different from background color = potential watermark
        diff = cv2.absdiff(img, bg_color)
        mask = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(mask, threshold, 255, cv2.THRESH_BINARY)
        
        # Dilate mask to cover entire watermark text
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        # Inpaint
        result = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
        
        cv2.imwrite(output_path, result)
        return output_path
        
    except ImportError:
        print("  OpenCV not available, using crop method")
        return remove_watermark_by_crop(img_path, output_path)


def process_images_from_json(json_path: str, max_images: int = 20):
    """Process images from a JSON file (output from crawlers)."""
    ensure_dirs()
    
    if not os.path.exists(json_path):
        print(f"JSON file not found: {json_path}")
        return
    
    with open(json_path) as f:
        data = json.load(f)
    
    # Handle both single news item and image list formats
    if isinstance(data, list):
        images = data
    elif isinstance(data, dict):
        images = data.get('images', [])
    else:
        images = []
    
    # Filter for reasonably large images (skip icons)
    valid_images = [
        img for img in images 
        if img.get('width', 0) > 400 and img.get('height', 0) > 300
    ][:max_images]
    
    print(f"Processing {len(valid_images)} images...")
    
    results = []
    for i, img in enumerate(valid_images):
        url = img['src']
        ext = url.split('.')[-1].split('?')[0][:4]
        if ext not in ['jpg', 'jpeg', 'png', 'webp']:
            ext = 'jpg'
        
        filename = f"leapmotor_{i:02d}.{ext}"
        download_path = os.path.join(DOWNLOAD_DIR, filename)
        clean_path = os.path.join(CLEAN_DIR, filename)
        
        print(f"\n[{i+1}/{len(valid_images)}] {img.get('alt', 'No alt')[:40]}")
        print(f"  URL: {url[:70]}...")
        
        # Download
        if download_image(url, download_path, referer='https://www.leapmotor.com'):
            print(f"  Downloaded: {os.path.getsize(download_path)} bytes")
            
            # Process
            try:
                remove_watermark_by_crop(download_path, clean_path)
                print(f"  Cleaned -> {clean_path}")
                results.append({
                    'original': url,
                    'downloaded': download_path,
                    'clean': clean_path,
                    'size': os.path.getsize(clean_path),
                })
            except Exception as e:
                print(f"  Processing error: {e}")
    
    # Save manifest
    manifest_path = os.path.join(OUTPUT_DIR, 'image_manifest.json')
    with open(manifest_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nDone! {len(results)} images processed.")
    print(f"Manifest saved: {manifest_path}")
    return results


if __name__ == '__main__':
    # Process images from different sources
    sources = [
        os.path.join(OUTPUT_DIR, 'images.json'),  # Homepage
        os.path.join(OUTPUT_DIR, 'news_2583.json'),
        os.path.join(OUTPUT_DIR, 'news_2687.json'),
        os.path.join(OUTPUT_DIR, 'news_3419.json'),
        os.path.join(OUTPUT_DIR, 'news_3322.json'),
    ]
    
    for source in sources:
        if os.path.exists(source):
            print(f"\n{'='*60}")
            print(f"Processing: {os.path.basename(source)}")
            print('='*60)
            process_images_from_json(source, max_images=10)
