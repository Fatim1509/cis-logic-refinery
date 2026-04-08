#!/usr/bin/env python3
"""
CIS Scraper Orchestrator

Coordinates stealth data extraction from 5 financial data sources.
Implements anti-detection measures and consensus building.
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path
import argparse

# Import scrapers
from scrapers.reuters_scraper import ReutersScraper
from scrapers.investing_scraper import InvestingScraper
from scrapers.tradingeconomics_scraper import TradingEconomicsScraper
from scrapers.finviz_scraper import FinvizScraper
from scrapers.twitter_scraper import TwitterScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ScraperOrchestrator:
    def __init__(self, stealth_mode=True, delay_range=(2, 7), rotate_ua=True):
        self.stealth_mode = stealth_mode
        self.delay_range = delay_range
        self.rotate_ua = rotate_ua
        self.scrapers = {
            'reuters': ReutersScraper(),
            'investing': InvestingScraper(),
            'tradingeconomics': TradingEconomicsScraper(),
            'finviz': FinvizScraper(),
            'twitter': TwitterScraper()
        }
        self.raw_data = {}
        self.consolidated_intel = []
        
    def apply_stealth_measures(self):
        """Apply anti-detection measures"""
        if not self.stealth_mode:
            return
            
        # Add random delay between requests
        delay = random.uniform(*self.delay_range)
        logger.info(f"Applying stealth delay: {delay:.2f}s")
        time.sleep(delay)
        
        # Rotate user agent if enabled
        if self.rotate_ua:
            ua_pool = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)',
                'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X)'
            ]
            selected_ua = random.choice(ua_pool)
            logger.info(f"Rotating User-Agent: {selected_ua[:50]}...")
            
            # Apply to all scrapers
            for scraper in self.scrapers.values():
                if hasattr(scraper, 'set_user_agent'):
                    scraper.set_user_agent(selected_ua)
    
    async def scrape_source(self, source_name):
        """Scrape a single data source"""
        logger.info(f"🕷️ Scraping {source_name}...")
        
        try:
            self.apply_stealth_measures()
            scraper = self.scrapers[source_name]
            
            # Check if scraper is healthy
            if not await scraper.health_check():
                logger.warning(f"{source_name} health check failed, skipping...")
                return None
                
            # Extract data
            data = await scraper.extract()
            
            if data:
                logger.info(f"✅ Extracted {len(data)} items from {source_name}")
                return {
                    'source': source_name,
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': data,
                    'metadata': await scraper.get_metadata()
                }
            else:
                logger.warning(f"⚠️ No data extracted from {source_name}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error scraping {source_name}: {str(e)}")
            return None
    
    async def run_extraction_pipeline(self):
        """Run the complete extraction pipeline"""
        logger.info("🚀 Starting CIS extraction pipeline...")
        start_time = time.time()
        
        # Scrape all sources concurrently
        tasks = []
        for source_name in self.scrapers.keys():
            tasks.append(self.scrape_source(source_name))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_extractions = 0
        for i, result in enumerate(results):
            source_name = list(self.scrapers.keys())[i]
            
            if isinstance(result, Exception):
                logger.error(f"❌ {source_name} failed: {result}")
            elif result is None:
                logger.warning(f"⚠️ {source_name} returned no data")
            else:
                self.raw_data[source_name] = result
                successful_extractions += 1
                logger.info(f"✅ {source_name} extraction successful")
        
        elapsed_time = time.time() - start_time
        logger.info(f"📊 Extraction pipeline completed in {elapsed_time:.2f}s")
        logger.info(f"✅ {successful_extractions}/{len(self.scrapers)} sources extracted successfully")
        
        return successful_extractions >= 3  # Require at least 3 sources
    
    def save_raw_data(self):
        """Save raw extraction data"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"data/raw_extraction_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.raw_data, f, indent=2, default=str)
        
        logger.info(f"💾 Raw data saved to {filename}")
        return filename
    
    async def execute(self):
        """Execute the complete scraping orchestration"""
        try:
            # Run extraction pipeline
            success = await self.run_extraction_pipeline()
            
            if not success:
                logger.error("❌ Insufficient data sources extracted")
                return False
            
            # Save raw data
            raw_file = self.save_raw_data()
            
            logger.info("✅ CIS extraction orchestration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Orchestration failed: {str(e)}")
            return False

async def main():
    parser = argparse.ArgumentParser(description='CIS Scraper Orchestrator')
    parser.add_argument('--stealth', action='store_true', help='Enable stealth mode')
    parser.add_argument('--delay', type=str, default='2-7', help='Delay range (e.g., 2-7)')
    parser.add_argument('--rotate-ua', action='store_true', help='Rotate user agents')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Parse delay range
    delay_parts = args.delay.split('-')
    delay_range = (int(delay_parts[0]), int(delay_parts[1]))
    
    # Initialize orchestrator
    orchestrator = ScraperOrchestrator(
        stealth_mode=args.stealth,
        delay_range=delay_range,
        rotate_ua=args.rotate_ua
    )
    
    # Execute
    success = await orchestrator.execute()
    
    if success:
        logger.info("🎉 CIS orchestration completed successfully")
        exit(0)
    else:
        logger.error("💥 CIS orchestration failed")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())