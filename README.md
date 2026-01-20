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
- 📎 **Attachment Downloads**: Optionally download files alongside exports with organized folder structure
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

# Download attachments from saved messages
python slack.py later -t "xoxp-your-token" -o my_saved_messages.md --download-attachments

# Custom attachments directory
python slack.py later -t "xoxp-your-token" -o my_saved_messages.md --download-attachments --attachments-dir ./my_attachments
```

#### Export DM Conversation
```bash
# Export DM from 2024
python slack.py dm -t "xoxp-your-token" -c D0889Q50GPM --since 2024-01-01

# Recent messages only (default: 2025-01-01)
python slack.py dm -t "xoxp-your-token" -c D0889Q50GPM -o conversation.md

# Export DM with attachments
python slack.py dm -t "xoxp-your-token" -c D0889Q50GPM -o conversation.md --download-attachments

# Export DM with specific attachment directory
python slack.py dm -t "xoxp-your-token" -c D0889Q50GPM -o conversation.md --download-attachments --attachments-dir ./dm_files
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

# Download all attachments from messages
python slack.py search -t "xoxp-your-token" -q "has:attachment" --monthly-chunks --download-attachments

# Download attachments from specific user's messages
python slack.py search -t "xoxp-your-token" -q "from:@john.smith has:attachment" -m 500 --download-attachments --attachments-dir ./john_files
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

## Attachment Downloads

You can optionally download attachment files (images, PDFs, documents, etc.) alongside your message exports. Files are organized by channel in a structured folder hierarchy with date-prefixed filenames.

### Basic Usage

#### Interactive Mode
When running the tool in interactive mode, you'll be prompted:
```bash
python slack.py
# After selecting export type and entering settings:
# 📎 Attachment Download Options
# Download attachments to local disk? (y/N): y
# Attachments directory (default: <output>_attachments):
```

#### Direct Commands
```bash
# Download attachments with saved messages
python slack.py later -t "xoxp-your-token" --download-attachments

# Custom attachments directory
python slack.py dm -t "xoxp-your-token" -c D0889Q50GPM --download-attachments --attachments-dir ./dm_files

# Download files from search results
python slack.py search -t "xoxp-your-token" -q "has:attachment" --download-attachments --monthly-chunks
```

### Folder Structure

Downloaded files are organized by channel with date-prefixed filenames:

```
slack_export_20260120/                          # Export directory
├── saved_messages.md                           # Main export file
└── saved_messages_attachments/                 # Attachment root directory
    ├── general_C123ABC/                        # Channel-based folder
    │   ├── 20260115_U12AB_document.pdf         # Format: YYYYMMDD_USERID_filename
    │   ├── 20260115_U12AB_document_1.pdf       # Auto-incremented for duplicates
    │   └── 20260116_U456DEF_image.png
    ├── engineering_C456DEF/
    │   └── 20260114_deployment_log.txt
    └── dm_dm_john_smith_D789GHI/               # DM conversations
        └── 20260112_U98XYZ_screenshot.png
```

**Key Features:**
- **Organized**: Files grouped by channel for easy browsing
- **Date Prefixed**: Sort files chronologically with YYYYMMDD format
- **Collision Handling**: Automatic numbering for duplicate filenames
- **Relative Paths**: Export markdown files reference local paths for easy access

### What Gets Downloaded

- **Images**: PNG, JPG, GIF, etc.
- **Documents**: PDF, Word, Excel, etc.
- **Archives**: ZIP, TAR, etc.
- **Code**: Source files shared in messages
- **All File Types**: Any file attached to Slack messages

### Export Format References

#### Markdown with Downloaded Files
```markdown
**Files:** 2 file(s)
- report.pdf
  - Downloaded: saved_messages_attachments/general_C123/20260115_U12AB_report.pdf
  - Original URL: https://files.slack.com/files-pri/T123/F456/report.pdf
- image.png
  - Downloaded: saved_messages_attachments/general_C123/20260115_U12AB_image.png
  - Original URL: https://files.slack.com/files-pri/T123/F789/image.png
```

#### JSON with Downloaded Files
```json
{
  "files": [
    {
      "name": "report.pdf",
      "url_private": "https://files.slack.com/...",
      "local_path": "./saved_messages_attachments/general_C123/20260115_U12AB_report.pdf",
      "size": 1234567,
      "mimetype": "application/pdf"
    }
  ]
}
```

### Performance Notes

- **Sequential Downloads**: Files are downloaded one at a time to respect Slack's rate limits
- **Automatic Throttling**: ~1-2 files per second (rate-limited appropriately)
- **Error Resilience**: Failed downloads don't stop the export process; summary shows success/failure counts
- **Resumable**: Re-run the command with the same options to retry failed downloads

### Required Scope

To download attachments, your token needs the `files:read` scope in addition to the scopes required for the export operation.

| Operation | Required Scopes for Downloads |
|-----------|-------------------------------|
| **Saved Messages** | `search:read`, `channels:read`, `users:read`, `files:read` |
| **DMs** | `im:history`, `groups:history`, `channels:read`, `users:read`, `files:read` |
| **Channels/Search** | `search:read`, `channels:read`, `users:read`, `files:read` |

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

#### Attachment Download Issues

**"No download URL found for file"**
- Some older files may no longer be accessible via download URL
- The export continues with other files (resilient processing)

**"Failed to download X attachments"**
- Check that your token has `files:read` scope
- Verify network connectivity
- Some files may require additional permissions
- Files that fail are logged; rerun the export to retry

**"Disk space errors"**
- Ensure sufficient disk space for all attachments
- Limit exports using date ranges: `-q "after:2025-01-01"`
- Use `--max-file-size` (future feature) to skip large files

**Slow downloads**
- Sequential downloads are intentional (respects rate limits)
- Typical speed: 1-2 files per second depending on file size
- Large exports will take longer; consider exporting by date range

### Getting Help

1. **Interactive Mode**: Use `python slack.py` for guided setup
2. **List First**: Run `python slack.py list` to see available channels
3. **Start Small**: Try exporting saved messages first to test your token
4. **Check Scopes**: Ensure your token has required permissions

## Known Limitations

### Saved Messages Cannot Be Filtered by Status

**Important**: The saved messages export retrieves ALL messages you've ever saved, including both:
- ✅ Active/in-progress items you still need to act on
- ✔️ Completed items you've marked as done

**Why this limitation exists:**
- Slack's `search.messages` API (used for saved messages) does not expose completion status
- The deprecated `stars.list` API no longer tracks new saved items
- The newer `slackLists.items.list` API requires knowing a specific list ID and additional scopes not practical for general use
- Search operators like `is:saved_completed` do not exist in Slack's search syntax

**Workaround:**
Export all saved messages and manually filter them, or use Slack's UI to review completion status before exporting. The export will include all metadata (channel, user, date, text) to help with manual filtering.

**Example:**
If Slack shows you have 55 active saved items, the export may contain 300+ messages because it includes your entire saved message history (active + completed + archived).

## Tips for Best Results

1. **Use Interactive Mode**: Easiest way to get started
2. **Export Saved Messages First**: Great way to test token and see important messages
3. **List Channels**: Use `list` operation to find channel IDs before DM exports
4. **Monthly Chunks**: Use for complete channel history (overcomes search limits)
5. **Multiple Formats**: Export to JSON for further processing, Markdown for reading

## License

This tool is for personal use. Ensure you comply with your organisation's Slack data retention and privacy policies.
