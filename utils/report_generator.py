#!/usr/bin/env python3
"""
CIS Report Generator

Generates intelligence reports in various formats.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generates intelligence reports"""
    
    def __init__(self):
        self.output_dir = Path("data")
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_json_report(self, data: Dict, filename: str = None) -> str:
        """Generate JSON intelligence report"""
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"master_intel_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"✅ JSON report generated: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ Failed to generate JSON report: {e}")
            return ""
    
    def generate_summary_report(self, data: Dict) -> str:
        """Generate human-readable summary"""
        try:
            consensus = data.get('consensus', {})
            summary = data.get('summary', {})
            
            report_lines = [
                "🎯 CIS Intelligence Summary",
                f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                "",
                f"Recommendation: {consensus.get('recommendation', 'NEUTRAL')}",
                f"Confidence: {consensus.get('confidence', 0):.1%}",
                f"Dominant Sentiment: {consensus.get('dominant_sentiment', 'neutral').title()}",
                "",
                f"Total Signals: {summary.get('total_signals', 0)}",
                f"Sources Active: {summary.get('sources_active', 0)}/5",
                ""
            ]
            
            # Add source breakdown if available
            breakdown = consensus.get('source_breakdown', {})
            if breakdown:
                report_lines.extend([
                    "Source Breakdown:",
                    f"  Positive: {breakdown.get('positive_count', 0)}",
                    f"  Negative: {breakdown.get('negative_count', 0)}",
                    f"  Neutral: {breakdown.get('neutral_count', 0)}"
                ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"❌ Failed to generate summary: {e}")
            return "Error generating summary"

def main():
    """Test report generation"""
    # Mock data
    test_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'consensus': {
            'recommendation': 'BUY',
            'confidence': 0.75,
            'dominant_sentiment': 'positive',
            'source_breakdown': {
                'positive_count': 8,
                'negative_count': 2,
                'neutral_count': 3
            }
        },
        'summary': {
            'total_signals': 13,
            'sources_active': 4
        }
    }
    
    generator = ReportGenerator()
    
    # Generate JSON report
    json_file = generator.generate_json_report(test_data)
    print(f"JSON report: {json_file}")
    
    # Generate summary
    summary = generator.generate_summary_report(test_data)
    print("Summary Report:")
    print(summary)

if __name__ == "__main__":
    main()