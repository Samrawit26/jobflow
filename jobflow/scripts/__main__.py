"""
Entry point for running jobflow.scripts.review as a module.

This allows the script to be run as:
    python -m jobflow.scripts.review job_discovery
"""

import sys
from jobflow.scripts.review import main

if __name__ == "__main__":
    sys.exit(main())
