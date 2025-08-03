# Slack Export Tool

A unified Python tool to export Slack data with multiple specialized fetchers and an easy-to-use interface.

## 🚀 Quick Start (Recommended)

Just run the main script and follow the interactive menu:

```bash
python slack.py
```

The interactive mode will guide you through:
- Choosing what to export (bookmarks, DMs, channels, search results)
- Getting your Slack token
- Configuring export options
- Running the appropriate specialized tool

## Quick Decision Guide

- **New to this tool?** → Use `python slack.py` (interactive mode)
- **For Bookmarked Messages** → `python slack.py bookmarks`
- **For Direct Messages (DMs)** → `python slack.py dm`
- **For Channels or Complex Searches** → `python slack.py channel` or `python slack.py search`
- **To Find Channel IDs** → `python slack.py list`

## Features

- 🎯 **Unified Interface**: Single command for all export operations
- 📥 **Multiple Export Types**: DMs, channels, bookmarks, search results
- 🔄 **Interactive & CLI Modes**: Choose your preferred workflow
- 📊 **Real-time Progress**: Track export progress (X/Y messages)
- 💾 **Multiple Formats**: Markdown, JSON, JSONL output
- 🔄 **Smart Rate Limiting**: Automatic backoff and retry
- 📝 **Rich Context**: Channel names, user names, timestamps, reactions
- ⚡ **Optimized Performance**: Streaming writes, concurrent processing

## Prerequisites

- Python 3.6+
- `requests` library (`pip install requests`)
- Slack User OAuth Token (see below)

## Installation

1. Clone or download this repository:
   ```bash
   cd /Users/shreyas/Downloads/slack
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   # Create virtual environment
   python3 -m venv slack-export-env
   
   # Activate virtual environment
   # On macOS/Linux:
   source slack-export-env/bin/activate
   
   # On Windows:
   # slack-export-env\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   # Option 1: Install from requirements file (recommended)
   pip install -r requirements.txt
   
   # Option 2: Install manually
   pip install requests
   ```

4. **Verify installation:**
   ```bash
   python slack.py --help
   ```

### Virtual Environment Notes

- **Why use a virtual environment?** Keeps dependencies isolated from your system Python
- **Activation required:** Run `source slack-export-env/bin/activate` each time you use the tool
- **Deactivation:** Run `deactivate` when finished
- **Requirements file:** All dependencies are listed in the single `requests` library

## Getting Your Slack Token

You need a Slack User OAuth Token (starts with `xoxp-`) with appropriate scopes based on what you want to export:

### Required Scopes by Operation

| Operation | Required Scopes |
|-----------|----------------|
| **Bookmarks** | `stars:read`, `channels:read`, `users:read`, `groups:read` |
| **DMs** | `im:history`, `groups:history`, `channels:read`, `users:read` |
| **Channels** | `search:read`, `channels:read`, `users:read` |
| **Search** | `search:read`, `channels:read`, `users:read` |
| **List** | `channels:read`, `groups:read`, `im:read` |

### Getting Your Token
1. Go to https://api.slack.com/apps
2. Create a new app or select an existing one
3. Navigate to "OAuth & Permissions"
4. Add the required scopes for your use case
5. Install the app to your workspace
6. Copy the "User OAuth Token" (starts with `xoxp-`)

## Usage Examples

### Interactive Mode (Easiest)
```bash
# Launch interactive menu
python slack.py

# Follow the prompts to:
# 1. Choose export type
# 2. Enter your token
# 3. Configure options
# 4. Run the export
```

### Direct Commands

#### Export Bookmarks
```bash
# Basic bookmarks export
python slack.py bookmarks -t "xoxp-your-token" -o my_bookmarks.md

# JSON format
python slack.py bookmarks -t "xoxp-your-token" -o bookmarks.json

# Custom page size
python slack.py bookmarks -t "xoxp-your-token" --page-size 50 -o bookmarks.md
```

#### Export DM Conversation
```bash
# Export DM from 2024
python slack.py dm -t "xoxp-your-token" -c D0889Q50GPM --since 2024-01-01

# Recent messages only (default: 2025-01-01)
python slack.py dm -t "xoxp-your-token" -c D0889Q50GPM -o conversation.md
```

#### Export Channel Messages
```bash
# Export channel with complete history
python slack.py channel -t "xoxp-your-token" -q "in:#general" --monthly-chunks

# Export recent channel messages
python slack.py channel -t "xoxp-your-token" -q "in:#engineering" -m 500
```

#### Search Messages
```bash
# Messages from specific user
python slack.py search -t "xoxp-your-token" -q "from:@username" -o user_messages.md

# Messages with attachments
python slack.py search -t "xoxp-your-token" -q "has:attachment" --monthly-chunks

# Complex search
python slack.py search -t "xoxp-your-token" -q "in:#general project after:2024-01-01"
```

