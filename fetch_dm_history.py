#!/usr/bin/env python3
"""
Fetch Slack DM history using conversations.history API with streaming write and progress bar
"""

import requests
import json
import time
import os
import argparse
from datetime import datetime, timezone

class SlackDMFetcher:
    def __init__(self, token, channel_id, output_file):
        self.token = token
        self.channel_id = channel_id
        self.output_file = output_file
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        self.base_url = "https://slack.com/api/conversations.history"
        
    def fetch_and_save(self, since_date="2025-01-01"):
        """Fetch and save messages incrementally with progress tracking"""
        
        # Convert date to timestamp
        since_ts = datetime.strptime(since_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
        
        print(f"Fetching messages from channel {self.channel_id} since {since_date}")
        print(f"Output file: {self.output_file}")
        print("\nPhase 1: Collecting all messages...")
        
        # First pass: collect all messages for accurate progress tracking
        all_messages = self._collect_all_messages(since_ts)
        
        if not all_messages:
            print("No messages found!")
            return 0
        
        total_count = len(all_messages)
        print(f"\nFound {total_count} messages to process")
        print("\nPhase 2: Writing messages to file...")
        
        # Open file for writing
        with open(self.output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"# DM Conversation History\n\n")
            f.write(f"**Channel ID:** {self.channel_id}\n")
            f.write(f"**Messages since:** {since_date}\n")
            f.write(f"**Export date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total messages:** {total_count}\n\n")
            f.write("---\n\n")
            f.flush()
            os.fsync(f.fileno())
            
            # Sort all messages by timestamp (oldest first)
            all_messages.sort(key=lambda x: float(x.get('ts', 0)))
            
            # Write messages with progress tracking
            for i, msg in enumerate(all_messages, 1):
                self._write_message(f, msg, i)
                
                # Update progress
                if i % 10 == 0 or i == total_count:
                    f.flush()
                    os.fsync(f.fileno())
                    progress = (i / total_count) * 100
                    print(f"\r  Progress: {i}/{total_count} messages ({progress:.1f}%) ", end='', flush=True)
            
            print()  # New line after progress
            
            # Write footer
            f.write(f"\n---\n\n")
            f.write(f"**Export completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.flush()
            os.fsync(f.fileno())
        
        print(f"\n✓ Successfully saved {total_count} messages to {self.output_file}")
        return total_count
    
    def _collect_all_messages(self, since_ts):
        """Collect all messages (first pass for counting)"""
        all_messages = []
        cursor = None
        page = 1
        
        while True:
            params = {
                'channel': self.channel_id,
                'oldest': since_ts,
                'limit': 200,  # Max allowed
                'inclusive': True
            }
            
            if cursor:
                params['cursor'] = cursor
            
            print(f"\r  Scanning page {page}... (found {len(all_messages)} messages so far)", end='', flush=True)
            
            try:
                response = requests.get(self.base_url, headers=self.headers, params=params)
                
                if response.status_code == 429:
                    # Get retry-after value - it might be a float
                    retry_after = response.headers.get('Retry-After', '60')
                    try:
                        retry_after = float(retry_after)
                    except (ValueError, TypeError):
                        retry_after = 60.0
                    
                    # Add a small buffer (10%) to be safe
                    retry_after = retry_after * 1.1
                    
                    print(f"\n  Rate limited. Waiting {retry_after:.1f} seconds (includes 10% buffer)...")
                    print(f"    Raw Retry-After header: {response.headers.get('Retry-After', 'Not provided')}")
                    time.sleep(retry_after)
                    continue
                
                # Check rate limit headers proactively
                remaining = response.headers.get('X-Rate-Limit-Remaining')
                if remaining and int(remaining) <= 1:
                    # Proactively wait if we're about to hit the limit
                    retry_after = response.headers.get('X-Rate-Limit-Reset')
                    if retry_after:
                        try:
                            reset_time = float(retry_after)
                            wait_time = max(0, reset_time - time.time()) + 1  # Add 1 second buffer
                            if wait_time > 0:
                                print(f"\n  Approaching rate limit (remaining: {remaining}). Waiting {wait_time:.1f} seconds...")
                                time.sleep(wait_time)
                        except (ValueError, TypeError):
                            pass
                
                data = response.json()
                
                if not data.get('ok'):
                    error = data.get('error', 'Unknown error')
                    print(f"\n✗ Error: {error}")
                    if error == 'missing_scope':
                        print("\nYour token is missing required scopes. You need:")
                        print("  - channels:history (for public channels)")
                        print("  - groups:history (for private channels)")
                        print("  - im:history (for direct messages)")
                        print("  - mpim:history (for group DMs)")
                    return []
                
                batch = data.get('messages', [])
                all_messages.extend(batch)
                
                if not data.get('has_more', False):
                    break
                
                cursor = data.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
                
                page += 1
                # Small delay to be nice to the API, but not too much since we handle rate limits
                time.sleep(0.1)
                
            except Exception as e:
                print(f"\n✗ Error during collection: {e}")
                return all_messages
        
        print()  # New line after progress
        return all_messages
    
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
            formatted_text = formatted_text.replace('\n', '  \n')  # Preserve line breaks
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
        
        # Thread info if it's a thread
        if msg.get('thread_ts') and msg.get('thread_ts') != msg.get('ts'):
            file_handle.write(f"**Thread:** Reply to message at {msg.get('thread_ts')}\n\n")
        
        file_handle.write("---\n\n")

def main():
    parser = argparse.ArgumentParser(
        description='Fetch Slack DM history with progress tracking',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch messages from January 2025 onwards
  python fetch_dm_history.py -t xoxp-your-token -c D0889Q50GPM
  
  # Fetch messages from a specific date
  python fetch_dm_history.py -t xoxp-your-token -c D0889Q50GPM -s 2024-01-01
  
  # Specify output file
  python fetch_dm_history.py -t xoxp-your-token -c D0889Q50GPM -o my_messages.md
        """
    )
    
    parser.add_argument(
        '-t', '--token',
        required=True,
        help='Slack User OAuth Token (xoxp-...)'
    )
    
    parser.add_argument(
        '-c', '--channel',
        required=True,
        help='Channel/DM ID (e.g., D0889Q50GPM)'
    )
    
    parser.add_argument(
        '-s', '--since',
        default='2025-01-01',
        help='Fetch messages since this date (YYYY-MM-DD format, default: 2025-01-01)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file path (default: dm_CHANNELID_TIMESTAMP.md)'
    )
    
    args = parser.parse_args()
    
    # Generate output filename if not specified
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"dm_{args.channel}_{timestamp}.md"
    else:
        output_file = args.output
    
    # Create fetcher and run
    fetcher = SlackDMFetcher(args.token, args.channel, output_file)
    
    try:
        total_messages = fetcher.fetch_and_save(args.since)
        
        if total_messages == 0:
            print("\nNo messages found. Possible reasons:")
            print("1. No messages exist in the specified date range")
            print("2. Token doesn't have required permissions")
            print("3. Channel ID is incorrect")
    except KeyboardInterrupt:
        print("\n\n✗ Cancelled by user")
        print(f"Partial results may be saved in: {output_file}")
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
        print(f"Partial results may be saved in: {output_file}")

if __name__ == "__main__":
    main()
