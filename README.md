# Slack Export Tool

A unified Python tool to export Slack data with multiple specialized fetchers and an easy-to-use interface.

## 🚀 Quick Start (Recommended)

Just run the main script and follow the interactive menu:

```bash
python slack.py
```

The interactive mode will guide you through:
- Choosing what to export (saved messages, DMs, channels, search results)
- Getting your Slack token
- Configuring export options
- Running the appropriate specialized tool

## Quick Decision Guide

- **New to this tool?** → Use `python slack.py` (interactive mode)
- **For Saved Messages ("Later")** → `python slack.py later`
- **For Direct Messages (DMs)** → `python slack.py dm`
- **For Channels or Complex Searches** → `python slack.py channel` or `python slack.py search`
- **To Find Channel IDs** → `python slack.py list`

## Features

- 🎯 **Unified Interface**: Single command for all export operations
- 📥 **Multiple Export Types**: DMs, channels, saved messages, search results
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

2. **Recommended**: Create and activate a virtual environment:
   ```bash
   # Create virtual environment
   python3 -m venv slack-export-env
   
   # Activate it (macOS/Linux)
   source slack-export-env/bin/activate
   
   # On Windows, use:
   # slack-export-env\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install requests
   ```

4. **Optional**: Create a requirements.txt for easy setup:
   ```bash
   pip freeze > requirements.txt
   ```

   Later installations can use:
   ```bash
   pip install -r requirements.txt
   ```

## Getting Your Slack Token

You need a Slack User OAuth Token (starts with `xoxp-`) with appropriate scopes based on what you want to export:

### Required Scopes by Operation

| Operation | Required Scopes |
|-----------|----------------|
| **Saved Messages** | `search:read`, `channels:read`, `users:read`, `groups:read` |
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

#### Export Saved Messages ("Later")
```bash
# Basic saved messages export
python slack.py later -t "xoxp-your-token" -o my_saved_messages.md

# JSON format
python slack.py later -t "xoxp-your-token" -o saved.json

# Custom page size
python slack.py later -t "xoxp-your-token" --page-size 50 -o saved.md
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

# Export recent channel messages (limit to 500 messages)
python slack.py channel -t "xoxp-your-token" -q "in:#engineering" -m 500
```

#### Search Messages
```bash
# Messages from specific user (limit to 1000 messages)
python slack.py search -t "xoxp-your-token" -q "from:@username" -m 1000 -o user_messages.md

# Messages with attachments (complete history)
python slack.py search -t "xoxp-your-token" -q "has:attachment" --monthly-chunks

# Complex search with custom limit
python slack.py search -t "xoxp-your-token" -q "in:#general project after:2024-01-01" -m 500
```

#### Export All Messages from a Specific User
```bash
# Get all messages from a user across DMs and channels (complete history)
python slack.py search -t "xoxp-your-token" -q "from:@john.smith" --monthly-chunks -o user_complete_history.md

# User messages in a specific time period (e.g., all of 2024) - up to 2000 messages
python slack.py search -t "xoxp-your-token" -q "from:@john.smith after:2024-01-01 before:2024-12-31" -m 2000 -o user_2024_messages.md

# User messages from the last week - up to 1000 messages
python slack.py search -t "xoxp-your-token" -q "from:@john.smith after:2025-09-01" -m 1000 -o user_recent.md

# User messages from the last 30 days - up to 1500 messages
python slack.py search -t "xoxp-your-token" -q "from:@john.smith after:2025-08-08" -m 1500 -o user_last_30_days.md

# Alternative: Use user ID if username doesn't work (find ID with 'list' command)
python slack.py search -t "xoxp-your-token" -q "from:U123456789 after:2025-09-01" -m 1000 -o user_messages_by_id.md

# ⚠️ Important: Don't use --monthly-chunks with recent date ranges (causes date conflicts)
# Only use --monthly-chunks for complete historical exports without specific date filters
```

#### List Channels and DMs
```bash
# Show all available channels and DMs with IDs
python slack.py list -t "xoxp-your-token"
```

## Search Query Syntax

When using search operations, you can use Slack's powerful search operators:

