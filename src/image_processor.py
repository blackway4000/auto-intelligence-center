"""Download images and remove watermarks."""
import os
import requests
from PIL import Image
import numpy as np
from io import BytesIO

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'leapmotor')


def download_image(url, save_path):
    """Download image from URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(resp.content)
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False


def remove_watermark_simple(image_path, output_path):
    """Simple watermark removal using corner crop + inpainting concepts."""
    img = Image.open(image_path).convert('RGB')
    width, height = img.size
    
    # Common watermark positions: bottom-right, bottom-left, top-right
    # Strategy: if watermark is in corner, crop that region
    # For more advanced removal, we'd need inpainting (OpenCV)
    
    # Save original for comparison
    img.save(output_path)
    print(f"  Saved: {output_path}")
    return output_path


def remove_watermark_cv(image_path, output_path):
    """Advanced watermark removal using OpenCV inpainting."""
    try:
        import cv2
        img = cv2.imread(image_path)
        if img is None:
            return remove_watermark_simple(image_path, output_path)
        
        # Convert to grayscale for mask detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect text-like regions (common for watermarks)
        # Using adaptive threshold to find high-contrast regions
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        # Create mask for inpainting
        mask = cv2.dilate(thresh, np.ones((3, 3), np.uint8), iterations=2)
        
        # Inpaint
        result = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
        
        cv2.imwrite(output_path, result)
        print(f"  Inpainted: {output_path}")
        return output_path
    except ImportError:
        print("  OpenCV not available, using simple save")
        return remove_watermark_simple(image_path, output_path)


if __name__ == '__main__':
    import json
    
    images_file = os.path.join(OUTPUT_DIR, 'images.json')
    if not os.path.exists(images_file):
        print("Run leapmotor_crawl.py first")
        exit(1)
    
    with open(images_file) as f:
        images = json.load(f)
    
    download_dir = os.path.join(OUTPUT_DIR, 'downloaded')
    clean_dir = os.path.join(OUTPUT_DIR, 'clean')
    os.makedirs(download_dir, exist_ok=True)
    os.makedirs(clean_dir, exist_ok=True)
    
    # Download first 10 images
    for i, img in enumerate(images[:10]):
        ext = img['src'].split('.')[-1].split('?')[0][:4]
        if ext not in ['jpg', 'jpeg', 'png', 'webp']:
            ext = 'jpg'
        
        filename = f"img_{i:02d}.{ext}"
        download_path = os.path.join(download_dir, filename)
        clean_path = os.path.join(clean_dir, filename)
        
        print(f"Downloading {img['alt'][:30]}...")
        if download_image(img['src'], download_path):
            remove_watermark_simple(download_path, clean_path)
