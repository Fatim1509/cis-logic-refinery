#!/usr/bin/env python3
"""
CIS Health Check Utility

Monitors system health and diagnostics.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

class HealthChecker:
    """Monitors CIS system health"""
    
    def __init__(self):
        self.checks = {
            'github_access': self.check_github_access,
            'data_files': self.check_data_files,
            'dependencies': self.check_dependencies,
            'disk_space': self.check_disk_space,
            'memory': self.check_memory_usage
        }
    
    def check_github_access(self) -> Dict:
        """Check GitHub repository access"""
        try:
            import requests
            
            # Check if we can access GitHub API
            response = requests.get('https://api.github.com', timeout=10)
            
            return {
                'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'response_time': response.elapsed.total_seconds(),
                'status_code': response.status_code
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_data_files(self) -> Dict:
        """Check data file integrity"""
        try:
            data_dir = Path("data")
            if not data_dir.exists():
                return {
                    'status': 'warning',
                    'message': 'Data directory not found'
                }
            
            # Check for required files
            required_files = ['master_intel.json', 'last_update.txt']
            missing_files = []
            
            for filename in required_files:
                file_path = data_dir / filename
                if not file_path.exists():
                    missing_files.append(filename)
            
            if missing_files:
                return {
                    'status': 'warning',
                    'missing_files': missing_files
                }
            else:
                return {
                    'status': 'healthy',
                    'message': 'All data files present'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_dependencies(self) -> Dict:
        """Check critical dependencies"""
        try:
            required_modules = [
                'requests', 'discord', 'feedparser', 'vaderSentiment'
            ]
            
            missing_modules = []
            for module in required_modules:
                try:
                    __import__(module)
                except ImportError:
                    missing_modules.append(module)
            
            if missing_modules:
                return {
                    'status': 'warning',
                    'missing_modules': missing_modules
                }
            else:
                return {
                    'status': 'healthy',
                    'message': 'All dependencies available'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_disk_space(self) -> Dict:
        """Check available disk space"""
        try:
            import shutil
            
            # Get disk usage statistics
            usage = shutil.disk_usage('/')
            free_gb = usage.free / (1024**3)  # Convert to GB
            total_gb = usage.total / (1024**3)
            used_percent = (usage.used / usage.total) * 100
            
            status = 'healthy'
            if used_percent > 90:
                status = 'critical'
            elif used_percent > 80:
                status = 'warning'
            
            return {
                'status': status,
                'free_gb': round(free_gb, 2),
                'total_gb': round(total_gb, 2),
                'used_percent': round(used_percent, 1)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_memory_usage(self) -> Dict:
        """Check memory usage"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            
            return {
                'status': 'healthy',
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_percent': memory.percent
            }
            
        except ImportError:
            return {
                'status': 'warning',
                'message': 'psutil not available'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def run_health_check(self, check_all: bool = True, specific_checks: List[str] = None) -> Dict:
        """Run health checks"""
        logger.info("🏥 Running health diagnostics...")
        
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        checks_to_run = specific_checks if specific_checks else list(self.checks.keys())
        
        for check_name in checks_to_run:
            if check_name in self.checks:
                logger.info(f"🔍 Running {check_name} check...")
                try:
                    result = self.checks[check_name]()
                    results['checks'][check_name] = result
                    
                    # Update overall status
                    if result['status'] == 'critical':
                        results['overall_status'] = 'critical'
                    elif result['status'] == 'error' and results['overall_status'] == 'healthy':
                        results['overall_status'] = 'warning'
                        
                except Exception as e:
                    logger.error(f"❌ {check_name} check failed: {e}")
                    results['checks'][check_name] = {
                        'status': 'error',
                        'error': str(e)
                    }
                    if results['overall_status'] == 'healthy':
                        results['overall_status'] = 'warning'
        
        logger.info(f"✅ Health check completed: {results['overall_status']}")
        return results

def main():
    """Run health check"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CIS Health Check')
    parser.add_argument('--check-all', action='store_true', help='Run all checks')
    parser.add_argument('--checks', nargs='+', help='Specific checks to run')
    parser.add_argument('--output', help='Output file for results')
    
    args = parser.parse_args()
    
    checker = HealthChecker()
    
    # Run checks
    if args.check_all or not args.checks:
        results = checker.run_health_check(check_all=True)
    else:
        results = checker.run_health_check(specific_checks=args.checks)
    
    # Print results
    print(f"Overall Status: {results['overall_status']}")
    print(f"Timestamp: {results['timestamp']}")
    print("\nCheck Results:")
    
    for check_name, result in results['checks'].items():
        status = result['status']
        print(f"  {check_name}: {status}")
        if 'error' in result:
            print(f"    Error: {result['error']}")
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {args.output}")

if __name__ == "__main__":
    main()