"""AutoScraper adapter for rapid brand website adaptation.

References:
- https://github.com/alirezamika/autoscraper
- Give it 2 examples and it learns the scraping rule automatically.
"""

from autoscraper import AutoScraper
from typing import List
import os


class AutoScraperAdapter:
    """Learn scraping rules from examples, then apply to new pages."""
    
    def __init__(self, model_path: str = 'data/autoscraper_models'):
        self.model_path = model_path
        os.makedirs(model_path, exist_ok=True)
        self.scraper = AutoScraper()
    
    def train(self, url: str, wanted_list: List[str], model_name: str) -> None:
        """Train on a page with examples.
        
        Args:
            url: The page URL to learn from
            wanted_list: List of text snippets to extract (e.g. ["小米YU9", "25.99万起"])
            model_name: Save model as this name for later use
        """
        result = self.scraper.build(url=url, wanted_list=wanted_list)
        model_file = os.path.join(self.model_path, f"{model_name}.json")
        self.scraper.save(model_file)
        print(f"Model '{model_name}' trained and saved. Found rules: {len(result)}")
    
    def extract(self, url: str, model_name: str) -> List[str]:
        """Extract data from a new page using a trained model."""
        model_file = os.path.join(self.model_path, f"{model_name}.json")
        
        if not os.path.exists(model_file):
            raise FileNotFoundError(f"Model '{model_name}' not found. Train it first.")
        
        self.scraper.load(model_file)
        return self.scraper.get_result_similar(url)
    
    def train_brand_page(self, brand_key: str, url: str, sample_titles: List[str]) -> None:
        """Quick helper to train on a brand news page."""
        print(f"Training autoscraper for {brand_key}...")
        self.train(url, sample_titles, f"{brand_key}_news")
        print(f"  Done. Next time just call extract(url, '{brand_key}_news')")


if __name__ == '__main__':
    # Example: Train on Xiaomi news page
    adapter = AutoScraperAdapter()
    
    # You would run this once per brand to learn the layout
    # adapter.train_brand_page(
    #     'xiaomi',
    #     'https://www.xiaomiev.com/news',
    #     ['小米YU9正式发布', '小米SU7']  # Example titles on the page
    # )
    
    # Then reuse:
    # results = adapter.extract('https://www.xiaomiev.com/news', 'xiaomi_news')
    # print(results)
