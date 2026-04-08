#!/usr/bin/env python3
"""
CIS Repository Dispatcher

Handles cross-repository communication using GitHub repository_dispatch API.
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import requests
from github import Github

logger = logging.getLogger(__name__)

class RepositoryDispatcher:
    """Handles dispatch events between repositories"""
    
    def __init__(self, token: str):
        self.token = token
        self.github = Github(token)
        
        logger.info("🔔 Repository dispatcher initialized")
    
    def create_dispatch_event(
        self, 
        target_owner: str, 
        target_repo: str, 
        event_type: str = "cis-intelligence-update",
        client_payload: Optional[Dict] = None,
        payload_file: Optional[str] = None
    ) -> bool:
        """Create a repository dispatch event"""
        
        try:
            # Load payload from file if provided
            if payload_file:
                with open(payload_file, 'r') as f:
                    payload_data = json.load(f)
                
                # Truncate if too large (65KB limit)
                payload_str = json.dumps(payload_data)
                if len(payload_str.encode('utf-8')) > 65000:
                    logger.warning("Payload too large, truncating...")
                    # Keep only essential fields
                    truncated_data = {
                        'summary': payload_data.get('summary', ''),
                        'signals': payload_data.get('signals', [])[:10],  # Limit to 10 signals
                        'timestamp': payload_data.get('timestamp', datetime.utcnow().isoformat()),
                        'source': 'cis-logic-refinery'
                    }
                    client_payload = truncated_data
                else:
                    client_payload = payload_data
            
            # Ensure payload has required structure
            if not client_payload:
                client_payload = {
                    'message': 'CIS intelligence update',
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': 'cis-logic-refinery'
                }
            
            # Add metadata
            client_payload['dispatch_time'] = datetime.utcnow().isoformat()
            client_payload['sender'] = 'cis-logic-refinery'
            client_payload['version'] = '1.0.0'
            
            logger.info(f"📤 Creating dispatch event for {target_owner}/{target_repo}")
            logger.info(f"Event type: {event_type}")
            logger.info(f"Payload size: {len(json.dumps(client_payload).encode('utf-8'))} bytes")
            
            # Use GitHub API directly for better control
            url = f"https://api.github.com/repos/{target_owner}/{target_repo}/dispatches"
            headers = {
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            }
            
            data = {
                'event_type': event_type,
                'client_payload': client_payload
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 204:
                logger.info("✅ Dispatch event created successfully")
                return True
            else:
                logger.error(f"❌ Failed to create dispatch event: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error creating dispatch event: {e}")
            return False
    
    def wait_for_completion(self, target_owner: str, target_repo: str, timeout: int = 300) -> bool:
        """Wait for the dispatched workflow to complete"""
        try:
            repo = self.github.get_repo(f"{target_owner}/{target_repo}")
            
            logger.info(f"⏳ Waiting for workflow completion (timeout: {timeout}s)")
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Check recent workflow runs
                runs = repo.get_workflow_runs()
                
                for run in runs[:5]:  # Check last 5 runs
                    if run.created_at.timestamp() > start_time:
                        status = run.status
                        conclusion = run.conclusion
                        
                        logger.info(f"Workflow run {run.id}: {status} - {conclusion}")
                        
                        if status == 'completed':
                            if conclusion == 'success':
                                logger.info("✅ Target workflow completed successfully")
                                return True
                            else:
                                logger.error(f"❌ Target workflow failed: {conclusion}")
                                return False
                
                time.sleep(10)  # Check every 10 seconds
            
            logger.warning("⏰ Timeout waiting for workflow completion")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error waiting for completion: {e}")
            return False

def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CIS Repository Dispatcher')
    parser.add_argument('--target-owner', required=True, help='Target repository owner')
    parser.add_argument('--target-repo', required=True, help='Target repository name')
    parser.add_argument('--token', required=True, help='GitHub personal access token')
    parser.add_argument('--event-type', default='cis-intelligence-update', help='Event type')
    parser.add_argument('--payload-file', help='JSON file containing client payload')
    parser.add_argument('--wait', action='store_true', help='Wait for workflow completion')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout in seconds')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create dispatcher
    dispatcher = RepositoryDispatcher(args.token)
    
    # Create dispatch event
    success = dispatcher.create_dispatch_event(
        target_owner=args.target_owner,
        target_repo=args.target_repo,
        event_type=args.event_type,
        payload_file=args.payload_file
    )
    
    if success and args.wait:
        dispatcher.wait_for_completion(
            target_owner=args.target_owner,
            target_repo=args.target_repo,
            timeout=args.timeout
        )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()