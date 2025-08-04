#!/usr/bin/env python3
"""
Unified Slack Export CLI

A single entry point for all Slack data export operations.
Automatically routes to the appropriate specialized tool based on what you want to export.
"""

import argparse
import sys
import os
import subprocess
from datetime import datetime
from typing import Optional, List

class SlackCLI:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Map operations to their corresponding scripts
        self.operations = {
            'bookmarks': 'bookmarks.py',
            'dm': 'history.py', 
            'channel': 'search.py',
            'search': 'search.py',
            'list': 'list.py'
        }
    
    def show_interactive_menu(self) -> str:
        """Show interactive menu and return selected operation."""
        print("\n🚀 Slack Export Tool")
        print("=" * 50)
        print("What would you like to export?")
        print()
        print("1. 📌 Bookmarked/Starred Messages")
        print("   Export all messages you've starred across all channels")
        print()
        print("2. 💬 Direct Messages (DMs)")
        print("   Export conversation history from a specific DM")
        print()
        print("3. 📺 Channel Messages")
        print("   Export all messages from a specific channel")
        print()
        print("4. 🔍 Search Messages")
        print("   Search and export messages using Slack's search syntax")
        print()
        print("5. 📋 List Channels/DMs")
        print("   Show all available channels and DMs with their IDs")
        print()
        print("6. ❌ Exit")
        print()
        
        while True:
            try:
                choice = input("Enter your choice (1-6): ").strip()
                if choice == '1':
                    return 'bookmarks'
                elif choice == '2':
                    return 'dm'
                elif choice == '3':
                    return 'channel'
                elif choice == '4':
                    return 'search'
                elif choice == '5':
                    return 'list'
                elif choice == '6':
                    print("Goodbye! 👋")
                    sys.exit(0)
                else:
                    print("❌ Invalid choice. Please enter 1-6.")
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                sys.exit(0)
    
    def get_token_interactively(self) -> str:
        """Get Slack token from user interactively."""
        print("\n🔑 Slack Token Required")
        print("You need a Slack User OAuth Token (starts with 'xoxp-')")
        print("Get one at: https://api.slack.com/apps")
        print()
        
        while True:
            token = input("Enter your Slack token: ").strip()
            if token.startswith('xoxp-'):
                return token
            elif not token:
                print("❌ Token cannot be empty")
            else:
                print("❌ Token should start with 'xoxp-'")
    
    def get_output_file_interactively(self, operation: str, default_extension: str = 'md') -> str:
        """Get output filename from user interactively."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"slack_{operation}_{timestamp}.{default_extension}"
        
        print(f"\n📁 Output File")
        filename = input(f"Output filename (default: {default_name}): ").strip()
        
        if not filename:
            filename = default_name
        
        return filename
    
    def run_bookmarks(self, args) -> int:
        """Run bookmarks export."""
        cmd = ['python3', os.path.join(self.script_dir, 'slack_bookmarks_fetcher.py')]
        
        if args.interactive:
            token = self.get_token_interactively()
            output = self.get_output_file_interactively('bookmarks')
            cmd.extend(['-t', token, '-o', output])
            
            # Ask about page size
            page_size = input("\nPage size for fetching (default: 100): ").strip()
            if page_size and page_size.isdigit():
                cmd.extend(['--page-size', page_size])
        else:
            if not args.token:
                print("❌ Error: --token is required for bookmarks export")
                return 1
            
            cmd.extend(['-t', args.token])
            
            if args.output:
                cmd.extend(['-o', args.output])
            
            if args.page_size:
                cmd.extend(['--page-size', str(args.page_size)])
        
        print(f"\n🚀 Running: {' '.join(cmd[2:])}")  # Hide python3 path
        return subprocess.run(cmd).returncode
    
    def run_dm(self, args) -> int:
        """Run DM export."""
        cmd = ['python3', os.path.join(self.script_dir, 'fetch_dm_history.py')]
        
        if args.interactive:
            token = self.get_token_interactively()
            
            print("\n💬 DM Channel Information")
            print("You'll need the DM channel ID. Run 'list' operation first if you don't know it.")
            channel = input("Enter DM channel ID (e.g., D0889Q50GPM): ").strip()
            
            if not channel:
                print("❌ Channel ID is required")
                return 1
            
            output = self.get_output_file_interactively('dm')
            
            print("\n📅 Date Range")
            since = input("Start date (YYYY-MM-DD, default: 2025-01-01): ").strip()
            if not since:
                since = '2025-01-01'
            
            cmd.extend(['-t', token, '-c', channel, '-o', output, '-s', since])
        else:
            if not args.token or not args.channel:
                print("❌ Error: --token and --channel are required for DM export")
                return 1
            
            cmd.extend(['-t', args.token, '-c', args.channel])
            
            if args.output:
                cmd.extend(['-o', args.output])
            
            if args.since:
                cmd.extend(['-s', args.since])
        
        print(f"\n🚀 Running: {' '.join(cmd[2:])}")
        return subprocess.run(cmd).returncode
    
    def run_channel(self, args) -> int:
        """Run channel export."""
        cmd = ['python3', os.path.join(self.script_dir, 'fetch_channel_search.py')]
        
        if args.interactive:
            token = self.get_token_interactively()
            
            print("\n📺 Channel Information")
            print("Enter the channel name (e.g., #general) or ID")
            channel = input("Channel name/ID: ").strip()
            
            if not channel:
                print("❌ Channel name/ID is required")
                return 1
            
            # Build query for channel
            if channel.startswith('#'):
                query = f"in:{channel}"
            elif channel.startswith('C'):  # Channel ID
                query = f"in:#{channel}"  # Let Slack handle ID lookup
            else:
                query = f"in:#{channel}"  # Assume it's a channel name
            
            output = self.get_output_file_interactively('channel')
            
            # Ask about monthly chunks for complete history
            use_chunks = input("\nUse monthly chunks for complete history? (y/N): ").strip().lower()
            
            cmd.extend(['-t', token, '-q', query, '-o', output])
            
            if use_chunks == 'y':
                cmd.append('--monthly-chunks')
        else:
            if not args.token or not args.query:
                print("❌ Error: --token and --query are required for channel export")
                return 1
            
            cmd.extend(['-t', args.token, '-q', args.query])
            
            if args.output:
                cmd.extend(['-o', args.output])
            
            if args.monthly_chunks:
                cmd.append('--monthly-chunks')
            
            if args.max_results:
                cmd.extend(['-m', str(args.max_results)])
        
        print(f"\n🚀 Running: {' '.join(cmd[2:])}")
        return subprocess.run(cmd).returncode
    
    def run_search(self, args) -> int:
        """Run search export."""
        cmd = ['python3', os.path.join(self.script_dir, 'fetch_channel_search.py')]
        
        if args.interactive:
            token = self.get_token_interactively()
            
            print("\n🔍 Search Query")
            print("Examples:")
            print("  from:@username              - Messages from specific user")
            print("  has:attachment               - Messages with attachments") 
            print("  in:#channel project         - Messages in channel containing 'project'")
            print("  after:2024-01-01            - Messages after date")
            print()
            
            query = input("Enter search query: ").strip()
            
            if not query:
                print("❌ Search query is required")
                return 1
            
            output = self.get_output_file_interactively('search')
            
            # Ask about options
            max_results = input("Max results (default: 100): ").strip()
            use_chunks = input("Use monthly chunks for complete history? (y/N): ").strip().lower()
            
            cmd.extend(['-t', token, '-q', query, '-o', output])
            
            if max_results and max_results.isdigit():
                cmd.extend(['-m', max_results])
            
            if use_chunks == 'y':
                cmd.append('--monthly-chunks')
        else:
            if not args.token or not args.query:
                print("❌ Error: --token and --query are required for search")
                return 1
            
            cmd.extend(['-t', args.token, '-q', args.query])
            
            if args.output:
                cmd.extend(['-o', args.output])
            
            if args.max_results:
                cmd.extend(['-m', str(args.max_results)])
            
            if args.monthly_chunks:
                cmd.append('--monthly-chunks')
        
        print(f"\n🚀 Running: {' '.join(cmd[2:])}")
        return subprocess.run(cmd).returncode
    
    def run_list(self, args) -> int:
        """Run channel/DM listing."""
        cmd = ['python3', os.path.join(self.script_dir, 'list_conversations.py')]
        
        if args.interactive:
            token = self.get_token_interactively()
            cmd.append(token)
        else:
            if not args.token:
                print("❌ Error: --token is required for listing")
                return 1
            cmd.append(args.token)
        
        print(f"\n🚀 Running: {' '.join(cmd[2:])}")
        return subprocess.run(cmd).returncode


def create_parser():
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        description='Unified Slack Export CLI - Export DMs, channels, bookmarks and more',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (recommended)
  python slack.py

  # Export bookmarks directly
  python slack.py bookmarks -t "xoxp-token" -o bookmarks.md

  # Export DM conversation  
  python slack.py dm -t "xoxp-token" -c D0889Q50GPM --since 2024-01-01

  # Export channel with complete history
  python slack.py channel -t "xoxp-token" -q "in:#general" --monthly-chunks

  # Search for messages
  python slack.py search -t "xoxp-token" -q "from:@username has:attachment"

  # List all channels and DMs
  python slack.py list -t "xoxp-token"

Interactive mode will guide you through the process step by step.
        """
    )
    
    # Main operation (optional for interactive mode)
    parser.add_argument('operation', nargs='?', 
                       choices=['bookmarks', 'dm', 'channel', 'search', 'list'],
                       help='What to export (omit for interactive mode)')
    
    # Common arguments
    parser.add_argument('-t', '--token', 
                       help='Slack User OAuth Token (starts with xoxp-)')
    parser.add_argument('-o', '--output',
                       help='Output file path')
    parser.add_argument('-i', '--interactive', action='store_true',
                       help='Force interactive mode even when operation is specified')
    
    # DM-specific arguments
    parser.add_argument('-c', '--channel',
                       help='DM channel ID (for dm operation)')
    parser.add_argument('-s', '--since',
                       help='Start date YYYY-MM-DD (for dm operation)')
    
    # Search/Channel arguments  
    parser.add_argument('-q', '--query',
                       help='Search query or channel specification')
    parser.add_argument('-m', '--max-results', type=int,
                       help='Maximum number of results')
    parser.add_argument('--monthly-chunks', action='store_true',
                       help='Use monthly chunks for complete history')
    
    # Bookmarks arguments
    parser.add_argument('--page-size', type=int,
                       help='Page size for bookmarks fetching')
    
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    
    cli = SlackCLI()
    
    # Determine operation
    if not args.operation or args.interactive:
        operation = cli.show_interactive_menu()
    else:
        operation = args.operation
    
    # Route to appropriate handler
    if operation == 'bookmarks':
        return cli.run_bookmarks(args)
    elif operation == 'dm':
        return cli.run_dm(args)
    elif operation == 'channel':
        return cli.run_channel(args)
    elif operation == 'search':
        return cli.run_search(args)
    elif operation == 'list':
        return cli.run_list(args)
    else:
        print(f"❌ Unknown operation: {operation}")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user. Goodbye! 👋")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
