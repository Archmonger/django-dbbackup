#!/usr/bin/env python3
"""
Simple PostgreSQL Live Testing Script for django-dbbackup

This is a simplified version that runs each connector test in isolation
to avoid Django configuration conflicts.

Usage:
    python scripts/postgres_live_test_simple.py [--connector CONNECTOR] [--verbose]
"""

import subprocess
import sys
import os
from pathlib import Path


def run_single_connector_test(connector_name, verbose=False):
    """Run a test for a single connector in isolation."""
    script_path = Path(__file__).parent / "postgres_live_test.py"
    cmd = [sys.executable, str(script_path), "--connector", connector_name]
    if verbose:
        cmd.append("--verbose")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode == 0


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run live PostgreSQL tests for django-dbbackup")
    parser.add_argument('--connector', default='PgDumpConnector', 
                       choices=['PgDumpConnector', 'PgDumpBinaryConnector', 'PgDumpGisConnector'],
                       help='PostgreSQL connector to test')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--all', action='store_true', help='Test all PostgreSQL connectors')
    
    args = parser.parse_args()
    
    connectors_to_test = ['PgDumpConnector', 'PgDumpBinaryConnector', 'PgDumpGisConnector'] if args.all else [args.connector]
    
    print("🐘 Starting PostgreSQL Live Tests for django-dbbackup (Isolated)")
    print("=" * 60)
    
    results = {}
    for connector in connectors_to_test:
        print(f"\n📋 Testing {connector}...")
        results[connector] = run_single_connector_test(connector, verbose=args.verbose)
        
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    for connector, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {connector}: {status}")
        
    total_tests = len(results)
    passed_tests = sum(results.values())
    print(f"\nResults: {passed_tests}/{total_tests} tests passed")
    
    # Exit with error code if any tests failed
    sys.exit(0 if passed_tests == total_tests else 1)


if __name__ == '__main__':
    main()