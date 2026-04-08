#!/usr/bin/env python3
"""
Investing.com Scraper

Extracts financial data from Investing.com using RSS and Playwright.
"""

import asyncio
import feedparser
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

class InvestingScraper:
    """Investing.com scraper"""
    
    def __init__(self):
        self.rss_feeds = [
            "https://www.investing.com/rss/news.rss",
            "https://www.investing.com/rss/forex.rss",
            "https://www.investing.com/rss/stocks.rss"
        ]
        
    async def health_check(self) -> bool:
        """Check if Investing.com is accessible"""
        try:
            # Simple connectivity check
            import requests
            response = requests.get("https://www.investing.com", timeout=10)
            return response.status_code == 200
        except:
            return False
    
    async def extract(self) -> List[Dict]:
        """Extract data from RSS feeds"""
        logger.info("📈 Starting Investing.com extraction...")
        
        all_articles = []
        
        for feed_url in self.rss_feeds:
            try:
                await asyncio.sleep(1)  # Rate limiting
                
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:5]:  # Limit articles
                    article = {
                        'title': entry.get('title', ''),
                        'link': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'summary': entry.get('summary', ''),
                        'source': 'investing.com',
                        'category': 'market_analysis',
                        'confidence': 0.8
                    }
                    all_articles.append(article)
                    
            except Exception as e:
                logger.error(f"Error extracting from {feed_url}: {e}")
                continue
        
        # Add timestamps
        for article in all_articles:
            article['extracted_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"✅ Investing.com extraction completed: {len(all_articles)} articles")
        return all_articles
    
    async def get_metadata(self) -> Dict:
        return {
            'source': 'investing.com',
            'version': '1.0.0',
            'last_updated': datetime.utcnow().isoformat(),
            'extraction_method': 'rss_feedparser'
        }