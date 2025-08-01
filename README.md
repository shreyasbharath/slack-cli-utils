# Slack DM History Fetcher

A Python tool to fetch and export Slack Direct Message (DM) history with progress tracking and robust error handling.

## Quick Decision Guide

- **For Direct Messages (DMs)**: Use `fetch_dm_history.py`
- **For Channels or Complex Searches**: Use `slack_posts_fetcher.py`
- **To Find Channel IDs**: Use `list_conversations.py`

## Features

- 📥 Fetches complete DM history from any Slack conversation
- 📊 Real-time progress tracking (X/Y messages)
- 💾 Streaming write - messages saved immediately (no data loss on failure)
- 🔄 Smart rate limit handling with proper backoff
- 📝 Exports to clean, readable Markdown format
- 🎯 Includes messages, reactions, files, attachments, and thread info
- ⚡ Optimised for speed while respecting API limits

## Prerequisites

- Python 3.6+
- `requests` library (`pip install requests`)
- Slack User OAuth Token (see below)

## Installation

1. Clone or download this repository:
   ```bash
   cd /Users/shreyas/Downloads/slack
   ```

2. Install dependencies:
   ```bash
   pip install requests
   ```

## Getting Your Slack Token

You need a Slack User OAuth Token (starts with `xoxp-`) with the following scopes:
- `channels:history` (for public channels)
- `groups:history` (for private channels)
- `im:history` (for direct messages)
- `mpim:history` (for group DMs)

To get your token:
1. Go to https://api.slack.com/apps
2. Create a new app or select an existing one
3. Navigate to "OAuth & Permissions"
4. Add the required scopes listed above
5. Install the app to your workspace
6. Copy the "User OAuth Token" (starts with `xoxp-`)

## Finding Your DM Channel ID

1. Run the channel listing script first:
   ```bash
   python3 list_conversations.py "xoxp-your-token-here"
   ```

2. Look for your DM in the output. It will show something like:
   ```
   Direct Message Channels (82):
     ID: D0889Q50GPM - User: U07C33KQM5Z
   ```

3. Copy the channel ID (e.g., `D0889Q50GPM`)

## Usage

### Using `fetch_dm_history.py` (Best for DMs)

Fetch messages from January 2025 onwards (default):
```bash
python fetch_dm_history.py -t "xoxp-your-token-here" -c D0889Q50GPM
```

Fetch all messages from January 2024:
```bash
python fetch_dm_history.py -t "xoxp-your-token-here" -c D0889Q50GPM -s 2024-01-01
```

Specify your own output filename:
```bash
python fetch_dm_history.py -t "xoxp-your-token-here" -c D0889Q50GPM -o my_conversation.md
```

### Using `slack_posts_fetcher.py` (Best for Channels & Search)

This script uses Slack's search API and is more powerful for complex queries.

#### Basic Usage

Search for messages from a specific user:
```bash
python slack_posts_fetcher.py -t "xoxp-your-token" -q "from:U123456789" -o user_posts.md
```

Search in a specific channel:
```bash
python slack_posts_fetcher.py -t "xoxp-your-token" -q "in:#general" -o general_channel.md
```

#### Get Complete History with Monthly Chunks (Recommended)

For complete history, use monthly chunks to overcome search API limitations:
```bash
python slack_posts_fetcher.py -t "xoxp-your-token" -q "from:U123456789" --monthly-chunks -o complete_history.md
```

With custom date range:
```bash
python slack_posts_fetcher.py -t "xoxp-your-token" -q "in:#general" --monthly-chunks --start-date "2023-01-01" --end-date "2024-12-31" -o 2023-2024_posts.md
```

#### Advanced Search Queries

Combine multiple search operators:
```bash
# Messages from user containing "project"
python slack_posts_fetcher.py -t "xoxp-your-token" -q "from:U123456789 project" -o project_messages.md

# Messages with attachments in specific channel
python slack_posts_fetcher.py -t "xoxp-your-token" -q "in:#general has:attachment" -o attachments.md

# Messages containing links from last 30 days
python slack_posts_fetcher.py -t "xoxp-your-token" -q "has:link" --date-range "2024-12-01:" -o recent_links.md
```

#### Output Formats

The script supports multiple output formats:
```bash
# Markdown (default for .md extension)
python slack_posts_fetcher.py -t "xoxp-your-token" -q "from:me" -o my_posts.md

# JSON format
python slack_posts_fetcher.py -t "xoxp-your-token" -q "from:me" -o my_posts.json

# JSON Lines format (one JSON object per line)
python slack_posts_fetcher.py -t "xoxp-your-token" -q "from:me" -o my_posts.jsonl
```

### Command Line Options

#### `fetch_dm_history.py` Options

- `-t, --token` (required): Your Slack User OAuth Token
- `-c, --channel` (required): The DM channel ID
- `-s, --since`: Start date in YYYY-MM-DD format (default: 2025-01-01)
- `-o, --output`: Output file path (default: auto-generated with timestamp)

#### `slack_posts_fetcher.py` Options