### User & Channel Operators
- `from:@username` - Messages from specific user using their Slack handle (recommended - works reliably)
- `from:U123456` - Messages from specific user using User ID (alternative if handle doesn't work)
- `to:@username` - Messages to specific user  
- `in:#channel` - Messages in specific channel
- `in:@username` - DMs with specific user only

### Content Operators
- `has:attachment` - Messages with attachments
- `has:link` - Messages containing links
- `has:reaction` - Messages with reactions
- `is:saved` - Messages saved for later

### Date Operators
- `after:2024-01-01` - Messages after date
- `before:2024-12-31` - Messages before date
- `during:2024-06` - Messages during specific month

### Combining Operators
```bash
# User's messages in specific channel with attachments
"from:username in:#general has:attachment"

# Recent saved messages
"is:saved after:2024-12-01"

# User messages across all channels in time period
"from:@username after:2024-01-01 before:2024-12-31"

# User messages mentioning specific topics
"from:@username (project OR deployment OR release)"
```

## Output Formats

### Markdown Format (Default)
Human-readable format with rich formatting, perfect for documentation and review.

### JSON Format  
Structured data format for programmatic processing:
```bash
python slack.py later -t "token" -o data.json
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
├── slack.py                    # 🎯 Main unified CLI entry point (START HERE)
├── cli.py                      # CLI routing and interactive menu logic
├── later.py                    # Saved messages ("Later") fetcher
├── history.py                  # Direct message history fetcher  
├── search.py                   # Search-based channel/message fetcher
├── list.py                     # Channel and DM discovery tool
├── extract.py                  # Message extraction from exports
├── utils.py                    # Common utilities and base classes
└── README.md                   # This documentation
```

### When to Use Each Operation

Most users should use `python slack.py` with the interactive menu, but here's when to use each operation directly:

- **`later`**: Export all messages you've saved for later across your workspace
- **`dm`**: Export conversation history from a specific direct message channel
- **`channel`**: Export all messages from a specific channel using search API
- **`search`**: Complex queries across multiple channels with advanced filters
- **`list`**: Discover channel IDs and see what conversations are available

## Example Workflows

### 1. First Time Setup
```bash
# 1. List available channels/DMs to explore
python slack.py list -t "your-token"

# 2. Export your saved messages to see important items
python slack.py later -t "your-token"

# 3. Export a key DM conversation
python slack.py dm -t "your-token" -c CHANNEL_ID
```

### 2. Project Documentation
```bash
# Export all messages from project channel
python slack.py channel -t "token" -q "in:#project-alpha" --monthly-chunks

# Export all your messages about the project - up to 1000 messages
python slack.py search -t "token" -q "from:me project-alpha" -m 1000 -o my_project_posts.md
```

### 3. User Message History Analysis
```bash
# Export complete message history for a user (all channels + DMs) - use for historical data only
python slack.py search -t "token" -q "from:@john.smith" --monthly-chunks -o complete_user_history.md

# User activity in specific time period (don't use --monthly-chunks with date ranges) - up to 2000 messages
python slack.py search -t "token" -q "from:@john.smith after:2024-01-01 before:2024-06-30" -m 2000 -o user_h1_2024.md

# Recent user messages (last week/month) - up to 1000 messages
python slack.py search -t "token" -q "from:@john.smith after:2025-08-01" -m 1000 -o user_recent.md

# User messages with specific content - up to 500 messages
python slack.py search -t "token" -q "from:@john.smith deployment" -m 500 -o user_deployment_messages.md

# Export messages with attachments from user - up to 300 messages
python slack.py search -t "token" -q "from:@john.smith has:attachment" -m 300 -o user_attachments.md
```

### 4. Finding User IDs
```bash
# First, list channels to find user IDs from DM names
python slack.py list -t "token"

# Look for entries like: "ID: D0889Q50GPM - User: U07C33KQM5Z"
# Then use the User ID (U07C33KQM5Z) for more reliable searches
python slack.py search -t "token" -q "from:U07C33KQM5Z" --monthly-chunks
```

## Troubleshooting

### Common Issues

#### "No data found"
- **Saved Messages**: Check that you have messages saved for later in Slack
- **DMs**: Verify the channel ID using `python slack.py list`
- **Channels**: Ensure you have access to the channel
- **Search**: Try a broader search query

#### Permission Errors
Make sure your token has the required scopes:
```
missing_scope: search:read         # Add search:read for saved/search operations
missing_scope: im:history          # Add im:history for DMs  
missing_scope: channels:read       # Add channels:read for channel info
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
3. **Start Small**: Try exporting saved messages first to test your token
4. **Check Scopes**: Ensure your token has required permissions

## Tips for Best Results

1. **Use Interactive Mode**: Easiest way to get started
2. **Export Saved Messages First**: Great way to test token and see important messages
3. **List Channels**: Use `list` operation to find channel IDs before DM exports
4. **Monthly Chunks**: Use for complete channel history (overcomes search limits)
5. **Multiple Formats**: Export to JSON for further processing, Markdown for reading

## License

This tool is for personal use. Ensure you comply with your organisation's Slack data retention and privacy policies.
