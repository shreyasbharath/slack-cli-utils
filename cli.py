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


class InteractivePrompts:
    """Handles all user input prompts."""
    
    @staticmethod
    def get_token() -> str:
        """Get Slack token from user."""
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
    
    @staticmethod
    def get_output_filename(operation: str, extension: str = 'md') -> str:
        """Get output filename from user."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"slack_{operation}_{timestamp}.{extension}"
        
        print(f"\n📁 Output File")
        filename = input(f"Output filename (default: {default_name}): ").strip()
        
        return filename if filename else default_name
    
    @staticmethod
    def get_channel_id() -> str:
        """Get DM channel ID from user."""
        print("\n💬 DM Channel Information")
        print("You'll need the DM channel ID. Run 'list' operation first if you don't know it.")
        
        while True:
            channel = input("Enter DM channel ID (e.g., D0889Q50GPM): ").strip()
            if channel:
                return channel
            print("❌ Channel ID is required")
    
    @staticmethod
    def get_date_range() -> str:
        """Get start date for DM export."""
        print("\n📅 Date Range")
        since = input("Start date (YYYY-MM-DD, default: 2025-01-01): ").strip()
        return since if since else '2025-01-01'
    
    @staticmethod
    def get_channel_query() -> str:
        """Get channel information and build query."""
        print("\n📺 Channel Information")
        print("Enter the channel name (e.g., #general) or ID")
        
        while True:
            channel = input("Channel name/ID: ").strip()
            if not channel:
                print("❌ Channel name/ID is required")
                continue
            
            if channel.startswith('#'):
                return f"in:{channel}"
            elif channel.startswith('C'):
                return f"in:#{channel}"
            else:
                return f"in:#{channel}"
    
    @staticmethod
    def get_search_query() -> str:
        """Get search query from user with examples."""
        print("\n🔍 Search Query")
        print("Examples:")
        print("  from:@john.smith                        - ALL messages from user using Slack handle")
        print("  from:@john.smith after:2025-09-01       - User messages since Sept 1, 2025")
        print("  from:U123456789                         - Alternative: use user ID")
        print("  has:attachment                          - Messages with attachments")
        print("  in:#channel project                     - Messages in channel containing 'project'")
        print()
        
        while True:
            query = input("Enter search query: ").strip()
            if query:
                return query
            print("❌ Search query is required")
    
    @staticmethod
    def get_page_size() -> Optional[str]:
        """Get page size with validation."""
        page_size = input("\nPage size for fetching (default: 100): ").strip()
        return page_size if page_size and page_size.isdigit() else None
    
    @staticmethod
    def get_max_results() -> Optional[str]:
        """Get max results with validation."""
        max_results = input("Max results (default: 100): ").strip()
        return max_results if max_results and max_results.isdigit() else None
    
    @staticmethod
    def use_monthly_chunks() -> bool:
        """Ask if user wants monthly chunks."""
        response = input("\nUse monthly chunks for complete history? (y/N): ").strip().lower()
        return response == 'y'


class MenuDisplay:
    """Handles menu display and user choice selection."""
    
    @staticmethod
    def show_main_menu() -> str:
        """Display main menu and return selected operation."""
        print("\n🚀 Slack Export Tool")
        print("=" * 50)
        print("What would you like to export?")
        print()
        print("1. 📌 Saved Messages (Later)")
        print("   Export all messages you've saved for later across all channels")
        print("2. 💬 Direct Messages (DMs)")
        print("   Export conversation history from a specific DM")
        print("3. 📺 Channel Messages")
        print("   Export all messages from a specific channel")
        print("4. 🔍 Search Messages")
        print("   Search and export messages using Slack's search syntax")
        print("5. 📋 List Channels/DMs")
        print("   Show all available channels and DMs with their IDs")
        print("6. ❌ Exit")
        print()
        
        return MenuDisplay._get_user_choice()
    
    @staticmethod
    def _get_user_choice() -> str:
        """Get and validate user menu choice."""
        choice_map = {
            '1': 'later',
            '2': 'dm', 
            '3': 'channel',
            '4': 'search',
            '5': 'list',
            '6': 'exit'
        }
        
        while True:
            try:
                choice = input("Enter your choice (1-6): ").strip()
                if choice == '6':
                    print("Goodbye! 👋")
                    sys.exit(0)
                elif choice in choice_map:
                    return choice_map[choice]
                else:
                    print("❌ Invalid choice. Please enter 1-6.")
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                sys.exit(0)


class CommandBuilder:
    """Builds command arguments for subprocess execution."""
    
    def __init__(self, script_dir: str):
        self.script_dir = script_dir
        
        # Map operations to their corresponding scripts
        self.operation_scripts = {
            'later': 'later.py',
            'dm': 'history.py', 
            'channel': 'search.py',
            'search': 'search.py',
            'list': 'list.py'
        }
    
    def build_base_command(self, operation: str) -> List[str]:
        """Build base command with script path."""
        script_name = self.operation_scripts[operation]
        return ['python3', os.path.join(self.script_dir, script_name)]
    
    def add_common_params(self, cmd: List[str], token: str, output: str) -> None:
        """Add common token and output parameters."""
        cmd.extend(['-t', token, '-o', output])
    
    def add_optional_param(self, cmd: List[str], flag: str, value: Optional[str]) -> None:
        """Add optional parameter if value exists."""
        if value:
            cmd.extend([flag, value])
    
    def add_flag_if_true(self, cmd: List[str], flag: str, condition: bool) -> None:
        """Add flag if condition is true."""
        if condition:
            cmd.append(flag)


class OperationHandler:
    """Handles execution of specific Slack export operations."""
    
    def __init__(self, script_dir: str):
        self.script_dir = script_dir
        self.prompts = InteractivePrompts()
        self.cmd_builder = CommandBuilder(script_dir)
    
    def should_run_interactively(self, args, required_params: List[str]) -> bool:
        """Determine if operation should run in interactive mode."""
        if args.interactive:
            return True
        
        return any(not getattr(args, param, None) for param in required_params)
    
    def execute_command(self, cmd: List[str]) -> int:
        """Execute command and return exit code."""
        print(f"\n🚀 Running: {' '.join(cmd[2:])}")
        return subprocess.run(cmd).returncode
    
    def run_later_export(self, args) -> int:
        """Run saved messages (bookmarks) export."""
        cmd = self.cmd_builder.build_base_command('later')
        
        if self.should_run_interactively(args, ['token']):
            return self._run_later_interactive(cmd)
        else:
            return self._run_later_direct(cmd, args)
    
    def _run_later_interactive(self, cmd: List[str]) -> int:
        """Run bookmarks export interactively."""
        token = self.prompts.get_token()
        output = self.prompts.get_output_filename('bookmarks')
        
        self.cmd_builder.add_common_params(cmd, token, output)
        
        page_size = self.prompts.get_page_size()
        self.cmd_builder.add_optional_param(cmd, '--page-size', page_size)
        
        return self.execute_command(cmd)
    
    def _run_later_direct(self, cmd: List[str], args) -> int:
        """Run bookmarks export with direct arguments."""
        if not args.token:
            print("❌ Error: --token is required for bookmarks export")
            return 1
        
        cmd.extend(['-t', args.token])
        self.cmd_builder.add_optional_param(cmd, '-o', args.output)
        
        if args.page_size:
            cmd.extend(['--page-size', str(args.page_size)])
        
        return self.execute_command(cmd)
    
    def run_dm_export(self, args) -> int:
        """Run DM export."""
        cmd = self.cmd_builder.build_base_command('dm')
        
        if self.should_run_interactively(args, ['token', 'channel']):
            return self._run_dm_interactive(cmd)
        else:
            return self._run_dm_direct(cmd, args)
    
    def _run_dm_interactive(self, cmd: List[str]) -> int:
        """Run DM export interactively."""
        token = self.prompts.get_token()
        channel = self.prompts.get_channel_id()
        output = self.prompts.get_output_filename('dm')
        since = self.prompts.get_date_range()
        
        cmd.extend(['-t', token, '-c', channel, '-o', output, '-s', since])
        
        return self.execute_command(cmd)
    
    def _run_dm_direct(self, cmd: List[str], args) -> int:
        """Run DM export with direct arguments."""
        if not args.token or not args.channel:
            print("❌ Error: --token and --channel are required for DM export")
            return 1
        
        cmd.extend(['-t', args.token, '-c', args.channel])
        self.cmd_builder.add_optional_param(cmd, '-o', args.output)
        self.cmd_builder.add_optional_param(cmd, '-s', args.since)
        
        return self.execute_command(cmd)
    
    def run_channel_export(self, args) -> int:
        """Run channel export."""
        cmd = self.cmd_builder.build_base_command('channel')
        
        if self.should_run_interactively(args, ['token', 'query']):
            return self._run_channel_interactive(cmd)
        else:
            return self._run_channel_direct(cmd, args)
    
    def _run_channel_interactive(self, cmd: List[str]) -> int:
        """Run channel export interactively."""
        token = self.prompts.get_token()
        query = self.prompts.get_channel_query()
        output = self.prompts.get_output_filename('channel')
        use_chunks = self.prompts.use_monthly_chunks()
        
        self.cmd_builder.add_common_params(cmd, token, output)
        cmd.extend(['-q', query])
        self.cmd_builder.add_flag_if_true(cmd, '--monthly-chunks', use_chunks)
        
        return self.execute_command(cmd)
    
    def _run_channel_direct(self, cmd: List[str], args) -> int:
        """Run channel export with direct arguments."""
        if not args.token or not args.query:
            print("❌ Error: --token and --query are required for channel export")
            return 1
        
        cmd.extend(['-t', args.token, '-q', args.query])
        self.cmd_builder.add_optional_param(cmd, '-o', args.output)
        self.cmd_builder.add_flag_if_true(cmd, '--monthly-chunks', args.monthly_chunks)
        
        if args.max_results:
            cmd.extend(['-m', str(args.max_results)])
        
        return self.execute_command(cmd)
    
    def run_search_export(self, args) -> int:
        """Run search export."""
        cmd = self.cmd_builder.build_base_command('search')
        
        if self.should_run_interactively(args, ['token', 'query']):
            return self._run_search_interactive(cmd)
        else:
            return self._run_search_direct(cmd, args)
    
    def _run_search_interactive(self, cmd: List[str]) -> int:
        """Run search export interactively."""
        token = self.prompts.get_token()
        query = self.prompts.get_search_query()
        output = self.prompts.get_output_filename('search')
        
        self.cmd_builder.add_common_params(cmd, token, output)
        cmd.extend(['-q', query])
        
        max_results = self.prompts.get_max_results()
        self.cmd_builder.add_optional_param(cmd, '-m', max_results)
        
        use_chunks = self.prompts.use_monthly_chunks()
        self.cmd_builder.add_flag_if_true(cmd, '--monthly-chunks', use_chunks)
        
        return self.execute_command(cmd)
    
    def _run_search_direct(self, cmd: List[str], args) -> int:
        """Run search export with direct arguments."""
        if not args.token or not args.query:
            print("❌ Error: --token and --query are required for search")
            return 1
        
        cmd.extend(['-t', args.token, '-q', args.query])
        self.cmd_builder.add_optional_param(cmd, '-o', args.output)
        
        if args.max_results:
            cmd.extend(['-m', str(args.max_results)])
        
        self.cmd_builder.add_flag_if_true(cmd, '--monthly-chunks', args.monthly_chunks)
        
        return self.execute_command(cmd)
    
    def run_list_operation(self, args) -> int:
        """Run channel/DM listing."""
        cmd = self.cmd_builder.build_base_command('list')
        
        if self.should_run_interactively(args, ['token']):
            token = self.prompts.get_token()
            cmd.extend(['-t', token])
        else:
            if not args.token:
                print("❌ Error: --token is required for listing")
                return 1
            cmd.extend(['-t', args.token])
        
        return self.execute_command(cmd)


class SlackCLI:
    """Main CLI coordinator class."""
    
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.handler = OperationHandler(self.script_dir)
        self.menu = MenuDisplay()
    
    def run(self, args) -> int:
        """Main entry point for CLI execution."""
        operation = self._determine_operation(args)
        
        # Route to appropriate handler
        operation_map = {
            'later': self.handler.run_later_export,
            'dm': self.handler.run_dm_export,
            'channel': self.handler.run_channel_export,
            'search': self.handler.run_search_export,
            'list': self.handler.run_list_operation
        }
        
        if operation in operation_map:
            return operation_map[operation](args)
        else:
            print(f"❌ Unknown operation: {operation}")
            return 1
    
    def _determine_operation(self, args) -> str:
        """Determine which operation to run."""
        if not args.operation or args.interactive:
            return self.menu.show_main_menu()
        return args.operation



def create_parser():
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        description='Unified Slack Export CLI - Export DMs, channels, bookmarks and more',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (recommended)
  python slack.py

  # Export saved messages directly
  python slack.py later -t "xoxp-token" -o saved_messages.md

  # Export DM conversation  
  python slack.py dm -t "xoxp-token" -c D0889Q50GPM --since 2024-01-01

  # Export channel with complete history
  python slack.py channel -t "xoxp-token" -q "in:#general" --monthly-chunks

  # Search for messages from user
  python slack.py search -t "xoxp-token" -q "from:@john.smith" --monthly-chunks

  # List all channels and DMs
  python slack.py list -t "xoxp-token"

Interactive mode will guide you through the process step by step.
        """
    )
    
    # Main operation (optional for interactive mode)
    parser.add_argument('operation', nargs='?', 
                       choices=['later', 'dm', 'channel', 'search', 'list'],
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
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    cli = SlackCLI()
    return cli.run(args)


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
