#!/usr/bin/env python3
"""
Slack Messages Fetcher

Fetches and exports both starred messages AND saved messages ("Later" tab) from Slack.
Supports multiple output formats and includes progress tracking.
"""

import requests
import argparse
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

class SlackMessagesFetcher:
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
        Fetch all starred messages from Slack.
        Uses the stars.list API endpoint.
        """
        all_starred = []
        cursor = None
        page_num = 1
        
        print("Phase 1a: Fetching starred messages...")
        
        while True:
            print(f"  Fetching starred page {page_num}...", end=" ", flush=True)
            
            # API call to get starred items
            url = "https://slack.com/api/stars.list"
            params = {
                'limit': page_size
            }
            if cursor:
                params['cursor'] = cursor
            
            try:
                response = self.session.get(url, params=params, timeout=30)
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
                
                # Filter for messages only and mark as starred
                messages = []
                for item in items:
                    if item.get('type') == 'message':
                        item['source_type'] = 'starred'
                        messages.append(item)
                
                all_starred.extend(messages)
                print(f"({len(messages)} starred)")
                
                # Check for pagination
                cursor = data.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
                
                page_num += 1
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"\nError fetching starred messages: {e}")
                break
        
        return all_starred
    
    def get_saved_messages(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch saved messages ("Later" tab) from Slack using search API.
        Uses search.messages with 'is:saved' query.
        """
        all_saved = []
        page = 1
        
        print("Phase 1b: Fetching saved messages (Later tab)...")
        
        while True:
            print(f"  Fetching saved page {page}...", end=" ", flush=True)
            
            url = "https://slack.com/api/search.messages"
            params = {
                'query': 'is:saved',
                'count': page_size,
                'page': page
            }
            
            try:
                response = self.session.get(url, params=params, timeout=30)
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
                        print(f"\nWarning: Could not fetch saved messages: {error_msg}")
                        break
                
                messages_data = data.get('messages', {})
                matches = messages_data.get('matches', [])
                
                if not matches:
                    break
                
                # Convert search results to message format
                converted_messages = []
                for match in matches:
                    # Convert search match format to starred message format for consistency
                    message_item = {
                        'type': 'message',
                        'message': match,  # The search result is already in message format
                        'source_type': 'saved',
                        'date_create': None  # Search API doesn't provide save date
                    }
                    converted_messages.append(message_item)
                
                all_saved.extend(converted_messages)
                print(f"({len(converted_messages)} saved)")
                
                # Check if we have more pages
                pagination = messages_data.get('pagination', {})
                total_pages = pagination.get('page_count', 0)
                
                if page >= total_pages:
                    break
                
                page += 1
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"\nWarning: Error fetching saved messages: {e}")
                break
        
        return all_saved
    
    def get_all_messages(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch both starred and saved messages.
        """
        starred_messages = self.get_starred_messages(page_size)
        saved_messages = self.get_saved_messages(page_size)
        
        all_messages = starred_messages + saved_messages
        
        total_starred = len(starred_messages)
        total_saved = len(saved_messages)
        total_messages = len(all_messages)
        
        print(f"\nFound {total_starred} starred messages and {total_saved} saved messages")
        print(f"Total: {total_messages} messages to process")
        
        if total_messages == 0:
            print("No starred or saved messages found.")
            return []
        
        return all_messages    
    def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get channel information."""
        url = "https://slack.com/api/conversations.info"
        params = {'channel': channel_id}
        
        response = self.session.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('ok'):
            channel = data.get('channel', {})
            return {
                'name': f"#{channel.get('name', channel_id)}",
                'id': channel_id
            }
        else:
            return {'name': f'Channel-{channel_id}', 'id': channel_id}
    
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information."""
        url = "https://slack.com/api/users.info"
        params = {'user': user_id}
        
        response = self.session.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('ok'):
            user = data.get('user', {})
            profile = user.get('profile', {})
            return {
                'display_name': profile.get('display_name') or profile.get('real_name') or user.get('name', user_id),
                'real_name': profile.get('real_name', ''),
                'id': user_id
            }
        else:
            return {'display_name': f'User-{user_id}', 'id': user_id}
    
    def enrich_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich messages with context. For search results, use existing data.
        For starred messages, fetch additional context if needed.
        """
        if not messages:
            return []
        
        print(f"\nPhase 2: Processing {len(messages)} messages...")
        
        enriched_messages = []
        
        for i, item in enumerate(messages, 1):
            print(f"  Processing message {i}/{len(messages)}", end="\r", flush=True)
            
            message = item.get('message', {})
            source_type = item.get('source_type', 'unknown')
            
            # For saved messages from search API, data is already rich
            if source_type == 'saved':
                # Search API provides rich data structure
                channel_data = message.get('channel', {})
                channel_name = f"#{channel_data.get('name', 'unknown')}"
                channel_id = channel_data.get('id', 'unknown')
                
                user_name = message.get('username', 'unknown')
                user_id = message.get('user', 'unknown')
                
                # Use search API data directly
                enriched_message = {
                    'source_type': source_type,
                    'action_date': None,  # Search API doesn't provide save date
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
            else:
                # For starred messages, use the original enrichment logic
                channel_id = message.get('channel')
                user_id = message.get('user')
                
                # This would require API calls - for now, use basic data
                enriched_message = {
                    'source_type': source_type,
                    'action_date': datetime.fromtimestamp(float(item.get('date_create', 0))).isoformat() if item.get('date_create') else None,
                    'message_date': datetime.fromtimestamp(float(message.get('ts', 0))).isoformat(),
                    'channel_id': channel_id or 'unknown',
                    'channel_name': f'Channel-{channel_id}' if channel_id else 'Unknown Channel',
                    'user_id': user_id or 'unknown',
                    'user_name': f'User-{user_id}' if user_id else 'Unknown User',
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
            
            enriched_messages.append(enriched_message)
        
        print(f"\n  Processed {len(enriched_messages)} messages successfully")
        return enriched_messages
    
    def export_to_markdown(self, messages: List[Dict[str, Any]], output_file: str):
        """Export messages to Markdown format."""
        print(f"\nExporting {len(messages)} messages to {output_file}...")
        
        starred_count = len([m for m in messages if m.get('source_type') == 'starred'])
        saved_count = len([m for m in messages if m.get('source_type') == 'saved'])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Slack Messages Export\n\n")
            f.write(f"**Export date:** {datetime.now().isoformat()}\n")
            f.write(f"**Total messages:** {len(messages)}\n")
            f.write(f"**Starred messages:** {starred_count}\n")
            f.write(f"**Saved messages:** {saved_count}\n\n")
            f.write("---\n\n")
            
            for i, message in enumerate(messages, 1):
                source_icon = "⭐" if message['source_type'] == 'starred' else "🔖"
                source_label = "Starred" if message['source_type'] == 'starred' else "Saved"
                
                f.write(f"## {source_icon} Message {i}\n\n")
                
                if message['action_date']:
                    f.write(f"**{source_label}:** {message['action_date']}\n")
                f.write(f"**Message Date:** {message['message_date']}\n")
                f.write(f"**Channel:** {message['channel_name']} ({message['channel_id']})\n")
                f.write(f"**User:** {message['user_name']} ({message['user_id']})\n")
                
                if message['permalink']:
                    f.write(f"**Permalink:** {message['permalink']}\n")
                
                f.write("\n**Message:**\n\n")
                f.write(f"{message['text']}\n\n")
                
                # Add thread info
                if message['is_thread_reply']:
                    f.write("**Note:** This is a thread reply\n\n")
                
                # Add attachments info
                if message['attachments']:
                    f.write(f"**Attachments:** {len(message['attachments'])} attachment(s)\n")
                    for attachment in message['attachments']:
                        title = attachment.get('title', 'Attachment')
                        title_link = attachment.get('title_link', '')
                        if title_link:
                            f.write(f"- {title}: {title_link}\n")
                        else:
                            f.write(f"- {title}\n")
                    f.write("\n")
                
                # Add files info
                if message['files']:
                    f.write(f"**Files:** {len(message['files'])} file(s)\n")
                    for file_obj in message['files']:
                        name = file_obj.get('name', 'File')
                        url = file_obj.get('url_private', file_obj.get('permalink', ''))
                        if url:
                            f.write(f"- {name}: {url}\n")
                        else:
                            f.write(f"- {name}\n")
                    f.write("\n")
                
                # Add reactions
                if message['reactions']:
                    f.write("**Reactions:**\n")
                    for reaction in message['reactions']:
                        emoji = reaction.get('name', 'unknown')
                        count = reaction.get('count', 0)
                        f.write(f"- :{emoji}: ({count})\n")
                    f.write("\n")
                
                f.write("---\n\n")
        
        print(f"  Exported {len(messages)} messages successfully")
    
    def export_to_json(self, messages: List[Dict[str, Any]], output_file: str):
        """Export messages to JSON format."""
        print(f"\nExporting {len(messages)} messages to {output_file}...")
        
        starred_count = len([m for m in messages if m.get('source_type') == 'starred'])
        saved_count = len([m for m in messages if m.get('source_type') == 'saved'])
        
        export_data = {
            'export_date': datetime.now().isoformat(),
            'total_messages': len(messages),
            'starred_messages': starred_count,
            'saved_messages': saved_count,
            'messages': messages
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"Exported {len(messages)} messages successfully")


def main():
    parser = argparse.ArgumentParser(
        description='Fetch and export both starred and saved Slack messages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export both starred and saved messages to Markdown
  python slack_bookmarks_fetcher.py -t "xoxp-your-token" -o my_messages.md

  # Export to JSON format
  python slack_bookmarks_fetcher.py -t "xoxp-your-token" -o my_messages.json

  # Custom page size for faster fetching
  python slack_bookmarks_fetcher.py -t "xoxp-your-token" --page-size 50 -o messages.md

Required Slack token scopes:
  - stars:read (to read starred messages)
  - bookmarks:read (to read saved messages from "Later" tab)
  - channels:read (to get channel names)
  - users:read (to get user names)
  - groups:read (for private channels)
        """
    )
    
    parser.add_argument('-t', '--token', required=True,
                        help='Slack User OAuth Token (starts with xoxp-)')
    parser.add_argument('-o', '--output', 
                        help='Output file path (default: timestamped file)')
    parser.add_argument('--page-size', type=int, default=100,
                        help='Number of messages to fetch per API call (default: 100)')
    
    args = parser.parse_args()
    
    # Generate default output filename if not provided
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"slack_messages_{timestamp}.md"
    
    try:
        fetcher = SlackMessagesFetcher(args.token)
        
        # Fetch all messages (starred + saved)
        messages = fetcher.get_all_messages(args.page_size)
        
        if not messages:
            print("No messages found to export.")
            return
        
        # Enrich with context
        enriched_messages = fetcher.enrich_messages(messages)
        
        # Export based on file extension
        if args.output.lower().endswith('.json'):
            fetcher.export_to_json(enriched_messages, args.output)
        else:
            fetcher.export_to_markdown(enriched_messages, args.output)
        
        print(f"\n🎉 Successfully exported to {args.output}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    main()
