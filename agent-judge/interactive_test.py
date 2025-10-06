#!/usr/bin/env python3
"""
Agent Judge Interactive Test - Allows manual input of questions and responses for evaluation.
"""

import asyncio
import httpx
import json
import uuid
import sys

async def evaluate_single_response(client, base_url, query, response):
    """Send a single evaluation request."""
    request_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "message/send",
        "params": {
            "message": {
                "messageId": message_id,
                "role": "user",
                "parts": [{"type": "text", "text": f"{query}|||{response}"}]
            }
        }
    }
    
    print(f"\nEvaluating Response...")
    print(f"Query: {query}")
    print(f"Response: {response}")
    print("=" * 60)
    
    try:
        response_obj = await client.post(f"{base_url}/", json=payload)
        
        if response_obj.status_code == 200:
            data = response_obj.json()
            
            if "result" in data and "history" in data["result"]:
                # Extract the evaluation from the history
                history = data['result']['history']
                for msg in history:
                    if msg['role'] == 'agent' and 'EVALUATION RESULT' in msg['parts'][0]['text']:
                        evaluation = msg['parts'][0]['text']
                        
                        # Print the full evaluation
                        print("AGENT JUDGE EVALUATION:")
                        print("-" * 60)
                        print(evaluation)
                        print("=" * 60)
                        return True
                
                print("Could not find evaluation in response")
                return False
            else:
                print(f"Unexpected response format")
                print(f"Response: {json.dumps(data, indent=2)}")
                return False
        else:
            print(f"Error: {response_obj.status_code}")
            print(f"Response: {response_obj.text}")
            return False
            
    except Exception as e:
        print(f"Exception occurred: {e}")
        return False

def get_user_input(prompt, allow_empty=False):
    """Get input from user with proper handling."""
    while True:
        try:
            value = input(prompt).strip()
            if value or allow_empty:
                return value
            print("Please enter a value (cannot be empty)")
        except (EOFError, KeyboardInterrupt):
            print("\n\nExiting...")
            sys.exit(0)

async def interactive_test():
    """Run interactive test where user can input custom questions."""
    base_url = "http://localhost:10001"
    
    print("AGENT JUDGE INTERACTIVE TEST")
    print("=" * 60)
    print("Enter your questions and responses to get Agent Judge evaluations.")
    print("Press Ctrl+C to exit anytime.")
    print("=" * 60)
    
    # Test connection first
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/.well-known/agent.json")
            if response.status_code == 200:
                agent_info = response.json()
                print(f"Connected to: {agent_info['name']}")
                print(f"Server: {base_url}")
            else:
                print(f"Cannot connect to Agent Judge server at {base_url}")
                print("Please make sure the server is running.")
                return
    except Exception as e:
        print(f"Connection error: {e}")
        print("Please make sure the Agent Judge server is running.")
        return
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            print("\n" + "="*60)
            print("NEW EVALUATION")
            print("="*60)
            
            # Get user query
            query = get_user_input("\nEnter your question/query: ")
            
            # Get agent response
            agent_response = get_user_input("Enter the agent's response to evaluate: ")
            
            # Confirm before sending
            print(f"\nReview your input:")
            print(f"   Query: {query}")
            print(f"   Response: {agent_response}")
            
            confirm = get_user_input("\nSend for evaluation? (y/n/q to quit): ", allow_empty=True).lower()
            
            if confirm in ['q', 'quit', 'exit']:
                break
            elif confirm in ['', 'y', 'yes']:
                # Send for evaluation
                print("\nSending to Agent Judge...")
                success = await evaluate_single_response(client, base_url, query, agent_response)
                
                if success:
                    print("\nEvaluation completed successfully!")
                else:
                    print("\nEvaluation failed.")
                
                # Ask if user wants to continue
                continue_prompt = get_user_input("\nEvaluate another response? (y/n): ", allow_empty=True).lower()
                if continue_prompt in ['n', 'no', 'q', 'quit']:
                    break
            else:
                print("Skipping evaluation...")
                continue
    
    print("\nThanks for using Agent Judge Interactive Test!")

if __name__ == "__main__":
    try:
        asyncio.run(interactive_test())
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)