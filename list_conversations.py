#!/usr/bin/env python3
"""
List all Slack conversations to find the correct channel ID
"""

import requests
import json

def list_conversations(token):
    """List all conversations accessible to the token"""
    
    base_url = "https://slack.com/api/conversations.list"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    all_conversations = []
    cursor = None
    
    print("Fetching all conversations...")
    
    while True:
        params = {
            'types': 'public_channel,private_channel,mpim,im',
            'limit': 200
        }
        
        if cursor:
            params['cursor'] = cursor
        
        response = requests.get(base_url, headers=headers, params=params)
        data = response.json()
        
        if not data.get('ok'):
            print(f"Error: {data.get('error', 'Unknown error')}")
            break
        
        channels = data.get('channels', [])
        all_conversations.extend(channels)
        
        print(f"Got {len(channels)} conversations (Total: {len(all_conversations)})")
        
        # Check if there are more
        cursor = data.get('response_metadata', {}).get('next_cursor')
        if not cursor:
            break
    
    return all_conversations

def find_dm_channel(conversations, user_name=None):
    """Find DM channels, optionally filtering by user name"""
    
    dm_channels = []
    
    for conv in conversations:
        if conv.get('is_im', False):
            dm_channels.append({
                'id': conv['id'],
                'user': conv.get('user', 'Unknown'),
                'created': conv.get('created', 0)
            })
    
    return dm_channels

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python list_conversations.py <token>")
        sys.exit(1)
    
    token = sys.argv[1]
    
    conversations = list_conversations(token)
    print(f"\nTotal conversations found: {len(conversations)}")
    
    # Find DM channels
    dm_channels = find_dm_channel(conversations)
    
    print(f"\nDirect Message Channels ({len(dm_channels)}):")
    for dm in dm_channels:
        print(f"  ID: {dm['id']} - User: {dm['user']}")
    
    # Look for the specific channel
    target_id = "D0889Q50GPM"
    found = False
    for conv in conversations:
        if conv['id'] == target_id:
            print(f"\n✓ Found channel {target_id}:")
            print(f"  Type: {'DM' if conv.get('is_im') else 'Channel'}")
            print(f"  Name: {conv.get('name', 'N/A')}")
            print(f"  User: {conv.get('user', 'N/A')}")
            print(f"  Is IM: {conv.get('is_im', False)}")
            print(f"  Is Group: {conv.get('is_group', False)}")
            print(f"  Is Private: {conv.get('is_private', False)}")
            found = True
            break
    
    if not found:
        print(f"\n✗ Channel {target_id} not found in accessible conversations")
