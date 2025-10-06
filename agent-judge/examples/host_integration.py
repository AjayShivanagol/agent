"""
Example integration of Agent Judge with a host agent.
This demonstrates how to integrate the Agent Judge into the evaluation workflow.
"""

import httpx
import asyncio
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class HostAgentWithJudge:
    """
    Example host agent that integrates with Agent Judge for response validation.
    """
    
    def __init__(self, judge_url: str = "http://localhost:10001"):
        self.judge_url = judge_url
        self.client = httpx.AsyncClient()
    
    async def send_to_judge(self, user_query: str, agent_response: str) -> Dict[str, Any]:
        """
        Send user query and agent response to Agent Judge for evaluation.
        
        Args:
            user_query: Original user question
            agent_response: Agent's proposed response
            
        Returns:
            Dictionary with evaluation result
        """
        try:
            # Format input as expected by Agent Judge
            judge_input = f"{user_query}|||{agent_response}"
            
            # Send to judge
            response = await self.client.post(
                f"{self.judge_url}/tasks",
                json={
                    "message": {
                        "parts": [{"type": "text", "text": judge_input}]
                    }
                }
            )
            
            if response.status_code == 201:
                task_data = response.json()
                task_id = task_data["id"]
                
                # Poll for result
                return await self._poll_judge_result(task_id)
            else:
                logger.error(f"Failed to submit to judge: {response.status_code}")
                return {"result": "FAIL", "reasoning": "Judge service unavailable"}
                
        except Exception as e:
            logger.error(f"Error communicating with judge: {e}")
            return {"result": "FAIL", "reasoning": f"Judge communication error: {str(e)}"}
    
    async def _poll_judge_result(self, task_id: str, max_attempts: int = 30) -> Dict[str, Any]:
        """Poll the judge for evaluation results."""
        for _ in range(max_attempts):
            try:
                response = await self.client.get(f"{self.judge_url}/tasks/{task_id}")
                
                if response.status_code == 200:
                    task_data = response.json()
                    
                    if task_data["state"] == "completed":
                        content = task_data["message"]["parts"][0]["text"]
                        return self._parse_judge_response(content)
                    elif task_data["state"] in ["failed", "error"]:
                        return {"result": "FAIL", "reasoning": "Judge evaluation failed"}
                
                await asyncio.sleep(1)  # Wait before next poll
                
            except Exception as e:
                logger.error(f"Error polling judge result: {e}")
                break
        
        return {"result": "FAIL", "reasoning": "Judge evaluation timeout"}
    
    def _parse_judge_response(self, content: str) -> Dict[str, Any]:
        """Parse the judge response content."""
        try:
            # Extract key information from the response
            result = "FAIL"
            if "PASS" in content:
                result = "PASS"
            
            # Extract confidence if available
            confidence = 5
            import re
            conf_match = re.search(r'Confidence:\s*(\d+)', content)
            if conf_match:
                confidence = int(conf_match.group(1))
            
            return {
                "result": result,
                "reasoning": content,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Error parsing judge response: {e}")
            return {"result": "FAIL", "reasoning": "Failed to parse judge response"}
    
    async def process_user_query(self, user_query: str, max_retries: int = 2) -> str:
        """
        Process user query with Agent Judge validation.
        
        Args:
            user_query: User's question
            max_retries: Maximum number of retry attempts
            
        Returns:
            Final validated response
        """
        for attempt in range(max_retries + 1):
            # Generate response (placeholder - replace with actual agent logic)
            agent_response = await self._generate_response(user_query)
            
            # Send to judge for evaluation
            judge_result = await self.send_to_judge(user_query, agent_response)
            
            if judge_result["result"] == "PASS":
                logger.info(f"Response passed judge evaluation on attempt {attempt + 1}")
                return agent_response
            
            logger.warning(f"Response failed judge evaluation on attempt {attempt + 1}: {judge_result['reasoning']}")
            
            # If not the last attempt, try to improve the response
            if attempt < max_retries:
                agent_response = await self._improve_response(
                    user_query, 
                    agent_response, 
                    judge_result["reasoning"]
                )
        
        # If all attempts failed, return the last attempt with a disclaimer
        logger.error(f"All attempts failed judge evaluation for query: {user_query}")
        return f"I apologize, but I'm having difficulty providing a fully satisfactory response. Here's my best attempt: {agent_response}"
    
    async def _generate_response(self, user_query: str) -> str:
        """
        Generate initial response to user query.
        Replace this with your actual agent implementation.
        """
        # Placeholder implementation
        if "capital" in user_query.lower() and "france" in user_query.lower():
            return "The capital of France is Paris."
        elif "weather" in user_query.lower():
            return "I don't have access to current weather information."
        else:
            return "I'll do my best to help you with that question."
    
    async def _improve_response(self, user_query: str, original_response: str, judge_feedback: str) -> str:
        """
        Improve response based on judge feedback.
        Replace this with your actual improvement logic.
        """
        # Placeholder improvement logic
        improved_response = f"{original_response} Let me provide more detail to better address your question."
        return improved_response
    
    async def close(self):
        """Clean up resources."""
        await self.client.aclose()


# Example usage
async def main():
    """Example of using the host agent with judge integration."""
    host_agent = HostAgentWithJudge("http://localhost:10001")
    
    try:
        # Example queries
        test_queries = [
            "What is the capital of France?",
            "How do I bake a chocolate cake?",
            "Explain quantum computing in simple terms."
        ]
        
        for query in test_queries:
            print(f"\nUser Query: {query}")
            response = await host_agent.process_user_query(query)
            print(f"Final Response: {response}")
            
    finally:
        await host_agent.close()


if __name__ == "__main__":
    asyncio.run(main())