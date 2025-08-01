#!/usr/bin/env python3
"""
Slack Posts Fetcher

A configurable script to fetch Slack posts using Slack's search API with proper
rate limiting and retry handling.
"""

import argparse
import datetime
import json
import logging
import os
import sys
import time
import calendar
from dataclasses import dataclass
from typing import Dict, List, Optional, Iterator
from urllib.parse import urlencode

import requests


@dataclass
class SlackConfig:
    """Configuration for Slack API interactions."""
    token: str
    query: str
    max_results: int = 100
    results_per_page: int = 20
    max_retries: int = 5
    base_delay: float = 1.0
    date_range: Optional[str] = None
    monthly_chunks: bool = False
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class SlackRateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after} seconds")


class SlackAPIClient:
    """Handles Slack API interactions with rate limiting and retry logic."""
    
    BASE_URL = "https://slack.com/api"
    
    def __init__(self, config: SlackConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config.token}',
            'Content-Type': 'application/json'
        })
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """Make a request to Slack API with retry logic."""
        url = f"{self.BASE_URL}/{endpoint}"
        
        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(f"🌐 Making request to {endpoint} (attempt {attempt + 1}/{self.config.max_retries})")
                response = self.session.get(url, params=params)
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = float(response.headers.get('Retry-After', self.config.base_delay))
                    self.logger.warning(f"⏸️  Rate limited! Slack says wait {retry_after} seconds (attempt {attempt + 1})")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                if not data.get('ok'):
                    error = data.get('error', 'Unknown error')
                    self.logger.error(f"❌ Slack API error: {error}")
                    raise RuntimeError(f"Slack API error: {error}")
                
                # Check for rate limit headers and sleep if needed
                rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
                retry_after_header = response.headers.get('X-RateLimit-Retry-After')
                
                if rate_limit_remaining and int(rate_limit_remaining) <= 1:
                    retry_after = float(retry_after_header or self.config.base_delay)
                    self.logger.info(f"⚠️  Low rate limit ({rate_limit_remaining} remaining). Slack says wait {retry_after}s")
                    time.sleep(retry_after)
                elif rate_limit_remaining:
                    self.logger.debug(f"🔄 Rate limit remaining: {rate_limit_remaining}")
                
                if retry_after_header:
                    self.logger.debug(f"🕐 Retry-After header present: {retry_after_header}s")
                
                return data
                
            except requests.RequestException as e:
                self.logger.warning(f"🔌 Request failed (attempt {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt < self.config.max_retries - 1:
                    delay = self.config.base_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.info(f"⏳ Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"💥 All retry attempts exhausted!")
                    raise
        
        raise RuntimeError(f"Failed to make request after {self.config.max_retries} attempts")
    
    def search_messages(self) -> Iterator[Dict]:
        """Search for messages matching the query."""
        page = 1
        total_fetched = 0
        start_time = time.time()
        total_pages = None
        
        self.logger.info(f"Starting search for query: '{self.config.query}'")
        self.logger.info(f"Will fetch up to {self.config.max_results} results, {self.config.results_per_page} per page")
        
        while total_fetched < self.config.max_results:
            page_start_time = time.time()
            params = {
                'query': self.config.query,
                'count': min(self.config.results_per_page, self.config.max_results - total_fetched),
                'sort': 'timestamp',
                'sort_dir': 'desc',
                'page': page
            }
            
            self.logger.info(f"📄 Fetching page {page}" + (f"/{total_pages}" if total_pages else "") + f" (requesting {params['count']} messages)...")
            
            try:
                response = self._make_request('search.messages', params)
                
                messages = response.get('messages', {})
                matches = messages.get('matches', [])
                pagination = messages.get('pagination', {})
                
                page_time = time.time() - page_start_time
                self.logger.info(f"✅ Page {page} received {len(matches)} messages in {page_time:.2f}s")
                
                if not matches:
                    self.logger.info("❌ No more messages found")
                    break
                
                # Log pagination info on first page
                if page == 1:
                    total_available = pagination.get('total_count', 0)
                    total_pages = pagination.get('page_count', 0)
                    estimated_time = (total_pages * page_time) / 60  # rough estimate in minutes
                    self.logger.info(f"📊 Found {total_available:,} total messages across {total_pages:,} pages")
                    self.logger.info(f"⏱️  Estimated completion time: {estimated_time:.1f} minutes at current rate")
                    
                    # Adjust max_results if user requested more than available
                    if self.config.max_results > total_available:
                        self.logger.info(f"📝 Adjusting max_results from {self.config.max_results} to {total_available} (all available)")
                        self.config.max_results = total_available
                
                for message in matches:
                    if total_fetched >= self.config.max_results:
                        break
                    yield message
                    total_fetched += 1
                
                # Progress reporting - use our tracked page number, not API response
                progress_pct = (total_fetched / self.config.max_results) * 100
                elapsed_time = time.time() - start_time
                rate = total_fetched / elapsed_time if elapsed_time > 0 else 0
                
                page_display = f"{page}/{total_pages}" if total_pages else str(page)
                self.logger.info(f"📈 Progress: {total_fetched:,}/{self.config.max_results:,} messages ({progress_pct:.1f}%) | "
                               f"Page {page_display} | "
                               f"Rate: {rate:.1f} msg/sec | "
                               f"Elapsed: {elapsed_time:.1f}s")
                
                # Check if we've reached the last page
                if total_pages and page >= total_pages:
                    self.logger.info(f"🏁 Reached last page ({page}/{total_pages})")
                    break
                
                # Show estimated remaining time every 10 pages
                if page % 10 == 0 and rate > 0:
                    remaining_messages = self.config.max_results - total_fetched
                    eta_seconds = remaining_messages / rate
                    self.logger.info(f"⏳ ETA for completion: {eta_seconds/60:.1f} minutes")
                
                page += 1
                
            except Exception as e:
                self.logger.error(f"❌ Error during search on page {page}: {e}")
                raise
        
        elapsed_time = time.time() - start_time
        final_rate = total_fetched / elapsed_time if elapsed_time > 0 else 0
        self.logger.info(f"🎉 Completed search! Fetched {total_fetched:,} messages in {elapsed_time:.1f}s ({final_rate:.1f} msg/sec)")


class StreamingFileWriter:
    """Handles incremental writing to files in different formats."""
    
    def __init__(self, filename: str, format_type: str, query: str):
        self.filename = filename
        self.format_type = format_type
        self.query = query
        self.file = None
        self.posts_written = 0
        self.start_time = time.time()
        
    def __enter__(self):
        self.file = open(self.filename, 'w', encoding='utf-8')
        
        if self.format_type in ['markdown', 'md']:
            self._write_markdown_header()
        elif self.format_type == 'json':
            self._write_json_header()
        elif self.format_type == 'jsonl':
            # JSON Lines format - no header needed, each line is a separate JSON object
            pass
        
        # Immediate flush and sync to make file visible right away
        self.file.flush()
        os.fsync(self.file.fileno())
            
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            if self.format_type == 'json':
                self._write_json_footer()
            self.file.close()
    
    def _write_markdown_header(self):
        """Write markdown file header."""
        self.file.write(f"# Slack Posts Export\n\n")
        self.file.write(f"**Query:** `{self.query}`  \n")
        self.file.write(f"**Started:** {time.strftime('%Y-%m-%d %H:%M:%S')}  \n")
        self.file.write(f"**Status:** In Progress...  \n\n")
        self.file.write("---\n\n")
        self.file.flush()
        os.fsync(self.file.fileno())
    
    def _write_json_header(self):
        """Write JSON file header."""
        self.file.write('{\n')
        self.file.write(f'  "query": {json.dumps(self.query)},\n')
        self.file.write(f'  "started_at": "{time.strftime("%Y-%m-%d %H:%M:%S")}",\n')
        self.file.write(f'  "posts": [\n')
        self.file.flush()
        os.fsync(self.file.fileno())
    
    def _write_json_footer(self):
        """Write JSON file footer."""
        self.file.write('\n  ],\n')
        self.file.write(f'  "total_posts": {self.posts_written},\n')
        self.file.write(f'  "completed_at": "{time.strftime("%Y-%m-%d %H:%M:%S")}"\n')
        self.file.write('}\n')
        self.file.flush()
    
    def write_post(self, post: Dict):
        """Write a single post to the file."""
        if self.format_type in ['markdown', 'md']:
            self._write_markdown_post(post)
        elif self.format_type == 'json':
            self._write_json_post(post)
        elif self.format_type == 'jsonl':
            self._write_jsonl_post(post)
        
        self.posts_written += 1
        
        # Flush frequently for real-time visibility
        if self.posts_written % 10 == 0:  # Every 10 posts instead of 50
            self.file.flush()
        
        # Force flush periodically to ensure OS writes to disk
        if self.posts_written % 100 == 0:
            self.file.flush()
            os.fsync(self.file.fileno())  # Force OS to write to disk
    
    def _write_markdown_post(self, post: Dict):
        """Write a single post in markdown format."""
        user_id = post.get('user', 'Unknown')
        text = post.get('text', '').strip()
        timestamp = post.get('ts', '')
        
        # Convert timestamp to readable date
        try:
            dt = datetime.datetime.fromtimestamp(float(timestamp))
            readable_date = dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            readable_date = timestamp
        
        # Get channel info if available
        channel = post.get('channel', {})
        channel_name = channel.get('name', 'Unknown Channel')
        
        # Get user info if available  
        user = post.get('username', user_id)
        
        # Write post
        self.file.write(f"## Post {self.posts_written + 1}\n\n")
        self.file.write(f"**Author:** {user} (`{user_id}`)  \n")
        self.file.write(f"**Channel:** #{channel_name}  \n")
        self.file.write(f"**Date:** {readable_date}  \n")
        self.file.write(f"**Timestamp:** {timestamp}  \n\n")
        
        # Handle message text with better formatting
        if text:
            # Basic Slack formatting cleanup
            formatted_text = text.replace('<@', '@').replace('>', '')
            # Preserve line breaks
            formatted_text = formatted_text.replace('\n', '  \n')
            self.file.write(f"**Message:**\n\n{formatted_text}\n\n")
        else:
            self.file.write("**Message:** *(No text content)*\n\n")
        
        # Add attachments/files info if present
        attachments = post.get('attachments', [])
        if attachments:
            self.file.write("**Attachments:**\n")
            for att in attachments:
                title = att.get('title', 'Untitled')
                url = att.get('title_link', att.get('url', ''))
                if url:
                    self.file.write(f"- [{title}]({url})\n")
                else:
                    self.file.write(f"- {title}\n")
            self.file.write("\n")
        
        # Add files info if present
        files = post.get('files', [])
        if files:
            self.file.write("**Files:**\n")
            for file_obj in files:
                name = file_obj.get('name', 'Unknown File')
                url = file_obj.get('url_private', file_obj.get('permalink', ''))
                filetype = file_obj.get('filetype', 'unknown')
                if url:
                    self.file.write(f"- [{name}]({url}) ({filetype})\n")
                else:
                    self.file.write(f"- {name} ({filetype})\n")
            self.file.write("\n")
        
        self.file.write("---\n\n")
        
        # Flush after each markdown post for immediate visibility
        self.file.flush()
    
    def _write_json_post(self, post: Dict):
        """Write a single post in JSON format."""
        if self.posts_written > 0:
            self.file.write(',\n')
        
        json.dump(post, self.file, indent=4, ensure_ascii=False)
        # Note: Don't flush here as it would break JSON format mid-stream
    
    def _write_jsonl_post(self, post: Dict):
        """Write a single post in JSON Lines format."""
        json.dump(post, self.file, ensure_ascii=False)
        self.file.write('\n')
        
        # Flush after each JSONL post for immediate visibility
        self.file.flush()


class SlackPostsFetcher:
    """Main class for fetching Slack posts."""
    
    def __init__(self, config: SlackConfig):
        self.config = config
        self.client = SlackAPIClient(config)
    
    def fetch_posts_with_streaming(self, output_file: Optional[str] = None, format_type: Optional[str] = None) -> int:
        """Fetch posts with streaming output and optional monthly chunking."""
        self.client.logger.info(f"🚀 Starting to fetch posts...")
        
        if self.config.monthly_chunks:
            return self._fetch_posts_monthly_chunks(output_file, format_type)
        else:
            return self._fetch_posts_single_query(output_file, format_type)

    def _fetch_posts_monthly_chunks(self, output_file: Optional[str], format_type: Optional[str]) -> int:
        """Fetch posts using monthly chunks to get complete history."""
        
        # Determine date range
        if self.config.start_date:
            start_date = datetime.datetime.strptime(self.config.start_date, '%Y-%m-%d')
        else:
            # Default to 2 years ago
            start_date = datetime.datetime.now() - datetime.timedelta(days=730)
            start_date = start_date.replace(day=1)  # Start of month
        
        if self.config.end_date:
            end_date = datetime.datetime.strptime(self.config.end_date, '%Y-%m-%d')
        else:
            end_date = datetime.datetime.now()
        
        self.client.logger.info(f"📅 Using monthly chunks from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Generate monthly chunks
        chunks = []
        current = start_date
        while current <= end_date:
            # Get last day of current month
            last_day = calendar.monthrange(current.year, current.month)[1]
            month_end = current.replace(day=last_day)
            
            # Don't go past the end date
            if month_end > end_date:
                month_end = end_date
            
            chunks.append((current, month_end))
            
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1, day=1)
            else:
                current = current.replace(month=current.month + 1, day=1)
        
        total_chunks = len(chunks)
        total_posts_written = 0
        
        self.client.logger.info(f"📊 Will process {total_chunks} monthly chunks")
        
        # Set up streaming file writer if output file specified
        writer = None
        if output_file:
            if not format_type:
                if output_file.lower().endswith(('.md', '.markdown')):
                    format_type = 'markdown'
                elif output_file.lower().endswith('.jsonl'):
                    format_type = 'jsonl'
                else:
                    format_type = 'json'
            
            writer = StreamingFileWriter(output_file, format_type, f"{self.config.query} (monthly chunks)")
        
        try:
            if writer:
                writer.__enter__()
            
            # Process each chunk
            for chunk_num, (chunk_start, chunk_end) in enumerate(chunks, 1):
                chunk_start_str = chunk_start.strftime('%Y-%m-%d')
                chunk_end_str = chunk_end.strftime('%Y-%m-%d')
                
                # Build query with date filter
                chunk_query = f"{self.config.query} after:{chunk_start_str} before:{chunk_end_str}"
                
                self.client.logger.info(f"📅 Chunk {chunk_num}/{total_chunks}: {chunk_start_str} to {chunk_end_str}")
                self.client.logger.info(f"🔍 Query: {chunk_query}")
                
                # Temporarily update config for this chunk
                original_query = self.config.query
                original_max_results = self.config.max_results
                self.config.query = chunk_query
                # Set a high limit for each chunk to get all messages in that month
                self.config.max_results = 10000  # Reasonable per-month limit
                
                try:
                    chunk_posts = 0
                    for post in self.client.search_messages():
                        if writer:
                            writer.write_post(post)
                        chunk_posts += 1
                        total_posts_written += 1
                        
                        # Respect overall max_results across all chunks
                        if total_posts_written >= original_max_results:
                            self.client.logger.info(f"🛑 Reached max_results limit ({original_max_results})")
                            break
                    
                    self.client.logger.info(f"✅ Chunk {chunk_num} completed: {chunk_posts} posts")
                    
                    if total_posts_written >= original_max_results:
                        break
                        
                finally:
                    # Restore original config
                    self.config.query = original_query
                    self.config.max_results = original_max_results
            
            self.client.logger.info(f"🎉 All chunks completed! Total posts: {total_posts_written}")
            
        finally:
            if writer:
                writer.__exit__(None, None, None)
        
        return total_posts_written

    def _fetch_posts_single_query(self, output_file: Optional[str], format_type: Optional[str]) -> int:
        """Fetch posts using a single query (original behavior)."""
        total_posts_written = 0
        
        # Apply date range to query if specified
        query = self.config.query
        if self.config.date_range:
            if ':' in self.config.date_range:
                start_date, end_date = self.config.date_range.split(':', 1)
                if start_date:
                    query += f" after:{start_date}"
                if end_date:
                    query += f" before:{end_date}"
            else:
                query += f" after:{self.config.date_range}"
        
        self.client.logger.info(f"🔍 Final query: {query}")
        
        # Temporarily update config
        original_query = self.config.query
        self.config.query = query
        
        try:
            # Set up streaming file writer if output file specified
            writer = None
            if output_file:
                if not format_type:
                    if output_file.lower().endswith(('.md', '.markdown')):
                        format_type = 'markdown'
                    elif output_file.lower().endswith('.jsonl'):
                        format_type = 'jsonl'
                    else:
                        format_type = 'json'
                
                writer = StreamingFileWriter(output_file, format_type, query)
            
            try:
                if writer:
                    writer.__enter__()
                
                for post in self.client.search_messages():
                    if writer:
                        writer.write_post(post)
                    total_posts_written += 1
            
            finally:
                if writer:
                    writer.__exit__(None, None, None)
                    
        finally:
            # Restore original query
            self.config.query = original_query
        
        return total_posts_written

    # Keep the old method for backwards compatibility
    def fetch_posts(self, output_file: Optional[str] = None, format_type: Optional[str] = None) -> List[Dict]:
        """Legacy method - returns empty list but does streaming fetch."""
        self.fetch_posts_with_streaming(output_file, format_type)
        return []  # Return empty list since we're streaming


def create_config_from_args() -> SlackConfig:
    """Create configuration from command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch Slack posts using search API with rate limiting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python slack_fetcher.py -t xoxp-your-token -q "from:U123456789" -o posts.md
  
  # Get complete history using monthly chunks (RECOMMENDED for full history)
  python slack_fetcher.py -t xoxp-your-token -q "from:U123456789" --monthly-chunks -o complete_history.md
  
  # Specific date range
  python slack_fetcher.py -t xoxp-your-token -q "from:U123456789" --date-range "2024-01-01:2024-12-31" -o 2024_posts.md
  
  # Last 6 months using monthly chunks
  python slack_fetcher.py -t xoxp-your-token -q "from:U123456789" --monthly-chunks --start-date "2024-12-01" -o recent_posts.md
  
  # Everything from 2023 onwards
  python slack_fetcher.py -t xoxp-your-token -q "from:U123456789" --monthly-chunks --start-date "2023-01-01" -o full_history.md
  
  # Channel-specific with date range
  python slack_fetcher.py -t xoxp-your-token -q "in:#general" --date-range "2024-06-01:" -o general_recent.md
        """
    )
    
    parser.add_argument(
        '-t', '--token',
        required=True,
        help='Slack Bot User OAuth Token (xoxb-...)'
    )
    
    parser.add_argument(
        '-q', '--query',
        required=True,
        help='Slack search query (e.g., "from:@user", "in:#channel", "has:link")'
    )
    
    parser.add_argument(
        '-m', '--max-results',
        type=int,
        default=100,
        help='Maximum number of results to fetch (default: 100)'
    )
    
    parser.add_argument(
        '--page-size',
        type=int,
        default=20,
        help='Number of results per API call (default: 20, max: 100)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file to save results (format detected by extension: .json, .jsonl, .md)'
    )
    
    parser.add_argument(
        '--date-range',
        help='Date range for search in YYYY-MM-DD format. Examples: "2024-01-01:2024-12-31", "2024-06-01:", ":2024-05-31"'
    )
    
    parser.add_argument(
        '--monthly-chunks',
        action='store_true',
        help='Automatically break search into monthly chunks to get complete history'
    )
    
    parser.add_argument(
        '--start-date',
        help='Start date for monthly chunks (YYYY-MM-DD). Defaults to 2 years ago if not specified'
    )
    
    parser.add_argument(
        '--end-date',
        help='End date for monthly chunks (YYYY-MM-DD). Defaults to today if not specified'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=5,
        help='Maximum number of retries for failed requests (default: 5)'
    )
    
    parser.add_argument(
        '--base-delay',
        type=float,
        default=1.0,
        help='Base delay for exponential backoff in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate page size
    if args.page_size > 100:
        parser.error("Page size cannot exceed 100 (Slack API limit)")
    
    return SlackConfig(
        token=args.token,
        query=args.query,
        max_results=args.max_results,
        results_per_page=args.page_size,
        max_retries=args.max_retries,
        base_delay=args.base_delay,
        date_range=args.date_range,
        monthly_chunks=args.monthly_chunks,
        start_date=args.start_date,
        end_date=args.end_date
    )


def main():
    """Main entry point."""
    try:
        config = create_config_from_args()
        
        # Nice startup summary
        print("=" * 60)
        print("🔍 SLACK POSTS FETCHER")
        print("=" * 60)
        print(f"📝 Query: {config.query}")
        
        if config.monthly_chunks:
            print("📅 Mode: Monthly chunks")
            if config.start_date:
                print(f"📅 Start date: {config.start_date}")
            if config.end_date:
                print(f"📅 End date: {config.end_date}")
        elif config.date_range:
            print(f"📅 Date range: {config.date_range}")
        else:
            print("📅 Mode: Recent messages")
            
        print(f"📊 Max results: {config.max_results:,}")
        print(f"📄 Page size: {config.results_per_page}")
        print(f"🔄 Max retries: {config.max_retries}")
        print(f"⏱️  Base delay: {config.base_delay}s")
        print("=" * 60)
        
        fetcher = SlackPostsFetcher(config)
        
        # Parse output file and format from args
        import sys
        output_file = None
        output_format = None
        
        if '-o' in sys.argv or '--output' in sys.argv:
            try:
                idx = sys.argv.index('-o') if '-o' in sys.argv else sys.argv.index('--output')
                output_file = sys.argv[idx + 1]
                print(f"📁 Output file: {output_file}")
            except (IndexError, ValueError):
                pass
        
        if '--format' in sys.argv:
            try:
                idx = sys.argv.index('--format')
                output_format = sys.argv[idx + 1]
                print(f"📄 Output format: {output_format}")
            except (IndexError, ValueError):
                pass
        
        # Auto-detect format from filename if not specified
        if output_file and not output_format:
            if output_file.lower().endswith(('.md', '.markdown')):
                output_format = 'markdown'
                print(f"📝 Auto-detected format: markdown")
            elif output_file.lower().endswith('.jsonl'):
                output_format = 'jsonl'
                print(f"📄 Auto-detected format: JSON Lines")
            else:
                output_format = 'json'
                print(f"📄 Auto-detected format: json")
        
        if output_file:
            print("=" * 60)
        
        posts_count = fetcher.fetch_posts_with_streaming(output_file, output_format)
        
        print("\n" + "=" * 60)
        print("📈 FINAL SUMMARY")
        print("=" * 60)
        
        if not output_file:
            # Print summary to stdout
            print(f"✅ Fetched {posts_count:,} posts for query: '{config.query}'")
            print("💡 Use -o filename to save results and see post samples")
        else:
            print(f"✅ Fetched and saved {posts_count:,} posts to {output_file}")
        
        print("=" * 60)
        print("🎉 COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("⛔ OPERATION CANCELLED BY USER")
        print("=" * 60)
        sys.exit(1)
    except Exception as e:
        print(f"\n" + "=" * 60)
        print("💥 ERROR OCCURRED")
        print("=" * 60)
        print(f"❌ {e}")
        print("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()
