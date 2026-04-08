#!/usr/bin/env python3
"""
TradingEconomics Scraper

Extracts economic indicators from TradingEconomics API and RSS.
"""

import asyncio
import feedparser
import logging
from datetime import datetime
from typing import List, Dict
import requests

logger = logging.getLogger(__name__)

class TradingEconomicsScraper:
    """TradingEconomics scraper"""
    
    def __init__(self):
        self.rss_feeds = [
            "https://tradingeconomics.com/rss/",
            "https://tradingeconomics.com/rss/news"
        ]
        self.api_base = "https://api.tradingeconomics.com"
        
    async def health_check(self) -> bool:
        """Check if TradingEconomics is accessible"""
        try:
            response = requests.get("https://tradingeconomics.com", timeout=10)
            return response.status_code == 200
        except:
            return False
    
    async def extract(self) -> List[Dict]:
        """Extract economic indicators"""
        logger.info("📊 Starting TradingEconomics extraction...")
        
        all_data = []
        
        # Extract from RSS feeds
        for feed_url in self.rss_feeds:
            try:
                await asyncio.sleep(1)
                
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:5]:
                    indicator = {
                        'title': entry.get('title', ''),
                        'description': entry.get('description', ''),
                        'published': entry.get('published', ''),
                        'source': 'tradingeconomics',
                        'type': 'economic_indicator',
                        'confidence': 0.85
                    }
                    all_data.append(indicator)
                    
            except Exception as e:
                logger.error(f"Error extracting from {feed_url}: {e}")
                continue
        
        # Add timestamps
        for item in all_data:
            item['extracted_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"✅ TradingEconomics extraction completed: {len(all_data)} indicators")
        return all_data
    
    async def get_metadata(self) -> Dict:
        return {
            'source': 'tradingeconomics',
            'version': '1.0.0',
            'last_updated': datetime.utcnow().isoformat(),
            'extraction_method': 'rss_feedparser'
        }