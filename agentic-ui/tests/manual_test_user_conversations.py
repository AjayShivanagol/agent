#!/usr/bin/env python3
"""
Manual test script for user-specific conversations.
This script helps test the userinfo header decoding and user-specific conversation handling.
"""

import base64
import httpx
import json
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.user_info import decode_userinfo, get_user_id

# Test configurations
TEST_USERS = [
    {"id": "AJSHIVA", "email": "ajshiva@example.com"},
    {"id": "test_user", "email": "test@example.com"},
    {"id": "user123", "email": "user123@example.com"}
]

# Local server URL
BASE_URL = "http://localhost:8000"

def create_userinfo_header(user_data):
    """Create base64-encoded userinfo header from user data"""
    return base64.b64encode(json.dumps(user_data).encode()).decode()

async def test_conversation_operations(user_data):
    """Test creating, listing, and deleting conversations for a specific user"""
    user_id = user_data["id"]
    userinfo_header = create_userinfo_header(user_data)
    
    print(f"\n--- Testing with user: {user_id} ---")
    print(f"Using header: {userinfo_header}")
    
    # Create httpx client with default headers
    headers = {"x-userinfo": userinfo_header}
    async with httpx.AsyncClient(headers=headers, base_url=BASE_URL) as client:
        # Create conversation
        print(f"Creating conversation for {user_id}...")
        create_response = await client.post("/conversation/create")
        if create_response.status_code == 200:
            conv_data = create_response.json()
            conv_id = conv_data.get("result", {}).get("conversation_id")
            print(f"Created conversation with ID: {conv_id}")
        else:
            print(f"Error creating conversation: {create_response.status_code}")
            print(create_response.text)
            return
        
        # List conversations
        print(f"Listing conversations for {user_id}...")
        list_response = await client.post("/conversation/list")
        if list_response.status_code == 200:
            conversations = list_response.json().get("result", [])
            print(f"Found {len(conversations)} conversations:")
            for conv in conversations:
                print(f"- {conv.get('conversation_id')}")
        else:
            print(f"Error listing conversations: {list_response.status_code}")
        
        # Send a test message
        if conv_id:
            print(f"Sending test message in conversation {conv_id}...")
            message_data = {
                "params": {
                    "messageId": "test-msg-id",
                    "conversationId": conv_id,
                    "contextId": conv_id,
                    "role": "user",
                    "parts": [{"text": f"Test message from {user_id}"}]
                }
            }
            send_response = await client.post("/message/send", json=message_data)
            if send_response.status_code == 200:
                print("Test message sent successfully")
            else:
                print(f"Error sending message: {send_response.status_code}")
        
        # Verify user-specific data by checking conversation file on disk
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
        conv_file = os.path.join(data_dir, f"conversation-{user_id}.json")
        if os.path.exists(conv_file):
            print(f"Found user-specific conversation file: {conv_file}")
            with open(conv_file, 'r') as f:
                file_data = json.load(f)
                print(f"File contains {len(file_data)} conversations")
        else:
            print(f"Warning: Conversation file not found at {conv_file}")

async def main():
    """Run tests for all configured users"""
    print("Starting user-specific conversation tests")
    
    # Test utility functions first
    print("\n--- Testing userinfo decoding ---")
    for user_data in TEST_USERS:
        header = create_userinfo_header(user_data)
        decoded = decode_userinfo(header)
        user_id = get_user_id(header)
        print(f"User {user_data['id']}: Header encoding/decoding: {'Success' if user_id == user_data['id'] else 'Failed'}")
    
    # Test conversation operations for each user
    for user_data in TEST_USERS:
        await test_conversation_operations(user_data)
    
    print("\nTests completed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error running tests: {e}")
