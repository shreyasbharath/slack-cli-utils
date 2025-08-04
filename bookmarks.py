#!/usr/bin/env python3
"""
Slack Bookmarks/Starred Messages Fetcher

Fetches all starred/bookmarked messages from Slack with full context including
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


class SlackBookmarksFetcher(SlackExporter):
    """Fetches starred/bookmarked messages from Slack."""
    
    def __init__(self, token: str):
        super().__init__(token, "BookmarksFetcher")
        self.user_cache = {}
        self.channel_cache = {}
    
    def fetch_starred_messages(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """Fetch all starred messages using the stars.list API."""
        self.logger.phase(1, "Fetching starred messages")
        
        all_starred = []
        page = 1
        cursor = None
        
        while True:
            params = {'limit': page_size}
            if cursor:
                params['cursor'] = cursor
            
            self.logger.api_call("stars.list", page=page)
            data = self.make_api_request('https://slack.com/api/stars.list', params)
            
            if not data:
                break
            
            items = data.get('items', [])
            if not items:
                self.logger.info("No more starred items found", indent=1)
                break
            
            # Filter for messages only (skip files, channels, etc.)
            messages = [item for item in items if item.get('type') == 'message']
            if messages:
                all_starred.extend(messages)
                self.logger.progress(len(all_starred), len(all_starred), f"Found {len(messages)} messages on page {page}")
            
            # Check for pagination
            if not data.get('paging', {}).get('page'):
                break
            
            page_info = data.get('paging', {})
            if page >= page_info.get('pages', 1):
                break
            
            cursor = data.get('response_metadata', {}).get('next_cursor')
            if not cursor:
                break
            
            page += 1
        
        self.logger.success(f"Found {len(all_starred)} starred messages")
        return all_starred
    
    def fetch_saved_messages(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """Fetch saved for later messages using search API."""
        self.logger.phase(2, "Fetching saved messages")
        
        all_saved = []
        page = 1
        
        while True:
            params = {
                'query': 'in:@saved',
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
            
            # Convert search results to standard message format
            converted_messages = []
            for match in matches:
                # Extract the message data
                message_data = {
                    'type': 'message',
                    'message': match,
                    'date_create': match.get('ts', ''),
                    'channel': match.get('channel', {}).get('id', ''),
                }
                converted_messages.append(message_data)
            
            all_saved.extend(converted_messages)
            self.logger.progress(len(all_saved), len(all_saved), f"Found {len(matches)} messages on page {page}")
            
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
        
        self.logger.phase(3, f"Enriching {len(messages)} messages")
        
        enriched_messages = []
        
        for i, item in enumerate(messages):
            try:
                # Extract message data based on source (starred vs saved)
                if 'message' in item:
                    message = item['message']
                    channel_id = item.get('channel', message.get('channel', ''))
                    bookmark_date = item.get('date_create', '')
                else:
                    # This shouldn't happen with current APIs but keeping for safety
                    message = item
                    channel_id = message.get('channel', '')
                    bookmark_date = ''
                
                # Get user and channel names
                user_id = message.get('user', '')
                user_name = get_user_name(self.user_cache, user_id, self.session) if user_id else 'Unknown User'
                channel_name = get_channel_name(self.channel_cache, channel_id, self.session) if channel_id else 'Unknown Channel'
                
                # Create enriched message
                enriched_message = {
                    'bookmark_date': bookmark_date,
                    'message_date': message.get('ts', ''),
                    'channel_id': channel_id,
                    'channel_name': channel_name,
                    'user_id': user_id,
                    'user_name': user_name,
                    'text': message.get('text', ''),
                    'permalink': message.get('permalink', ''),
                    'reactions': message.get('reactions', []),
                    'files': message.get('files', []),
                    'attachments': message.get('attachments', []),
                    'thread_ts': message.get('thread_ts', ''),
                    'reply_count': message.get('reply_count', 0),
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
        self.logger.phase(4, f"Exporting to Markdown: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Header
            f.write("# Slack Bookmarked Messages\n\n")
            f.write(f"**Export date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total bookmarks:** {len(messages)}\n\n")
            f.write("---\n\n")
            
            # Messages
            for i, msg in enumerate(messages, 1):
                f.write(f"## Bookmark {i}\n\n")
                
                # Metadata
                if msg['bookmark_date']:
                    f.write(f"**Bookmarked:** {format_timestamp(msg['bookmark_date'])}\n")
                f.write(f"**Message Date:** {format_timestamp(msg['message_date'])}\n")
                f.write(f"**Channel:** {msg['channel_name']} ({msg['channel_id']})\n")
                f.write(f"**User:** {msg['user_name']} ({msg['user_id']})\n")
                
                if msg['permalink']:
                    f.write(f"**Permalink:** {msg['permalink']}\n")
                
                f.write("\n**Message:**\n\n")
                f.write(f"{msg['text']}\n\n")
                
                # Files/Attachments
                if msg['files']:
                    f.write(f"**Attachments:** {len(msg['files'])} attachment(s)\n")
                    for file_info in msg['files']:
                        name = file_info.get('name', 'Unknown file')
                        url = file_info.get('url_private', file_info.get('permalink', ''))
                        f.write(f"- {name}: {url}\n")
                    f.write("\n")
                
                if msg['attachments']:
                    f.write(f"**Rich Attachments:** {len(msg['attachments'])} attachment(s)\n")
                    for att in msg['attachments']:
                        title = att.get('title', att.get('fallback', 'Rich attachment'))
                        f.write(f"- {title}\n")
                    f.write("\n")
                
                # Reactions
                if msg['reactions']:
                    f.write("**Reactions:**\n")
                    for reaction in msg['reactions']:
                        name = reaction.get('name', '')
                        count = reaction.get('count', 0)
                        f.write(f"- :{name}: ({count})\n")
                    f.write("\n")
                
                # Thread info
                if msg['reply_count'] > 0:
                    f.write(f"**Thread:** {msg['reply_count']} replies\n\n")
                
                f.write("---\n\n")
                
                # Update progress
                self.logger.progress(i, len(messages), f"Writing message {i}")
        
        self.logger.success(f"Exported to {output_file}")
    
    def export_to_json(self, messages: List[Dict[str, Any]], output_file: str):
        """Export messages to JSON format."""
        self.logger.phase(4, f"Exporting to JSON: {output_file}")
        
        export_data = {
            'export_date': datetime.now().isoformat(),
            'total_bookmarks': len(messages),
            'messages': messages
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        self.logger.success(f"Exported to {output_file}")
    
    def fetch_and_export(self, output_file: str, page_size: int = 100):
        """Main method to fetch and export bookmarks."""
        start_time = datetime.now()
        
        try:
            # Fetch both starred and saved messages
            starred_messages = self.fetch_starred_messages(page_size)
            saved_messages = self.fetch_saved_messages(page_size)
            
            # Combine and deduplicate
            all_messages = starred_messages + saved_messages
            
            # Remove duplicates based on message timestamp and channel
            seen = set()
            unique_messages = []
            for msg in all_messages:
                message_data = msg.get('message', msg)
                key = (message_data.get('ts', ''), message_data.get('channel', ''))
                if key not in seen:
                    seen.add(key)
                    unique_messages.append(msg)
            
            # Summary
            total_starred = len(starred_messages)
            total_saved = len(saved_messages)
            total_unique = len(unique_messages)
            
            self.logger.info(f"⭐ Starred messages: {total_starred}")
            self.logger.info(f"🔖 Saved messages: {total_saved}")
            self.logger.info(f"📝 Unique messages: {total_unique}")
            
            if not unique_messages:
                self.logger.warning("No bookmarked messages found")
                return 0
            
            # Enrich messages
            enriched_messages = self.enrich_messages(unique_messages)
            
            # Sort by bookmark date (most recent first)
            enriched_messages.sort(key=lambda x: x.get('bookmark_date', ''), reverse=True)
            
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
        description='Fetch Slack bookmarked/starred messages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bookmarks.py -t "xoxp-token" -o bookmarks.md
  python bookmarks.py -t "xoxp-token" -o bookmarks.json --page-size 50

Required Slack API scopes:
  - stars:read (to read starred messages)
  - channels:read (to get channel names)  
  - users:read (to get user names)
  - groups:read (for private channels)
        """
    )
    
    parser.add_argument('-t', '--token', required=True,
                        help='Slack User OAuth Token (starts with xoxp-)')
    parser.add_argument('-o', '--output', 
                        help='Output file path (default: bookmarks_<timestamp>.md)')
    parser.add_argument('--page-size', type=int, default=100,
                        help='Messages per API call (default: 100)')
    
    args = parser.parse_args()
    
    # Default output filename
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'bookmarks_{timestamp}.md'
    
    try:
        fetcher = SlackBookmarksFetcher(args.token)
        message_count = fetcher.fetch_and_export(args.output, args.page_size)
        
        if message_count > 0:
            print(f"\n🎉 Successfully exported {message_count} bookmarked messages to {args.output}")
            return 0
        else:
            print(f"\n⚠️  No bookmarked messages found or export failed")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Export interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
