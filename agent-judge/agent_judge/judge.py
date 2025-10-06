from collections.abc import AsyncIterable
from typing import Any, Literal, Dict, List, Optional
import json
import os
import re

import httpx
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
# Optional import with fallback for Azure OpenAI
try:
    from langchain_openai import AzureChatOpenAI
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from dotenv import load_dotenv
load_dotenv()

memory = MemorySaver()

class JudgeInput(BaseModel):
    """Input model for judge evaluation following LLM-as-a-Judge best practices"""
    user_query: str = Field(description="The original user query to evaluate against")
    agent_response: str = Field(description="The agent's response to evaluate")
    context: str = Field(default="", description="Additional context for evaluation")

class JudgeOutput(BaseModel):
    """Output model for judge evaluation following G-EVAL structured approach"""
    result: Literal["PASS", "FAIL"]
    reasoning: str = Field(description="Chain-of-thought reasoning for the decision")
    confidence: int = Field(ge=1, le=10, description="Confidence score from 1-10")
    accuracy_score: int = Field(ge=1, le=5, description="Factual accuracy score")
    completeness_score: int = Field(ge=1, le=5, description="Response completeness score")
    relevance_score: int = Field(ge=1, le=5, description="Response relevance score")
    clarity_score: int = Field(ge=1, le=5, description="Response clarity score")
    recommendations: str = Field(default="", description="Improvement recommendations for FAIL cases")

# G-EVAL inspired prompt template following the Medium article's best practices
judge_prompt = PromptTemplate.from_template("""You are a highly sophisticated AI Judge specialized in evaluating agent responses using the G-EVAL methodology.
        Your role is to provide accurate, consistent, and detailed assessments of AI-generated answers.

        ## Evaluation Framework (G-EVAL):
        You will evaluate responses across 4 key dimensions, each scored 1-5:

        1. **ACCURACY** (1-5): Factual correctness and truthfulness
        - 5: Completely accurate, no factual errors
        - 4: Mostly accurate, minor factual issues
        - 3: Generally accurate, some notable errors
        - 2: Several factual errors present
        - 1: Significantly inaccurate or misleading

        2. **COMPLETENESS** (1-5): How fully the response addresses the query
        - 5: Comprehensively addresses all aspects
        - 4: Addresses most important aspects
        - 3: Addresses core aspects adequately
        - 2: Missing important elements
        - 1: Significantly incomplete

        3. **RELEVANCE** (1-5): How well the response stays on topic
        - 5: Perfectly relevant and focused
        - 4: Mostly relevant, minimal off-topic content
        - 3: Generally relevant, some tangents
        - 2: Partially relevant, notable off-topic content
        - 1: Largely irrelevant or off-topic

        4. **CLARITY** (1-5): How clear and understandable the response is
        - 5: Exceptionally clear and well-structured
        - 4: Clear and easy to follow
        - 3: Generally clear, minor confusion
        - 2: Somewhat unclear or confusing
        - 1: Very unclear or poorly structured

        ## Evaluation Process:
        1. **Chain-of-Thought Analysis**: Think step-by-step about each aspect
        2. **Detailed Scoring**: Evaluate each dimension with specific reasoning
        3. **Quality Tools**: Use fact_check_tool for verification when needed
        4. **Final Decision**: Apply decision rules for PASS/FAIL

        ## Decision Rules:
        - **PASS**: Average score ≥ 3.0 AND accuracy score ≥ 3
        - **FAIL**: Average score < 3.0 OR accuracy score < 3

        **Original Query**: {user_query}
        **Agent Response**: {agent_response}
        **Additional Context**: {context}

        Please provide your evaluation following this format:

        ### Chain-of-Thought Analysis:
        [Your detailed reasoning process]

        ### Detailed Scoring:
        - Accuracy: [score]/5 - [brief justification]
        - Completeness: [score]/5 - [brief justification]
        - Relevance: [score]/5 - [brief justification]
        - Clarity: [score]/5 - [brief justification]

        ### Final Decision: [PASS/FAIL]
        Average Score: [calculated average]/5
        Confidence Level: [1-10]/10

        [If FAIL, include improvement recommendations]
""")

