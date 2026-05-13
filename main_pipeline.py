#!/usr/bin/env python3
"""
CIS Main Intelligence Pipeline
Orchestrates scraping → NLP → Consensus → Dispatch
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

# Local imports (will be adjusted based on structure)
try:
    from scrapers.orchestrator import ScraperOrchestrator
    from nlp.sentiment_analyzer import SentimentAnalyzer
    from nlp.consensus_engine import ConsensusEngine
    from utils.dispatcher import RepositoryDispatcher
    from utils.report_generator import ReportGenerator
except ImportError as e:
    print(f"Import warning: {e}")
    # Fallback stubs for now
    class ScraperOrchestrator:
        async def execute(self): return True
        raw_data = {}
    class SentimentAnalyzer:
        def analyze_text(self, text): return {"vader": 0.5, "finbert": 0.6}
    class ConsensusEngine:
        def verify_consensus(self, items): return items
    class ReportGenerator:
        def generate_report(self, intel): return {"summary": "Report generated"}
    class RepositoryDispatcher:
        def __init__(self, token=None): pass
        def create_dispatch_event(self, **kwargs): return True

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/pipeline.log', mode='a'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class CISPipeline:
    def __init__(self, github_token: str = None):
        self.orchestrator = ScraperOrchestrator()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.consensus_engine = ConsensusEngine()
        self.report_generator = ReportGenerator()
        self.dispatcher = RepositoryDispatcher(github_token) if github_token else None
        self.output_dir = Path("data")
        self.output_dir.mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)

    async def run_full_pipeline(self):
        logger.info("🚀 Starting full CIS Intelligence Pipeline...")

        # Step 1: Scrape
        success = await self.orchestrator.execute()
        if not success:
            logger.error("Scraping failed")
            return False

        # Step 2: Process
        processed_intel = await self._process_intelligence()

        # Step 3: Report
        report = self.report_generator.generate_report(processed_intel)

        # Step 4: Save & Dispatch
        output_file = self._save_intelligence(processed_intel, report)
        
        if self.dispatcher:
            await self._dispatch_to_operational_center(output_file)

        logger.info("🎉 Full pipeline completed successfully!")
        return True

    async def _process_intelligence(self):
        all_items = []
        # Placeholder for real data from orchestrator
        for source_data in getattr(self.orchestrator, 'raw_data', {}).values():
            if isinstance(source_data, dict) and 'data' in source_data:
                for item in source_data['data']:
                    text = item.get('title', '') + " " + item.get('summary', '')
                    if text.strip():
                        sentiment = self.sentiment_analyzer.analyze_text(text)
                        item['sentiment_analysis'] = sentiment
                    all_items.append(item)
        
        verified = self.consensus_engine.verify_consensus(all_items)
        return {'verified_items': verified, 'timestamp': datetime.utcnow().isoformat()}

    def _save_intelligence(self, intel: dict, report: dict):
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"intel_report_{timestamp}.json"
        
        payload = {
            **intel,
            'report': report,
            'pipeline_run': datetime.utcnow().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, default=str)
        
        logger.info(f"💾 Intelligence saved to {filepath}")
        return str(filepath)

    async def _dispatch_to_operational_center(self, payload_file: str):
        success = self.dispatcher.create_dispatch_event(
            target_owner="Fatim1509",
            target_repo="cis-operational-center",
            payload_file=payload_file
        )
        if success:
            logger.info("📤 Dispatched to Operational Center")

async def main():
    token = os.getenv("GITHUB_TOKEN")
    pipeline = CISPipeline(github_token=token)
    await pipeline.run_full_pipeline()

if __name__ == "__main__":
    asyncio.run(main())
