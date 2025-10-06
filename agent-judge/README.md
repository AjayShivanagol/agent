# Agent Judge

A specialized AI agent designed to evaluate the accuracy, completeness, and quality of AI agent responses. The Agent Judge acts as a quality control layer to ensure agent outputs meet high standards before being delivered to users.

## Overview

The Agent Judge system provides:
- **Response Evaluation**: Comprehensive assessment of agent responses against user queries
- **Quality Metrics**: Structured evaluation including accuracy, completeness, relevance, clarity, and safety
- **Pass/Fail Decisions**: Clear judgments with detailed reasoning
- **Fact Checking**: Tools to verify factual claims in responses
- **Quality Assessment**: Analysis of response structure, specificity, and comprehensiveness

## Architecture

The Agent Judge follows the same architectural pattern as other agents in the system:

```
agent-judge/
├── agent_judge/
│   ├── __init__.py
│   ├── __main__.py          # Server startup and configuration
│   ├── judge.py             # Core Agent Judge implementation
│   ├── agent_executor.py    # A2A integration layer
│   ├── logger_config.py     # Logging configuration
│   └── system_instructions.txt  # System prompt and instructions
├── tests/
│   └── test_judge.py        # Unit tests
├── requirements.txt         # Dependencies
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## 🏗️ Design Decisions

### Why No Streaming?
Unlike the CSC Agent which uses streaming for long-running database queries and multi-step workflows, the Agent Judge is designed for **fast, synchronous evaluation**:

- **Quick Response Time**: Evaluations typically complete in 1-3 seconds
- **Single-Step Process**: Input → Evaluate → Return (no complex tool chains)
- **Integration Context**: Usually called by other agents, not directly by end users
- **Simplicity**: Fewer failure points and cleaner integration patterns

### Architecture Philosophy
- **Fast & Reliable**: Optimized for quick, consistent evaluation
- **Integration-First**: Designed primarily for agent-to-agent communication
- **Quality Focus**: Emphasis on evaluation accuracy over real-time feedback
- **Minimal Complexity**: Simple, robust implementation

## Key Features

### 1. Comprehensive Evaluation Framework
- **Accuracy**: Factual correctness verification
- **Completeness**: Full query coverage assessment
- **Relevance**: Response-to-query alignment
- **Clarity**: Communication effectiveness
- **Safety**: Harm prevention and appropriateness

### 2. Advanced Tools
- **Fact Checking Tool**: Verifies claims against knowledge sources
- **Quality Assessment Tool**: Analyzes response structure and metrics
- **Chain-of-Thought Reasoning**: Transparent evaluation process

### 3. Structured Output
```json
{
  "result": "PASS|FAIL",
  "reasoning": "Detailed explanation...",
  "confidence": 8,
  "recommendations": "Specific improvement suggestions..."
}
```

## Usage

### As a Standalone Service
```bash
cd agent-judge
python -m agent_judge --host localhost --port 10001
```

### Integration Format
Send evaluation requests in the format:
```
USER_QUERY|||AGENT_RESPONSE
```

Example:
```
What is the capital of France?|||The capital of France is Paris, located in the north-central part of the country.
```

### Environment Configuration
```bash
# For Google Gemini
MODEL_SOURCE=google
GOOGLE_API_KEY=your_api_key

# For Azure OpenAI
MODEL_SOURCE=azure
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
```

## Agent Skills

The Agent Judge exposes the following skills:

1. **Agent Response Evaluation** (`evaluate_agent_response`)
   - Primary evaluation functionality
   - Comprehensive quality assessment
   - Pass/fail decision with reasoning

2. **Fact Checking** (`fact_check_claims`)
   - Verify factual claims
   - Cross-reference with knowledge sources
   - Confidence scoring

3. **Quality Assessment** (`assess_response_quality`)
   - Structural analysis
   - Relevance scoring
   - Completeness evaluation

## Integration with Host Agents

The Agent Judge is designed to be integrated into the agent workflow:

1. **Host Agent receives user query**
2. **Host Agent generates response**
3. **Host Agent sends query + response to Agent Judge**
4. **Agent Judge evaluates and returns PASS/FAIL**
5. **If PASS**: Host Agent sends response to user
6. **If FAIL**: Host Agent retries or refines response

## Example Workflow

```python
# In host agent system prompt:
"""
Before sending any response to the user, you must:
1. Generate your response
2. Send both the user query and your response to the Agent Judge
3. Wait for evaluation result
4. If PASS: Send response to user
5. If FAIL: Refine your response based on recommendations and retry
"""
```

## Testing

Run the test suite:
```bash
cd agent-judge
pytest tests/
```

## Development

### Adding New Evaluation Criteria
1. Modify `system_instructions.txt` to include new criteria
2. Add corresponding tools in `judge.py` if needed
3. Update the evaluation logic in the `evaluate` method
4. Add tests for the new criteria

### Custom Fact-Checking Sources
Extend the `fact_check_tool` to integrate with:
- External APIs
- Knowledge databases
- Domain-specific sources

## Deployment

The Agent Judge can be deployed alongside other agents and integrated into the agentic UI system for comprehensive response quality control.

## Performance Considerations

- **Evaluation Speed**: Optimized for quick evaluation cycles
- **Accuracy**: High-precision evaluation with confidence scoring
- **Scalability**: Stateless design for horizontal scaling
- **Resource Usage**: Efficient tool usage to minimize API calls

## Future Enhancements

- Domain-specific evaluation models
- Multi-language support
- Advanced fact-checking integration
- Performance analytics and metrics
- Custom evaluation criteria configuration

## Features
- Evaluates answers for factual correctness and completeness
- Returns pass/fail with reasoning
- Designed for easy integration with other agents

## Getting Started
1. Install dependencies: `pip install -r requirements.txt`
2. Run tests: `pytest`
3. Integrate `AgentJudge` into your agent workflow

## Structure
- `agent_judge/`: Main module
- `tests/`: Unit tests
- `requirements.txt`: Dependencies

## License
MIT
