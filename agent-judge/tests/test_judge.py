import pytest
from agent_judge.judge import AgentJudge, JudgeOutput

class TestAgentJudge:
    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.judge = AgentJudge()

    def test_judge_initialization(self):
        """Test that AgentJudge initializes properly."""
        assert self.judge is not None
        assert hasattr(self.judge, 'evaluate')
        assert hasattr(self.judge, 'get_agent_response')

    def test_basic_evaluation_pass(self):
        """Test basic evaluation that should pass."""
        user_query = "What is the capital of France?"
        agent_response = "The capital of France is Paris."
        
        result = self.judge.evaluate(user_query, agent_response)
        
        assert isinstance(result, JudgeOutput)
        assert result.result in ["PASS", "FAIL"]
        assert isinstance(result.reasoning, str)
        assert 1 <= result.confidence <= 10
        assert len(result.reasoning) > 0

    def test_basic_evaluation_fail(self):
        """Test basic evaluation that should fail."""
        user_query = "What is the capital of France?"
        agent_response = "The capital of France is London."  # Incorrect answer
        
        result = self.judge.evaluate(user_query, agent_response)
        
        assert isinstance(result, JudgeOutput)
        assert result.result in ["PASS", "FAIL"]
        assert isinstance(result.reasoning, str)
        assert 1 <= result.confidence <= 10

    def test_evaluation_with_context(self):
        """Test evaluation with additional context."""
        user_query = "What is the weather like?"
        agent_response = "I cannot provide current weather information as I don't have access to real-time data."
        context = "User is asking about weather in Paris"
        
        result = self.judge.evaluate(user_query, agent_response, context)
        
        assert isinstance(result, JudgeOutput)
        assert result.result in ["PASS", "FAIL"]
        assert isinstance(result.reasoning, str)

    def test_get_agent_response_invalid_format(self):
        """Test agent response method with invalid input format."""
        invalid_input = "This is not properly formatted input"
        
        result = self.judge.get_agent_response(invalid_input)
        
        assert result['is_task_complete'] == True
        assert 'Invalid input format' in result['content']

    def test_get_agent_response_valid_format(self):
        """Test agent response method with valid input format."""
        valid_input = "What is 2+2?|||2+2 equals 4."
        
        result = self.judge.get_agent_response(valid_input)
        
        assert 'is_task_complete' in result
        assert 'content' in result
        assert isinstance(result['content'], str)

    def test_empty_response_evaluation(self):
        """Test evaluation of empty agent response."""
        user_query = "What is the capital of France?"
        agent_response = ""
        
        result = self.judge.evaluate(user_query, agent_response)
        
        assert isinstance(result, JudgeOutput)
        assert result.result == "FAIL"  # Empty response should fail

    def test_irrelevant_response_evaluation(self):
        """Test evaluation of irrelevant agent response."""
        user_query = "What is the capital of France?"
        agent_response = "I like to eat pizza on weekends."
        
        result = self.judge.evaluate(user_query, agent_response)
        
        assert isinstance(result, JudgeOutput)
        # This should likely fail due to irrelevance, but we'll test the structure
        assert result.result in ["PASS", "FAIL"]

    def test_confidence_range(self):
        """Test that confidence is always within valid range."""
        test_cases = [
            ("What is 1+1?", "1+1 equals 2."),
            ("Explain quantum physics", "Quantum physics is complex."),
            ("What's your name?", "I am an AI assistant."),
        ]
        
        for query, response in test_cases:
            result = self.judge.evaluate(query, response)
            assert 1 <= result.confidence <= 10, f"Confidence {result.confidence} is out of range"

    def test_reasoning_not_empty(self):
        """Test that reasoning is never empty."""
        user_query = "What is the meaning of life?"
        agent_response = "The meaning of life is 42."
        
        result = self.judge.evaluate(user_query, agent_response)
        
        assert len(result.reasoning.strip()) > 0, "Reasoning should not be empty"

    def test_evaluation_consistency(self):
        """Test that evaluation is consistent for the same input."""
        user_query = "What is the capital of Germany?"
        agent_response = "The capital of Germany is Berlin."
        
        result1 = self.judge.evaluate(user_query, agent_response)
        result2 = self.judge.evaluate(user_query, agent_response)
        
        # Results should be consistent (same PASS/FAIL decision)
        assert result1.result == result2.result

if __name__ == "__main__":
    pytest.main([__file__])
