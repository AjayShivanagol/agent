#!/usr/bin/env python3
"""
Agent Judge comprehensive test - demonstrates both PASS and FAIL evaluations.
"""

import asyncio
import httpx
import json
import uuid

async def evaluate_response(client, base_url, query, response, description):
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
    
    print(f"\n📝 Test Case: {description}")
    print(f"Query: {query}")
    print(f"Response: {response}")
    print("-" * 50)
    
    response = await client.post(f"{base_url}/", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        
        if "result" in data and "history" in data["result"]:
            # Extract the evaluation from the history
            history = data['result']['history']
            for msg in history:
                if msg['role'] == 'agent' and 'EVALUATION RESULT' in msg['parts'][0]['text']:
                    evaluation = msg['parts'][0]['text']
                    
                    # Extract just the key parts for summary
                    lines = evaluation.split('\n')
                    result_line = [line for line in lines if 'EVALUATION RESULT:' in line][0]
                    
                    print(f"🏆 {result_line}")
                    
                    # Extract scores
                    score_section = False
                    for line in lines:
                        if 'G-EVAL Structured Scoring:' in line:
                            score_section = True
                            continue
                        elif score_section and line.startswith('- **'):
                            print(f"   {line}")
                        elif score_section and line.startswith('**Average Score:'):
                            print(f"   {line}")
                            break
                    break
        else:
            print(f"❌ Unexpected response format")
    else:
        print(f"❌ Error: {response.status_code}")

async def comprehensive_test():
    """Run comprehensive tests of Agent Judge."""
    base_url = "http://localhost:10001"
    
    async with httpx.AsyncClient() as client:
        print("🧪 AGENT JUDGE COMPREHENSIVE TEST")
        print("=" * 60)
        
        # Test cases
        test_cases = [
            {
                "query": "What is the capital of France?",
                "response": "The capital of France is Paris.",
                "description": "Perfect Factual Answer"
            },
            {
                "query": "What is 2+2?",
                "response": "2+2 equals 8.",
                "description": "Simple Math - Correct"
            },
            {
                "query": "What is the capital of Japan?",
                "response": "The capital of Japan is Beijing.",
                "description": "Factually Incorrect Answer"
            },
            {
                "query": "Explain quantum computing in detail",
                "response": "It's complicated.",
                "description": "Incomplete Response"
            },
            {
                "query": "What is machine learning?",
                "response": "Machine learning is a subset of artificial intelligence that enables computers to learn and make decisions from data without being explicitly programmed for every task.",
                "description": "Comprehensive Technical Answer"
            }
        ]
        
        for test_case in test_cases:
            await evaluate_response(
                client, base_url, 
                test_case["query"], 
                test_case["response"], 
                test_case["description"]
            )
            await asyncio.sleep(0.5)  # Small delay between requests

if __name__ == "__main__":
    asyncio.run(comprehensive_test())