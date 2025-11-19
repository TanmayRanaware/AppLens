#!/usr/bin/env python3
"""
Simple test runner for AppLens backend tests
Runs tests without requiring full application dependencies
"""

import sys
import os
import pytest
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def run_tests():
    """Run tests with coverage reporting"""
    
    # Test files that can run without full application dependencies
    test_files = [
        "tests/test_models.py",
        "tests/test_agents_simple.py", 
        "tests/test_performance_util.py"
    ]
    
    # Run pytest with coverage
    args = [
        "--cov=app",
        "--cov-report=html", 
        "--cov-report=term-missing",
        "-v"
    ]
    
    # Add test files
    args.extend(test_files)
    
    print("Running AppLens Backend Tests...")
    print("=" * 50)
    
    # Run pytest
    exit_code = pytest.main(args)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
        print("\nCoverage report generated in htmlcov/index.html")
    else:
        print(f"\n❌ Tests failed with exit code: {exit_code}")
    
    return exit_code

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)