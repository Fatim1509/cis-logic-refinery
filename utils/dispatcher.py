#!/usr/bin/env python3
"""
CIS Repository Dispatcher

Handles cross-repository communication using GitHub repository_dispatch API.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests
from github import Github

logger = logging.getLogger(__name__)

class RepositoryDispatcher:
    """Handles repository dispatch communication between CIS repos"""
    
    def __init__(self, token: str):
        self.token = token
        self.github = Github(token)
        
    def create_dispatch_payload(self, data: Dict, max_size_kb: int = 65) -> Dict:
        """Create dispatch payload within GitHub size limits"""
        
        # Convert data to JSON string
        payload_str = json.dumps(data, default=str)
        payload_size_kb = len(payload_str.encode('utf-8')) / 1024
        
        logger.info(f"📦 Original payload size: {payload_size_kb:.2f}KB")
        
        if payload_size_kb > max_size_kb:
            logger.warning(f"⚠️ Payload too large ({payload_size_kb:.2f}KB), truncating...")
            
            # Truncate strategy: keep only essential fields
            truncated_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0',
                'summary': {
                    'total_signals': len(data.get('consensus', {}).get('source_breakdown', {})),
                    'recommendation': data.get('consensus', {}).get('recommendation', 'NEUTRAL'),
                    'confidence': data.get('consensus', {}).get('confidence', 0),
                    'dominant_sentiment': data.get('consensus', {}).get('dominant_sentiment', 'neutral')
                },
                'data_url': f"https://raw.githubusercontent.com/{self.github.get_user().login}/cis-operational-center/main/data/master_intel.json"
            }
            
            payload_str = json.dumps(truncated_data, default=str)
            final_size_kb = len(payload_str.encode('utf-8')) / 1024
            
            logger.info(f"📦 Truncated payload size: {final_size_kb:.2f}KB")
            return truncated_data
        
        return data
    
    def send_dispatch(self, owner: str, repo: str, event_type: str = "cis-intelligence-update", 
                       client_payload: Optional[Dict] = None) -> bool:
        """Send repository dispatch to target repository"""
        
        try:
            # Get target repository
            target_repo = self.github.get_repo(f"{owner}/{repo}")
            
            # Prepare payload
            if client_payload is None:
                client_payload = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'message': 'CIS intelligence update',
                    'version': '1.0'
                }
            
            # Ensure payload is within size limits
            payload = self.create_dispatch_payload(client_payload)
            
            logger.info(f"🚀 Sending dispatch to {owner}/{repo}")
            logger.info(f"   Event type: {event_type}")
            logger.info(f"   Payload size: {len(json.dumps(payload).encode('utf-8'))} bytes")
            
            # Send dispatch
            target_repo.create_repository_dispatch(event_type, payload)
            
            logger.info(f"✅ Dispatch sent successfully to {owner}/{repo}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send dispatch to {owner}/{repo}: {e}")
            return False
    
    def send_file_dispatch(self, owner: str, repo: str, payload_file: str, 
                          event_type: str = "cis-intelligence-update") -> bool:
        """Send dispatch with payload loaded from file"""
        
        try:
            # Load payload from file
            file_path = Path(payload_file)
            if not file_path.exists():
                logger.error(f"❌ Payload file not found: {payload_file}")
                return False
            
            with open(file_path, 'r') as f:
                payload_data = json.load(f)
            
            logger.info(f"📄 Loaded payload from {payload_file}")
            return self.send_dispatch(owner, repo, event_type, payload_data)
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in payload file: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to load payload file: {e}")
            return False
    
    def test_dispatch(self, owner: str, repo: str) -> bool:
        """Send test dispatch to verify connectivity"""
        
        test_payload = {
            'test': True,
            'timestamp': datetime.utcnow().isoformat(),
            'message': 'CIS test dispatch - connectivity verification'
        }
        
        logger.info(f"🧪 Sending test dispatch to {owner}/{repo}")
        return self.send_dispatch(owner, repo, "cis-test", test_payload)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='CIS Repository Dispatcher')
    parser.add_argument('--target-owner', required=True, help='Target repository owner')
    parser.add_argument('--target-repo', required=True, help='Target repository name')
    parser.add_argument('--token', required=True, help='GitHub personal access token')
    parser.add_argument('--payload-file', help='Path to payload JSON file')
    parser.add_argument('--event-type', default='cis-intelligence-update', help='Event type')
    parser.add_argument('--test', action='store_true', help='Send test dispatch')
    
    args = parser.parse_args()
    
    # Initialize dispatcher
    dispatcher = RepositoryDispatcher(args.token)
    
    if args.test:
        # Send test dispatch
        success = dispatcher.test_dispatch(args.target_owner, args.target_repo)
        sys.exit(0 if success else 1)
    
    elif args.payload_file:
        # Send dispatch with file payload
        success = dispatcher.send_file_dispatch(
            args.target_owner,
            args.target_repo,
            args.payload_file,
            args.event_type
        )
        sys.exit(0 if success else 1)
    
    else:
        # Send basic dispatch
        success = dispatcher.send_dispatch(
            args.target_owner,
            args.target_repo,
            args.event_type
        )
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()