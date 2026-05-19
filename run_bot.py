"""Run the C3MR Manager Bot as a standalone process."""
import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from backend.bot_service import run_bot

if __name__ == "__main__":
    run_bot()
