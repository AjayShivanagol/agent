import os
import sys
import types
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Provide lightweight stubs for optional Google ADK and GenAI dependencies so
# the HostAgent module can be imported without the full runtime environment.
google_pkg = sys.modules.setdefault('google', types.ModuleType('google'))

adk_pkg = types.ModuleType('google.adk')
sys.modules['google.adk'] = adk_pkg
adk_pkg.Agent = type('Agent', (), {})

agents_pkg = types.ModuleType('google.adk.agents')
sys.modules['google.adk.agents'] = agents_pkg

callback_pkg = types.ModuleType('google.adk.agents.callback_context')
callback_pkg.CallbackContext = type('CallbackContext', (), {'state': {}})
sys.modules['google.adk.agents.callback_context'] = callback_pkg

readonly_pkg = types.ModuleType('google.adk.agents.readonly_context')
readonly_pkg.ReadonlyContext = type('ReadonlyContext', (), {'state': {}})
sys.modules['google.adk.agents.readonly_context'] = readonly_pkg

tools_pkg = types.ModuleType('google.adk.tools')
sys.modules['google.adk.tools'] = tools_pkg

tool_context_pkg = types.ModuleType('google.adk.tools.tool_context')
tool_context_pkg.ToolContext = type('ToolContext', (), {'state': {}, 'actions': type('Actions', (), {'skip_summarization': False, 'escalate': False})()})
sys.modules['google.adk.tools.tool_context'] = tool_context_pkg

genai_pkg = types.ModuleType('google.genai')
sys.modules['google.genai'] = genai_pkg
genai_types_pkg = types.ModuleType('google.genai.types')
genai_types_pkg.Part = type('Part', (), {'from_text': staticmethod(lambda text: None)})
genai_types_pkg.Blob = type('Blob', (), {})
sys.modules['google.genai.types'] = genai_types_pkg
genai_pkg.types = genai_types_pkg

from hosts.multiagent.host_agent import HostAgent


class HostAgentValidationTest(unittest.TestCase):
    """Unit tests for HostAgent validation parsing helpers."""

    def test_parse_validation_response_pass(self):
        evaluation = (
            "## EVALUATION RESULT: PASS\n"
            "### Chain-of-Thought Analysis:\nAll good.\n"
            "### G-EVAL Structured Scoring:\n- Accuracy: 5/5\n"
            "Confidence Level: 8/10\n"
        )
        result = HostAgent._parse_validation_response(evaluation)
        self.assertTrue(result.passed)
        self.assertEqual(result.confidence, 8)
        self.assertEqual(result.feedback, '')

    def test_parse_validation_response_fail_with_recommendations(self):
        evaluation = (
            "## EVALUATION RESULT: FAIL\n"
            "### Recommendations for Improvement:\nProvide more pricing details.\n"
        )
        result = HostAgent._parse_validation_response(evaluation)
        self.assertFalse(result.passed)
        self.assertIn('Provide more pricing details', result.feedback)

    def test_parse_validation_response_json_payload(self):
        evaluation = (
            '{"result": "FAIL", "recommendations": "Double-check costs", "confidence": 4}'
        )
        result = HostAgent._parse_validation_response(evaluation)
        self.assertFalse(result.passed)
        self.assertEqual(result.confidence, 4)
        self.assertEqual(result.feedback, 'Double-check costs')

    def test_evaluation_indicates_judge_unavailable(self):
        parts = ['Agent Agent Judge returned an error: HTTP Error 503']
        self.assertTrue(
            HostAgent._evaluation_indicates_judge_unavailable(parts, 'Agent Judge')
        )

        self.assertFalse(
            HostAgent._evaluation_indicates_judge_unavailable(
                ['✅ Agent Judge validated this response.'], 'Agent Judge'
            )
        )


if __name__ == '__main__':
    unittest.main()