- `-t, --token` (required): Slack Bot User OAuth Token (xoxb-...)
- `-q, --query` (required): Slack search query
- `-m, --max-results`: Maximum number of results (default: 100)
- `--page-size`: Results per API call (default: 20, max: 100)
- `-o, --output`: Output file (.md, .json, or .jsonl)
- `--date-range`: Date range in YYYY-MM-DD format (e.g., "2024-01-01:2024-12-31")
- `--monthly-chunks`: Break search into monthly chunks for complete history
- `--start-date`: Start date for monthly chunks (default: 2 years ago)
- `--end-date`: End date for monthly chunks (default: today)
- `--max-retries`: Maximum retry attempts (default: 5)
- `--base-delay`: Base delay for exponential backoff (default: 1.0)
- `-v, --verbose`: Enable verbose logging

## Slack Search Query Syntax

The `slack_posts_fetcher.py` script supports Slack's powerful search operators:

### User Operators
- `from:@username` or `from:U123456` - Messages from specific user
- `to:@username` - Messages to specific user

### Channel Operators
- `in:#channel` - Messages in specific channel
- `in:@username` - DMs with specific user (Note: use channel ID directly for better results)

### Content Operators
- `has:attachment` - Messages with attachments
- `has:link` - Messages containing links
- `has:reaction` - Messages with reactions
- `is:starred` - Starred messages

### Date Operators
- `after:2024-01-01` - Messages after date
- `before:2024-12-31` - Messages before date
- `during:2024-06` - Messages during specific month

### Combining Operators
```bash
# User's messages in specific channel with attachments
"from:U123456 in:#general has:attachment"

# Messages mentioning "deploy" in last week
"deploy after:2024-12-25"
```

## Example Output

The script creates a Markdown file with messages formatted like:

```markdown
# DM Conversation History

**Channel ID:** D0889Q50GPM
**Messages since:** 2024-01-01
**Export date:** 2025-07-15 12:45:30
**Total messages:** 523

---

## Message 1

**User:** U07C33KQM5Z
**Date:** 2024-01-15 09:30:45
**Timestamp:** 1705308645.123456

**Message:**

Hello, this is a sample message!

---
```

## Progress Tracking

The script shows real-time progress in two phases:

```
Phase 1: Collecting all messages...
  Scanning page 5... (found 823 messages so far)

Found 1047 messages to process

Phase 2: Writing messages to file...
  Progress: 523/1047 messages (49.9%)
```

## Troubleshooting

### No messages found
- Verify the channel ID is correct
- Check that your token has the required permissions
- Ensure there are messages in the specified date range

### Rate limiting
The script handles rate limits automatically, but if you're frequently rate limited:
- The script will wait the exact time Slack specifies (plus 10% buffer)
- Consider fetching smaller date ranges

### Permission errors
If you get "missing_scope" errors, your token needs additional permissions:
- `im:history` for DMs
- `groups:history` for private channels
- `mpim:history` for group DMs

## Files in This Project

### 1. `fetch_dm_history.py` - Direct Message Fetcher (Recommended for DMs)
Main script for fetching DM history using the conversations.history API. Best for:
- Direct messages (DMs)
- Private conversations
- When you have a specific channel ID

### 2. `slack_posts_fetcher.py` - Search-based Fetcher (Recommended for Channels)
Powerful search-based fetcher using Slack's search API. Best for:
- Public channels
- Finding messages by user across multiple channels
- Complex search queries
- Getting complete history with monthly chunks

### 3. `list_conversations.py` - Channel Finder
Helper script to find channel IDs and list all accessible conversations.

### 4. `slack_post_individual.py` - Message Extractor
Script for extracting messages by author from already exported Markdown files.

## Example Use Cases

### 1. Export Your DM with a Colleague
```bash
# First, find the DM channel ID
python3 list_conversations.py "xoxp-your-token"

# Then fetch the messages
python fetch_dm_history.py -t "xoxp-your-token" -c D0889Q50GPM -s 2024-01-01
```

### 2. Export All Your Messages Across Slack
```bash
# Find your user ID first (look for "from:USERID" in any Slack message you sent)
python slack_posts_fetcher.py -t "xoxp-your-token" -q "from:U123456789" --monthly-chunks -o all_my_messages.md
```

### 3. Archive a Project Channel
```bash
python slack_posts_fetcher.py -t "xoxp-your-token" -q "in:#project-alpha" --monthly-chunks --start-date "2023-06-01" -o project_alpha_archive.md
```

### 4. Find All Messages with Attachments from Someone
```bash
python slack_posts_fetcher.py -t "xoxp-your-token" -q "from:U123456789 has:attachment" -m 1000 -o user_attachments.md
```

## Tips

1. **Large Conversations**: The script handles large conversations well, writing messages incrementally to prevent data loss.

2. **Multiple Exports**: Output files are timestamped by default, so you won't accidentally overwrite previous exports.

3. **Partial Exports**: If the script fails partway through, the output file will contain all messages fetched up to that point.

4. **Date Ranges**: To fetch a specific date range, run multiple exports with different start dates.

## Support

If you encounter issues:
1. Check that your token is valid and has required permissions
2. Verify the channel ID using `list_conversations.py`
3. Try a more recent date to test with fewer messages
4. Check the error messages - they usually indicate what's wrong

## License

This tool is for personal use. Ensure you comply with your organisation's Slack data retention and privacy policies.
