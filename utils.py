#!/usr/bin/env python3
"""
Slack Export Utilities

Standardized logging, progress tracking, and rate limiting utilities
for all Slack export tools.
"""

import time
import sys
import os
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

class SlackLogger:
    """Standardized logging for Slack export tools."""
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.start_time = time.time()
    
    def phase(self, phase_num: int, description: str):
        """Log a major phase of operation."""
        print(f"\n📋 Phase {phase_num}: {description}")
    
    def info(self, message: str, indent: int = 0):
        """Log general information."""
        prefix = "  " * indent
        print(f"{prefix}ℹ️  {message}")
    
    def success(self, message: str, indent: int = 0):
        """Log success message."""
        prefix = "  " * indent
        print(f"{prefix}✅ {message}")
    
    def warning(self, message: str, indent: int = 0):
        """Log warning message."""
        prefix = "  " * indent
        print(f"{prefix}⚠️  Warning: {message}")
    
    def error(self, message: str, indent: int = 0):
        """Log error message."""
        prefix = "  " * indent
        print(f"{prefix}❌ Error: {message}")
    
    def progress(self, current: int, total: int, description: str = "", end: str = "\r"):
        """Log progress with consistent formatting."""
        percentage = (current / total * 100) if total > 0 else 0
        bar_length = 20
        filled_length = int(bar_length * current // total) if total > 0 else 0
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        elapsed = time.time() - self.start_time
        if current > 0 and total > current:
            eta = (elapsed / current) * (total - current)
            eta_str = f" ETA: {eta:.0f}s" if eta > 0 else ""
        else:
            eta_str = ""
        
        progress_msg = f"  📊 Progress: {current:,}/{total:,} ({percentage:.1f}%) |{bar}|{eta_str}"
        if description:
            progress_msg += f" - {description}"
        
        print(progress_msg, end=end, flush=True)
        
        if current == total:
            print()  # New line when complete
    
    def api_call(self, endpoint: str, page: int = None, result_count: int = None):
        """Log API call with consistent formatting."""
        page_info = f" page {page}" if page else ""
        result_info = f" ({result_count} items)" if result_count is not None else ""
        print(f"  🔄 API: {endpoint}{page_info}{result_info}", flush=True)
    
    def completion_summary(self, total_items: int, total_time: float):
        """Log completion summary."""
        rate = total_items / total_time if total_time > 0 else 0
        print(f"\n🎉 Complete! Processed {total_items:,} items in {total_time:.1f}s ({rate:.1f} items/sec)")


class SlackRateLimiter:
    """Standardized rate limiting and backoff for Slack API calls."""
    
    def __init__(self, logger: SlackLogger):
        self.logger = logger
        self.last_request_time = 0
        self.min_interval = 0.1  # Minimum 100ms between requests
    
    def handle_rate_limit(self, response) -> bool:
        """
        Handle rate limiting from Slack API response.
        Returns True if request should be retried, False otherwise.
        """
        if response.status_code == 429:
            # Explicit rate limit
            retry_after = self._get_retry_after(response)
            self.logger.warning(f"Rate limited - waiting {retry_after:.1f}s", indent=1)
            time.sleep(retry_after)
            return True
        
        # Check rate limit headers proactively
        remaining = response.headers.get('X-Rate-Limit-Remaining')
        if remaining and int(remaining) <= 1:
            reset_time = self._get_reset_time(response)
            if reset_time > 0:
                self.logger.info(f"Approaching rate limit - waiting {reset_time:.1f}s", indent=1)
                time.sleep(reset_time)
        
        return False
    
    def _get_retry_after(self, response) -> float:
        """Get retry-after time with safety buffer."""
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                wait_time = float(retry_after)
                # Add 10% buffer for safety
                return wait_time * 1.1
            except ValueError:
                pass
        
        # Default fallback
        return 60.0
    
    def _get_reset_time(self, response) -> float:
        """Get time to wait until rate limit resets."""
        reset_header = response.headers.get('X-Rate-Limit-Reset')
        if reset_header:
            try:
                reset_time = float(reset_header)
                wait_time = max(0, reset_time - time.time()) + 1  # Add 1 second buffer
                return wait_time
            except ValueError:
                pass
        
        return 1.0  # Default 1 second wait
    
    def throttle_request(self):
        """Ensure minimum interval between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def exponential_backoff(self, attempt: int, max_wait: float = 300.0) -> float:
        """Calculate exponential backoff delay."""
        base_delay = 1.0
        max_attempts = 10
        
        if attempt >= max_attempts:
            return max_wait
        
        delay = min(base_delay * (2 ** attempt), max_wait)
        self.logger.info(f"Backoff attempt {attempt + 1}: waiting {delay:.1f}s", indent=1)
        time.sleep(delay)
        return delay


class SlackExporter:
    """Base class for all Slack export tools with standardized utilities."""
    
    def __init__(self, token: str, tool_name: str):
        self.token = token
        self.logger = SlackLogger(tool_name)
        self.rate_limiter = SlackRateLimiter(self.logger)
        self.session = None
        self._setup_session()
    
    def _setup_session(self):
        """Setup requests session with consistent headers."""
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'User-Agent': f'SlackExporter/{self.logger.tool_name}'
        })
    
    def make_api_request(self, url: str, params: Dict[str, Any] = None, max_retries: int = 5) -> Optional[Dict[str, Any]]:
        """
        Make standardized API request with consistent error handling and backoff.
        """
        if params is None:
            params = {}
        
        for attempt in range(max_retries):
            try:
                # Throttle requests
                self.rate_limiter.throttle_request()
                
                # Make request
                response = self.session.get(url, params=params, timeout=30)
                
                # Handle rate limiting
                if self.rate_limiter.handle_rate_limit(response):
                    continue  # Retry after rate limit handling
                
                # Check response
                response.raise_for_status()
                data = response.json()
                
                if not data.get('ok'):
                    error = data.get('error', 'Unknown error')
                    if error in ['ratelimited']:
                        # Additional rate limit handling
                        continue
                    elif error == 'missing_scope':
                        self.logger.error("Missing required OAuth scopes")
                        self.logger.info("Required scopes depend on operation:", indent=1)
                        self.logger.info("- Bookmarks: stars:read, channels:read, users:read", indent=1)
                        self.logger.info("- DMs: im:history, groups:history, channels:read", indent=1)
                        self.logger.info("- Search: search:read, channels:read, users:read", indent=1)
                        return None
                    else:
                        self.logger.error(f"API error: {error}")
                        return None
                
                return data
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    self.rate_limiter.exponential_backoff(attempt)
                    continue
                else:
                    self.logger.error(f"Network error after {max_retries} attempts: {e}")
                    return None
            except Exception as e:
                if attempt < max_retries - 1:
                    self.rate_limiter.exponential_backoff(attempt)
                    continue
                else:
                    self.logger.error(f"API request failed after {max_retries} attempts: {e}")
                    return None
        
        return None
    
    def export_summary(self, output_file: str, total_items: int, export_time: float):
        """Log standardized export summary."""
        self.logger.success(f"Export complete!")
        self.logger.info(f"📁 Output file: {output_file}")
        self.logger.info(f"📊 Total items: {total_items:,}")
        self.logger.info(f"⏱️  Export time: {export_time:.1f}s")

        if total_items > 0:
            rate = total_items / export_time
            self.logger.info(f"🚀 Processing rate: {rate:.1f} items/sec")

    def download_file(self, file_obj: Dict[str, Any], download_dir: str,
                      channel_name: str, user_id: str, filename_counter: Dict) -> Optional[str]:
        """
        Download a file from Slack with authentication.

        Returns local file path if successful, None otherwise.
        """
        url = file_obj.get('url_private_download') or file_obj.get('url_private')
        if not url:
            self.logger.warning("No download URL found for file", indent=2)
            return None

        # Create channel-specific subdirectory
        channel_dir = os.path.join(download_dir, sanitize_dirname(channel_name))
        os.makedirs(channel_dir, exist_ok=True)

        # Generate safe filename
        filename = generate_safe_filename(file_obj, user_id, filename_counter)
        filepath = os.path.join(channel_dir, filename)

        # Download with retries
        for attempt in range(3):
            try:
                self.rate_limiter.throttle_request()
                response = self.session.get(url, stream=True, timeout=60)
                response.raise_for_status()

                # Stream to disk
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                file_size = os.path.getsize(filepath)
                self.logger.info(f"Downloaded: {filename} ({file_size:,} bytes)", indent=2)
                return filepath

            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    self.rate_limiter.exponential_backoff(attempt)
                else:
                    self.logger.error(f"Failed to download {filename}: {e}", indent=2)
                    return None

        return None

    def download_message_files(self, message: Dict, download_dir: str,
                               channel_name: str) -> Dict[str, int]:
        """
        Download all files attached to a message.

        Returns dict with download statistics.
        """
        files = message.get('files', [])
        if not files:
            return {'success': 0, 'failed': 0, 'total': 0}

        user_id = message.get('user_id', message.get('user', 'unknown'))
        filename_counter = {}
        stats = {'success': 0, 'failed': 0, 'total': len(files)}

        for file_obj in files:
            filepath = self.download_file(file_obj, download_dir, channel_name,
                                         user_id, filename_counter)
            if filepath:
                # Store local path in file object
                file_obj['local_path'] = os.path.relpath(filepath, os.path.dirname(download_dir))
                stats['success'] += 1
            else:
                stats['failed'] += 1

        return stats


def format_timestamp(ts: str) -> str:
    """Convert Slack timestamp to readable format."""
    try:
        timestamp = float(ts)
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return ts


def get_user_name(user_cache: Dict[str, str], user_id: str, session: requests.Session) -> str:
    """Get user name with caching."""
    if user_id in user_cache:
        return user_cache[user_id]
    
    try:
        response = session.get(f'https://slack.com/api/users.info', params={'user': user_id})
        if response.status_code == 200:
            data = response.json()
            if data.get('ok') and 'user' in data:
                name = data['user'].get('real_name') or data['user'].get('display_name') or data['user'].get('name', user_id)
                user_cache[user_id] = name
                return name
    except Exception:
        pass
    
    user_cache[user_id] = user_id
    return user_id


def get_channel_name(channel_cache: Dict[str, str], channel_id: str, session: requests.Session) -> str:
    """Get channel name with caching."""
    if channel_id in channel_cache:
        return channel_cache[channel_id]

    try:
        # Try conversations.info first
        response = session.get(f'https://slack.com/api/conversations.info', params={'channel': channel_id})
        if response.status_code == 200:
            data = response.json()
            if data.get('ok') and 'channel' in data:
                name = data['channel'].get('name', channel_id)
                if name != channel_id:
                    name = f"#{name}"
                channel_cache[channel_id] = name
                return name
    except Exception:
        pass

    channel_cache[channel_id] = channel_id
    return channel_id


def sanitize_filename(filename: str) -> str:
    """Remove invalid filesystem characters and truncate if needed."""
    invalid_chars = '<>:"|?*\\/\n\r'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    # Truncate to 200 chars (reserve space for prefix)
    if len(filename) > 200:
        base, ext = os.path.splitext(filename)
        filename = base[:200-len(ext)] + ext
    return filename


def sanitize_dirname(channel_name: str) -> str:
    """Create safe directory name from channel."""
    clean_name = channel_name.lstrip('#')
    clean_name = sanitize_filename(clean_name)
    return clean_name[:100]


def generate_safe_filename(file_obj: Dict, user_id: str, counter: Dict) -> str:
    """Generate unique filename with collision handling."""
    timestamp = file_obj.get('timestamp', file_obj.get('created', ''))
    try:
        date = datetime.fromtimestamp(float(timestamp)).strftime('%Y%m%d')
    except (ValueError, TypeError):
        date = datetime.now().strftime('%Y%m%d')

    user_short = user_id[:8] if user_id else 'unknown'
    original_name = sanitize_filename(file_obj.get('name', 'file'))

    # Create base filename
    base_name, ext = os.path.splitext(original_name)
    base = f"{date}_{user_short}_{base_name}"

    # Handle duplicates
    key = f"{base}{ext}"
    count = counter.get(key, 0)

    if count > 0:
        filename = f"{base}_{count}{ext}"
    else:
        filename = f"{base}{ext}"

    counter[key] = count + 1
    return filename
