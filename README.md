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
- **For Bookmarked Messages** → `python bookmarks.py` or `python slack.py bookmarks`
- **For Direct Messages (DMs)** → `python history.py` or `python slack.py dm`
- **For Channels or Complex Searches** → `python search.py` or `python slack.py search`
- **To Find Channel IDs** → `python list.py` or `python slack.py list`

## Features

- 🎯 **Unified Interface**: Single command for all export operations
- 📥 **Multiple Export Types**: DMs, channels, bookmarks, search results
- 🔄 **Interactive & CLI Modes**: Choose your preferred workflow
- 📊 **Real-time Progress**: Track export progress with beautiful progress bars
- 💾 **Multiple Formats**: Markdown, JSON, JSONL output
- 🔄 **Smart Rate Limiting**: Automatic backoff and retry with exponential backoff
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

2. Install dependencies:
   ```bash
   pip install requests
   ```

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
python bookmarks.py -t "xoxp-your-token" -o my_bookmarks.md

# JSON format
python bookmarks.py -t "xoxp-your-token" -o bookmarks.json

# Via unified CLI
python slack.py bookmarks -t "xoxp-your-token" -o bookmarks.md
```

#### Export DM Conversation
```bash
# Export DM from 2024
python history.py -t "xoxp-your-token" -c D0889Q50GPM --since 2024-01-01

# Via unified CLI
python slack.py dm -t "xoxp-your-token" -c D0889Q50GPM -s 2024-01-01
```

#### Export Channel Messages
```bash
# Export channel with complete history
python search.py -t "xoxp-your-token" -q "in:#general" --monthly-chunks

# Via unified CLI
python slack.py search -t "xoxp-your-token" -q "in:#general" --monthly-chunks
```

#### Search Messages
```bash
# Messages from specific user
python search.py -t "xoxp-your-token" -q "from:@username" -o user_messages.md

# Via unified CLI
python slack.py search -t "xoxp-your-token" -q "from:@username"
```

#### List Channels and DMs
```bash
# Show all available channels and DMs with IDs
python list.py -t "xoxp-your-token"

# Via unified CLI
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
python bookmarks.py -t "token" -o data.json
```

### JSONL Format
One JSON object per line, ideal for streaming processing:
```bash
python search.py -t "token" -q "query" -o results.jsonl
```

## Project Structure

```
slack/
├── slack.py                    # 🎯 Main unified entry point (START HERE)
├── cli.py                      # Unified CLI implementation
├── bookmarks.py                # Bookmarks/starred messages fetcher
├── history.py                  # Direct message history fetcher  
├── search.py                   # Search-based channel/message fetcher
├── list.py                     # Channel and DM discovery tool
├── extract.py                  # Message extraction from exports
├── utils.py                    # Standardized utilities (logging, rate limiting)
├── test.py                     # Test utilities and demonstrations
└── README.md                   # This documentation
```

### Individual Tools

While `python slack.py` is recommended, you can call the specialized tools directly:

- **`bookmarks.py`**: Export starred/bookmarked messages
- **`history.py`**: Export DM conversation history
- **`search.py`**: Complex search queries and channel exports  
- **`list.py`**: Discover channel IDs and available conversations
- **`extract.py`**: Extract messages from existing exports

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
python search.py -t "token" -q "in:#project-alpha" --monthly-chunks

# Export all your messages about the project
python search.py -t "token" -q "from:me project-alpha" -o my_project_posts.md
```

### 3. User Activity Analysis
```bash
# Export all messages from a user
python search.py -t "token" -q "from:@username" --monthly-chunks

# Export messages with attachments from user
python search.py -t "token" -q "from:@username has:attachment"
```

## Standardized Features

All tools now share:

### 🎨 **Consistent Logging**
- **Phase indicators**: `📋 Phase 1: Starting operations`
- **Progress bars**: `📊 Progress: 45/100 (45.0%) |█████████░░░░░░░░░░░| ETA: 2s`
- **Status messages**: `✅ Success`, `⚠️ Warning`, `❌ Error`, `ℹ️ Info`
- **API calls**: `🔄 API: conversations.history page 1 (200 items)`
- **Completion**: `🎉 Complete! Processed 1,247 items in 12.3s (101.4 items/sec)`

### 🔄 **Smart Rate Limiting**
- **Exponential backoff**: 1s → 2s → 4s → 8s → 16s...
- **Rate limit detection**: Automatic handling of 429 responses
- **Proactive throttling**: Respects `X-Rate-Limit-Remaining` headers
- **Safety buffers**: 10% extra wait time on Slack's retry-after suggestions

### 🛠 **Professional Features**
- **Consistent error handling** with helpful scope guidance
- **Real-time progress tracking** with ETA calculations
- **Graceful interruption** handling (Ctrl+C)
- **Memory-efficient streaming** for large exports
- **Multiple output formats** (Markdown, JSON, JSONL)

## Troubleshooting

### Common Issues

#### "No data found"
- **Bookmarks**: Check that you have starred messages in Slack
- **DMs**: Verify the channel ID using `python list.py`
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
2. **List First**: Run `python list.py` to see available channels
3. **Start Small**: Try exporting bookmarks first to test your token
4. **Check Scopes**: Ensure your token has required permissions

## Tips for Best Results

1. **Use Interactive Mode**: Easiest way to get started
2. **Export Bookmarks First**: Great way to test token and see important messages
3. **List Channels**: Use `list` operation to find channel IDs before DM exports
4. **Monthly Chunks**: Use for complete channel history (overcomes search limits)
5. **Multiple Formats**: Export to JSON for further processing, Markdown for reading

## License

This tool is for personal use. Ensure you comply with your organization's Slack data retention and privacy policies.