@tool
def fact_check_tool(claim: str) -> Dict[str, Any]:
    """
    Use this tool to verify factual claims when evaluating agent responses.
    
    Args:
        claim: The specific claim or fact to verify
    
    Returns:
        Dictionary containing verification result
    """
    try:
        # This is a placeholder implementation
        # In a real scenario, this would connect to fact-checking APIs or databases
        
        # Basic fact checking logic
        known_facts = {
            "paris": "Paris is the capital of France",
            "london": "London is the capital of the United Kingdom", 
            "berlin": "Berlin is the capital of Germany",
            "water boils": "Water boils at 100°C at sea level",
            "earth revolves": "The Earth revolves around the Sun"
        }
        
        claim_lower = claim.lower()
        verified = False
        confidence = 0.5
        
        for fact_key, fact_value in known_facts.items():
            if fact_key in claim_lower:
                verified = True
                confidence = 0.9
                break
        
        return {
            "claim": claim,
            "verified": verified,
            "confidence": confidence,
            "source": "Internal knowledge base",
            "details": f"Checking claim: {claim}"
        }
    except Exception as e:
        return {
            "claim": claim,
            "verified": False,
            "error": str(e),
            "confidence": 0.0
        }

@tool
def quality_assessment_tool(response_text: str, query_text: str) -> Dict[str, Any]:
    """
    Assess the quality aspects of an agent response.
    
    Args:
        response_text: The agent's response to evaluate
        query_text: The original user query
    
    Returns:
        Dictionary containing quality metrics
    """
    try:
        # Basic quality metrics
        word_count = len(response_text.split())
        
        # Check for key quality indicators
        has_structure = any(marker in response_text for marker in ['1.', '2.', '-', '*', '|', '\n'])
        has_specific_info = len([word for word in response_text.split() if word.isdigit() or '$' in word or '%' in word]) > 0
        
        # Check relevance by comparing key words
        query_words = set(query_text.lower().split())
        response_words = set(response_text.lower().split())
        overlap = len(query_words.intersection(response_words))
        relevance_score = overlap / len(query_words) if query_words else 0
        
        # Quality scoring
        quality_score = 0
        if word_count >= 20: quality_score += 2  # Adequate length
        if has_structure: quality_score += 2  # Well structured
        if has_specific_info: quality_score += 2  # Contains specific information
        if relevance_score > 0.3: quality_score += 4  # Addresses the query
        
        return {
            "word_count": word_count,
            "structure_score": 2 if has_structure else 0,
            "specificity_score": 2 if has_specific_info else 0,
            "relevance_score": int(relevance_score * 4),
            "overall_quality_score": quality_score,
            "max_score": 10,
            "relevance_percentage": round(relevance_score * 100, 1)
        }
    except Exception as e:
        return {
            "error": str(e),
            "overall_quality_score": 0,
            "max_score": 10
        }

def judge_agent_logic(input_data: Dict[str, str]) -> str:
    """
    Core judge logic that evaluates answers based on the criteria.
    This matches the pattern from your LangChain implementation.
    """
    query = input_data.get("query", "")
    answer = input_data.get("answer", "")
    
    # Check for obvious failures first
    if not answer or not answer.strip():
        return "FAIL: The answer is empty or contains no meaningful content."
    
    if "factually incorrect" in answer.lower():
        return "FAIL: The answer contains factually incorrect information."
    
    if len(answer.split()) < 5:
        return "FAIL: The answer is too brief and incomplete to adequately address the query."
    
    # Check for obvious wrong answers
    query_lower = query.lower()
    answer_lower = answer.lower()
    
    # Common factual checks
    if "capital of france" in query_lower:
        if "london" in answer_lower and "paris" not in answer_lower:
            return "FAIL: Incorrect factual information - London is not the capital of France."
        if "paris" in answer_lower:
            return "PASS: Correct factual information provided."
    
    if "capital of uk" in query_lower or "capital of united kingdom" in query_lower:
        if "paris" in answer_lower and "london" not in answer_lower:
            return "FAIL: Incorrect factual information - Paris is not the capital of the UK."
        if "london" in answer_lower:
            return "PASS: Correct factual information provided."
    
    # Check for relevance
    query_words = set(query.lower().split())
    answer_words = set(answer.lower().split())
    overlap = len(query_words.intersection(answer_words))
    relevance = overlap / len(query_words) if query_words else 0
    
    if relevance < 0.1:
        return "FAIL: The answer does not appear to be relevant to the query asked."
    
    # Check for completeness based on answer length and structure
    if len(answer.split()) >= 10 and relevance > 0.2:
        return "PASS: The answer appears accurate, complete, and relevant to the query."
    
    return "PASS: The answer meets basic quality criteria."

