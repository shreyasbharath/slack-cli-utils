#!/usr/bin/env python3
"""
Slack Bookmarks Fetcher

Fetches and exports all bookmarked messages from Slack with dates and context.
Supports multiple output formats and includes progress tracking.
"""

import requests
import argparse
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

class SlackBookmarksFetcher:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_starred_messages(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch all starred/bookmarked messages from Slack.
        Uses the stars.list API endpoint.
        """
        all_bookmarks = []
        cursor = None
        page_num = 1
        
        print("Phase 1: Fetching bookmarked messages...")
        
        while True:
            print(f"  Fetching page {page_num}...", end=" ", flush=True)
            
            # API call to get starred items
            url = "https://slack.com/api/stars.list"
            params = {
                'limit': page_size
            }
            if cursor:
                params['cursor'] = cursor
            
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if not data.get('ok'):
                    error_msg = data.get('error', 'Unknown error')
                    if error_msg == 'ratelimited':
                        retry_after = int(response.headers.get('Retry-After', 60))
                        print(f"\nRate limited. Waiting {retry_after} seconds...")
                        time.sleep(retry_after)
                        continue
                    else:
                        raise Exception(f"Slack API error: {error_msg}")
                
                items = data.get('items', [])
                if not items:
                    break
                
                # Filter for messages only (not files or other items)
                messages = [item for item in items if item.get('type') == 'message']
                all_bookmarks.extend(messages)
                
                print(f"({len(messages)} bookmarks)")
                
                # Check for pagination
                cursor = data.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
                
                page_num += 1
                
                # Respect rate limits
                time.sleep(0.5)
                
            except requests.exceptions.RequestException as e:
                print(f"\nNetwork error: {e}")
                time.sleep(5)
                continue
        
        print(f"\nFound {len(all_bookmarks)} bookmarked messages")
        return all_bookmarks
    
    def enrich_bookmark_data(self, bookmarks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich bookmark data with additional context like channel names, user names.
        """
        print("\nPhase 2: Enriching bookmark data with context...")
        
        # Get channel and user info
        channels_cache = {}
        users_cache = {}
        
        enriched_bookmarks = []
        
        for i, bookmark in enumerate(bookmarks, 1):
            print(f"  Processing bookmark {i}/{len(bookmarks)}", end="\r", flush=True)
            
            message = bookmark.get('message', {})
            channel_id = message.get('channel')
            user_id = message.get('user')
            
            # Get channel info
            channel_name = "Unknown Channel"
            if channel_id and channel_id not in channels_cache:
                try:
                    channel_info = self.get_channel_info(channel_id)
                    channels_cache[channel_id] = channel_info
                except Exception as e:
                    channels_cache[channel_id] = {'name': f'Channel-{channel_id}', 'error': str(e)}
            
            if channel_id in channels_cache:
                channel_name = channels_cache[channel_id].get('name', channel_id)
            
            # Get user info
            user_name = "Unknown User"
            if user_id and user_id not in users_cache:
                try:
                    user_info = self.get_user_info(user_id)
                    users_cache[user_id] = user_info
                except Exception as e:
                    users_cache[user_id] = {'name': f'User-{user_id}', 'error': str(e)}
            
            if user_id in users_cache:
                user_name = users_cache[user_id].get('display_name') or users_cache[user_id].get('real_name', user_id)
            
            # Enrich the bookmark
            enriched_bookmark = {
                'bookmark_date': datetime.fromtimestamp(float(bookmark.get('date_create', 0))).isoformat(),
                'message_date': datetime.fromtimestamp(float(message.get('ts', 0))).isoformat(),
                'channel_id': channel_id,
                'channel_name': channel_name,
                'user_id': user_id,
                'user_name': user_name,
                'text': message.get('text', ''),
                'permalink': message.get('permalink', ''),
                'message_ts': message.get('ts'),
                'thread_ts': message.get('thread_ts'),
                'is_thread_reply': bool(message.get('thread_ts') and message.get('thread_ts') != message.get('ts')),
                'attachments': message.get('attachments', []),
                'files': message.get('files', []),
                'reactions': message.get('reactions', []),
                'raw_message': message
            }
            
            enriched_bookmarks.append(enriched_bookmark)
            
            # Rate limiting
            time.sleep(0.1)
        
        print(f"  Processed {len(enriched_bookmarks)} bookmarks")
        return enriched_bookmarks
    
    def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get channel information from Slack API."""
        url = "https://slack.com/api/conversations.info"
        params = {'channel': channel_id}
        
        response = self.session.get(url, params=params)
        data = response.json()
        
        if data.get('ok'):
            channel = data.get('channel', {})
            return {
                'name': channel.get('name', channel_id),
                'is_private': channel.get('is_private', False),
                'is_im': channel.get('is_im', False),
                'is_mpim': channel.get('is_mpim', False)
            }
        else:
            # Fallback for DMs and private channels
            return {'name': f'Channel-{channel_id}'}
    
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information from Slack API."""
        url = "https://slack.com/api/users.info"
        params = {'user': user_id}
        
        response = self.session.get(url, params=params)
        data = response.json()
        
        if data.get('ok'):
            user = data.get('user', {})
            profile = user.get('profile', {})
            return {
                'real_name': user.get('real_name', user_id),
                'display_name': profile.get('display_name', ''),
                'email': profile.get('email', ''),
                'title': profile.get('title', '')
            }
        else:
            return {'real_name': user_id, 'display_name': user_id}
    
    def export_to_markdown(self, bookmarks: List[Dict[str, Any]], output_file: str):
        """Export bookmarks to Markdown format."""
        print(f"\nPhase 3: Writing {len(bookmarks)} bookmarks to {output_file}...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Header
            f.write("# Slack Bookmarked Messages\n\n")
            f.write(f"**Export date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total bookmarks:** {len(bookmarks)}\n\n")
            f.write("---\n\n")
            
            # Sort by bookmark date (most recent first)
            sorted_bookmarks = sorted(bookmarks, key=lambda x: x['bookmark_date'], reverse=True)
            
            for i, bookmark in enumerate(sorted_bookmarks, 1):
                print(f"  Writing bookmark {i}/{len(bookmarks)}", end="\r", flush=True)
                
                f.write(f"## Bookmark {i}\n\n")
                f.write(f"**Bookmarked:** {bookmark['bookmark_date']}\n")
                f.write(f"**Message Date:** {bookmark['message_date']}\n")
                f.write(f"**Channel:** #{bookmark['channel_name']} ({bookmark['channel_id']})\n")
                f.write(f"**User:** {bookmark['user_name']} ({bookmark['user_id']})\n")
                
                if bookmark['is_thread_reply']:
                    f.write(f"**Thread Reply:** Yes\n")
                
                if bookmark['permalink']:
                    f.write(f"**Permalink:** {bookmark['permalink']}\n")
                
                f.write("\n**Message:**\n\n")
                
                # Format message text
                message_text = bookmark['text'] or "*No text content*"
                f.write(f"{message_text}\n\n")
                
                # Add attachments info
                if bookmark['attachments']:
                    f.write(f"**Attachments:** {len(bookmark['attachments'])} attachment(s)\n")
                    for att in bookmark['attachments']:
                        f.write(f"- {att.get('title', 'Untitled')}: {att.get('title_link', 'No link')}\n")
                    f.write("\n")
                
                # Add files info
                if bookmark['files']:
                    f.write(f"**Files:** {len(bookmark['files'])} file(s)\n")
                    for file in bookmark['files']:
                        f.write(f"- {file.get('name', 'Unnamed')}: {file.get('url_private', 'No URL')}\n")
                    f.write("\n")
                
                # Add reactions
                if bookmark['reactions']:
                    f.write("**Reactions:**\n")
                    for reaction in bookmark['reactions']:
                        emoji = reaction.get('name', 'unknown')
                        count = reaction.get('count', 0)
                        f.write(f"- :{emoji}: ({count})\n")
                    f.write("\n")
                
                f.write("---\n\n")
        
        print(f"  Exported {len(bookmarks)} bookmarks successfully")
    
    def export_to_json(self, bookmarks: List[Dict[str, Any]], output_file: str):
        """Export bookmarks to JSON format."""
        print(f"\nExporting {len(bookmarks)} bookmarks to {output_file}...")
        
        export_data = {
            'export_date': datetime.now().isoformat(),
            'total_bookmarks': len(bookmarks),
            'bookmarks': bookmarks
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"Exported {len(bookmarks)} bookmarks successfully")


def main():
    parser = argparse.ArgumentParser(
        description='Fetch and export Slack bookmarked messages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export bookmarks to Markdown
  python fetch_bookmarks.py -t "xoxp-your-token" -o my_bookmarks.md

  # Export to JSON format
  python fetch_bookmarks.py -t "xoxp-your-token" -o my_bookmarks.json

  # Custom page size for faster fetching
  python fetch_bookmarks.py -t "xoxp-your-token" --page-size 50 -o bookmarks.md

Required Slack token scopes:
  - stars:read (to read starred messages)
  - channels:read (to get channel names)
  - users:read (to get user names)
  - groups:read (for private channels)
        """
    )
    
    parser.add_argument('-t', '--token', required=True,
                       help='Slack User OAuth Token (starts with xoxp-)')
    parser.add_argument('-o', '--output', 
                       default=f'slack_bookmarks_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md',
                       help='Output file path (default: timestamped)')
    parser.add_argument('--page-size', type=int, default=100,
                       help='Number of bookmarks to fetch per API call (default: 100)')
    
    args = parser.parse_args()
    
    # Validate token format
    if not args.token.startswith('xoxp-'):
        print("Error: Token should be a User OAuth Token starting with 'xoxp-'")
        return 1
    
    # Determine output format from file extension
    output_format = 'json' if args.output.endswith('.json') else 'markdown'
    
    try:
        # Initialize fetcher
        fetcher = SlackBookmarksFetcher(args.token)
        
        # Fetch bookmarks
        bookmarks = fetcher.get_starred_messages(args.page_size)
        
        if not bookmarks:
            print("No bookmarked messages found.")
            return 0
        
        # Enrich with context
        enriched_bookmarks = fetcher.enrich_bookmark_data(bookmarks)
        
        # Export to chosen format
        if output_format == 'json':
            fetcher.export_to_json(enriched_bookmarks, args.output)
        else:
            fetcher.export_to_markdown(enriched_bookmarks, args.output)
        
        print(f"\n✅ Successfully exported {len(enriched_bookmarks)} bookmarks to {args.output}")
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
