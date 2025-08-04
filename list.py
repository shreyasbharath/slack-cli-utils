#!/usr/bin/env python3
"""
List all Slack conversations to find channel IDs with standardized logging
"""

import argparse
import sys
from typing import List, Dict, Any

# Import our standardized utilities
from utils import SlackExporter, get_user_name


class SlackConversationLister(SlackExporter):
    """Lists all accessible Slack conversations."""
    
    def __init__(self, token: str):
        super().__init__(token, "ConversationLister")
        self.user_cache = {}
    
    def list_all_conversations(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all conversations accessible to the token"""
        
        self.logger.phase(1, "Fetching all conversations")
        
        all_conversations = []
        cursor = None
        page_num = 1
        
        while True:
            self.logger.api_call("conversations.list", page=page_num)
            
            params = {
                'types': 'public_channel,private_channel,mpim,im',
                'limit': 200
            }
            if cursor:
                params['cursor'] = cursor
            
            data = self.make_api_request("https://slack.com/api/conversations.list", params)
            if not data:
                break
            
            channels = data.get('channels', [])
            if not channels:
                self.logger.info("No more conversations found", indent=1)
                break
            
            all_conversations.extend(channels)
            self.logger.progress(len(all_conversations), len(all_conversations), 
                               f"Found {len(channels)} conversations on page {page_num}")
            
            # Check for pagination
            cursor = data.get('response_metadata', {}).get('next_cursor')
            if not cursor:
                break
            
            page_num += 1
        
        self.logger.success(f"Found {len(all_conversations)} total conversations")
        
        # Categorize conversations
        categorized = self._categorize_conversations(all_conversations)
        return categorized
    
    def _categorize_conversations(self, conversations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize conversations by type."""
        
        self.logger.phase(2, "Categorizing conversations")
        
        categorized = {
            'public_channels': [],
            'private_channels': [],
            'direct_messages': [],
            'group_messages': []
        }
        
        for conv in conversations:
            if conv.get('is_channel') and not conv.get('is_private'):
                categorized['public_channels'].append(conv)
            elif conv.get('is_group') or (conv.get('is_channel') and conv.get('is_private')):
                categorized['private_channels'].append(conv)
            elif conv.get('is_im'):
                categorized['direct_messages'].append(conv)
            elif conv.get('is_mpim'):
                categorized['group_messages'].append(conv)
        
        # Log counts
        self.logger.info(f"📺 Public channels: {len(categorized['public_channels'])}")
        self.logger.info(f"🔒 Private channels: {len(categorized['private_channels'])}")
        self.logger.info(f"💬 Direct messages: {len(categorized['direct_messages'])}")
        self.logger.info(f"👥 Group messages: {len(categorized['group_messages'])}")
        
        return categorized
    
    def print_conversations(self, categorized: Dict[str, List[Dict[str, Any]]]):
        """Print formatted conversation list."""
        
        self.logger.phase(3, "Displaying conversations")
        
        # Public Channels
        public_channels = categorized['public_channels']
        if public_channels:
            print(f"\n📺 Public Channels ({len(public_channels)}):")
            for channel in sorted(public_channels, key=lambda x: x.get('name', '')):
                name = channel.get('name', 'Unknown')
                channel_id = channel.get('id', 'Unknown')
                member_count = channel.get('num_members', 0)
                print(f"  ID: {channel_id} - #{name} ({member_count} members)")
        
        # Private Channels
        private_channels = categorized['private_channels']
        if private_channels:
            print(f"\n🔒 Private Channels ({len(private_channels)}):")
            for channel in sorted(private_channels, key=lambda x: x.get('name', '')):
                name = channel.get('name', 'Unknown')
                channel_id = channel.get('id', 'Unknown')
                member_count = channel.get('num_members', 0)
                print(f"  ID: {channel_id} - #{name} ({member_count} members)")
        
        # Direct Messages
        direct_messages = categorized['direct_messages']
        if direct_messages:
            print(f"\n💬 Direct Message Channels ({len(direct_messages)}):")
            
            # Get user info for DMs (show first 10, then summary)
            for i, dm in enumerate(direct_messages[:10]):
                channel_id = dm.get('id', 'Unknown')
                user_id = dm.get('user', 'Unknown')
                user_name = get_user_name(self.user_cache, user_id, self.session) if user_id != 'Unknown' else 'Unknown User'
                print(f"  ID: {channel_id} - User: {user_name} ({user_id})")
            
            if len(direct_messages) > 10:
                print(f"  ... and {len(direct_messages) - 10} more DM channels")
        
        # Group Messages
        group_messages = categorized['group_messages']
        if group_messages:
            print(f"\n👥 Group Message Channels ({len(group_messages)}):")
            for group in group_messages:
                name = group.get('name', 'Unnamed Group')
                channel_id = group.get('id', 'Unknown')
                member_count = group.get('num_members', 0)
                print(f"  ID: {channel_id} - {name} ({member_count} members)")
        
        # Summary
        total = sum(len(cats) for cats in categorized.values())
        print(f"\n📊 Summary: {total} total conversations")
        self.logger.success("Conversation listing complete")


def main():
    parser = argparse.ArgumentParser(
        description='List all Slack conversations to find channel IDs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python list.py -t "xoxp-your-token"

This will show all channels, DMs, and groups you have access to along with their IDs.
Use the channel IDs with other export tools.

Required Slack API scopes:
  - channels:read (to list public channels)
  - groups:read (to list private channels)
  - im:read (to list direct messages)
  - users:read (to get user names for DMs)
        """
    )
    
    parser.add_argument('-t', '--token', required=True,
                        help='Slack User OAuth Token (starts with xoxp-)')
    
    args = parser.parse_args()
    
    try:
        lister = SlackConversationLister(args.token)
        categorized = lister.list_all_conversations()
        lister.print_conversations(categorized)
        
        print(f"\n💡 Tip: Use the channel IDs above with other export tools")
        return 0
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Listing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
