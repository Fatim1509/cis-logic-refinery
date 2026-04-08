#!/usr/bin/env python3
"""
Reuters Financial News Scraper

Extracts financial news from Reuters RSS feeds using stealth techniques.
"""

import asyncio
import feedparser
import logging
import random
import time
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ReutersScraper:
    """Reuters financial news scraper with stealth capabilities"""
    
    def __init__(self):
        self.base_url = "https://www.reuters.com"
        self.rss_feeds = [
            "https://feeds.reuters.com/reuters/businessNews",
            "https://feeds.reuters.com/reuters/companyNews",
            "https://feeds.reuters.com/reuters/technologyNews",
            "https://feeds.reuters.com/reuters/marketsNews"
        ]
        self.user_agent = None
        self.session = None
        
    def set_user_agent(self, user_agent: str):
        """Set custom user agent for stealth"""
        self.user_agent = user_agent
        
    async def health_check(self) -> bool:
        """Check if Reuters is accessible"""
        try:
            headers = self._get_headers()
            response = requests.get(self.base_url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Reuters health check failed: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with optional user agent rotation"""
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        if self.user_agent:
            headers['User-Agent'] = self.user_agent
        else:
            # Default Reuters-friendly user agent
            headers['User-Agent'] = 'Mozilla/5.0 (compatible; ReutersBot/1.0; +http://reuters.com/bot)'
            
        return headers
    
    async def extract_rss_feed(self, feed_url: str) -> List[Dict]:
        """Extract news from RSS feed"""
        try:
            logger.info(f"📡 Parsing RSS feed: {feed_url}")
            
            # Add random delay to avoid detection
            await asyncio.sleep(random.uniform(1, 3))
            
            # Parse RSS feed
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                logger.warning(f"RSS parsing error for {feed_url}")
                return []
            
            articles = []
            for entry in feed.entries[:10]:  # Limit to top 10 articles
                try:
                    article = {
                        'title': entry.get('title', ''),
                        'link': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'summary': entry.get('summary', ''),
                        'source': 'reuters',
                        'category': self._categorize_article(entry.get('title', '')),
                        'confidence': 0.9  # High confidence for Reuters
                    }
                    
                    # Extract additional metadata
                    if hasattr(entry, 'tags'):
                        article['tags'] = [tag.term for tag in entry.tags]
                    
                    if hasattr(entry, 'author'):
                        article['author'] = entry.author
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.error(f"Error processing RSS entry: {e}")
                    continue
            
            logger.info(f"✅ Extracted {len(articles)} articles from {feed_url}")
            return articles
            
        except Exception as e:
            logger.error(f"❌ Error extracting RSS feed {feed_url}: {e}")
            return []
    
    def _categorize_article(self, title: str) -> str:
        """Categorize article based on title keywords"""
        title_lower = title.lower()
        
        categories = {
            'earnings': ['earnings', 'profit', 'revenue', 'quarterly'],
            'mergers': ['merger', 'acquisition', 'acquire', 'bought'],
            'ipo': ['ipo', 'public offering', 'listing'],
            'regulation': ['regulation', 'sec', 'fed', 'central bank'],
            'crypto': ['bitcoin', 'crypto', 'blockchain', 'digital currency'],
            'tech': ['ai', 'artificial intelligence', 'technology', 'software'],
            'energy': ['oil', 'gas', 'energy', 'renewable'],
            'healthcare': ['fda', 'drug', 'medical', 'health']
        }
        
        for category, keywords in categories.items():
            if any(keyword in title_lower for keyword in keywords):
                return category
        
        return 'general'
    
    async def extract_article_content(self, article_url: str) -> Optional[str]:
        """Extract full article content from URL"""
        try:
            headers = self._get_headers()
            response = requests.get(article_url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"Article fetch failed: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try different content selectors
            content_selectors = [
                'article',
                '.article-body',
                '.story-content',
                '.StandardArticleBody_body',
                '[data-testid="paragraph"]'
            ]
            
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = ' '.join([elem.get_text(strip=True) for elem in elements])
                    break
            
            return content if content else None
            
        except Exception as e:
            logger.error(f"❌ Error extracting article content: {e}")
            return None
    
    async def extract(self) -> List[Dict]:
        """Main extraction method"""
        logger.info("🗞️ Starting Reuters extraction...")
        start_time = time.time()
        
        all_articles = []
        
        # Extract from all RSS feeds
        for feed_url in self.rss_feeds:
            articles = await self.extract_rss_feed(feed_url)
            all_articles.extend(articles)
        
        # Remove duplicates based on title
        seen_titles = set()
        unique_articles = []
        for article in all_articles:
            if article['title'] not in seen_titles:
                seen_titles.add(article['title'])
                unique_articles.append(article)
        
        # Add extraction timestamp
        for article in unique_articles:
            article['extracted_at'] = datetime.utcnow().isoformat()
        
        elapsed_time = time.time() - start_time
        logger.info(f"✅ Reuters extraction completed: {len(unique_articles)} unique articles in {elapsed_time:.2f}s")
        
        return unique_articles
    
    async def get_metadata(self) -> Dict:
        """Get scraper metadata"""
        return {
            'source': 'reuters',
            'version': '1.0.0',
            'last_updated': datetime.utcnow().isoformat(),
            'rss_feeds': len(self.rss_feeds),
            'base_url': self.base_url,
            'extraction_method': 'rss_feedparser'
        }

# Example usage
async def main():
    scraper = ReutersScraper()
    
    # Health check
    if await scraper.health_check():
        print("✅ Reuters is accessible")
        
        # Extract articles
        articles = await scraper.extract()
        
        print(f"📊 Extracted {len(articles)} articles")
        for article in articles[:3]:  # Show first 3
            print(f"- {article['title'][:60]}...")
            
    else:
        print("❌ Reuters is not accessible")

if __name__ == "__main__":
    asyncio.run(main())