#### List Channels and DMs
```bash
# Show all available channels and DMs with IDs
python slack.py list -t "xoxp-your-token"
```

## Search Query Syntax

When using search operations, you can use Slack's powerful search operators:

### User & Channel Operators
- `from:@username` - Messages from specific user
- `to:@username` - Messages to specific user  
- `in:#channel` - Messages in specific channel
- `in:@username` - DMs with specific user

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
"from:username in:#general has:attachment"

# Recent important messages
"is:starred after:2024-12-01"
```

## Output Formats

### Markdown Format (Default)
Human-readable format with rich formatting, perfect for documentation and review.

### JSON Format  
Structured data format for programmatic processing:
```bash
python slack.py bookmarks -t "token" -o data.json
```

### JSONL Format
One JSON object per line, ideal for streaming processing:
```bash
python slack.py search -t "token" -q "query" -o results.jsonl
```

## Advanced Usage

### Monthly Chunks for Complete History
For channels with extensive history, use monthly chunks to overcome API limitations:
```bash
python slack.py channel -t "token" -q "in:#general" --monthly-chunks
```

### Custom Date Ranges
```bash
# DMs from specific period
python slack.py dm -t "token" -c CHANNEL_ID --since 2023-06-01

# Search with date bounds
python slack.py search -t "token" -q "project after:2024-01-01 before:2024-06-30"
```

## Project Structure

```
slack/
├── slack.py                    # 🎯 Main unified CLI (START HERE)
├── fetch_bookmarks.py          # Bookmarks/starred messages fetcher
├── fetch_dm_history.py         # Direct message history fetcher  
├── fetch_channel_search.py     # Search-based channel/message fetcher
├── list_conversations.py       # Channel and DM discovery tool
├── extract_messages.py         # Message extraction from exports
├── requirements.txt            # Python dependencies
└── README.md                   # This documentation
```

### When to Use Each Tool Directly

Most users should use `python slack.py`, but you can call the specialized tools directly:

- **`fetch_bookmarks.py`**: When you only need bookmarks and want fine control
- **`fetch_dm_history.py`**: For DM exports with specific date ranges
- **`fetch_channel_search.py`**: For complex search queries and channel exports
- **`list_conversations.py`**: When you need to discover channel IDs

## Detailed Tool Documentation

### 1. Bookmarks Export (`fetch_bookmarks.py`)

Fetches all your starred/bookmarked messages across all channels with rich context.

#### Command Options
- `-t, --token` (required): Your Slack User OAuth Token
- `-o, --output`: Output file path (default: timestamped)
- `--page-size`: Number of bookmarks per API call (default: 100)

#### Example Output Format
```markdown
# Slack Bookmarked Messages

**Export date:** 2025-08-04 14:30:00
**Total bookmarks:** 47

---

## Bookmark 1

**Bookmarked:** 2025-07-10T14:30:45
**Message Date:** 2025-07-08T09:15:22
**Channel:** #engineering (C1234567890)
**User:** shreyas.balakrishna (U0987654321)
**Permalink:** https://playhq.slack.com/archives/C1234567890/p1720425322123456

**Message:**

Here's the architecture diagram for the new feature. Note the database schema changes needed.

**Attachments:** 1 attachment(s)
- Architecture Diagram: https://files.slack.com/files-pri/...

**Reactions:**
- :eyes: (3)
- :thumbsup: (5)

---
```

### 2. DM History Export (`fetch_dm_history.py`)

Fetches complete conversation history from Direct Messages with progress tracking.

#### Command Options
- `-t, --token` (required): Your Slack User OAuth Token
- `-c, --channel` (required): The DM channel ID
- `-s, --since`: Start date in YYYY-MM-DD format (default: 2025-01-01)
- `-o, --output`: Output file path (default: auto-generated with timestamp)

#### Finding DM Channel IDs
```bash
# First, list all conversations to find the DM channel ID
python slack.py list -t "xoxp-your-token"

# Look for entries like:
# Direct Message Channels (82):
#   ID: D0889Q50GPM - User: U07C33KQM5Z
```

### 3. Channel & Search Export (`fetch_channel_search.py`)

Powerful search-based fetcher using Slack's search API for channels and complex queries.

#### Command Options
- `-t, --token` (required): Slack User OAuth Token
- `-q, --query` (required): Slack search query
- `-m, --max-results`: Maximum number of results (default: 100)
- `--page-size`: Results per API call (default: 20, max: 100)
- `-o, --output`: Output file (.md, .json, or .jsonl)
- `--monthly-chunks`: Break search into monthly chunks for complete history
- `--start-date`: Start date for monthly chunks (default: 2 years ago)
- `--end-date`: End date for monthly chunks (default: today)

#### Advanced Search Examples
```bash
# Complete user message history with monthly chunks
python fetch_channel_search.py -t "token" -q "from:@username" --monthly-chunks