class ResponseFormat(BaseModel):
    """Response format for the judge agent."""
    status: Literal['completed', 'input_required', 'error']
    message: str

class AgentJudge:
    """
    Agent Judge - Evaluates the accuracy and quality of agent responses.
    Updated to match LangChain pattern with specific judge logic.
    """
    
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']
    
    def __init__(self):
        self.system_instructions = self._load_system_instructions()
        self.agent = self._create_agent()
        self.prompt_template = judge_prompt
    
    def _load_system_instructions(self) -> str:
        """Load system instructions from file."""
        try:
            instructions_path = os.path.join(os.path.dirname(__file__), 'system_instructions.txt')
            with open(instructions_path, 'r') as f:
                return f.read()
        except Exception:
            return "You are an Agent Judge. Evaluate responses for accuracy and quality."
    
    def _create_agent(self):
        """Create the LangGraph agent for judge evaluation."""
        try:
            # Initialize LLM based on environment configuration
            if os.getenv('MODEL_SOURCE') == "google":
                llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-pro",
                    google_api_key=os.getenv('GOOGLE_API_KEY'),
                    temperature=0.1  # Low temperature for consistent evaluation
                )
            else:
                # Default to Azure OpenAI if available
                if AZURE_AVAILABLE:
                    llm = AzureChatOpenAI(
                        azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', 'https://your-endpoint.openai.azure.com/'),
                        api_key=os.getenv('AZURE_OPENAI_API_KEY'),
                        api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview'),
                        deployment_name=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4'),
                        temperature=0.0  # Zero temperature for consistent evaluation
                    )
                else:
                    # Fallback to Google if Azure not available
                    llm = ChatGoogleGenerativeAI(
                        model="gemini-1.5-pro",
                        google_api_key=os.getenv('GOOGLE_API_KEY', 'your-google-key'),
                        temperature=0.0
                    )
            
            # Create agent with tools
            tools = [fact_check_tool, quality_assessment_tool]
            
            agent = create_react_agent(
                llm, 
                tools, 
                checkpointer=memory
            )
            
            return agent
            
        except Exception as e:
            print(f"Error creating agent: {e}")
            return None
    
    
    def evaluate(self, user_query: str, agent_response: str, context: str = "") -> JudgeOutput:
        """
        Main evaluation method using G-EVAL methodology.
        
        Args:
            user_query: The original user question
            agent_response: The agent's response to evaluate  
            context: Additional context if needed
            
        Returns:
            JudgeOutput with structured G-EVAL results
        """
        try:
            if self.agent:
                # Use LLM for G-EVAL structured evaluation
                return self._llm_evaluation(user_query, agent_response, context)
            else:
                # Fallback to enhanced rule-based evaluation
                return self._fallback_evaluation(user_query, agent_response, context)
                
        except Exception as e:
            return JudgeOutput(
                result="FAIL",
                reasoning=f"Evaluation error occurred: {str(e)}",
                confidence=1,
                accuracy_score=1,
                completeness_score=1,
                relevance_score=1,
                clarity_score=1,
                recommendations="Please retry the evaluation with proper configuration"
            )
    
    def _llm_evaluation(self, user_query: str, agent_response: str, context: str) -> JudgeOutput:
        """LLM-based evaluation using G-EVAL methodology."""
        try:
            # Use the enhanced prompt template
            formatted_prompt = self.prompt_template.format(
                user_query=user_query,
                agent_response=agent_response,
                context=context or "No additional context provided"
            )
            
            config = {"configurable": {"thread_id": f"judge_{hash(user_query + agent_response)}"}}
            response = self.agent.invoke({"messages": [("user", formatted_prompt)]}, config=config)
            
            # Extract and parse the response
            if response and "messages" in response:
                messages = response["messages"]
                if messages:
                    last_message = messages[-1]
                    if hasattr(last_message, 'content'):
                        return self._parse_geval_response(last_message.content)
            
            # Fallback if parsing fails
            return self._fallback_evaluation(user_query, agent_response, context)
            
        except Exception as e:
            print(f"LLM evaluation error: {e}")
            return self._fallback_evaluation(user_query, agent_response, context)
    
    def _parse_geval_response(self, content: str) -> JudgeOutput:
        """Parse G-EVAL structured response from LLM."""
        try:
            # Extract PASS/FAIL decision
            result = "FAIL"  # Default to FAIL for safety
            if "PASS" in content and "FAIL" not in content:
                result = "PASS"
            elif "Final Decision: PASS" in content:
                result = "PASS"
            
            # Extract individual scores using regex patterns
            def extract_score(pattern: str, default: int = 3) -> int:
                import re
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    try:
                        score = int(match.group(1))
                        return max(1, min(5, score))  # Clamp between 1-5
                    except:
                        return default
                return default
            
            accuracy_score = extract_score(r'Accuracy:\s*(\d)', 3)
            completeness_score = extract_score(r'Completeness:\s*(\d)', 3)
            relevance_score = extract_score(r'Relevance:\s*(\d)', 3)
            clarity_score = extract_score(r'Clarity:\s*(\d)', 3)
            
            # Extract confidence
            import re
            confidence_match = re.search(r'Confidence Level:\s*(\d+)', content, re.IGNORECASE)
            confidence = 5  # Default confidence
            if confidence_match:
                confidence = max(1, min(10, int(confidence_match.group(1))))
            else:
                # Calculate confidence based on scores
                avg_score = (accuracy_score + completeness_score + relevance_score + clarity_score) / 4
                confidence = max(1, int(avg_score * 2))
            
            # Extract reasoning (Chain-of-Thought section)
            reasoning_match = re.search(r'Chain-of-Thought Analysis:\s*(.*?)(?:### Detailed Scoring|$)', content, re.DOTALL | re.IGNORECASE)
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
            else:
                reasoning = content[:300] + "..." if len(content) > 300 else content
            
            # Extract recommendations for FAIL cases
            recommendations = ""
            if result == "FAIL":
                rec_match = re.search(r'[Rr]ecommend(?:ation)?s?[:\s]*(.*?)(?:\n\n|\Z)', content, re.DOTALL)
                if rec_match:
                    recommendations = rec_match.group(1).strip()
                else:
                    recommendations = "Review the detailed scoring and address identified weaknesses"
            
            return JudgeOutput(
                result=result,
                reasoning=reasoning,
                confidence=confidence,
                accuracy_score=accuracy_score,
                completeness_score=completeness_score,
                relevance_score=relevance_score,
                clarity_score=clarity_score,
                recommendations=recommendations
            )
            
        except Exception as e:
            print(f"Error parsing G-EVAL response: {e}")
            return self._fallback_evaluation("", "", "")
    
    def _get_agent_response(self, user_query: str, agent_response: str) -> Dict[str, Any]:
        """Get response from the LangGraph agent using the prompt template."""
        try:
            # Use the prompt template
            formatted_prompt = self.prompt_template.format(
                query=user_query,
                answer=agent_response
            )
            
            config = {"configurable": {"thread_id": "judge_thread"}}
            response = self.agent.invoke({"messages": [("user", formatted_prompt)]}, config=config)
            
            # Extract the final message
            if response and "messages" in response:
                messages = response["messages"]
                if messages:
                    last_message = messages[-1]
                    if hasattr(last_message, 'content'):
                        return {
                            'is_task_complete': True,
                            'require_user_input': False,
                            'content': last_message.content
                        }
            
            return {
                'is_task_complete': False,
                'require_user_input': True,
                'content': 'Unable to complete evaluation'
            }
            
        except Exception as e:
            return {
                'is_task_complete': False,
                'require_user_input': True,
                'content': f'Error during evaluation: {str(e)}'
            }
    
    def _parse_agent_response(self, response: Dict[str, Any]) -> JudgeOutput:
        """Parse the agent response into a structured JudgeOutput."""
        try:
            content = response.get('content', '')
            
            # Extract result (PASS/FAIL)
            result = "FAIL"  # Default to FAIL for safety
            if "PASS" in content.upper():
                result = "PASS"
            
            # Extract confidence (look for numbers 1-10)
            confidence = 7  # Default confidence for LLM evaluation
            import re
            conf_match = re.search(r'confidence[:\s]*([1-9]|10)', content.lower())
            if conf_match:
                confidence = int(conf_match.group(1))
            
            # Extract reasoning and recommendations
            reasoning = content
            recommendations = ""
            
            if result == "FAIL":
                # Try to extract actionable recommendations
                if "should" in content.lower() or "need" in content.lower():
                    recommendations = "Review the issues mentioned in the reasoning and address them."
                else:
                    recommendations = "Improve accuracy, completeness, and relevance of the response."
            
            return JudgeOutput(
                result=result,
                reasoning=reasoning,
                confidence=confidence,
                recommendations=recommendations
            )
            
        except Exception as e:
            return JudgeOutput(
                result="FAIL",
                reasoning=f"Failed to parse evaluation: {str(e)}",
                confidence=1,
                recommendations="Please retry evaluation"
            )
    
    
    def _fallback_evaluation(self, user_query: str, agent_response: str, context: str = "") -> JudgeOutput:
        """
        Enhanced fallback evaluation using G-EVAL structured scoring when LLM is not available.
        Implements rule-based approach with the same 4-dimension scoring as G-EVAL.
        """
        try:
            # Basic relevance analysis without using tool
            query_words = set(word.lower().strip('.,?!') for word in user_query.split() if len(word) > 2)
            response_words = set(word.lower().strip('.,?!') for word in agent_response.split())
            
            # Calculate G-EVAL style scores (1-5 scale)
            
            # Accuracy Score - check for factual correctness
            accuracy_score = 4  # Default to good
            
            # Simple fact checking without tool invocation
            false_indicators = ["factually incorrect", "wrong", "false", "2+2=5", "earth is flat"]
            if any(indicator in agent_response.lower() for indicator in false_indicators):
                accuracy_score = 1
            
            # Check for common knowledge facts
            if "capital of france" in user_query.lower():
                if "london" in agent_response.lower() and "paris" not in agent_response.lower():
                    accuracy_score = 1  # Wrong answer
                elif "paris" in agent_response.lower():
                    accuracy_score = 5  # Correct answer
                    
            # Completeness Score - based on response depth and coverage
            word_count = len(agent_response.split())
            if word_count < 10:
                completeness_score = 1  # Very incomplete
            elif word_count < 30:
                completeness_score = 2  # Brief but some content
            elif word_count < 50:
                completeness_score = 3  # Adequate
            elif word_count < 150:
                completeness_score = 4  # Good coverage
            else:
                completeness_score = 5  # Comprehensive
                
            # Relevance Score - keyword overlap and topic alignment
            query_words = set(word.lower().strip('.,?!') for word in user_query.split() if len(word) > 2)
            response_words = set(word.lower().strip('.,?!') for word in agent_response.split())
            
            if query_words:
                overlap = len(query_words.intersection(response_words))
                relevance_ratio = overlap / len(query_words)
                relevance_score = max(1, min(5, int(relevance_ratio * 5) + 1))
            else:
                relevance_score = 3  # Default for empty query
                
            # Clarity Score - structure and readability
            has_structure = bool(re.search(r'[\u2022\u2023\u25E6\u2043\u2219]|^\s*[\-\*\+]|\d+\.', agent_response, re.MULTILINE))
            sentence_count = len(re.findall(r'[.!?]+', agent_response))
            avg_sentence_length = word_count / max(sentence_count, 1)
            
            clarity_score = 3  # Start with neutral
            if has_structure:
                clarity_score += 1  # Well structured
            if 10 <= avg_sentence_length <= 25:  # Optimal sentence length
                clarity_score += 1
            elif avg_sentence_length > 40:  # Too complex
                clarity_score -= 1
                
            clarity_score = max(1, min(5, clarity_score))
            
            # Calculate overall decision using G-EVAL decision rules
            avg_score = (accuracy_score + completeness_score + relevance_score + clarity_score) / 4
            result = "PASS" if avg_score >= 3.0 and accuracy_score >= 3 else "FAIL"
            
            # Calculate confidence based on score consistency
            scores = [accuracy_score, completeness_score, relevance_score, clarity_score]
            score_variance = sum(abs(score - avg_score) for score in scores) / 4
            confidence = max(1, min(10, int(8 - score_variance * 2)))
            
            # Generate Chain-of-Thought reasoning
            reasoning = f"""Structured evaluation completed using G-EVAL methodology:

**Analysis Process:**
- Response length: {word_count} words across {sentence_count} sentences
- Keyword overlap: {len(query_words.intersection(response_words))}/{len(query_words)} relevant terms found
- Structure indicators: {'Present' if has_structure else 'Minimal'}
- Accuracy assessment: {'High confidence' if accuracy_score >= 4 else 'Issues detected' if accuracy_score <= 2 else 'Generally acceptable'}

**Quality Metrics:**
- Average sentence length: {avg_sentence_length:.1f} words
- Relevance ratio: {(len(query_words.intersection(response_words)) / len(query_words) * 100) if query_words else 0:.1f}%
- Structure quality: {'Well organized' if has_structure else 'Basic formatting'}
"""
            
            # Generate recommendations for FAIL cases
            recommendations = ""
            if result == "FAIL":
                issues = []
                if accuracy_score < 3:
                    issues.append("verify and correct factual accuracy")
                if completeness_score < 3:
                    issues.append("provide more comprehensive coverage of the topic")
                if relevance_score < 3:
                    issues.append("better address the specific query asked")
                if clarity_score < 3:
                    issues.append("improve clarity and structure of the response")
                
                recommendations = f"Improvements needed: {', '.join(issues)}"
            
            return JudgeOutput(
                result=result,
                reasoning=reasoning,
                confidence=confidence,
                accuracy_score=accuracy_score,
                completeness_score=completeness_score,
                relevance_score=relevance_score,
                clarity_score=clarity_score,
                recommendations=recommendations
            )
            
        except Exception as e:
            return JudgeOutput(
                result="FAIL",
                reasoning=f"Fallback evaluation failed: {str(e)}",
                confidence=1,
                accuracy_score=1,
                completeness_score=1,
                relevance_score=1,
                clarity_score=1,
                recommendations="Please retry with proper system configuration"
            )

    def _basic_evaluation(self, user_query: str, agent_response: str) -> JudgeOutput:
        """Enhanced basic evaluation using our judge logic."""
        try:
            input_data = {
                "query": user_query,
                "answer": agent_response
            }
            
            # Use our judge logic
            judge_result = judge_agent_logic(input_data)
            
            if judge_result.startswith("PASS"):
                return JudgeOutput(
                    result="PASS",
                    reasoning=judge_result,
                    confidence=6,
                    recommendations=""
                )
            else:
                return JudgeOutput(
                    result="FAIL",
                    reasoning=judge_result,
                    confidence=7,
                    recommendations="Address the issues mentioned in the reasoning"
                )
                
        except Exception as e:
            return JudgeOutput(
                result="FAIL",
                reasoning=f"Basic evaluation failed: {str(e)}",
                confidence=1,
                recommendations="Please retry with proper agent setup"
            )
    
    def get_agent_response(self, user_input: str, conversation_id: str = "default") -> Dict[str, Any]:
        """
        Main interface method for A2A integration using G-EVAL methodology.
        Expects input in format: "USER_QUERY|||AGENT_RESPONSE"
        """
        try:
            # Parse input format
            if "|||" in user_input:
                parts = user_input.split("|||", 1)
                user_query = parts[0].strip()
                agent_response = parts[1].strip()
            else:
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': 'Invalid input format. Please use: USER_QUERY|||AGENT_RESPONSE'
                }
            
            # Evaluate using G-EVAL methodology
            evaluation = self.evaluate(user_query, agent_response)
            
            # Format response following G-EVAL structured approach
            avg_score = (evaluation.accuracy_score + evaluation.completeness_score + 
                        evaluation.relevance_score + evaluation.clarity_score) / 4
            
            response_content = f"""## EVALUATION RESULT: {evaluation.result}

### Chain-of-Thought Analysis:
{evaluation.reasoning}

### G-EVAL Structured Scoring:
- **Accuracy:** {evaluation.accuracy_score}/5 - Factual correctness and truthfulness
- **Completeness:** {evaluation.completeness_score}/5 - How fully the response addresses the query
- **Relevance:** {evaluation.relevance_score}/5 - How well the response stays on topic
- **Clarity:** {evaluation.clarity_score}/5 - How clear and understandable the response is

**Average Score:** {avg_score:.1f}/5.0
**Confidence Level:** {evaluation.confidence}/10

{("### Recommendations for Improvement:" + chr(10) + evaluation.recommendations) if evaluation.recommendations else ("### Assessment:" + chr(10) + "Response meets quality standards across all evaluation dimensions.")}

---
*Evaluation completed using LLM-as-a-Judge methodology with G-EVAL structured scoring*
"""
            
            return {
                'is_task_complete': True,
                'require_user_input': False,
                'content': response_content.strip()
            }
            
        except Exception as e:
            return {
                'is_task_complete': False,
                'require_user_input': True,
                'content': f'Evaluation error: {str(e)}'
            }
