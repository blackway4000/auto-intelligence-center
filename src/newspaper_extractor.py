"""Media content extraction using newspaper4k.

References:
- https://github.com/AndyTheFactory/newspaper4k
- Best for extracting article content from media sites (autohome, dongchedi, etc.)
"""

from newspaper import Article
from typing import Optional
from datetime import datetime


class MediaExtractor:
    """Extract structured article data from media URLs."""
    
    def extract(self, url: str) -> Optional[dict]:
        """Download and parse a news article."""
        try:
            article = Article(url, language='zh')
            article.download()
            article.parse()
            article.nlp()  # Keywords + summary
            
            return {
                'title': article.title,
                'text': article.text,
                'summary': article.summary,
                'keywords': article.keywords,
                'publish_date': article.publish_date.isoformat() if article.publish_date else None,
                'authors': article.authors,
                'top_image': article.top_image,
                'url': url,
                'source': 'media_platform',
                'extracted_at': datetime.now().isoformat(),
            }
        except Exception as e:
            print(f"Failed to extract {url}: {e}")
            return None
    
    def extract_batch(self, urls: list[str]) -> list[dict]:
        """Extract multiple articles."""
        results = []
        for url in urls:
            data = self.extract(url)
            if data:
                results.append(data)
        return results


if __name__ == '__main__':
    # Example: extract a test article
    extractor = MediaExtractor()
    result = extractor.extract('https://www.autohome.com.cn/news/')
    if result:
        print(f"Title: {result['title']}")
        print(f"Keywords: {result['keywords']}")
