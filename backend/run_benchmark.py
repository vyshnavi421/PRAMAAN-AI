"""
Convenient entry point to execute PRAMAAN-AI reproducible benchmark.
Usage:
  python run_benchmark.py
  python run_benchmark.py --verbose
  python run_benchmark.py --report-path ../docs/EVALUATION_REPORT.md
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.benchmark.runner import main

if __name__ == "__main__":
    main()
