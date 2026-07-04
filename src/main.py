"""Auto Intelligence Center - Main entry point.

Usage:
    python src/main.py              # Crawl all brands
    python src/main.py --brand xiaomi  # Crawl specific brand
    python src/main.py --media URL     # Extract media article
    python src/main.py --train URL     # Train autoscraper on URL
"""

import asyncio
import argparse
from datetime import datetime

from crawlee_spider import crawl_all_brands
from newspaper_extractor import MediaExtractor
from autoscraper_adapter import AutoScraperAdapter


def parse_args():
    parser = argparse.ArgumentParser(description='Auto Intelligence Center')
    parser.add_argument('--brand', help='Crawl specific brand only')
    parser.add_argument('--media', help='Extract media article from URL')
    parser.add_argument('--train', help='Train autoscraper on URL')
    parser.add_argument('--examples', nargs='+', help='Example texts for autoscraper training')
    return parser.parse_args()


async def main():
    args = parse_args()
    
    if args.media:
        print(f"Extracting media content from: {args.media}")
        extractor = MediaExtractor()
        result = extractor.extract(args.media)
        if result:
            print(f"Title: {result['title']}")
            print(f"Date: {result['publish_date']}")
            print(f"Keywords: {result['keywords']}")
            print(f"Summary: {result['summary'][:200]}...")
        return
    
    if args.train:
        if not args.examples:
            print("Error: --examples required for training (e.g. --examples '小米YU9' '25.99万')")
            return
        adapter = AutoScraperAdapter()
        adapter.train(args.train, args.examples, 'custom_model')
        return
    
    # Default: crawl all brands
    print(f"Starting crawl at {datetime.now().isoformat()}")
    results = await crawl_all_brands()
    
    total = sum(len(v) for v in results.values())
    print(f"\nCrawl complete. Total entries: {total}")
    for brand, data in results.items():
        print(f"  {brand}: {len(data)} page(s)")


if __name__ == '__main__':
    asyncio.run(main())