# Channel archive with attachments only
python fetch_channel_search.py -t "token" -q "in:#project has:attachment" -m 1000

# Recent discussions about specific topic
python fetch_channel_search.py -t "token" -q "deployment after:2024-07-01" -o recent_deploys.md
```

### 4. Channel Discovery (`list_conversations.py`)

Lists all accessible channels, DMs, and groups with their IDs for use in other tools.

#### Usage
```bash
python list_conversations.py "xoxp-your-token"
```

#### Example Output
```
Public Channels (45):
  ID: C1234567890 - Name: general (👥 1,234 members)
  ID: C0987654321 - Name: engineering (👥 67 members)

Private Channels (12):
  ID: G1111111111 - Name: leadership-team (👥 8 members)

Direct Message Channels (82):
  ID: D0889Q50GPM - User: U07C33KQM5Z
  ID: D0123456789 - User: U08D44LMN2P

Group DMs (5):
  ID: G2222222222 - Members: 4
```

## Example Workflows

### 1. First Time Setup
```bash
# 1. List available channels/DMs to explore
python slack.py list -t "your-token"

# 2. Export your bookmarks to see important messages
python slack.py bookmarks -t "your-token"

# 3. Export a key DM conversation
python slack.py dm -t "your-token" -c CHANNEL_ID
```

### 2. Project Documentation
```bash
# Export all messages from project channel
python slack.py channel -t "token" -q "in:#project-alpha" --monthly-chunks

# Export all your messages about the project
python slack.py search -t "token" -q "from:me project-alpha" -o my_project_posts.md
```

### 3. User Activity Analysis
```bash
# Export all messages from a user
python slack.py search -t "token" -q "from:@username" --monthly-chunks

# Export messages with attachments from user
python slack.py search -t "token" -q "from:@username has:attachment"
```

### 4. Team Retrospective
```bash
# Export team channel for sprint retrospective
python slack.py channel -t "token" -q "in:#team-falcon during:2024-07"

# Export decision-making discussions
python slack.py search -t "token" -q "in:#architecture decision after:2024-06-01"
```

## Troubleshooting

### Common Issues

#### "No data found"
- **Bookmarks**: Check that you have starred messages in Slack
- **DMs**: Verify the channel ID using `python slack.py list`
- **Channels**: Ensure you have access to the channel
- **Search**: Try a broader search query

#### Permission Errors
Make sure your token has the required scopes:
```
missing_scope: stars:read          # Add stars:read for bookmarks
missing_scope: im:history          # Add im:history for DMs  
missing_scope: search:read         # Add search:read for channels/search
```

#### Rate Limiting
All tools handle rate limits automatically:
- Scripts wait the exact time Slack specifies
- Progress continues after rate limit period
- Consider smaller page sizes for large exports

#### Token Issues
- Ensure token starts with `xoxp-` (User OAuth Token, not Bot Token)
- Verify token is from the correct workspace
- Check that the app is installed in your workspace

### Getting Help

1. **Interactive Mode**: Use `python slack.py` for guided setup
2. **List First**: Run `python slack.py list` to see available channels
3. **Start Small**: Try exporting bookmarks first to test your token
4. **Check Scopes**: Ensure your token has required permissions

## Tips for Best Results

1. **Use Interactive Mode**: Easiest way to get started
2. **Export Bookmarks First**: Great way to test token and see important messages
3. **List Channels**: Use `list` operation to find channel IDs before DM exports
4. **Monthly Chunks**: Use for complete channel history (overcomes search limits)
5. **Multiple Formats**: Export to JSON for further processing, Markdown for reading

## Performance Notes

- **Bookmarks**: Fast fetching, enrichment adds ~0.1s per bookmark for context
- **DMs**: Streaming writes prevent data loss, ~100-500 messages/minute
- **Channels**: Monthly chunks bypass 10K message search limit
- **Large Exports**: Consider running overnight for years of history

## Data Privacy & Security

- All data stays local - nothing sent to external services
- Tokens are only used for Slack API calls
- Generated files contain your actual Slack data
- Ensure compliance with your organization's data policies
- Consider using `.gitignore` for exported files in repositories

## License

This tool is for personal use. Ensure you comply with your organization's Slack data retention and privacy policies.

---

**Version**: 2.0  
**Last Updated**: August 2025  
**Author**: For personal Slack data management
