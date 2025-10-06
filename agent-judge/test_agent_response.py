#!/usr/bin/env python3

import asyncio
import httpx
import json
from uuid import uuid4

async def test_agent_judge():
    async with httpx.AsyncClient() as client:
        # Test the Agent Judge response format
        payload = {
            'messageId': str(uuid4()),
            'role': 'user',
            'parts': [
                {
                    'text': 'What is the capital of France?|||The capital of France is Paris. It is located in the northern part of the country.'
                }
            ]
        }
        
        print("Sending request to Agent Judge...")
        response = await client.post(
            'http://localhost:10001/',
            json={
                'jsonrpc': '2.0',
                'method': 'sendMessage',
                'params': {
                    'message': payload,
                    'configuration': {
                        'acceptedOutputModes': ['text']
                    }
                },
                'id': str(uuid4())
            },
            headers={'Content-Type': 'application/json'},
            timeout=30.0
        )
        
        print('Status:', response.status_code)
        result = response.json()
        print('Response:', json.dumps(result, indent=2))
        
        # If we got a task ID, let's poll for the result
        if 'result' in result and 'taskId' in result['result']:
            task_id = result['result']['taskId']
            print(f'\nGot task ID: {task_id}')
            
            # Poll for completion
            for i in range(10):
                print(f'Polling attempt {i+1}...')
                await asyncio.sleep(2)
                poll_response = await client.post(
                    'http://localhost:10001/',
                    json={
                        'jsonrpc': '2.0',
                        'method': 'pollTask',
                        'params': {
                            'taskId': task_id
                        },
                        'id': str(uuid4())
                    },
                    headers={'Content-Type': 'application/json'}
                )
                
                poll_result = poll_response.json()
                print(f'Poll result:', json.dumps(poll_result, indent=2))
                
                if 'result' in poll_result and poll_result['result'].get('status') == 'completed':
                    print('\n✅ Task completed!')
                    return poll_result
                    
        return result

if __name__ == '__main__':
    asyncio.run(test_agent_judge())