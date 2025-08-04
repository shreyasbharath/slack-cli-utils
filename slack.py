#!/usr/bin/env python3
"""
Slack Export Tool

A unified tool for exporting Slack data with clean, consistent interface.
"""

import sys
import subprocess
import os
from pathlib import Path

def main():
    """Main entry point that delegates to the CLI."""
    script_dir = Path(__file__).parent
    cli_script = script_dir / "cli.py"
    
    if not cli_script.exists():
        print("❌ Error: cli.py not found")
        return 1
    
    # Pass all arguments to the CLI script
    cmd = [sys.executable, str(cli_script)] + sys.argv[1:]
    return subprocess.run(cmd).returncode

if __name__ == "__main__":
    sys.exit(main())
