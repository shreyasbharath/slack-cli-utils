#!/usr/bin/env python3
"""
Extract all Slack messages from a specific author from markdown files.
"""

import os
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class SlackMessageExtractor:
    def __init__(self, directory: str, author: str, output_file: str = None):
        """
        Initialize the extractor.

        Args:
            directory: Path to directory containing markdown files
            author: Author name or user ID to search for
            output_file: Optional output file path (defaults to author_messages.md)
        """
        self.directory = Path(directory)
        self.author = author
        self.output_file = output_file or f"{author}_messages.md"
        self.messages = []

        # Regex pattern to match message blocks
        self.message_pattern = re.compile(
            r'---\s*\n'
            r'## Post (\d+)\s*\n'
            r'\*\*Author:\*\* ([^(]+) \((`[^`]+`)\)\s*\n'
            r'\*\*Channel:\*\* ([^\n]+)\s*\n'
            r'\*\*Date:\*\* ([^\n]+)\s*\n'
            r'\*\*Timestamp:\*\* ([^\n]+)\s*\n'
            r'\*\*Message:\*\*\s*\n'
            r'(.*?)'
            r'(?=---|$)',
            re.DOTALL | re.MULTILINE
        )

    def extract_messages(self) -> List[Dict]:
        """
        Extract all messages from markdown files in the directory.
        """
        print(f"Searching for messages by '{self.author}' in {self.directory}")

        # Find all markdown files
        md_files = list(self.directory.rglob("*.md"))
        print(f"Found {len(md_files)} markdown files to process")

        for file_path in md_files:
            self._process_file(file_path)

        print(f"Found {len(self.messages)} messages by {self.author}")
        return self.messages

    def _process_file(self, file_path: Path) -> None:
        """
        Process a single markdown file to extract messages.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all messages in the file
            for match in self.message_pattern.finditer(content):
                post_num = match.group(1)
                author_name = match.group(2).strip()
                author_id = match.group(3).strip('`')
                channel = match.group(4).strip()
                date = match.group(5).strip()
                timestamp = match.group(6).strip()
                message_text = match.group(7).strip()

                # Check if this message is by our target author
                if (self.author.lower() in author_name.lower() or
                    self.author.lower() in author_id.lower()):

                    self.messages.append({
                        'file': str(file_path),
                        'post_number': post_num,
                        'author_name': author_name,
                        'author_id': author_id,
                        'channel': channel,
                        'date': date,
                        'timestamp': timestamp,
                        'message': message_text
                    })

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    def save_results(self, format: str = 'markdown') -> None:
        """
        Save extracted messages to file.

        Args:
            format: Output format ('markdown' or 'csv')
        """
        if format == 'markdown':
            self._save_as_markdown()
        elif format == 'csv':
            self._save_as_csv()
        else:
            raise ValueError(f"Unknown format: {format}")

    def _save_as_markdown(self) -> None:
        """Save results as markdown file."""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Messages by {self.author}\n")
            f.write(f"**Total messages found:** {len(self.messages)}\n")
            f.write(f"**Extraction date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Group messages by channel
            messages_by_channel = {}
            for msg in self.messages:
                channel = msg['channel']
                if channel not in messages_by_channel:
                    messages_by_channel[channel] = []
                messages_by_channel[channel].append(msg)

            # Write messages grouped by channel
            for channel, channel_messages in sorted(messages_by_channel.items()):
                f.write(f"\n## Channel: {channel}\n")
                f.write(f"**Messages in this channel:** {len(channel_messages)}\n\n")

                # Sort by date/timestamp
                sorted_messages = sorted(channel_messages, key=lambda x: x['timestamp'])

                for msg in sorted_messages:
                    f.write("---\n")
                    f.write(f"### Post {msg['post_number']}\n")
                    f.write(f"**Author:** {msg['author_name']} (`{msg['author_id']}`)\n")
                    f.write(f"**Date:** {msg['date']}\n")
                    f.write(f"**Timestamp:** {msg['timestamp']}\n")
                    f.write(f"**Source File:** `{msg['file']}`\n\n")
                    f.write("**Message:**\n")
                    f.write(f"{msg['message']}\n")
                    f.write("---\n\n")

        print(f"Results saved to {self.output_file}")

    def _save_as_csv(self) -> None:
        """Save results as CSV file."""
        import csv

        csv_file = self.output_file.replace('.md', '.csv')
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'post_number', 'author_name', 'author_id', 'channel',
                'date', 'timestamp', 'message', 'file'
            ])
            writer.writeheader()
            writer.writerows(self.messages)

        print(f"Results saved to {csv_file}")

    def print_summary(self) -> None:
        """Print a summary of extracted messages."""
        if not self.messages:
            print("No messages found.")
            return

        # Channel statistics
        channels = {}
        for msg in self.messages:
            channel = msg['channel']
            channels[channel] = channels.get(channel, 0) + 1

        print("\n=== SUMMARY ===")
        print(f"Total messages: {len(self.messages)}")
        print(f"Channels: {len(channels)}")
        print("\nMessages per channel:")
        for channel, count in sorted(channels.items(), key=lambda x: x[1], reverse=True):
            print(f"  {channel}: {count}")


def main():
    parser = argparse.ArgumentParser(description='Extract Slack messages by a specific author')
    parser.add_argument('directory', help='Directory containing Slack markdown files')
    parser.add_argument('author', help='Author name or user ID to search for')
    parser.add_argument('-o', '--output', help='Output file path (default: author_messages.md)')
    parser.add_argument('-f', '--format', choices=['markdown', 'csv'], default='markdown',
                        help='Output format (default: markdown)')
    parser.add_argument('-s', '--summary', action='store_true',
                        help='Print summary statistics')

    args = parser.parse_args()

    # Create extractor
    extractor = SlackMessageExtractor(
        directory=args.directory,
        author=args.author,
        output_file=args.output
    )

    # Extract messages
    extractor.extract_messages()

    # Print summary if requested
    if args.summary:
        extractor.print_summary()

    # Save results
    if extractor.messages:
        extractor.save_results(format=args.format)
    else:
        print(f"No messages found for author '{args.author}'")


if __name__ == "__main__":
    main()
