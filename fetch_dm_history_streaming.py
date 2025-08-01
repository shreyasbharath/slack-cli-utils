#!/usr/bin/env python3
"""
Fetch DM history using conversations.history API with streaming write
"""

import requests
import json
import time
import os
from datetime import datetime, timezone

class StreamingDMFetcher:
    def __init__(self, token, channel_id, output_file):
        self.token = token
        self.channel_id = channel_id
        self.output_file = output_file
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        self.base_url = "https://slack.com/api/conversations.history"
        self.messages_written = 0
        
    def fetch_and_save(self, since_date="2025-01-01"):
        """Fetch and save messages incrementally"""
        
        # Convert date to timestamp
        since_ts = datetime.strptime(since_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
        
        # Open file for writing
        with open(self.output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"# DM Conversation History\n\n")
            f.write(f"**Channel ID:** {self.channel_id}\n")
            f.write(f"**Fetching messages since:** {since_date}\n")
            f.write(f"**Export started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Status:** In Progress...\n\n")
            f.write("---\n\n")
            f.flush()
            os.fsync(f.fileno())  # Force OS to write to disk
            
            print(f"Fetching messages from channel {self.channel_id} since {since_date}")
            print(f"Writing to: {self.output_file}")
            
            cursor = None
            page = 1
            total_messages = 0
            
            while True:
                params = {
                    'channel': self.channel_id,
                    'oldest': since_ts,
                    'limit': 200,  # Max allowed by Slack
                    'inclusive': True
                }
                
                if cursor:
                    params['cursor'] = cursor
                
                print(f"\nFetching page {page}...")
                
                try:
                    response = requests.get(self.base_url, headers=self.headers, params=params)
                    
                    if response.status_code == 429:
                        # Rate limited
                        retry_after = int(response.headers.get('Retry-After', 60))
                        print(f"Rate limited. Waiting {retry_after} seconds...")
                        time.sleep(retry_after)
                        continue
                    
                    data = response.json()
                    
                    if not data.get('ok'):
                        error = data.get('error', 'Unknown error')
                        print(f"Error: {error}")
                        if error == 'missing_scope':
                            print("Your token is missing required scopes. You need:")
                            print("  - channels:history (for public channels)")
                            print("  - groups:history (for private channels)")
                            print("  - im:history (for direct messages)")
                            print("  - mpim:history (for group DMs)")
                        f.write(f"\n\n**ERROR:** {error}\n")
                        f.flush()
                        break
                    
                    batch_messages = data.get('messages', [])
                    
                    if not batch_messages:
                        print("No messages found in this page")
                    else:
                        # Sort messages by timestamp (oldest first) within this batch
                        batch_messages.sort(key=lambda x: float(x.get('ts', 0)))
                        
                        # Write messages immediately
                        for msg in batch_messages:
                            total_messages += 1
                            self._write_message(f, msg, total_messages)
                            
                            # Flush every 5 messages
                            if total_messages % 5 == 0:
                                f.flush()
                                os.fsync(f.fileno())
                                print(f"  Written {total_messages} messages so far...")
                    
                    print(f"Page {page}: Got {len(batch_messages)} messages (Total: {total_messages})")
                    
                    # Check if there are more messages
                    if not data.get('has_more', False):
                        print("\nNo more messages to fetch")
                        break
                    
                    cursor = data.get('response_metadata', {}).get('next_cursor')
                    if not cursor:
                        print("\nNo next cursor, ending fetch")
                        break
                    
                    page += 1
                    time.sleep(1)  # Be nice to the API
                    
                except Exception as e:
                    print(f"\nError during fetch: {e}")
                    f.write(f"\n\n**ERROR DURING FETCH:** {str(e)}\n")
                    f.flush()
                    break
            
            # Write final summary
            f.write(f"\n\n---\n\n")
            f.write(f"**Export completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total messages fetched:** {total_messages}\n")
            f.flush()
            os.fsync(f.fileno())
            
        print(f"\nCompleted! Total messages: {total_messages}")
        print(f"Messages saved to: {self.output_file}")
        
        return total_messages
    
    def _write_message(self, file_handle, msg, msg_number):
        """Write a single message to the file"""
        
        # Extract message details
        user = msg.get('user', 'Unknown')
        text = msg.get('text', '')
        ts = msg.get('ts', '')
        
        # Convert timestamp
        try:
            dt = datetime.fromtimestamp(float(ts))
            readable_date = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            readable_date = ts
        
        # Write message
        file_handle.write(f"## Message {msg_number}\n\n")
        file_handle.write(f"**User:** {user}\n")
        file_handle.write(f"**Date:** {readable_date}\n")
        file_handle.write(f"**Timestamp:** {ts}\n\n")
        
        # Handle message text
        if text:
            # Basic Slack formatting cleanup
            formatted_text = text.replace('<@', '@').replace('>', '')
            formatted_text = formatted_text.replace('\n', '  \n')  # Preserve line breaks in markdown
            file_handle.write(f"**Message:**\n\n{formatted_text}\n\n")
        else:
            file_handle.write("**Message:** *(No text content)*\n\n")
        
        # Add attachments info if present
        if msg.get('attachments'):
            file_handle.write("**Attachments:**\n")
            for att in msg['attachments']:
                title = att.get('title', 'Untitled')
                url = att.get('title_link', att.get('url', ''))
                if url:
                    file_handle.write(f"- [{title}]({url})\n")
                else:
                    file_handle.write(f"- {title}\n")
            file_handle.write("\n")
        
        # Add files info if present
        if msg.get('files'):
            file_handle.write("**Files:**\n")
            for file_obj in msg['files']:
                name = file_obj.get('name', 'Unknown File')
                url = file_obj.get('url_private', file_obj.get('permalink', ''))
                filetype = file_obj.get('filetype', 'unknown')
                if url:
                    file_handle.write(f"- [{name}]({url}) ({filetype})\n")
                else:
                    file_handle.write(f"- {name} ({filetype})\n")
            file_handle.write("\n")
        
        # Add reactions if present
        if msg.get('reactions'):
            file_handle.write("**Reactions:**\n")
            for reaction in msg['reactions']:
                name = reaction.get('name', 'unknown')
                count = reaction.get('count', 0)
                file_handle.write(f"- :{name}: ({count})\n")
            file_handle.write("\n")
        
        file_handle.write("---\n\n")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python fetch_dm_history_streaming.py <token> <channel_id> [since_date]")
        print("Example: python fetch_dm_history_streaming.py xoxp-... D0889Q50GPM 2025-01-01")
        sys.exit(1)
    
    token = sys.argv[1]
    channel_id = sys.argv[2]
    since_date = sys.argv[3] if len(sys.argv) > 3 else "2025-01-01"
    
    # Create output filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"dm_{channel_id}_{timestamp}.md"
    
    fetcher = StreamingDMFetcher(token, channel_id, output_file)
    total_messages = fetcher.fetch_and_save(since_date)
    
    if total_messages == 0:
        print("\nNo messages found. Possible reasons:")
        print("1. No messages exist in the specified date range")
        print("2. Token doesn't have required permissions")
        print("3. Channel ID is incorrect")
