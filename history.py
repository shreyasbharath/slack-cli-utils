#!/usr/bin/env python3
"""
Fetch Slack DM history using conversations.history API with standardized logging and progress tracking
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import our standardized utilities
from utils import SlackExporter, format_timestamp, sanitize_dirname


class SlackDMFetcher(SlackExporter):
    """Fetches DM conversation history from Slack."""

    def __init__(self, token: str, download_dir: Optional[str] = None):
        super().__init__(token, "DMFetcher")
        self.download_dir = download_dir
        
    def fetch_and_export(self, channel_id: str, output_file: str, since_date: str = "2025-01-01") -> int:
        """Fetch and save messages incrementally with progress tracking"""
        start_time = datetime.now()
        
        # Convert date to timestamp
        try:
            since_ts = datetime.strptime(since_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            self.logger.error(f"Invalid date format: {since_date}. Use YYYY-MM-DD")
            return 0
        
        self.logger.info(f"📋 Fetching messages from channel {channel_id} since {since_date}")
        self.logger.info(f"📁 Output file: {output_file}")
        
        # First pass: collect all messages for accurate progress tracking
        all_messages = self._collect_all_messages(channel_id, since_ts)
        
        if not all_messages:
            self.logger.warning("No messages found!")
            return 0
        
        total_count = len(all_messages)
        self.logger.success(f"Found {total_count:,} messages to process")

        # Write messages to file with progress tracking
        self._write_messages_to_file(all_messages, channel_id, since_date, output_file, self.download_dir)
        
        # Summary
        export_time = (datetime.now() - start_time).total_seconds()
        self.export_summary(output_file, total_count, export_time)
        
        return total_count
    
    def _collect_all_messages(self, channel_id: str, since_ts: float) -> List[Dict[str, Any]]:
        """Collect all messages first for accurate progress tracking"""
        
        self.logger.phase(1, "Collecting all messages")
        
        all_messages = []
        cursor = None
        page_num = 1
        
        while True:
            self.logger.api_call("conversations.history", page=page_num)
            
            params = {
                'channel': channel_id,
                'limit': 200,  # Max per request
                'oldest': str(since_ts)
            }
            if cursor:
                params['cursor'] = cursor
            
            data = self.make_api_request("https://slack.com/api/conversations.history", params)
            if not data:
                break
            
            messages = data.get('messages', [])
            if not messages:
                self.logger.info("No more messages found", indent=1)
                break
            
            all_messages.extend(messages)
            self.logger.progress(len(all_messages), len(all_messages), f"Collected {len(messages)} messages from page {page_num}")
            
            # Check for more pages
            if not data.get('has_more', False):
                break
                
            cursor = data.get('response_metadata', {}).get('next_cursor')
            if not cursor:
                break
            
            page_num += 1
        
        # Sort messages by timestamp (oldest first)
        all_messages.sort(key=lambda x: float(x.get('ts', 0)))
        
        return all_messages
    
    def _write_messages_to_file(self, messages: List[Dict[str, Any]], channel_id: str, since_date: str, output_file: str, download_dir: Optional[str] = None):
        """Write messages to file with progress tracking"""

        # Download files if directory specified
        if download_dir:
            self.logger.phase(2, f"Downloading and writing {len(messages):,} messages to file")
        else:
            self.logger.phase(2, f"Writing {len(messages):,} messages to file")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"# DM Conversation History\n\n")
            f.write(f"**Channel ID:** {channel_id}\n")
            f.write(f"**Messages since:** {since_date}\n")
            f.write(f"**Export date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total messages:** {len(messages)}\n\n")
            f.write("---\n\n")
            
            # Write messages
            for i, message in enumerate(messages, 1):
                f.write(f"## Message {i}\n\n")
                f.write(f"**User:** {message.get('user', 'Unknown')}\n")
                f.write(f"**Date:** {format_timestamp(message.get('ts', ''))}\n")
                f.write(f"**Timestamp:** {message.get('ts', '')}\n\n")
                
                # Message content
                f.write("**Message:**\n\n")
                text = message.get('text', '')
                if text:
                    f.write(f"{text}\n\n")
                else:
                    f.write("*(No text content)*\n\n")
                
                # Files and attachments
                files = message.get('files', [])
                if files:
                    # Download files if directory specified
                    if download_dir:
                        self.download_message_files(message, download_dir, "dm")

                    f.write(f"**Files:** {len(files)} file(s)\n")
                    for file_info in files:
                        name = file_info.get('name', 'Unknown file')
                        local_path = file_info.get('local_path')
                        if local_path:
                            f.write(f"- {name}\n")
                            f.write(f"  - Downloaded: {local_path}\n")
                            url = file_info.get('url_private', file_info.get('permalink', ''))
                            f.write(f"  - Original URL: {url}\n")
                        else:
                            url = file_info.get('url_private', file_info.get('permalink', ''))
                            f.write(f"- {name}: {url}\n")
                    f.write("\n")
                
                attachments = message.get('attachments', [])
                if attachments:
                    f.write(f"**Attachments:** {len(attachments)} attachment(s)\n")
                    for att in attachments:
                        title = att.get('title', att.get('fallback', 'Attachment'))
                        f.write(f"- {title}\n")
                    f.write("\n")
                
                # Reactions
                reactions = message.get('reactions', [])
                if reactions:
                    f.write("**Reactions:**\n")
                    for reaction in reactions:
                        name = reaction.get('name', '')
                        count = reaction.get('count', 0)
                        f.write(f"- :{name}: ({count})\n")
                    f.write("\n")
                
                # Thread info
                if message.get('thread_ts'):
                    f.write(f"**Thread:** Part of thread {message.get('thread_ts')}\n")
                    if message.get('reply_count', 0) > 0:
                        f.write(f" - {message.get('reply_count')} replies\n")
                    f.write("\n")
                
                f.write("---\n\n")
                
                # Update progress
                self.logger.progress(i, len(messages), f"Writing message {i}")
        
        self.logger.success(f"Messages written to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Fetch Slack DM conversation history',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python history.py -t "xoxp-token" -c D0889Q50GPM
  python history.py -t "xoxp-token" -c D0889Q50GPM -s 2024-01-01
  python history.py -t "xoxp-token" -c D0889Q50GPM -o conversation.md

Required Slack API scopes:
  - im:history (for direct messages)
  - groups:history (for private channels)
  - channels:history (for public channels)
  - mpim:history (for group DMs)
        """
    )
    
    parser.add_argument('-t', '--token', required=True,
                        help='Slack User OAuth Token (starts with xoxp-)')
    parser.add_argument('-c', '--channel', required=True,
                        help='DM channel ID (e.g., D0889Q50GPM)')
    parser.add_argument('-s', '--since', default='2025-01-01',
                        help='Start date in YYYY-MM-DD format (default: 2025-01-01)')
    parser.add_argument('-o', '--output',
                        help='Output file path (default: dm_<channel>_<timestamp>.md)')
    parser.add_argument('--download-attachments', action='store_true',
                        help='Download attachment files to disk')
    parser.add_argument('--attachments-dir', type=str,
                        help='Directory for downloaded attachments (default: <output>_attachments)')
    
    args = parser.parse_args()

    # Default output filename
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'dm_{args.channel}_{timestamp}.md'

    # Determine download directory
    download_dir = None
    if args.download_attachments:
        if args.attachments_dir:
            download_dir = args.attachments_dir
        else:
            # Default: output_name_attachments
            base_name = Path(args.output).stem
            download_dir = f'{base_name}_attachments'

    try:
        fetcher = SlackDMFetcher(args.token, download_dir)
        message_count = fetcher.fetch_and_export(args.channel, args.output, args.since)
        
        if message_count > 0:
            print(f"\n🎉 Successfully exported {message_count} messages to {args.output}")
            return 0
        else:
            print(f"\n⚠️  No messages found or export failed")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Export interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
