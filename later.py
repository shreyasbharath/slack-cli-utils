#!/usr/bin/env python3
"""
Slack Later/Saved Messages Fetcher

Fetches all "Save for Later" messages from Slack with full context including
channel names, user names, attachments, and reactions.
"""

import json
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import our standardized utilities
from utils import SlackExporter, format_timestamp, get_user_name, get_channel_name


class SlackLaterFetcher(SlackExporter):
    """Fetches Slack 'Save for Later' messages."""
    
    def __init__(self, token: str):
        super().__init__(token, "LaterFetcher")
        self.user_cache = {}
        self.channel_cache = {}
    
    def fetch_saved_messages(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """Fetch all saved messages using the search API with 'is:saved' query."""
        self.logger.phase(1, "Fetching saved for later messages")
        
        all_saved = []
        page = 1
        
        while True:
            params = {
                'query': 'is:saved',
                'count': page_size,
                'page': page
            }
            
            self.logger.api_call("search.messages", page=page)
            data = self.make_api_request('https://slack.com/api/search.messages', params)
            
            if not data:
                break
            
            messages_data = data.get('messages', {})
            matches = messages_data.get('matches', [])
            
            if not matches:
                self.logger.info("No more saved messages found", indent=1)
                break
            
            all_saved.extend(matches)
            total = messages_data.get('total', len(all_saved))
            self.logger.progress(len(all_saved), total, f"Found {len(matches)} messages on page {page}")
            
            # Check if we have more pages
            total_pages = messages_data.get('paging', {}).get('pages', 1)
            if page >= total_pages:
                break
            
            page += 1
        
        self.logger.success(f"Found {len(all_saved)} saved messages")
        return all_saved
    
    def enrich_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich messages with user names, channel names, and other metadata."""
        if not messages:
            return messages
        
        self.logger.phase(2, f"Enriching {len(messages)} messages")
        
        enriched_messages = []
        
        for i, message in enumerate(messages):
            try:
                # Get user and channel information
                user_id = message.get('user', '')
                channel_info = message.get('channel', {})
                
                if isinstance(channel_info, dict):
                    channel_id = channel_info.get('id', '')
                    channel_name = channel_info.get('name', '')
                    if channel_name and not channel_name.startswith('#'):
                        channel_name = f"#{channel_name}"
                else:
                    channel_id = str(channel_info) if channel_info else ''
                    channel_name = get_channel_name(self.channel_cache, channel_id, self.session) if channel_id else 'Unknown Channel'
                
                user_name = get_user_name(self.user_cache, user_id, self.session) if user_id else 'Unknown User'
                
                # Create enriched message
                enriched_message = {
                    'message_date': message.get('ts', ''),
                    'channel_id': channel_id,
                    'channel_name': channel_name,
                    'user_id': user_id,
                    'user_name': user_name,
                    'username': message.get('username', ''),  # Display name from search
                    'text': message.get('text', ''),
                    'permalink': message.get('permalink', ''),
                    'attachments': message.get('attachments', []),
                    'blocks': message.get('blocks', []),
                    'files': message.get('files', []),
                    'reactions': message.get('reactions', []),
                    'thread_ts': message.get('thread_ts', ''),
                    'raw_message': message  # Keep original for reference
                }
                
                enriched_messages.append(enriched_message)
                
                # Update progress
                self.logger.progress(i + 1, len(messages), f"Processing message {i + 1}")
                
            except Exception as e:
                self.logger.warning(f"Error enriching message {i + 1}: {e}", indent=1)
                continue
        
        self.logger.success(f"Enriched {len(enriched_messages)} messages")
        return enriched_messages
    
    def export_to_markdown(self, messages: List[Dict[str, Any]], output_file: str):
        """Export messages to Markdown format."""
        self.logger.phase(3, f"Exporting to Markdown: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Header
            f.write("# Slack Saved Messages (Later)\n\n")
            f.write(f"**Export date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total saved messages:** {len(messages)}\n\n")
            f.write("---\n\n")
            
            # Messages
            for i, msg in enumerate(messages, 1):
                f.write(f"## Saved Message {i}\n\n")
                
                # Metadata
                f.write(f"**Message Date:** {format_timestamp(msg['message_date'])}\n")
                f.write(f"**Channel:** {msg['channel_name']} ({msg['channel_id']})\n")
                f.write(f"**User:** {msg['user_name']}")
                if msg['username'] and msg['username'] != msg['user_name']:
                    f.write(f" (@{msg['username']})")
                f.write(f" ({msg['user_id']})\n")
                
                if msg['permalink']:
                    f.write(f"**Permalink:** {msg['permalink']}\n")
                
                f.write("\n**Message:**\n\n")
                f.write(f"{msg['text']}\n\n")
                
                # Attachments
                if msg['attachments']:
                    f.write(f"**Attachments:** {len(msg['attachments'])} attachment(s)\n")
                    for att in msg['attachments']:
                        title = att.get('title', att.get('fallback', 'Attachment'))
                        f.write(f"- {title}\n")
                    f.write("\n")
                
                # Files
                if msg['files']:
                    f.write(f"**Files:** {len(msg['files'])} file(s)\n")
                    for file_info in msg['files']:
                        name = file_info.get('name', 'Unknown file')
                        url = file_info.get('url_private', file_info.get('permalink', ''))
                        f.write(f"- {name}: {url}\n")
                    f.write("\n")
                
                # Blocks (rich content)
                if msg['blocks']:
                    f.write(f"**Rich Content:** {len(msg['blocks'])} block(s)\n\n")
                
                # Thread info
                if msg['thread_ts']:
                    f.write(f"**Thread:** Part of thread {msg['thread_ts']}\n\n")
                
                f.write("---\n\n")
                
                # Update progress
                self.logger.progress(i, len(messages), f"Writing message {i}")
        
        self.logger.success(f"Exported to {output_file}")
    
    def export_to_json(self, messages: List[Dict[str, Any]], output_file: str):
        """Export messages to JSON format."""
        self.logger.phase(3, f"Exporting to JSON: {output_file}")
        
        export_data = {
            'export_date': datetime.now().isoformat(),
            'total_saved_messages': len(messages),
            'messages': messages
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        self.logger.success(f"Exported to {output_file}")
    
    def fetch_and_export(self, output_file: str, page_size: int = 100):
        """Main method to fetch and export saved messages."""
        start_time = datetime.now()
        
        try:
            # Fetch saved messages
            saved_messages = self.fetch_saved_messages(page_size)
            
            if not saved_messages:
                self.logger.warning("No saved messages found")
                return 0
            
            # Enrich messages
            enriched_messages = self.enrich_messages(saved_messages)
            
            # Sort by message date (most recent first)
            enriched_messages.sort(key=lambda x: float(x.get('message_date', 0)), reverse=True)
            
            # Export based on file extension
            if output_file.endswith('.json'):
                self.export_to_json(enriched_messages, output_file)
            else:
                self.export_to_markdown(enriched_messages, output_file)
            
            # Summary
            export_time = (datetime.now() - start_time).total_seconds()
            self.export_summary(output_file, len(enriched_messages), export_time)
            
            return len(enriched_messages)
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            return 0


def main():
    parser = argparse.ArgumentParser(
        description='Fetch Slack saved messages (Save for Later)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python later.py -t "xoxp-token" -o saved_messages.md
  python later.py -t "xoxp-token" -o saved_messages.json --page-size 50

This tool fetches messages you've saved using Slack's "Save for Later" feature.

Required Slack API scopes:
  - search:read (to search for saved messages)
  - channels:read (to get channel names)  
  - users:read (to get user names)
        """
    )
    
    parser.add_argument('-t', '--token', required=True,
                        help='Slack User OAuth Token (starts with xoxp-)')
    parser.add_argument('-o', '--output', 
                        help='Output file path (default: saved_messages_<timestamp>.md)')
    parser.add_argument('--page-size', type=int, default=100,
                        help='Messages per API call (default: 100)')
    
    args = parser.parse_args()
    
    # Default output filename
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'saved_messages_{timestamp}.md'
    
    try:
        fetcher = SlackLaterFetcher(args.token)
        message_count = fetcher.fetch_and_export(args.output, args.page_size)
        
        if message_count > 0:
            print(f"\n🎉 Successfully exported {message_count} saved messages to {args.output}")
            return 0
        else:
            print(f"\n⚠️  No saved messages found or export failed")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Export interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
