#!/usr/bin/env python3
"""
Slack Posts Fetcher

Fetch Slack posts using search API with standardized logging and rate limiting.
Supports complex search queries and monthly chunking for complete history.
"""

import argparse
import json
import sys
import calendar
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Iterator
from dataclasses import dataclass

# Import our standardized utilities
from utils import SlackExporter, format_timestamp, get_user_name, get_channel_name


@dataclass
class SearchConfig:
    """Configuration for search operations."""
    query: str
    max_results: int = 100
    page_size: int = 20
    monthly_chunks: bool = False
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class SlackPostsFetcher(SlackExporter):
    """Fetches Slack posts using search API."""
    
    def __init__(self, token: str):
        super().__init__(token, "PostsFetcher")
        self.user_cache = {}
        self.channel_cache = {}
    
    def search_messages(self, config: SearchConfig) -> List[Dict]:
        """Search for messages with the given configuration."""
        if config.monthly_chunks:
            messages = self._search_with_monthly_chunks(config)
        else:
            messages = self._search_simple(config)
        
        return messages
    
    def _search_simple(self, config: SearchConfig) -> List[Dict]:
        """Simple search without date chunking."""
        self.logger.phase(1, f"Searching messages: '{config.query}'")
        
        all_messages = []
        page = 1
        
        while len(all_messages) < config.max_results:
            self.logger.api_call("search.messages", page=page)
            
            params = {
                'query': config.query,
                'count': min(config.page_size, config.max_results - len(all_messages)),
                'page': page
            }
            
            data = self.make_api_request('https://slack.com/api/search.messages', params)
            if not data:
                break
            
            messages_data = data.get('messages', {})
            matches = messages_data.get('matches', [])
            
            if not matches:
                self.logger.info("No more messages found", indent=1)
                break
            
            all_messages.extend(matches)
            self.logger.progress(len(all_messages), min(config.max_results, messages_data.get('total', len(all_messages))), 
                               f"Found {len(matches)} messages on page {page}")
            
            # Check pagination
            paging = messages_data.get('paging', {})
            if page >= paging.get('pages', 1):
                break
            
            page += 1
        
        self.logger.success(f"Found {len(all_messages)} messages")
        return all_messages[:config.max_results]
    
    def _search_with_monthly_chunks(self, config: SearchConfig) -> List[Dict]:
        """Search using monthly date chunks for complete history."""
        self.logger.phase(1, f"Searching with monthly chunks: '{config.query}'")
        
        # Set up date range
        if config.start_date:
            start_date = datetime.strptime(config.start_date, '%Y-%m-%d')
        else:
            start_date = datetime.now() - timedelta(days=730)  # 2 years ago
        
        if config.end_date:
            end_date = datetime.strptime(config.end_date, '%Y-%m-%d')
        else:
            end_date = datetime.now()
        
        all_messages = []
        
        for month_start, month_end in self._generate_monthly_chunks(start_date, end_date):
            month_query = f"{config.query} after:{month_start.strftime('%Y-%m-%d')} before:{month_end.strftime('%Y-%m-%d')}"
            
            self.logger.info(f"Searching {month_start.strftime('%Y-%m')}...", indent=1)
            
            month_config = SearchConfig(
                query=month_query,
                max_results=10000,  # High limit for monthly chunks
                page_size=config.page_size
            )
            
            month_messages = self._search_simple(month_config)
            all_messages.extend(month_messages)
            
            if len(month_messages) > 0:
                self.logger.progress(len(all_messages), len(all_messages), 
                                   f"Found {len(month_messages)} messages in {month_start.strftime('%Y-%m')}")
        
        # Remove duplicates based on timestamp
        seen = set()
        unique_messages = []
        for msg in all_messages:
            ts = msg.get('ts', '')
            if ts not in seen:
                seen.add(ts)
                unique_messages.append(msg)
        
        self.logger.success(f"Found {len(unique_messages)} unique messages across all months")
        return unique_messages
    
    def _generate_monthly_chunks(self, start_date: datetime, end_date: datetime) -> Iterator[tuple]:
        """Generate monthly date chunks."""
        current = start_date.replace(day=1)
        
        while current <= end_date:
            # Get last day of month
            last_day = calendar.monthrange(current.year, current.month)[1]
            month_end = current.replace(day=last_day)
            
            if month_end > end_date:
                month_end = end_date
            
            yield current, month_end
            
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
    
    def enrich_messages(self, messages: List[Dict]) -> List[Dict]:
        """Enrich messages with user and channel names."""
        if not messages:
            return messages
        
        self.logger.phase(2, f"Enriching {len(messages)} messages")
        
        enriched_messages = []
        
        for i, msg in enumerate(messages):
            try:
                # Get user and channel names
                user_id = msg.get('user', '')
                channel_id = msg.get('channel', {}).get('id', '') if isinstance(msg.get('channel'), dict) else msg.get('channel', '')
                
                user_name = get_user_name(self.user_cache, user_id, self.session) if user_id else 'Unknown User'
                channel_name = get_channel_name(self.channel_cache, channel_id, self.session) if channel_id else 'Unknown Channel'
                
                # Create enriched message
                enriched_msg = msg.copy()
                enriched_msg['user_name'] = user_name
                enriched_msg['channel_name'] = channel_name
                enriched_msg['formatted_date'] = format_timestamp(msg.get('ts', ''))
                
                enriched_messages.append(enriched_msg)
                
                # Update progress
                self.logger.progress(i + 1, len(messages), f"Processing message {i + 1}")
                
            except Exception as e:
                self.logger.warning(f"Error enriching message {i + 1}: {e}", indent=1)
                enriched_messages.append(msg)  # Include original if enrichment fails
                continue
        
        self.logger.success(f"Enriched {len(enriched_messages)} messages")
        return enriched_messages
    
    def export_to_markdown(self, messages: List[Dict], output_file: str, query: str):
        """Export messages to Markdown format."""
        self.logger.phase(3, f"Exporting to Markdown: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Header
            f.write("# Slack Search Results\n\n")
            f.write(f"**Search Query:** `{query}`\n")
            f.write(f"**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Messages:** {len(messages)}\n\n")
            f.write("---\n\n")
            
            # Messages
            for i, msg in enumerate(messages, 1):
                f.write(f"## Message {i}\n\n")
                
                # Metadata
                f.write(f"**Date:** {msg.get('formatted_date', format_timestamp(msg.get('ts', '')))}\n")
                f.write(f"**User:** {msg.get('user_name', msg.get('username', 'Unknown'))}\n")
                f.write(f"**Channel:** {msg.get('channel_name', 'Unknown')}\n")
                
                if msg.get('permalink'):
                    f.write(f"**Link:** {msg['permalink']}\n")
                
                f.write("\n**Message:**\n\n")
                f.write(f"{msg.get('text', '*(No text)*')}\n\n")
                
                # Attachments
                if msg.get('attachments'):
                    f.write(f"**Attachments:** {len(msg['attachments'])} attachment(s)\n\n")
                
                # Files
                if msg.get('files'):
                    f.write(f"**Files:** {len(msg['files'])} file(s)\n\n")
                
                f.write("---\n\n")
                
                # Update progress
                self.logger.progress(i, len(messages), f"Writing message {i}")
        
        self.logger.success(f"Exported to {output_file}")
    
    def export_to_json(self, messages: List[Dict], output_file: str, query: str):
        """Export messages to JSON format."""
        self.logger.phase(3, f"Exporting to JSON: {output_file}")
        
        export_data = {
            'search_query': query,
            'export_date': datetime.now().isoformat(),
            'total_messages': len(messages),
            'messages': messages
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        self.logger.success(f"Exported to {output_file}")
    
    def export_to_jsonl(self, messages: List[Dict], output_file: str, query: str):
        """Export messages to JSONL format."""
        self.logger.phase(3, f"Exporting to JSONL: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for i, msg in enumerate(messages, 1):
                json.dump(msg, f, ensure_ascii=False)
                f.write('\n')
                
                # Update progress
                self.logger.progress(i, len(messages), f"Writing message {i}")
        
        self.logger.success(f"Exported to {output_file}")
    
    def search_and_export(self, config: SearchConfig, output_file: str):
        """Main method to search and export messages."""
        start_time = datetime.now()
        
        try:
            # Search messages
            messages = self.search_messages(config)
            
            if not messages:
                self.logger.warning("No messages found matching the search criteria")
                return 0, False
            
            # Check if we likely hit the limit
            hit_limit = len(messages) >= config.max_results and not config.monthly_chunks
            
            # Enrich messages
            enriched_messages = self.enrich_messages(messages)
            
            # Sort by timestamp (newest first)
            enriched_messages.sort(key=lambda x: float(x.get('ts', 0)), reverse=True)
            
            # Export based on file extension
            if output_file.endswith('.json'):
                self.export_to_json(enriched_messages, output_file, config.query)
            elif output_file.endswith('.jsonl'):
                self.export_to_jsonl(enriched_messages, output_file, config.query)
            else:
                self.export_to_markdown(enriched_messages, output_file, config.query)
            
            # Summary
            export_time = (datetime.now() - start_time).total_seconds()
            self.export_summary(output_file, len(enriched_messages), export_time)
            
            # Return count and whether we hit limit
            return len(enriched_messages), hit_limit
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            return 0, False


def main():
    parser = argparse.ArgumentParser(
        description='Fetch Slack messages using search API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python search.py -t "xoxp-token" -q "from:@john.smith" --monthly-chunks -o user_all_messages.md
  python search.py -t "xoxp-token" -q "from:@john.smith after:2025-09-01" -o user_recent.md
  python search.py -t "xoxp-token" -q "in:#general" --monthly-chunks
  python search.py -t "xoxp-token" -q "has:attachment" -m 500 -o files.json

Search Query Examples:
  - from:@john.smith                  # Messages from user using Slack handle (RECOMMENDED)
  - from:U123456789                   # Messages from user using ID (alternative)
  - in:#channel                       # Messages in specific channel
  - has:attachment                    # Messages with attachments
  - after:2025-01-01                  # Messages after date
  - "exact phrase"                    # Messages containing exact phrase

Tips:
  - Use @username (Slack handle) - more reliable than User IDs
  - DON'T use --monthly-chunks with recent date filters (causes conflicts)
  - Use --monthly-chunks only for complete historical exports

Required Slack API scopes:
  - search:read (to use search API)
  - channels:read (to get channel names)
  - users:read (to get user names)
        """
    )
    
    parser.add_argument('-t', '--token', required=True,
                        help='Slack User OAuth Token (starts with xoxp-)')
    parser.add_argument('-q', '--query', required=True,
                        help='Slack search query')
    parser.add_argument('-m', '--max-results', type=int, default=100,
                        help='Maximum number of results (default: 100)')
    parser.add_argument('--page-size', type=int, default=20,
                        help='Results per API call (default: 20, max: 100)')
    parser.add_argument('-o', '--output',
                        help='Output file (.md, .json, or .jsonl)')
    parser.add_argument('--monthly-chunks', action='store_true',
                        help='Break search into monthly chunks for complete history)') 
    parser.add_argument('--start-date', type=str,
                        help='Start date for monthly chunks (YYYY-MM-DD, default: 2 years ago)')
    parser.add_argument('--end-date', type=str, 
                        help='End date for monthly chunks (YYYY-MM-DD, default: today)')
    
    args = parser.parse_args()
    
    # Default output filename
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'slack_search_{timestamp}.md'
    
    # Create search configuration
    config = SearchConfig(
        query=args.query,
        max_results=args.max_results,
        page_size=min(args.page_size, 100),
        monthly_chunks=args.monthly_chunks,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    try:
        fetcher = SlackPostsFetcher(args.token)
        message_count, hit_limit = fetcher.search_and_export(config, args.output)
        
        if message_count > 0:
            print(f"\n🎉 Successfully exported {message_count} messages to {args.output}")
            
            # Show warning if we hit the limit
            if hit_limit:
                print("\n⚠️  WARNING: Result limit reached!")
                print(f"   Exported {message_count} messages, but there may be more.")
                print(f"   To get complete history, re-run with:")
                print(f"   --monthly-chunks  (recommended for complete history)")
                print(f"   OR")
                print(f"   -m 1000  (to increase max results)")
            
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
